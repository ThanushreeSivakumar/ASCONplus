#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway Queueing Model & Scalability Simulation (SimPy).
========================================================

Simulates IoT Gateway queueing behavior under Poisson traffic loads across:
  - Topologies: Star (central gateway) vs Hierarchical (k=4 secondary gateways)
  - Network sizes: N in {5, 10, 25, 50, 100}
  - Sensitivity multipliers: 1x, 10x, 50x (modeling resource-constrained edge hardware like Pi Zero W)
  - Replications: 30 independent runs per condition with 300s simulated duration

Service times are loaded directly from empirical benchmark CSVs:
  results/raw/crypto_*.csv (op=decrypt, method=ecdh_ascon, payload_len=64)
  Prefers is_pi=True rows if available, otherwise labels source "laptop".

Outputs:
  - results/raw/sim_<label>.csv
  - results/processed/sim_summary.md
  - results/figures/sim_p99_vs_N.png
  - results/figures/sim_utilization_vs_N.png
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import random
import statistics
import sys
from typing import Dict, List, Tuple

try:
    import simpy
except ImportError:
    sys.exit("ERROR: SimPy is required. Run: pip install simpy")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(BASE_DIR, "results", "raw")
PROC_DIR = os.path.join(BASE_DIR, "results", "processed")
FIGS_DIR = os.path.join(BASE_DIR, "results", "figures")

DEFAULT_MSG_INTERVAL = 5.0  # seconds between messages per node (lambda_node = 0.2 msg/s)
DEFAULT_SIM_DURATION = 300.0  # seconds of simulated time per replication
DEFAULT_REPLICATIONS = 30
DEFAULT_N_LIST = [5, 10, 25, 50, 100]
DEFAULT_MULTIPLIERS = [1, 10, 50]
DEFAULT_K_SECONDARY = 4


# ── Service Time Discovery ───────────────────────────────────────────────────

def get_service_time() -> Tuple[float, str]:
    """
    Load base decryption service time (seconds) from results/raw/crypto_*.csv.
    Filters: op=decrypt, method=ecdh_ascon, payload_len=64.
    Prefers is_pi=True rows if present; otherwise uses laptop data.
    """
    pattern = os.path.join(RAW_DIR, "crypto_*.csv")
    csv_files = glob.glob(pattern)

    pi_times_ns: List[float] = []
    laptop_times_ns: List[float] = []

    for fpath in csv_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (
                        row.get("op") == "decrypt"
                        and row.get("method") == "ecdh_ascon"
                        and str(row.get("payload_len")) == "64"
                    ):
                        ns = float(row["ns"])
                        is_pi_str = str(row.get("is_pi", "False")).strip().lower()
                        if is_pi_str == "true":
                            pi_times_ns.append(ns)
                        else:
                            laptop_times_ns.append(ns)
        except Exception as e:
            print(f"  [warn] Could not parse {fpath}: {e}")

    if pi_times_ns:
        mean_ns = statistics.mean(pi_times_ns)
        source = "pi"
    elif laptop_times_ns:
        mean_ns = statistics.mean(laptop_times_ns)
        source = "laptop"
    else:
        # Fallback if no crypto CSV exists yet: 0.27 ms (laptop baseline)
        mean_ns = 270000.0
        source = "laptop"

    service_time_s = mean_ns / 1_000_000_000.0
    return service_time_s, source


# ── Simulation Models ────────────────────────────────────────────────────────

def simulate_star(
    env: simpy.Environment,
    n_nodes: int,
    msg_interval: float,
    service_time_s: float,
    metrics: Dict,
) -> None:
    """Simulate Star Topology: N nodes -> 1 Central Gateway FIFO queue."""
    gateway = simpy.Resource(env, capacity=1)
    arrival_rate = n_nodes / msg_interval

    def message_generator():
        while True:
            yield env.timeout(random.expovariate(arrival_rate))
            arrival_time = env.now
            current_q = len(gateway.queue) + gateway.count
            if current_q > metrics["max_queue"]:
                metrics["max_queue"] = current_q
            env.process(process_message(arrival_time))

    def process_message(arrival_time: float):
        with gateway.request() as req:
            yield req
            metrics["busy_time"] += service_time_s
            yield env.timeout(service_time_s)
            latency = env.now - arrival_time
            metrics["latencies"].append(latency)

    env.process(message_generator())


