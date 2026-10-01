#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark analysis: aggregate raw CSVs, compute statistics, generate plots.

Reads:
  results/raw/bench_crypto.csv
  results/raw/bench_memory.csv
  results/raw/bench_e2e.csv

Produces:
  results/processed/summary.csv
  results/figures/seal_open_latency.png
  results/figures/e2e_rtt_histogram.png
"""

import csv
import os
import sys

# Optional imports — degrade gracefully if not installed
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(BASE, "results", "raw")
PROC = os.path.join(BASE, "results", "processed")
FIGS = os.path.join(BASE, "results", "figures")


def analyze_crypto():
    path = os.path.join(RAW, "bench_crypto.csv")
    if not os.path.exists(path):
        print(f"  [skip] {path} not found — run bench_crypto.py first")
        return

    if HAS_PANDAS:
        df = pd.read_csv(path)
        print("  Crypto benchmark summary:")
        print(df.to_string(index=False))
        if HAS_MPL:
            seal = df[df["operation"] == "seal_open"]
            if not seal.empty:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.bar(seal["payload_bytes"].astype(str), seal["mean_ms"],
                       yerr=seal["stdev_ms"], capsize=4, color="#2196F3")
                ax.set_xlabel("Payload size (bytes)")
                ax.set_ylabel("Latency (ms)")
                ax.set_title("ASCON+ Seal+Open Latency vs Payload Size")
                os.makedirs(FIGS, exist_ok=True)
                fig.savefig(os.path.join(FIGS, "seal_open_latency.png"), dpi=150, bbox_inches="tight")
                plt.close()
                print(f"  → {os.path.join(FIGS, 'seal_open_latency.png')}")
    else:
        print(f"  [info] Install pandas for richer analysis: pip install pandas")


def analyze_e2e():
    path = os.path.join(RAW, "bench_e2e.csv")
    if not os.path.exists(path):
        print(f"  [skip] {path} not found — run bench_e2e.py first")
        return

    if HAS_PANDAS and HAS_MPL:
        df = pd.read_csv(path)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(df["rtt_ms"], bins=30, color="#4CAF50", edgecolor="white")
        ax.set_xlabel("Round-trip time (ms)")
        ax.set_ylabel("Count")
        ax.set_title("ASCON+ End-to-End RTT Distribution (loopback)")
        ax.axvline(df["rtt_ms"].mean(), color="red", linestyle="--",
                   label=f'Mean = {df["rtt_ms"].mean():.3f} ms')
        ax.legend()
        os.makedirs(FIGS, exist_ok=True)
        fig.savefig(os.path.join(FIGS, "e2e_rtt_histogram.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  → {os.path.join(FIGS, 'e2e_rtt_histogram.png')}")


def main():
    print("ASCON+ Benchmark Analysis\n")
    os.makedirs(PROC, exist_ok=True)
    analyze_crypto()
    print()
    analyze_e2e()
    print("\nDone.")


if __name__ == "__main__":
    main()
