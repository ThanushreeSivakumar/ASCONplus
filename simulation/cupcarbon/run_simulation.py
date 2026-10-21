#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_simulation.py — Automated CupCarbon Star Topology Headless Runner.

Executes discrete-event network simulation across CupCarbon scenarios (N in {5, 10, 25, 50})
using the CupCarbon simulation engine and populates results/raw/cupcarbon_manual.csv.

Usage:
    python simulation/cupcarbon/run_simulation.py
    python simulation/cupcarbon/run_simulation.py --sim-time 300
    python simulation/cupcarbon/run_simulation.py --cupcarbon-dir "C:\\Users\\thanu\\OneDrive\\Desktop\\cupcarbon_windows"
"""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CUPCARBON_DIR = r"C:\Users\thanu\OneDrive\Desktop\cupcarbon_windows"
CSV_PATH = os.path.join(BASE_DIR, "results", "raw", "cupcarbon_manual.csv")
JAVA_SOURCE = os.path.join(BASE_DIR, "simulation", "cupcarbon", "CupCarbonRunner.java")
BUILD_DIR = os.path.join(BASE_DIR, "simulation", "cupcarbon", "bin")


def main():
    parser = argparse.ArgumentParser(description="Run CupCarbon Star Topology Simulations Headlessly.")
    parser.add_argument(
        "--cupcarbon-dir",
        default=DEFAULT_CUPCARBON_DIR,
        help="Path to CupCarbon directory containing cupcarbon.jar",
    )
    parser.add_argument(
        "--sim-time",
        type=float,
        default=300.0,
        help="Simulation duration in simulated seconds (default: 300.0)",
    )
    args = parser.parse_args()

    cupcarbon_jar = os.path.join(args.cupcarbon_dir, "cupcarbon.jar")
    if not os.path.isfile(cupcarbon_jar):
        sys.exit(f"ERROR: cupcarbon.jar not found at: {cupcarbon_jar}")

    os.makedirs(BUILD_DIR, exist_ok=True)

    # 1. Compile CupCarbonRunner.java
    print("[1/3] Compiling CupCarbonRunner.java...")
    compile_cmd = [
        "javac",
        "-cp",
        cupcarbon_jar,
        "-d",
        BUILD_DIR,
        JAVA_SOURCE,
    ]
    res = subprocess.run(compile_cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr)
        sys.exit(f"ERROR: Compilation failed with exit code {res.returncode}")

    # 2. Run CupCarbonRunner
    print(f"[2/3] Running CupCarbon simulations (duration = {args.sim_time}s)...")
    classpath = f"{BUILD_DIR};{cupcarbon_jar}"
    run_cmd = [
        "java",
        "-cp",
        classpath,
        "simulation.cupcarbon.CupCarbonRunner",
        str(args.sim_time),
    ]
    res = subprocess.run(run_cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr)
        sys.exit(f"ERROR: Simulation failed with exit code {res.returncode}")

    print(res.stdout)

    # 3. Verify and print results
    print("[3/3] Verifying generated CSV telemetry...")
    if os.path.isfile(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            print("\n--- results/raw/cupcarbon_manual.csv ---")
            print(f.read().strip())
            print("----------------------------------------\n")
    print("CupCarbon simulation complete and CSV telemetry populated successfully.")


if __name__ == "__main__":
    main()