def simulate_hierarchical(
    env: simpy.Environment,
    n_nodes: int,
    msg_interval: float,
    service_time_s: float,
    k_secondary: int,
    metrics: Dict,
) -> None:
    """
    Simulate Hierarchical Topology:
    N nodes partitioned across k secondary gateways -> 1 Central Gateway.
    Secondary gateways perform decryption (service_time_s).
    Central gateway performs root aggregation/routing (service_time_s * 0.1).
    """
    sec_gateways = [simpy.Resource(env, capacity=1) for _ in range(k_secondary)]
    central_gateway = simpy.Resource(env, capacity=1)
    central_service_s = service_time_s * 0.1

    nodes_per_sec = n_nodes / k_secondary
    arrival_rate_sec = nodes_per_sec / msg_interval

    def sec_message_generator(sec_gw: simpy.Resource):
        while True:
            yield env.timeout(random.expovariate(arrival_rate_sec))
            arrival_time = env.now
            current_q = len(sec_gw.queue) + sec_gw.count
            if current_q > metrics["max_queue"]:
                metrics["max_queue"] = current_q
            env.process(process_hierarchical_message(sec_gw, arrival_time))

    def process_hierarchical_message(sec_gw: simpy.Resource, arrival_time: float):
        # Stage 1: Secondary gateway decryption
        with sec_gw.request() as req1:
            yield req1
            metrics["busy_time_sec"] += service_time_s
            yield env.timeout(service_time_s)

        # Stage 2: Central gateway root processing
        with central_gateway.request() as req2:
            yield req2
            metrics["busy_time_root"] += central_service_s
            yield env.timeout(central_service_s)
            latency = env.now - arrival_time
            metrics["latencies"].append(latency)

    for gw in sec_gateways:
        env.process(sec_message_generator(gw))


def run_single_simulation(
    topology: str,
    n_nodes: int,
    service_time_s: float,
    sim_duration: float,
    seed: int,
    msg_interval: float = DEFAULT_MSG_INTERVAL,
    k_secondary: int = DEFAULT_K_SECONDARY,
) -> Dict[str, float]:
    """Execute one simulation replication and return performance metrics."""
    random.seed(seed)
    env = simpy.Environment()

    metrics = {
        "latencies": [],
        "max_queue": 0,
        "busy_time": 0.0,
        "busy_time_sec": 0.0,
        "busy_time_root": 0.0,
    }

    if topology == "star":
        simulate_star(env, n_nodes, msg_interval, service_time_s, metrics)
    elif topology == "hierarchical":
        simulate_hierarchical(env, n_nodes, msg_interval, service_time_s, k_secondary, metrics)
    else:
        raise ValueError(f"Unknown topology: {topology}")

    env.run(until=sim_duration)

    latencies_ms = [d * 1000.0 for d in metrics["latencies"]]
    count = len(latencies_ms)

    if count > 0:
        sorted_l = sorted(latencies_ms)
        mean_l = statistics.mean(latencies_ms)
        p95_l = sorted_l[int(count * 0.95)]
        p99_l = sorted_l[int(count * 0.99)]
    else:
        mean_l, p95_l, p99_l = 0.0, 0.0, 0.0

    if topology == "star":
        utilization = min(1.0, metrics["busy_time"] / sim_duration)
    else:
        # Utilization of the most loaded resource
        sec_util = (metrics["busy_time_sec"] / k_secondary) / sim_duration
        root_util = metrics["busy_time_root"] / sim_duration
        utilization = min(1.0, max(sec_util, root_util))

    throughput = count / sim_duration

    return {
        "utilization": utilization,
        "mean_latency_ms": mean_l,
        "p95_latency_ms": p95_l,
        "p99_latency_ms": p99_l,
        "max_queue": metrics["max_queue"],
        "throughput_msg_s": throughput,
        "messages_handled": count,
    }


