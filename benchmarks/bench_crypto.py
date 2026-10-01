#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark: handshake + encrypt/decrypt per payload size.

Measures:
  - Full handshake time (ECDH + HKDF + PSK verification)
  - seal() + open() latency per payload size
  - Outputs CSV to results/raw/bench_crypto.csv
"""

import csv
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import client_handshake, server_handshake

PSK = b"benchmark-psk"
CLIENT_ID = b"bench-client"
SERVER_ID = b"bench-server"
PAYLOAD_SIZES = [16, 64, 128, 256, 512, 1024, 2048, 4096]
ITERATIONS = 200


def bench_handshake(n: int = ITERATIONS) -> list[float]:
    """Time n complete handshakes (seconds)."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        reply, _ = server_handshake(SERVER_ID, hello, psk=PSK)
        pending.complete(reply)
        times.append(time.perf_counter() - t0)
    return times


def bench_seal_open(payload_size: int, n: int = ITERATIONS) -> list[float]:
    """Time n seal+open cycles for a given payload size (seconds)."""
    hello, pending = client_handshake(CLIENT_ID, psk=PSK)
    reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
    cli = pending.complete(reply)

    payload = os.urandom(payload_size)
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        ct = cli.seal(payload)
        srv.open(ct, sender_node_id=CLIENT_ID)
        times.append(time.perf_counter() - t0)
    return times


def _stats(times: list[float]) -> dict:
    ms = [t * 1000 for t in times]
    return {
        "mean_ms": statistics.mean(ms),
        "stdev_ms": statistics.stdev(ms) if len(ms) > 1 else 0,
        "p95_ms": sorted(ms)[int(len(ms) * 0.95)],
        "p99_ms": sorted(ms)[int(len(ms) * 0.99)],
    }


def main() -> None:
    print(f"ASCON+ Crypto Benchmark  ({ITERATIONS} iterations)\n")

    rows = []

    hs_times = bench_handshake()
    s = _stats(hs_times)
    print(f"  Handshake          : {s['mean_ms']:.3f} ± {s['stdev_ms']:.3f} ms  "
          f"(p95={s['p95_ms']:.3f}, p99={s['p99_ms']:.3f})")
    rows.append(("handshake", 0, s["mean_ms"], s["stdev_ms"], s["p95_ms"], s["p99_ms"]))

    for size in PAYLOAD_SIZES:
        times = bench_seal_open(size)
        s = _stats(times)
        print(f"  Seal+Open {size:>5} B  : {s['mean_ms']:.3f} ± {s['stdev_ms']:.3f} ms  "
              f"(p95={s['p95_ms']:.3f}, p99={s['p99_ms']:.3f})")
        rows.append(("seal_open", size, s["mean_ms"], s["stdev_ms"], s["p95_ms"], s["p99_ms"]))

    out = os.path.join(os.path.dirname(__file__), "..", "results", "raw", "bench_crypto.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["operation", "payload_bytes", "mean_ms", "stdev_ms", "p95_ms", "p99_ms"])
        w.writerows(rows)
    print(f"\n  Results → {out}")


if __name__ == "__main__":
    main()
