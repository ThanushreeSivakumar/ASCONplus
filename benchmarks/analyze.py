#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py — Benchmark Analysis & Statistical Aggregation.

Uses benchmarks/data_source.py to load standardized Measured (Pi Zero W) datasets,
computes summary statistics (mean, std, p95, p99 in microseconds), determines
overhead comparisons, and generates publication-quality figures.

Produces:
    results/processed/summary.csv
    results/processed/summary.md
    results/figures/handshake_time.png
    results/figures/encrypt_decrypt_time.png
    results/figures/memory_rss_delta.png

Presentation Rule:
    All tables and figures are consistently titled and tagged:
    Measured (Pi Zero W).
"""

from __future__ import annotations

import os
import sys
import warnings

try:
    import pandas as pd
except ImportError:
    sys.exit("ERROR: pandas is required. pip install pandas")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    warnings.warn("matplotlib not installed — skipping plots")

import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

from benchmarks.data_source import (
    load_crypto,
    load_memory,
    load_e2e,
    get_data_label,
)

PROC = os.path.join(BASE, "results", "processed")
FIGS = os.path.join(BASE, "results", "figures")
DATA_LABEL = get_data_label()


def _stats_us(series: pd.Series) -> dict:
    """Compute stats from a Series of nanosecond values → microseconds."""
    us = series / 1000.0
    return {
        "n": int(len(us)),
        "mean_us": float(us.mean()),
        "std_us": float(us.std()) if len(us) > 1 else 0.0,
        "p95_us": float(us.quantile(0.95)),
        "p99_us": float(us.quantile(0.99)),
    }


# ── Crypto Analysis ──────────────────────────────────────────────────────────

def analyze_crypto(band: str = "mid") -> pd.DataFrame:
    """Analyze cryptographic operations for the specified band."""
    df = load_crypto(band=band)
    groups = df.groupby(["method", "op", "side", "payload_len"])
    rows = []
    for (method, op, side, plen), grp in groups:
        s = _stats_us(grp["ns"])
        rows.append({
            "method": method,
            "op": op,
            "side": side,
            "payload_len": int(plen),
            "scenario": band,
            **s,
        })
    return pd.DataFrame(rows)


def analyze_crypto_sensitivity() -> pd.DataFrame:
    """Analyze crypto across low, mid, and high sensitivity scenarios."""
    dfs = []
    for band in ["low", "mid", "high"]:
        df_band = analyze_crypto(band=band)
        dfs.append(df_band)
    return pd.concat(dfs, ignore_index=True)


# ── Memory Analysis ──────────────────────────────────────────────────────────

def analyze_memory() -> pd.DataFrame:
    """Analyze memory RSS measurements (unscaled memory proxy)."""
    df = load_memory()
    df["rss_delta_kb"] = df["rss_after_kb"] - df["rss_before_kb"]
    groups = df.groupby("method")
    rows = []
    for method, grp in groups:
        rows.append({
            "method": method,
            "n": int(len(grp)),
            "mean_rss_delta_kb": float(grp["rss_delta_kb"].mean()),
            "std_rss_delta_kb": float(grp["rss_delta_kb"].std()) if len(grp) > 1 else 0.0,
            "mean_hwm_kb": float(grp["hwm_kb"].mean()),
            "std_hwm_kb": float(grp["hwm_kb"].std()) if len(grp) > 1 else 0.0,
        })
    return pd.DataFrame(rows)


# ── E2E Analysis ─────────────────────────────────────────────────────────────

def analyze_e2e(band: str = "mid") -> pd.DataFrame:
    """Analyze end-to-end handshake latency."""
    df = load_e2e(band=band)
    groups = df.groupby("method")
    rows = []
    for method, grp in groups:
        s = _stats_us(grp["handshake_ns"])
        rows.append({
            "method": method,
            "scenario": band,
            **s,
        })
    return pd.DataFrame(rows)


# ── Overhead Calculation ─────────────────────────────────────────────────────

def compute_overhead_comparisons(crypto_df: pd.DataFrame, e2e_df: pd.DataFrame) -> dict:
    """Calculate absolute and percentage overhead of ECDH+ASCON over baseline."""
    comparisons = {}

    # 1. Crypto Handshake (both sides, mid scenario)
    hs = crypto_df[
        (crypto_df["op"] == "handshake")
        & (crypto_df["side"] == "both")
        & (crypto_df["scenario"] == "mid")
    ]
    base_hs = hs[hs["method"] == "baseline"]
    ecdh_hs = hs[hs["method"] == "ecdh_ascon"]

    if not base_hs.empty and not ecdh_hs.empty:
        b_mean = base_hs["mean_us"].values[0]
        e_mean = ecdh_hs["mean_us"].values[0]
        abs_ovh = e_mean - b_mean
        pct_ovh = ((e_mean - b_mean) / b_mean) * 100.0 if b_mean > 0 else 0.0
        comparisons["crypto_handshake"] = {
            "baseline_mean_us": b_mean,
            "ecdh_mean_us": e_mean,
            "abs_overhead_us": abs_ovh,
            "pct_overhead": pct_ovh,
        }

    # 2. E2E Handshake (mid scenario)
    e2e_mid = e2e_df[e2e_df["scenario"] == "mid"]
    base_e2e = e2e_mid[e2e_mid["method"] == "baseline"]
    ecdh_e2e = e2e_mid[e2e_mid["method"] == "ecdh_ascon"]

    if not base_e2e.empty and not ecdh_e2e.empty:
        b_e2e = base_e2e["mean_us"].values[0]
        e_e2e = ecdh_e2e["mean_us"].values[0]
        abs_e2e = e_e2e - b_e2e
        pct_e2e = ((e_e2e - b_e2e) / b_e2e) * 100.0 if b_e2e > 0 else 0.0
        comparisons["e2e_handshake"] = {
            "baseline_mean_us": b_e2e,
            "ecdh_mean_us": e_e2e,
            "abs_overhead_us": abs_e2e,
            "pct_overhead": pct_e2e,
        }

    # 3. Encrypt / Decrypt comparisons per payload size (16, 64, 128, 256)
    ed_comps = []
    ed_sub = crypto_df[
        (crypto_df["op"].isin(["encrypt", "decrypt"]))
        & (crypto_df["scenario"] == "mid")
    ]
    for op in ["encrypt", "decrypt"]:
        for plen in [16, 64, 128, 256]:
            b_row = ed_sub[
                (ed_sub["op"] == op)
                & (ed_sub["payload_len"] == plen)
                & (ed_sub["method"] == "baseline")
            ]
            e_row = ed_sub[
                (ed_sub["op"] == op)
                & (ed_sub["payload_len"] == plen)
                & (ed_sub["method"] == "ecdh_ascon")
            ]
            if not b_row.empty and not e_row.empty:
                b_m = b_row["mean_us"].values[0]
                e_m = e_row["mean_us"].values[0]
                diff = e_m - b_m
                pct = ((e_m - b_m) / b_m) * 100.0 if b_m > 0 else 0.0
                ed_comps.append({
                    "op": op,
                    "payload_len": plen,
                    "baseline_mean_us": b_m,
                    "ecdh_mean_us": e_m,
                    "abs_overhead_us": diff,
                    "pct_overhead": pct,
                })
    comparisons["encrypt_decrypt"] = ed_comps

    return comparisons


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot_handshake(crypto_df: pd.DataFrame, e2e_df: pd.DataFrame) -> None:
    """Bar chart: Baseline vs ECDH+ASCON handshake time."""
    if not HAS_MPL:
        return
    hs = crypto_df[
        (crypto_df["op"] == "handshake")
        & (crypto_df["side"] == "both")
        & (crypto_df["scenario"] == "mid")
    ]
    if hs.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    methods = hs["method"].tolist()
    labels = ["Baseline (Plaintext Key)", "ECDH + ASCON"]
    means = hs["mean_us"].tolist()
    stds = hs["std_us"].tolist()

    colors = ["#388E3C", "#1976D2"]
    bars = ax.bar(
        labels,
        means,
        yerr=stds,
        capsize=6,
        color=colors[:len(methods)],
        edgecolor="#333333",
        linewidth=1.0,
        width=0.55,
    )
    ax.set_ylabel("Latency (µs)", fontsize=11)
    ax.set_title(f"Handshake Latency: Baseline vs ECDH+ASCON\n[{DATA_LABEL}]", fontsize=12, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, m in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(means) * 0.02),
            f"{m:,.1f} µs",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    os.makedirs(FIGS, exist_ok=True)
    out_path = os.path.join(FIGS, "handshake_time.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> Generated: {out_path}")


def plot_encrypt_decrypt(crypto_df: pd.DataFrame) -> None:
    """Grouped bar chart: Encrypt and Decrypt latencies by payload size."""
    if not HAS_MPL:
        return
    ed = crypto_df[
        (crypto_df["op"].isin(["encrypt", "decrypt"]))
        & (crypto_df["scenario"] == "mid")
    ]
    if ed.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True, dpi=150)

    for ax, op in zip(axes, ["encrypt", "decrypt"]):
        sub = ed[ed["op"] == op]
        payload_lens = sorted(sub["payload_len"].unique())
        x = np.arange(len(payload_lens))
        width = 0.35

        for i, (method, label, col) in enumerate([
            ("baseline", "Baseline", "#388E3C"),
            ("ecdh_ascon", "ECDH + ASCON", "#1976D2"),
        ]):
            grp = sub[sub["method"] == method].set_index("payload_len")
            means = [grp.loc[p, "mean_us"] if p in grp.index else 0 for p in payload_lens]
            stds = [grp.loc[p, "std_us"] if p in grp.index else 0 for p in payload_lens]
            ax.bar(
                x + (i - 0.5) * width,
                means,
                width,
                yerr=stds,
                capsize=4,
                label=label,
                color=col,
                edgecolor="#333333",
                linewidth=0.8,
            )

        ax.set_xlabel("Payload Size (bytes)", fontsize=11)
        ax.set_ylabel("Latency (µs)", fontsize=11)
        ax.set_title(f"{op.title()} Latency", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels([str(p) for p in payload_lens])
        ax.legend(frameon=True)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.suptitle(f"ASCON-128 Encrypt & Decrypt Latency by Payload Size\n[{DATA_LABEL}]", fontsize=13)
    fig.tight_layout()
    os.makedirs(FIGS, exist_ok=True)
    out_path = os.path.join(FIGS, "encrypt_decrypt_time.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> Generated: {out_path}")


def plot_memory(mem_df: pd.DataFrame) -> None:
    """Bar chart: RSS Delta memory usage."""
    if not HAS_MPL or mem_df is None or mem_df.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    methods = mem_df["method"].tolist()
    labels = ["Baseline (Plaintext Key)", "ECDH + ASCON"]
    means = mem_df["mean_rss_delta_kb"].tolist()
    stds = mem_df["std_rss_delta_kb"].tolist()

    colors = ["#388E3C", "#1976D2"]
    bars = ax.bar(
        labels[:len(methods)],
        means,
        yerr=stds,
        capsize=6,
        color=colors[:len(methods)],
        edgecolor="#333333",
        linewidth=1.0,
        width=0.55,
    )
    ax.set_ylabel("RSS Delta (KB)", fontsize=11)
    ax.set_title(f"Memory: RSS Delta (Baseline vs ECDH+ASCON)\n[{DATA_LABEL}]", fontsize=12, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, m in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(means) * 0.02 if max(means) > 0 else 50),
            f"{m:,.1f} KB",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    os.makedirs(FIGS, exist_ok=True)
    out_path = os.path.join(FIGS, "memory_rss_delta.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> Generated: {out_path}")


# ── Markdown Report Generation ───────────────────────────────────────────────

def write_summary(
    crypto_df: pd.DataFrame,
    mem_df: pd.DataFrame,
    e2e_df: pd.DataFrame,
    comparisons: dict,
) -> None:
    """Write summary.csv and summary.md."""
    os.makedirs(PROC, exist_ok=True)

    # 1. summary.csv
    all_frames = []
    if crypto_df is not None:
        c_copy = crypto_df.copy()
        c_copy["bench"] = "crypto"
        all_frames.append(c_copy)
    if mem_df is not None:
        m_copy = mem_df.copy()
        m_copy["bench"] = "memory"
        all_frames.append(m_copy)
    if e2e_df is not None:
        e_copy = e2e_df.copy()
        e_copy["bench"] = "e2e"
        all_frames.append(e_copy)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        csv_path = os.path.join(PROC, "summary.csv")
        combined.to_csv(csv_path, index=False)
        print(f"  -> Generated: {csv_path}")

    # 2. summary.md
    def _df_to_md(df: pd.DataFrame) -> str:
        try:
            return df.to_markdown(index=False)
        except Exception:
            cols = [str(c) for c in df.columns]
            res = ["| " + " | ".join(cols) + " |"]
            res.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for _, r in df.iterrows():
                res.append("| " + " | ".join(str(val) for val in r) + " |")
            return "\n".join(res)

    md_path = os.path.join(PROC, "summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Benchmark Statistical Summary — {DATA_LABEL}\n\n")
        f.write(
            f"All metrics below report **{DATA_LABEL}** performance across cryptographic operations, "
            f"end-to-end handshake latency, and memory utilization.\n\n"
        )

        # Overhead Comparison Section
        f.write("## 1. Baseline vs. ECDH+ASCON Overhead Comparison\n\n")
        f.write(
            "Overhead calculations:\n"
            "- **Absolute Overhead** = $\\text{ECDH Latency} - \\text{Baseline Latency}$\n"
            "- **Percentage Overhead** = $\\left(\\frac{\\text{ECDH Latency} - \\text{Baseline Latency}}{\\text{Baseline Latency}}\\right) \\times 100\\%$\n\n"
        )

        f.write("### Handshake Latency Overhead\n\n")
        hs_comp = comparisons.get("crypto_handshake", {})
        e2e_comp = comparisons.get("e2e_handshake", {})
        f.write(
            "| Evaluation Scope | Baseline Mean (µs) | ECDH+ASCON Mean (µs) | Absolute Overhead (µs) | Percentage Overhead (%) |\n"
            "| :--- | :---: | :---: | :---: | :---: |\n"
        )
        if hs_comp:
            f.write(
                f"| Crypto Handshake (Both Sides) | {hs_comp['baseline_mean_us']:,.1f} | "
                f"{hs_comp['ecdh_mean_us']:,.1f} | +{hs_comp['abs_overhead_us']:,.1f} | "
                f"+{hs_comp['pct_overhead']:,.1f}% |\n"
            )
        if e2e_comp:
            f.write(
                f"| End-to-End Handshake (TCP Loopback) | {e2e_comp['baseline_mean_us']:,.1f} | "
                f"{e2e_comp['ecdh_mean_us']:,.1f} | +{e2e_comp['abs_overhead_us']:,.1f} | "
                f"+{e2e_comp['pct_overhead']:,.1f}% |\n"
            )
        f.write("\n")

        # Encrypt / Decrypt Overhead
        f.write("### ASCON Encryption and Decryption Overhead\n\n")
        ed_comps = comparisons.get("encrypt_decrypt", [])
        if ed_comps:
            f.write(
                "| Operation | Payload Size (bytes) | Baseline Mean (µs) | ECDH+ASCON Mean (µs) | Absolute Overhead (µs) | Percentage Overhead (%) |\n"
                "| :--- | :---: | :---: | :---: | :---: | :---: |\n"
            )
            for r in ed_comps:
                f.write(
                    f"| {r['op'].title()} | {r['payload_len']} | {r['baseline_mean_us']:,.1f} | "
                    f"{r['ecdh_mean_us']:,.1f} | {r['abs_overhead_us']:+,.1f} | "
                    f"{r['pct_overhead']:+,.2f}% |\n"
                )
            f.write("\n")

        # Full Crypto Table (Mid Scenario)
        f.write("## 2. Cryptographic Latency (Primary Scenario: Mid)\n\n")
        crypto_mid = crypto_df[crypto_df["scenario"] == "mid"].copy()
        f.write(_df_to_md(crypto_mid))
        f.write("\n\n")

        # Sensitivity Scenarios (Low, Mid, High)
        f.write("## 3. Cryptographic Sensitivity Scenarios (Low, Mid, High)\n\n")
        f.write(_df_to_md(crypto_df))
        f.write("\n\n")

        # E2E Handshake
        f.write("## 4. End-to-End Handshake Latency\n\n")
        f.write(_df_to_md(e2e_df))
        f.write("\n\n")

        # Memory Usage
        f.write("## 5. Memory Usage\n\n")
        f.write(
            "> **Memory Methodology**: RSS measurements are treated as an unscaled memory proxy representing "
            "Python runtime heap allocation and library residency.\n\n"
        )
        f.write(_df_to_md(mem_df))
        f.write("\n\n")

        f.write(
            "> ASCON is pure Python (`ascon` package); absolute times reflect interpreted Python execution. "
            "Compare methods relative to each other.\n"
        )

    print(f"  -> Generated: {md_path}")


def main() -> None:
    print(f"=== ASCON+ Benchmark Analysis [{DATA_LABEL}] ===\n")

    crypto_df = analyze_crypto_sensitivity()
    mem_df = analyze_memory()
    e2e_df = analyze_e2e(band="mid")
    comparisons = compute_overhead_comparisons(crypto_df, e2e_df)

    write_summary(crypto_df, mem_df, e2e_df, comparisons)

    if HAS_MPL:
        plot_handshake(crypto_df, e2e_df)
        plot_encrypt_decrypt(crypto_df)
        plot_memory(mem_df)

    print("\nBenchmark analysis and figure generation complete.")


if __name__ == "__main__":
    main()
