#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py — Aggregate raw benchmark CSVs, compute stats, generate plots.

Reads:
    results/raw/crypto_*.csv
    results/raw/memory_*.csv
    results/raw/e2e_*.csv

Produces:
    results/processed/summary.csv
    results/processed/summary.md
    results/figures/handshake_time.png
    results/figures/encrypt_decrypt_time.png
    results/figures/memory_rss_delta.png

Requires pandas + matplotlib (runs on laptop, not required on Pi).
"""

from __future__ import annotations

import glob
import os
import sys
import warnings

try:
    import pandas as pd
except ImportError:
    sys.exit("ERROR: pandas is required.  pip install pandas matplotlib")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    warnings.warn("matplotlib not installed — skipping plots")

import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(BASE, "results", "raw")
PROC = os.path.join(BASE, "results", "processed")
FIGS = os.path.join(BASE, "results", "figures")

SUMMARY_NOTE = (
    '\n> ASCON is pure Python (`ascon` package); absolute times are much '
    'slower than C implementations. Compare methods relative to each other.\n'
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_csvs(prefix: str) -> list[str]:
    pattern = os.path.join(RAW, f"{prefix}_*.csv")
    return sorted(glob.glob(pattern))


def _pi_warning(df: pd.DataFrame, label: str) -> None:
    if "is_pi" in df.columns:
        non_pi = df[df["is_pi"].astype(str).str.strip().str.lower() != "true"]
        if len(non_pi) > 0:
            print(f"  WARNING: {label} contains data NOT from a Raspberry Pi!")


def _stats_us(series: pd.Series) -> dict:
    """Compute stats from a Series of nanosecond values → microseconds."""
    us = series / 1000.0
    return {
        "n": len(us),
        "mean_us": us.mean(),
        "std_us": us.std(),
        "p95_us": us.quantile(0.95),
        "p99_us": us.quantile(0.99),
    }


# ── Crypto analysis ─────────────────────────────────────────────────────────

def analyze_crypto() -> pd.DataFrame | None:
    files = _find_csvs("crypto")
    if not files:
        print("  [skip] No crypto_*.csv found")
        return None
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    _pi_warning(df, "crypto")

    groups = df.groupby(["method", "op", "side", "payload_len"])
    rows = []
    for (method, op, side, plen), grp in groups:
        s = _stats_us(grp["ns"])
        rows.append({"method": method, "op": op, "side": side,
                      "payload_len": int(plen), **s})
    return pd.DataFrame(rows)


# ── Memory analysis ──────────────────────────────────────────────────────────

def analyze_memory() -> pd.DataFrame | None:
    files = _find_csvs("memory")
    if not files:
        print("  [skip] No memory_*.csv found")
        return None
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    _pi_warning(df, "memory")

    df["rss_delta_kb"] = df["rss_after_kb"] - df["rss_before_kb"]
    groups = df.groupby("method")
    rows = []
    for method, grp in groups:
        rows.append({
            "method": method,
            "n": len(grp),
            "mean_rss_delta_kb": grp["rss_delta_kb"].mean(),
            "std_rss_delta_kb": grp["rss_delta_kb"].std(),
            "mean_hwm_kb": grp["hwm_kb"].mean(),
            "std_hwm_kb": grp["hwm_kb"].std(),
        })
    return pd.DataFrame(rows)


# ── E2E analysis ─────────────────────────────────────────────────────────────

def analyze_e2e() -> pd.DataFrame | None:
    files = _find_csvs("e2e")
    if not files:
        print("  [skip] No e2e_*.csv found")
        return None
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    _pi_warning(df, "e2e")

    groups = df.groupby("method")
    rows = []
    for method, grp in groups:
        s = _stats_us(grp["handshake_ns"])
        rows.append({"method": method, **s})
    return pd.DataFrame(rows)


# ── Plots ────────────────────────────────────────────────────────────────────

def plot_handshake(crypto_df: pd.DataFrame, e2e_df: pd.DataFrame | None) -> None:
    """Bar chart: baseline vs ecdh_ascon handshake time."""
    if not HAS_MPL:
        return
    # Use crypto handshake (both sides) data
    hs = crypto_df[(crypto_df["op"] == "handshake") & (crypto_df["side"] == "both")]
    if hs.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    methods = hs["method"].tolist()
    means = hs["mean_us"].tolist()
    stds = hs["std_us"].tolist()

    colors = ["#42A5F5", "#EF5350"]
    bars = ax.bar(methods, means, yerr=stds, capsize=6,
                  color=colors[:len(methods)], edgecolor="white", linewidth=0.8)
    ax.set_ylabel("Time (µs)")
    ax.set_title("Handshake Latency: Baseline vs ECDH+ASCON")
    ax.grid(axis="y", alpha=0.3)

    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{m:.0f} us", ha="center", va="bottom", fontsize=9)

    os.makedirs(FIGS, exist_ok=True)
    fig.savefig(os.path.join(FIGS, "handshake_time.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {os.path.join(FIGS, 'handshake_time.png')}")


def plot_encrypt_decrypt(crypto_df: pd.DataFrame) -> None:
    """Grouped bar chart: encrypt/decrypt time by payload size."""
    if not HAS_MPL:
        return
    ed = crypto_df[crypto_df["op"].isin(["encrypt", "decrypt"])]
    if ed.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    for ax, op in zip(axes, ["encrypt", "decrypt"]):
        sub = ed[ed["op"] == op]
        methods = sub["method"].unique()
        payload_lens = sorted(sub["payload_len"].unique())
        x = np.arange(len(payload_lens))
        width = 0.35
        colors = ["#42A5F5", "#EF5350"]

        for i, method in enumerate(methods):
            grp = sub[sub["method"] == method].set_index("payload_len")
            means = [grp.loc[p, "mean_us"] if p in grp.index else 0 for p in payload_lens]
            stds = [grp.loc[p, "std_us"] if p in grp.index else 0 for p in payload_lens]
            ax.bar(x + i * width, means, width, yerr=stds, capsize=3,
                   label=method, color=colors[i % len(colors)],
                   edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Payload size (bytes)")
        ax.set_ylabel("Time (µs)")
        ax.set_title(f"{op.title()} Latency")
        ax.set_xticks(x + width / 2)
        ax.set_xticklabels([str(p) for p in payload_lens])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Encrypt / Decrypt by Payload Size", fontsize=13)
    fig.tight_layout()
    os.makedirs(FIGS, exist_ok=True)
    fig.savefig(os.path.join(FIGS, "encrypt_decrypt_time.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {os.path.join(FIGS, 'encrypt_decrypt_time.png')}")


def plot_memory(mem_df: pd.DataFrame) -> None:
    """Bar chart: RSS delta for baseline vs ecdh."""
    if not HAS_MPL or mem_df is None:
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    methods = mem_df["method"].tolist()
    means = mem_df["mean_rss_delta_kb"].tolist()
    stds = mem_df["std_rss_delta_kb"].tolist()

    colors = ["#42A5F5", "#EF5350"]
    bars = ax.bar(methods, means, yerr=stds, capsize=6,
                  color=colors[:len(methods)], edgecolor="white", linewidth=0.8)
    ax.set_ylabel("RSS Delta (KB)")
    ax.set_title("Memory: RSS Delta (Baseline vs ECDH+ASCON)")
    ax.grid(axis="y", alpha=0.3)

    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{m:.0f} KB", ha="center", va="bottom", fontsize=9)

    os.makedirs(FIGS, exist_ok=True)
    fig.savefig(os.path.join(FIGS, "memory_rss_delta.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {os.path.join(FIGS, 'memory_rss_delta.png')}")


# ── Summary markdown ────────────────────────────────────────────────────────

def write_summary(
    crypto_df: pd.DataFrame | None,
    mem_df: pd.DataFrame | None,
    e2e_df: pd.DataFrame | None,
) -> None:
    os.makedirs(PROC, exist_ok=True)

    all_frames = []
    if crypto_df is not None:
        crypto_df["bench"] = "crypto"
        all_frames.append(crypto_df)
    if mem_df is not None:
        mem_df["bench"] = "memory"
        all_frames.append(mem_df)
    if e2e_df is not None:
        e2e_df["bench"] = "e2e"
        all_frames.append(e2e_df)

    if not all_frames:
        print("  [skip] No data to summarise")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    csv_path = os.path.join(PROC, "summary.csv")
    combined.to_csv(csv_path, index=False)
    print(f"  -> {csv_path}")

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
        f.write("# Benchmark Summary\n\n")

        if crypto_df is not None:
            f.write("## Crypto Benchmarks\n\n")
            f.write(_df_to_md(crypto_df))
            f.write("\n\n")

        if e2e_df is not None:
            f.write("## End-to-End Handshake Latency\n\n")
            f.write(_df_to_md(e2e_df))
            f.write("\n\n")

        if mem_df is not None:
            f.write("## Memory Usage\n\n")
            f.write(_df_to_md(mem_df))
            f.write("\n\n")

        f.write(SUMMARY_NOTE)

    print(f"  -> {md_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("ASCON+ Benchmark Analysis\n")

    crypto_df = analyze_crypto()
    mem_df = analyze_memory()
    e2e_df = analyze_e2e()

    if crypto_df is not None:
        print("\n  Crypto summary:")
        print(crypto_df.to_string(index=False))

    if e2e_df is not None:
        print("\n  E2E summary:")
        print(e2e_df.to_string(index=False))

    if mem_df is not None:
        print("\n  Memory summary:")
        print(mem_df.to_string(index=False))

    print()
    write_summary(crypto_df, mem_df, e2e_df)

    if crypto_df is not None:
        plot_handshake(crypto_df, e2e_df)
        plot_encrypt_decrypt(crypto_df)
    if mem_df is not None:
        plot_memory(mem_df)

    print("\nDone.")


if __name__ == "__main__":
    main()
