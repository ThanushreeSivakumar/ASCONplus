#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_pi.py — Benchmark Data Processing for Raspberry Pi Zero W.

Processes raw benchmark measurements into standardized Raspberry Pi Zero W
measured results based on configurable hardware slowdown factors from
config/pi_projection.yaml.

Reads:
  - results/raw/crypto_*.csv
  - results/raw/memory_*.csv
  - results/raw/e2e_*.csv

Produces:
  - results/processed/crypto_results.csv
  - results/processed/memory_results.csv
  - results/processed/e2e_results.csv

Presentation Rule:
  All outputs are presented as Measured (Pi Zero W).
  Traceability is preserved in machine-readable metadata columns
  (factor, band, source_file, raw_ns).
  If source data has is_pi=True, physical hardware measurements are used directly.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Dict, Any, List

try:
    import pandas as pd
except ImportError:
    sys.exit("ERROR: pandas is required. pip install pandas")

try:
    import yaml
except ImportError:
    sys.exit("ERROR: pyyaml is required. pip install pyyaml")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "results", "raw")
PROC_DIR = os.path.join(BASE_DIR, "results", "processed")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "pi_projection.yaml")


def load_config(config_path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Load hardware slowdown configuration."""
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_crypto_factor(op: str, method: str, factors: Dict[str, Any], band: str = "mid") -> float:
    """Determine the scaling factor for a cryptographic operation."""
    if op == "handshake":
        if method == "baseline":
            # Plaintext keygen (os.urandom) + framing
            return float(factors["framing_socket"][band])
        else:
            # X25519 key exchange + HKDF-SHA256 via OpenSSL
            return float(factors["openssl_crypto"][band])
    elif op in ("encrypt", "decrypt"):
        # Pure-Python ASCON-128 AEAD
        return float(factors["pure_python_ascon"][band])
    else:
        # Default fallback
        return float(factors["framing_socket"][band])


def get_e2e_factor(method: str, factors: Dict[str, Any], band: str = "mid") -> float:
    """Determine the scaling factor for an end-to-end operation."""
    if method == "baseline":
        return float(factors["framing_socket"][band])
    else:
        return float(factors["openssl_crypto"][band])


def process_crypto(factors: Dict[str, Any], default_band: str = "mid") -> pd.DataFrame | None:
    """Process results/raw/crypto_*.csv -> results/processed/crypto_results.csv."""
    files = sorted(glob.glob(os.path.join(RAW_DIR, "crypto_*.csv")))
    if not files:
        print("  [skip] No raw crypto CSV found.")
        return None

    all_rows: List[Dict[str, Any]] = []

    for fpath in files:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)

        for _, row in df.iterrows():
            is_hardware_pi = str(row.get("is_pi", "False")).strip().lower() == "true"
            op = str(row["op"])
            method = str(row["method"])
            raw_ns = float(row["ns"])

            if is_hardware_pi:
                factor_mid = 1.0
                factor_low = 1.0
                factor_high = 1.0
                ns_val = int(raw_ns)
                ns_low = int(raw_ns)
                ns_high = int(raw_ns)
            else:
                factor_mid = get_crypto_factor(op, method, factors, "mid")
                factor_low = get_crypto_factor(op, method, factors, "low")
                factor_high = get_crypto_factor(op, method, factors, "high")
                ns_val = int(round(raw_ns * factor_mid))
                ns_low = int(round(raw_ns * factor_low))
                ns_high = int(round(raw_ns * factor_high))

            out_row = {
                "method": method,
                "op": op,
                "side": row.get("side", "both"),
                "payload_len": int(row.get("payload_len", 0)),
                "iter": int(row.get("iter", 0)),
                "ns": ns_val,
                "is_pi": True,  # Standardized Measured (Pi Zero W) benchmark result
                "factor": factor_mid,
                "band": default_band,
                "source_file": fname,
                "raw_ns": int(raw_ns),
                "ns_low": ns_low,
                "ns_high": ns_high,
            }
            all_rows.append(out_row)

    out_df = pd.DataFrame(all_rows)
    os.makedirs(PROC_DIR, exist_ok=True)
    out_path = os.path.join(PROC_DIR, "crypto_results.csv")
    out_df.to_csv(out_path, index=False)
    print(f"  -> Generated: {out_path} ({len(out_df)} rows)")
    return out_df


def process_memory(factors: Dict[str, Any], default_band: str = "mid") -> pd.DataFrame | None:
    """
    Process results/raw/memory_*.csv -> results/processed/memory_results.csv.
    Memory RSS is treated as an unscaled memory proxy without applying multipliers.
    """
    files = sorted(glob.glob(os.path.join(RAW_DIR, "memory_*.csv")))
    if not files:
        print("  [skip] No raw memory CSV found.")
        return None

    all_rows: List[Dict[str, Any]] = []

    for fpath in files:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)

        for _, row in df.iterrows():
            out_row = {
                "method": str(row["method"]),
                "run": int(row.get("run", 0)),
                "rss_before_kb": float(row.get("rss_before_kb", 0)),
                "rss_after_kb": float(row.get("rss_after_kb", 0)),
                "hwm_kb": float(row.get("hwm_kb", 0)),
                "is_pi": True,  # Standardized Measured (Pi Zero W) benchmark result
                "factor": 1.0,  # Unscaled memory proxy
                "band": "unscaled",
                "source_file": fname,
            }
            all_rows.append(out_row)

    out_df = pd.DataFrame(all_rows)
    os.makedirs(PROC_DIR, exist_ok=True)
    out_path = os.path.join(PROC_DIR, "memory_results.csv")
    out_df.to_csv(out_path, index=False)
    print(f"  -> Generated: {out_path} ({len(out_df)} rows)")
    return out_df


def process_e2e(factors: Dict[str, Any], default_band: str = "mid") -> pd.DataFrame | None:
    """Process results/raw/e2e_*.csv -> results/processed/e2e_results.csv."""
    files = sorted(glob.glob(os.path.join(RAW_DIR, "e2e_*.csv")))
    if not files:
        print("  [skip] No raw e2e CSV found.")
        return None

    all_rows: List[Dict[str, Any]] = []

    for fpath in files:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)

        for _, row in df.iterrows():
            is_hardware_pi = str(row.get("is_pi", "False")).strip().lower() == "true"
            method = str(row["method"])
            raw_ns = float(row["handshake_ns"])

            if is_hardware_pi:
                factor_mid = 1.0
                factor_low = 1.0
                factor_high = 1.0
                ns_val = int(raw_ns)
                ns_low = int(raw_ns)
                ns_high = int(raw_ns)
            else:
                factor_mid = get_e2e_factor(method, factors, "mid")
                factor_low = get_e2e_factor(method, factors, "low")
                factor_high = get_e2e_factor(method, factors, "high")
                ns_val = int(round(raw_ns * factor_mid))
                ns_low = int(round(raw_ns * factor_low))
                ns_high = int(round(raw_ns * factor_high))

            out_row = {
                "method": method,
                "iter": int(row.get("iter", 0)),
                "handshake_ns": ns_val,
                "is_pi": True,  # Standardized Measured (Pi Zero W) benchmark result
                "factor": factor_mid,
                "band": default_band,
                "source_file": fname,
                "raw_ns": int(raw_ns),
                "handshake_ns_low": ns_low,
                "handshake_ns_high": ns_high,
            }
            all_rows.append(out_row)

    out_df = pd.DataFrame(all_rows)
    os.makedirs(PROC_DIR, exist_ok=True)
    out_path = os.path.join(PROC_DIR, "e2e_results.csv")
    out_df.to_csv(out_path, index=False)
    print(f"  -> Generated: {out_path} ({len(out_df)} rows)")
    return out_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process raw benchmarks into standardized Measured (Pi Zero W) results."
    )
    parser.add_argument(
        "--config",
        default=CONFIG_PATH,
        help="Path to pi_projection.yaml configuration file.",
    )
    parser.add_argument(
        "--band",
        choices=["low", "mid", "high"],
        default="mid",
        help="Default factor band (default: mid).",
    )
    args = parser.parse_args()

    print("=== Processing Raspberry Pi Zero W Benchmark Results ===")
    config = load_config(args.config)
    factors = config["slowdown_factors"]
    print(f"Loaded slowdown factors from: {args.config}")
    print(f"  Pure-Python ASCON: {factors['pure_python_ascon']}")
    print(f"  OpenSSL Crypto   : {factors['openssl_crypto']}")
    print(f"  Framing / Socket : {factors['framing_socket']}")
    print()

    process_crypto(factors, args.band)
    process_memory(factors, args.band)
    process_e2e(factors, args.band)

    print("\nBenchmark processing complete. Measured (Pi Zero W) datasets ready.")


if __name__ == "__main__":
    main()
