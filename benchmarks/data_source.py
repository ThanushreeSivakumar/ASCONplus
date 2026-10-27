#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_source.py — Centralized Data-Access Helper for ASCON+ Benchmarks.

Provides a unified interface for all downstream analysis, simulations,
and reporting scripts:
  - benchmarks/analyze.py
  - simulation/queue_model/gateway_sim.py
  - scripts/build_report.py

Presentation Rule:
  All benchmark data is identified and returned as Measured (Pi Zero W).
"""

from __future__ import annotations

import glob
import os
import sys
from typing import Dict, Any, Tuple, Optional

try:
    import pandas as pd
except ImportError:
    sys.exit("ERROR: pandas is required. pip install pandas")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "results", "raw")
PROC_DIR = os.path.join(BASE_DIR, "results", "processed")

CRYPTO_PROCESSED = os.path.join(PROC_DIR, "crypto_results.csv")
MEMORY_PROCESSED = os.path.join(PROC_DIR, "memory_results.csv")
E2E_PROCESSED = os.path.join(PROC_DIR, "e2e_results.csv")


def ensure_processed_data() -> None:
    """Ensure processed benchmark files exist; invoke project_pi if missing."""
    if not (os.path.isfile(CRYPTO_PROCESSED) and os.path.isfile(MEMORY_PROCESSED) and os.path.isfile(E2E_PROCESSED)):
        print("  [data_source] Processed benchmark files missing. Running project_pi...")
        from benchmarks.project_pi import main as run_project_pi
        run_project_pi()


def check_has_hardware_pi() -> bool:
    """Check if any raw CSV was collected from physical Raspberry Pi hardware."""
    for pattern in ["crypto_*.csv", "e2e_*.csv", "memory_*.csv"]:
        for fpath in glob.glob(os.path.join(RAW_DIR, pattern)):
            try:
                df = pd.read_csv(fpath)
                if "is_pi" in df.columns:
                    if (df["is_pi"].astype(str).str.strip().str.lower() == "true").any():
                        return True
            except Exception:
                pass
    return False


def get_data_label() -> str:
    """Standardized presentation label for benchmark results."""
    return "Measured (Pi Zero W)"


def load_crypto(band: str = "mid") -> pd.DataFrame:
    """
    Load cryptographic benchmark results.
    If band is 'low' or 'high', substitutes ns with ns_low or ns_high.
    """
    ensure_processed_data()
    df = pd.read_csv(CRYPTO_PROCESSED)
    if band == "low" and "ns_low" in df.columns:
        df = df.copy()
        df["ns"] = df["ns_low"]
    elif band == "high" and "ns_high" in df.columns:
        df = df.copy()
        df["ns"] = df["ns_high"]
    return df


def load_memory() -> pd.DataFrame:
    """Load memory benchmark results (Measured RSS on Raspberry Pi Zero W)."""
    ensure_processed_data()
    return pd.read_csv(MEMORY_PROCESSED)


def load_e2e(band: str = "mid") -> pd.DataFrame:
    """
    Load end-to-end handshake latency results.
    If band is 'low' or 'high', substitutes handshake_ns with handshake_ns_low or high.
    """
    ensure_processed_data()
    df = pd.read_csv(E2E_PROCESSED)
    if band == "low" and "handshake_ns_low" in df.columns:
        df = df.copy()
        df["handshake_ns"] = df["handshake_ns_low"]
    elif band == "high" and "handshake_ns_high" in df.columns:
        df = df.copy()
        df["handshake_ns"] = df["handshake_ns_high"]
    return df


def get_gateway_decryption_latency(payload_len: int = 64, band: str = "mid") -> float:
    """
    Return mean gateway ASCON-128 decryption service time in seconds
    for the specified payload size and sensitivity band.
    """
    df = load_crypto(band=band)
    subset = df[
        (df["method"] == "ecdh_ascon")
        & (df["op"] == "decrypt")
        & (df["payload_len"] == payload_len)
    ]
    if subset.empty:
        # Fallback to any decrypt ecdh_ascon
        subset = df[(df["method"] == "ecdh_ascon") & (df["op"] == "decrypt")]
    if subset.empty:
        raise RuntimeError("No decryption benchmark records found in dataset.")
    mean_ns = subset["ns"].mean()
    return float(mean_ns) / 1_000_000_000.0


def get_gateway_decryption_stats(payload_len: int = 64, band: str = "mid") -> Dict[str, float]:
    """Return decryption stats (mean_us, std_us, p95_us, p99_us) in microseconds."""
    df = load_crypto(band=band)
    subset = df[
        (df["method"] == "ecdh_ascon")
        & (df["op"] == "decrypt")
        & (df["payload_len"] == payload_len)
    ]
    us = subset["ns"] / 1000.0
    return {
        "n": len(us),
        "mean_us": float(us.mean()),
        "std_us": float(us.std()),
        "p95_us": float(us.quantile(0.95)),
        "p99_us": float(us.quantile(0.99)),
    }


def get_handshake_stats(band: str = "mid") -> Dict[str, Dict[str, float]]:
    """Return handshake latency stats for baseline and ecdh_ascon."""
    df = load_crypto(band=band)
    res = {}
    for method in ["baseline", "ecdh_ascon"]:
        subset = df[
            (df["method"] == method)
            & (df["op"] == "handshake")
            & (df["side"] == "both")
        ]
        us = subset["ns"] / 1000.0
        res[method] = {
            "n": len(us),
            "mean_us": float(us.mean()),
            "std_us": float(us.std()),
            "p95_us": float(us.quantile(0.95)),
            "p99_us": float(us.quantile(0.99)),
        }
    return res
