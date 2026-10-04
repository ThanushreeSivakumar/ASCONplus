#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_memory.py — Memory usage: baseline vs ecdh_ascon.

Each scenario (baseline handshake+encrypt, ecdh handshake+encrypt) runs
in a fresh subprocess.  The subprocess reads VmRSS and VmHWM from
``/proc/self/status`` before and after, or falls back to ``psutil`` /
``tracemalloc`` on non-Linux systems.

Repeat 20 times per method.
Output: results/raw/memory_<hostname>.csv
"""

from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")
REPEATS = 20

# ── Subprocess scripts ──────────────────────────────────────────────────────

_BASELINE_SCRIPT = textwrap.dedent(r"""
import json, os, sys, platform
sys.path.insert(0, os.path.join(os.path.dirname(__file__) if __file__ != "<string>" else ".", ".."))

def _read_proc_mem():
    try:
        with open("/proc/self/status") as f:
            info = {}
            for line in f:
                if line.startswith("VmRSS:"):
                    info["rss_kb"] = int(line.split()[1])
                elif line.startswith("VmHWM:"):
                    info["hwm_kb"] = int(line.split()[1])
            return info
    except FileNotFoundError:
        # Windows / macOS fallback via tracemalloc approximation
        import tracemalloc
        if not tracemalloc.is_tracing():
            return {"rss_kb": 0, "hwm_kb": 0}
        cur, peak = tracemalloc.get_traced_memory()
        return {"rss_kb": cur // 1024, "hwm_kb": peak // 1024}

def _read_rss_portable():
    try:
        return _read_proc_mem()
    except Exception:
        return {"rss_kb": 0, "hwm_kb": 0}

import tracemalloc
tracemalloc.start()

before = _read_rss_portable()

from baseline.plaintext_key_baseline import baseline_keygen, baseline_encrypt
key = baseline_keygen()
for _ in range(10):
    baseline_encrypt(key, b"x" * 128)

after = _read_rss_portable()
_, peak_traced = tracemalloc.get_traced_memory()
tracemalloc.stop()

# Merge: prefer /proc if available, else use tracemalloc peak
if after["hwm_kb"] == 0:
    after["hwm_kb"] = peak_traced // 1024

print(json.dumps({"before": before, "after": after}))
""")

_ECDH_SCRIPT = textwrap.dedent(r"""
import json, os, sys, platform
sys.path.insert(0, os.path.join(os.path.dirname(__file__) if __file__ != "<string>" else ".", ".."))

def _read_proc_mem():
    try:
        with open("/proc/self/status") as f:
            info = {}
            for line in f:
                if line.startswith("VmRSS:"):
                    info["rss_kb"] = int(line.split()[1])
                elif line.startswith("VmHWM:"):
                    info["hwm_kb"] = int(line.split()[1])
            return info
    except FileNotFoundError:
        import tracemalloc
        if not tracemalloc.is_tracing():
            return {"rss_kb": 0, "hwm_kb": 0}
        cur, peak = tracemalloc.get_traced_memory()
        return {"rss_kb": cur // 1024, "hwm_kb": peak // 1024}

def _read_rss_portable():
    try:
        return _read_proc_mem()
    except Exception:
        return {"rss_kb": 0, "hwm_kb": 0}

import tracemalloc
tracemalloc.start()

before = _read_rss_portable()

import ascon
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from ascon_plus.kdf import derive_session_keys

# Handshake
client_priv = X25519PrivateKey.generate()
client_pub = client_priv.public_key().public_bytes_raw()
server_priv = X25519PrivateKey.generate()
server_pub = server_priv.public_key().public_bytes_raw()
shared = client_priv.exchange(server_priv.public_key())
c2s, s2c = derive_session_keys(shared, client_pub, server_pub)

# Encrypt
for _ in range(10):
    nonce = os.urandom(16)
    ascon.encrypt(key=c2s, nonce=nonce, associateddata=b"ad",
                  plaintext=b"x" * 128, variant="Ascon-128")

after = _read_rss_portable()
_, peak_traced = tracemalloc.get_traced_memory()
tracemalloc.stop()

if after["hwm_kb"] == 0:
    after["hwm_kb"] = peak_traced // 1024

print(json.dumps({"before": before, "after": after}))
""")


# ── Runner ───────────────────────────────────────────────────────────────────

def _run_subprocess(script: str, cwd: str) -> dict:
    """Run a Python script in a fresh subprocess and parse its JSON output."""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=30,
        cwd=cwd,
    )
    if result.returncode != 0:
        print(f"  [warn] subprocess failed:\n{result.stderr}", file=sys.stderr)
        return {"before": {"rss_kb": 0, "hwm_kb": 0},
                "after": {"rss_kb": 0, "hwm_kb": 0}}
    # Extract last line (may have import warnings before)
    for line in reversed(result.stdout.strip().split("\n")):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"before": {"rss_kb": 0, "hwm_kb": 0},
            "after": {"rss_kb": 0, "hwm_kb": 0}}


def _collect_env_is_pi() -> str:
    try:
        with open("/proc/device-tree/model") as f:
            return str("Raspberry Pi" in f.read())
    except FileNotFoundError:
        return "False"


def main() -> None:
    hostname = platform.node()
    csv_path = os.path.join(RESULTS_DIR, f"memory_{hostname}.csv")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cwd = os.path.join(os.path.dirname(__file__), "..")
    is_pi = _collect_env_is_pi()

    rows: list[tuple] = []

    print(f"bench_memory: {REPEATS} repeats per method, host={hostname}\n")

    for run in range(REPEATS):
        # Baseline
        data = _run_subprocess(_BASELINE_SCRIPT, cwd)
        b, a = data["before"], data["after"]
        rows.append(("baseline", run,
                      b["rss_kb"], a["rss_kb"], a["hwm_kb"], is_pi))
        print(f"  [baseline] run {run}: RSS {b['rss_kb']}→{a['rss_kb']} KB, HWM {a['hwm_kb']} KB")

        # ECDH+ASCON
        data = _run_subprocess(_ECDH_SCRIPT, cwd)
        b, a = data["before"], data["after"]
        rows.append(("ecdh_ascon", run,
                      b["rss_kb"], a["rss_kb"], a["hwm_kb"], is_pi))
        print(f"  [ecdh]     run {run}: RSS {b['rss_kb']}→{a['rss_kb']} KB, HWM {a['hwm_kb']} KB")

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "run", "rss_before_kb", "rss_after_kb", "hwm_kb", "is_pi"])
        w.writerows(rows)

    print(f"\n  Results → {csv_path}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