# ── Experiment Runner ────────────────────────────────────────────────────────

def run_study(
    base_service_time_s: float,
    source: str,
    n_list: List[int],
    multipliers: List[int],
    replications: int,
    sim_duration: float,
) -> Tuple[str, str, Dict]:
    """Execute complete parameter sweep across topologies, N, and multipliers."""
    topologies = ["star", "hierarchical"]
    raw_records = []
    summary_data = {}

    print(f"Base service time: {base_service_time_s * 1000.0:.4f} ms (source: {source})")
    print(f"N list           : {n_list}")
    print(f"Multipliers      : {multipliers}")
    print(f"Replications     : {replications}")
    print(f"Duration         : {sim_duration}s per run")
    print("-" * 70)

    for top in topologies:
        for mult in multipliers:
            eff_service_s = base_service_time_s * mult
            for n in n_list:
                rep_metrics: Dict[str, List[float]] = {
                    "utilization": [],
                    "mean_latency_ms": [],
                    "p95_latency_ms": [],
                    "p99_latency_ms": [],
                    "max_queue": [],
                    "throughput_msg_s": [],
                    "messages_handled": [],
                }

                for rep in range(1, replications + 1):
                    seed = 1000 * mult + 100 * n + rep
                    res = run_single_simulation(
                        topology=top,
                        n_nodes=n,
                        service_time_s=eff_service_s,
                        sim_duration=sim_duration,
                        seed=seed,
                    )

                    raw_records.append({
                        "topology": top,
                        "N": n,
                        "multiplier": mult,
                        "replication": rep,
                        "service_time_ms": f"{eff_service_s * 1000.0:.4f}",
                        "utilization": f"{res['utilization']:.4f}",
                        "mean_latency_ms": f"{res['mean_latency_ms']:.4f}",
                        "p95_latency_ms": f"{res['p95_latency_ms']:.4f}",
                        "p99_latency_ms": f"{res['p99_latency_ms']:.4f}",
                        "max_queue": res["max_queue"],
                        "throughput_msg_s": f"{res['throughput_msg_s']:.4f}",
                        "messages_handled": res["messages_handled"],
                    })

                    for k in rep_metrics:
                        rep_metrics[k].append(res[k])

                # Compute aggregate stats
                key = (top, mult, n)
                summary_data[key] = {
                    "service_time_ms": eff_service_s * 1000.0,
                    "util_mean": statistics.mean(rep_metrics["utilization"]),
                    "util_std": statistics.stdev(rep_metrics["utilization"]) if replications > 1 else 0.0,
                    "lat_mean_mean": statistics.mean(rep_metrics["mean_latency_ms"]),
                    "lat_mean_std": statistics.stdev(rep_metrics["mean_latency_ms"]) if replications > 1 else 0.0,
                    "lat_p95_mean": statistics.mean(rep_metrics["p95_latency_ms"]),
                    "lat_p95_std": statistics.stdev(rep_metrics["p95_latency_ms"]) if replications > 1 else 0.0,
                    "lat_p99_mean": statistics.mean(rep_metrics["p99_latency_ms"]),
                    "lat_p99_std": statistics.stdev(rep_metrics["p99_latency_ms"]) if replications > 1 else 0.0,
                    "max_q_mean": statistics.mean(rep_metrics["max_queue"]),
                    "max_q_std": statistics.stdev(rep_metrics["max_queue"]) if replications > 1 else 0.0,
                    "tp_mean": statistics.mean(rep_metrics["throughput_msg_s"]),
                    "tp_std": statistics.stdev(rep_metrics["throughput_msg_s"]) if replications > 1 else 0.0,
                }

    # 1. Write CSV
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_csv_path = os.path.join(RAW_DIR, f"sim_{source}.csv")
    fieldnames = [
        "topology",
        "N",
        "multiplier",
        "replication",
        "service_time_ms",
        "utilization",
        "mean_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "max_queue",
        "throughput_msg_s",
        "messages_handled",
    ]
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"# SIMULATED; service time source: {source}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(raw_records)
    print(f"\n  [+] Saved raw simulation records: {raw_csv_path}")

    # 2. Write Markdown Summary Table
    os.makedirs(PROC_DIR, exist_ok=True)
    summary_md_path = os.path.join(PROC_DIR, "sim_summary.md")
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write(f"# SIMULATED; service time source: {source}\n\n")
        f.write(f"## Gateway Scalability Simulation Summary (30 Replications, 300s Duration)\n\n")
        f.write(
            f"- **Base Service Time**: {base_service_time_s * 1000.0:.4f} ms (per message decryption)\n"
            f"- **Service Time Source**: `{source}` (`results/raw/crypto_*.csv`, op=decrypt, method=ecdh_ascon, payload_len=64)\n"
            f"- **Sensors Interval**: {DEFAULT_MSG_INTERVAL} s/node ($\\lambda_{{\\text{{node}}}} = {1.0/DEFAULT_MSG_INTERVAL:.2f}$ msg/s)\n\n"
        )
        f.write("| Topology | Sensitivity | N | Service Time (ms) | Utilization | Mean Latency (ms) | p99 Latency (ms) | Max Queue | Throughput (msg/s) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")

        for (top, mult, n), d in sorted(summary_data.items()):
            f.write(
                f"| {top.capitalize()} | {mult}x | {n} | {d['service_time_ms']:.3f} | "
                f"{d['util_mean']:.3f} ± {d['util_std']:.3f} | "
                f"{d['lat_mean_mean']:.3f} ± {d['lat_mean_std']:.3f} | "
                f"{d['lat_p99_mean']:.3f} ± {d['lat_p99_std']:.3f} | "
                f"{d['max_q_mean']:.1f} ± {d['max_q_std']:.1f} | "
                f"{d['tp_mean']:.2f} ± {d['tp_std']:.2f} |\n"
            )

    print(f"  [+] Saved markdown summary: {summary_md_path}")

    # 3. Generate Visualizations
    if HAS_MPL:
        generate_plots(summary_data, base_service_time_s, source, n_list, multipliers)

    return raw_csv_path, summary_md_path, summary_data


