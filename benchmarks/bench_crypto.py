#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_crypto.py — Compute-only crypto benchmark (no network).

Methods: "baseline" (plaintext key + ASCON-128) vs "ecdh_ascon" (X25519 + HKDF + ASCON-128).
Ops:     handshake, encrypt, decrypt — per payload size 16/64/128/256 B.

Timing: time.perf_counter_ns with gc.collect() before and gc.disable() during.
Output:  results/raw/crypto_<hostname>.csv
"""

from __future__ import annotations

import argparse
import csv
import gc
import os
import platform
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ascon
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from ascon_plus.kdf import derive_session_keys
from baseline.plaintext_key_baseline import (
    baseline_keygen,
    baseline_encrypt,
    baseline_decrypt,
)

PAYLOAD_SIZES = [16, 64, 128, 256]
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")

# ── Environment helper ───────────────────────────────────────────────────────

def write_environment() -> dict:
    """Collect environment info; append ENVIRONMENT.md once. Return env dict."""
    env = _collect_env()
    path = os.path.join(RESULTS_DIR, "ENVIRONMENT.md")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Benchmark Environment\n\n")
        for k, v in env.items():
            f.write(f"- **{k}**: {v}\n")
    return env


def _collect_env() -> dict:
    import importlib.metadata
    env: dict[str, str] = {}
    env["hostname"] = platform.node()
    env["machine"] = platform.machine()
    env["python"] = platform.python_version()
    try:
        env["ascon"] = importlib.metadata.version("ascon")
    except Exception:
        env["ascon"] = "unknown"
    try:
        env["cryptography"] = importlib.metadata.version("cryptography")
    except Exception:
        env["cryptography"] = "unknown"
    # Pi-specific
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read().strip().rstrip("\x00")
        env["device_model"] = model
        env["is_pi"] = str("Raspberry Pi" in model)
    except FileNotFoundError:
        env["device_model"] = "N/A"
        env["is_pi"] = "False"
    # CPU governor
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
            env["cpu_governor"] = f.read().strip()
    except FileNotFoundError:
        env["cpu_governor"] = "N/A"
    # Temperature
    try:
        import subprocess
        r = subprocess.run(["vcgencmd", "measure_temp"],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            env["temperature"] = r.stdout.strip()
    except Exception:
        pass
    return env


# ── Timing helpers ───────────────────────────────────────────────────────────

def _timed_ns(func, iters: int, warmup: int) -> list[int]:
    """Run *func()* warmup+iters times; return list of iters timings in ns."""
    for _ in range(warmup):
        func()
    gc.collect()
    gc.disable()
    try:
        results = []
        for _ in range(iters):
            t0 = time.perf_counter_ns()
            func()
            results.append(time.perf_counter_ns() - t0)
        return results
    finally:
        gc.enable()


# ── Baseline ops ─────────────────────────────────────────────────────────────

def _baseline_handshake():
    """Baseline handshake: just key generation (os.urandom(16))."""
    return baseline_keygen()


def _baseline_encrypt_fn(key, payload):
    def fn():
        baseline_encrypt(key, payload)
    return fn


def _baseline_decrypt_fn(key, nonce, ct):
    def fn():
        baseline_decrypt(key, nonce, ct)
    return fn


# ── ECDH+ASCON ops ───────────────────────────────────────────────────────────

def _ecdh_client_side():
    """Client side: keygen + serialize pubkey."""
    priv = X25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    return priv, pub


def _ecdh_server_side(client_pub_bytes):
    """Server side: keygen + exchange + HKDF."""
    server_priv = X25519PrivateKey.generate()
    server_pub = server_priv.public_key().public_bytes_raw()
    client_pub_obj = X25519PublicKey.from_public_bytes(client_pub_bytes)
    shared = server_priv.exchange(client_pub_obj)
    c2s, s2c = derive_session_keys(shared, client_pub_bytes, server_pub)
    return server_pub, c2s, s2c


def _ecdh_client_complete(client_priv, server_pub_bytes):
    """Client completes: exchange + HKDF."""
    client_pub = client_priv.public_key().public_bytes_raw()
    server_pub_obj = X25519PublicKey.from_public_bytes(server_pub_bytes)
    shared = client_priv.exchange(server_pub_obj)
    c2s, s2c = derive_session_keys(shared, client_pub, server_pub_bytes)
    return c2s, s2c


def _ecdh_full_handshake():
    priv, pub = _ecdh_client_side()
    server_pub, c2s, s2c = _ecdh_server_side(pub)
    _ecdh_client_complete(priv, server_pub)
    return c2s, s2c


def _ecdh_encrypt_fn(key, payload):
    def fn():
        nonce = os.urandom(16)
        ascon.encrypt(key=key, nonce=nonce, associateddata=b"ad",
                      plaintext=payload, variant="Ascon-128")
    return fn


def _ecdh_decrypt_fn(key, nonce, ct):
    def fn():
        ascon.decrypt(key=key, nonce=nonce, associateddata=b"ad",
                      ciphertext=ct, variant="Ascon-128")
    return fn


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto micro-benchmark")
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    hostname = platform.node()
    env = write_environment()
    is_pi = env.get("is_pi", "False")

    csv_path = os.path.join(RESULTS_DIR, f"crypto_{hostname}.csv")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    rows: list[tuple] = []

    print(f"bench_crypto: {args.iters} iters, {args.warmup} warmup, host={hostname}\n")

    # ── Handshake: baseline ──────────────────────────────────────────────
    print("  [baseline] handshake (keygen) ...")
    timings = _timed_ns(_baseline_handshake, args.iters, args.warmup)
    for i, ns in enumerate(timings):
        rows.append(("baseline", "handshake", "both", 0, i, ns, is_pi))

    # ── Handshake: ecdh — client side ────────────────────────────────────
    print("  [ecdh_ascon] handshake client side ...")
    timings = _timed_ns(lambda: _ecdh_client_side(), args.iters, args.warmup)
    for i, ns in enumerate(timings):
        rows.append(("ecdh_ascon", "handshake", "client", 0, i, ns, is_pi))

    # ── Handshake: ecdh — server side ────────────────────────────────────
    # Pre-generate a client pubkey for the server to use
    _priv, _pub = _ecdh_client_side()
    print("  [ecdh_ascon] handshake server side ...")
    timings = _timed_ns(lambda: _ecdh_server_side(_pub), args.iters, args.warmup)
    for i, ns in enumerate(timings):
        rows.append(("ecdh_ascon", "handshake", "server", 0, i, ns, is_pi))

    # ── Handshake: ecdh — full (both sides) ──────────────────────────────
    print("  [ecdh_ascon] handshake full ...")
    timings = _timed_ns(_ecdh_full_handshake, args.iters, args.warmup)
    for i, ns in enumerate(timings):
        rows.append(("ecdh_ascon", "handshake", "both", 0, i, ns, is_pi))

    # ── Encrypt / decrypt per payload size ───────────────────────────────
    for psize in PAYLOAD_SIZES:
        payload = os.urandom(psize)

        # Baseline encrypt
        bl_key = baseline_keygen()
        print(f"  [baseline] encrypt {psize}B ...")
        timings = _timed_ns(_baseline_encrypt_fn(bl_key, payload), args.iters, args.warmup)
        for i, ns in enumerate(timings):
            rows.append(("baseline", "encrypt", "both", psize, i, ns, is_pi))

        # Baseline decrypt
        bl_nonce, bl_ct = baseline_encrypt(bl_key, payload)
        print(f"  [baseline] decrypt {psize}B ...")
        timings = _timed_ns(_baseline_decrypt_fn(bl_key, bl_nonce, bl_ct), args.iters, args.warmup)
        for i, ns in enumerate(timings):
            rows.append(("baseline", "decrypt", "both", psize, i, ns, is_pi))

        # ECDH+ASCON encrypt
        ec_key = os.urandom(16)
        print(f"  [ecdh_ascon] encrypt {psize}B ...")
        timings = _timed_ns(_ecdh_encrypt_fn(ec_key, payload), args.iters, args.warmup)
        for i, ns in enumerate(timings):
            rows.append(("ecdh_ascon", "encrypt", "both", psize, i, ns, is_pi))

        # ECDH+ASCON decrypt
        ec_nonce = os.urandom(16)
        ec_ct = ascon.encrypt(key=ec_key, nonce=ec_nonce, associateddata=b"ad",
                              plaintext=payload, variant="Ascon-128")
        print(f"  [ecdh_ascon] decrypt {psize}B ...")
        timings = _timed_ns(_ecdh_decrypt_fn(ec_key, ec_nonce, ec_ct), args.iters, args.warmup)
        for i, ns in enumerate(timings):
            rows.append(("ecdh_ascon", "decrypt", "both", psize, i, ns, is_pi))

    # ── Write CSV ────────────────────────────────────────────────────────
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "op", "side", "payload_len", "iter", "ns", "is_pi"])
        w.writerows(rows)

    print(f"\n  Results → {csv_path}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
