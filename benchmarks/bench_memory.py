#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark: memory usage via tracemalloc.

Measures peak and current memory for:
  - Handshake
  - Session with N sealed messages
  - Outputs CSV to results/raw/bench_memory.csv
"""

import csv
import os
import sys
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import client_handshake, server_handshake

PSK = b"benchmark-psk"
CLIENT_ID = b"bench-client"
SERVER_ID = b"bench-server"


def measure_handshake() -> dict:
    tracemalloc.start()
    hello, pending = client_handshake(CLIENT_ID, psk=PSK)
    reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
    cli = pending.complete(reply)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"operation": "handshake", "current_kb": current / 1024, "peak_kb": peak / 1024}


def measure_session(n_messages: int) -> dict:
    hello, pending = client_handshake(CLIENT_ID, psk=PSK)
    reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
    cli = pending.complete(reply)

    tracemalloc.start()
    payload = os.urandom(128)
    for _ in range(n_messages):
        ct = cli.seal(payload)
        srv.open(ct, sender_node_id=CLIENT_ID)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "operation": f"session_{n_messages}_msgs",
        "current_kb": current / 1024,
        "peak_kb": peak / 1024,
    }


def main() -> None:
    print("ASCON+ Memory Benchmark\n")

    rows = []

    r = measure_handshake()
    print(f"  Handshake     : current={r['current_kb']:.1f} KB, peak={r['peak_kb']:.1f} KB")
    rows.append(r)

    for n in [10, 100, 1000]:
        r = measure_session(n)
        print(f"  Session ({n:>4} msgs) : current={r['current_kb']:.1f} KB, peak={r['peak_kb']:.1f} KB")
        rows.append(r)

    out = os.path.join(os.path.dirname(__file__), "..", "results", "raw", "bench_memory.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["operation", "current_kb", "peak_kb"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n  Results → {out}")


if __name__ == "__main__":
    main()