# ── Plotting ─────────────────────────────────────────────────────────────────

def generate_plots(
    summary_data: Dict,
    base_service_time_s: float,
    source: str,
    n_list: List[int],
    multipliers: List[int],
) -> None:
    """Generate high-resolution p99 latency and utilization plots with saturation marks."""
    os.makedirs(FIGS_DIR, exist_ok=True)
    msg_rate = 1.0 / DEFAULT_MSG_INTERVAL

    # Colors and styles
    top_colors = {"star": "#D32F2F", "hierarchical": "#1976D2"}
    mult_styles = {1: "-", 10: "--", 50: ":"}

    # -------------------------------------------------------------
    # Plot 1: p99 Latency vs N
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)

    for top in ["star", "hierarchical"]:
        for mult in multipliers:
            xs = n_list
            ys = [summary_data[(top, mult, n)]["lat_p99_mean"] for n in xs]
            y_errs = [summary_data[(top, mult, n)]["lat_p99_std"] for n in xs]
            label = f"{top.capitalize()} ({mult}x)"
            ax.errorbar(
                xs,
                ys,
                yerr=y_errs,
                label=label,
                color=top_colors[top],
                linestyle=mult_styles[mult],
                marker="o" if top == "star" else "s",
                markersize=5,
                capsize=3,
                linewidth=1.8,
            )

    # Theoretical saturation N* = 1 / (msg_rate * service_time)
    for mult in multipliers:
        eff_s = base_service_time_s * mult
        n_star_star = 1.0 / (msg_rate * eff_s)
        if min(n_list) <= n_star_star <= max(n_list) * 1.5:
            ax.axvline(
                x=n_star_star,
                color="#616161",
                linestyle="dashdot",
                alpha=0.6,
                linewidth=1.2,
            )
            ax.text(
                n_star_star + 1,
                ax.get_ylim()[1] * 0.75,
                f"N* ({mult}x)={n_star_star:.0f}",
                rotation=90,
                fontsize=8,
                color="#424242",
            )

    ax.set_xlabel("Number of Sensor Nodes (N)", fontsize=11, fontweight="bold")
    ax.set_ylabel("p99 Queueing + Service Latency (ms)", fontsize=11, fontweight="bold")
    ax.set_title(
        f"SIMULATED: Gateway p99 Latency vs Network Size (N)\n"
        f"Source: {source} (Service Time = {base_service_time_s*1000:.3f} ms)",
        fontsize=12,
    )
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    fig.tight_layout()

    p99_fig_path = os.path.join(FIGS_DIR, "sim_p99_vs_N.png")
    fig.savefig(p99_fig_path, dpi=150)
    plt.close(fig)
    print(f"  [+] Saved plot: {p99_fig_path}")

    # -------------------------------------------------------------
    # Plot 2: Utilization vs N
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)

    for top in ["star", "hierarchical"]:
        for mult in multipliers:
            xs = n_list
            ys = [summary_data[(top, mult, n)]["util_mean"] for n in xs]
            y_errs = [summary_data[(top, mult, n)]["util_std"] for n in xs]
            label = f"{top.capitalize()} ({mult}x)"
            ax.errorbar(
                xs,
                ys,
                yerr=y_errs,
                label=label,
                color=top_colors[top],
                linestyle=mult_styles[mult],
                marker="o" if top == "star" else "^",
                markersize=5,
                capsize=3,
                linewidth=1.8,
            )

    # Theoretical saturation line at rho = 1.0
    ax.axhline(y=1.0, color="#B71C1C", linestyle="--", linewidth=1.5, label="Saturation (rho = 1.0)")

    ax.set_xlabel("Number of Sensor Nodes (N)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Gateway Server Utilization (rho)", fontsize=11, fontweight="bold")
    ax.set_ylim(-0.05, 1.15)
    ax.set_title(
        f"SIMULATED: Gateway Server Utilization vs Network Size (N)\n"
        f"Source: {source} (Service Time = {base_service_time_s*1000:.3f} ms)",
        fontsize=12,
    )
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    fig.tight_layout()

    util_fig_path = os.path.join(FIGS_DIR, "sim_utilization_vs_N.png")
    fig.savefig(util_fig_path, dpi=150)
    plt.close(fig)
    print(f"  [+] Saved plot: {util_fig_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SimPy Gateway Scalability Study")
    parser.add_argument("--replications", type=int, default=DEFAULT_REPLICATIONS, help="Replications per condition")
    parser.add_argument("--sim-duration", type=float, default=DEFAULT_SIM_DURATION, help="Simulated duration (s)")
    parser.add_argument("--n-list", nargs="+", type=int, default=DEFAULT_N_LIST, help="Node counts to evaluate")
    parser.add_argument("--multipliers", nargs="+", type=int, default=DEFAULT_MULTIPLIERS, help="Service time multipliers")
    args = parser.parse_args()

    print("=" * 70)
    print("ASCON+ GATEWAY QUEUEING & SCALABILITY STUDY (SimPy)")
    print("=" * 70)

    base_service_time_s, source = get_service_time()

    run_study(
        base_service_time_s=base_service_time_s,
        source=source,
        n_list=args.n_list,
        multipliers=args.multipliers,
        replications=args.replications,
        sim_duration=args.sim_duration,
    )

    print("\n" + "=" * 70)
    print("SIMULATION STUDY COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
