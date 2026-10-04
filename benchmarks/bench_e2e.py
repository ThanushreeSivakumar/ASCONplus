#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_e2e.py — End-to-end loopback TCP handshake latency.

Measures connect → first DATA frame acknowledged for:
  - baseline   (plaintext key, baseline server)
  - ecdh_ascon (X25519 + HKDF, Stage 2 gateway server)

Uses asyncio loopback — no external processes.
Output: results/raw/e2e_<hostname>.csv
"""

from __future__ import annotations

import argparse
import asyncio
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
from ascon_plus.protocol import (
    FRAME_HELLO,
    FRAME_HELLO_ACK,
    FRAME_DATA,
    NONCE_LEN,
    PUBKEY_LEN,
    build_frame,
    read_frame,
    make_ad,
)
from ascon_plus.session import NodeSession

# Gateway handler (Stage 2)
from apps.gateway_server import handle_connection, SessionTable, _ensure_csv

# Baseline server
from baseline.plaintext_key_baseline import (
    start_baseline_server,
    baseline_keygen,
    baseline_client_handshake,
    baseline_send_data,
    ASCON_KEY_LEN,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")


def _collect_env_is_pi() -> str:
    try:
        with open("/proc/device-tree/model") as f:
            return str("Raspberry Pi" in f.read())
    except FileNotFoundError:
        return "False"


# ── Baseline handshake latency ───────────────────────────────────────────────

async def _measure_baseline_handshake(port: int) -> int:
    """Connect, send plaintext key HELLO, receive ACK, send one DATA.

    Returns total handshake-to-first-DATA ns.
    """
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    node_id = 99

    t0 = time.perf_counter_ns()

    # Handshake: send plaintext key, receive ACK
    key = baseline_keygen()
    hello = build_frame(FRAME_HELLO, node_id, 0, key)
    writer.write(hello)
    await writer.drain()

    ftype, _, _, _, _ = await read_frame(reader)
    assert ftype == FRAME_HELLO_ACK

    # Send one DATA frame
    nonce = os.urandom(NONCE_LEN)
    ct = ascon.encrypt(key=key, nonce=nonce, associateddata=b"",
                       plaintext=b"bench", variant="Ascon-128")
    frame = build_frame(FRAME_DATA, node_id, 0, ct, nonce=nonce)
    writer.write(frame)
    await writer.drain()

    elapsed = time.perf_counter_ns() - t0

    writer.close()
    await writer.wait_closed()
    return elapsed


# ── ECDH+ASCON handshake latency ────────────────────────────────────────────

async def _measure_ecdh_handshake(port: int) -> int:
    """Connect, X25519 HELLO/HELLO_ACK, send one DATA frame.

    Returns total handshake-to-first-DATA ns.
    """
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    node_id = 99

    t0 = time.perf_counter_ns()

    # Client keygen
    client_priv = X25519PrivateKey.generate()
    client_pub = client_priv.public_key().public_bytes_raw()

    hello = build_frame(FRAME_HELLO, node_id, 0, client_pub)
    writer.write(hello)
    await writer.drain()

    ftype, _, _, _, payload = await read_frame(reader)
    assert ftype == FRAME_HELLO_ACK
    assert len(payload) == PUBKEY_LEN

    server_pub = payload
    shared = client_priv.exchange(X25519PublicKey.from_public_bytes(server_pub))
    c2s, s2c = derive_session_keys(shared, client_pub, server_pub)

    # Send one DATA frame
    nonce = os.urandom(NONCE_LEN)
    ad = make_ad(FRAME_DATA, node_id, 0)
    ct = ascon.encrypt(key=c2s, nonce=nonce, associateddata=ad,
                       plaintext=b"bench", variant="Ascon-128")
    frame = build_frame(FRAME_DATA, node_id, 0, ct, nonce=nonce)
    writer.write(frame)
    await writer.drain()

    elapsed = time.perf_counter_ns() - t0

    writer.close()
    await writer.wait_closed()
    return elapsed


# ── Main ─────────────────────────────────────────────────────────────────────

async def _run(iters: int, warmup: int) -> list[tuple]:
    rows: list[tuple] = []
    is_pi = _collect_env_is_pi()

    # ── Baseline server ──────────────────────────────────────────────────
    bl_server, bl_port = await start_baseline_server()
    async with bl_server:
        print(f"  Baseline server on port {bl_port}")

        # Warmup
        for _ in range(warmup):
            await _measure_baseline_handshake(bl_port)

        gc.collect()
        gc.disable()
        try:
            for i in range(iters):
                ns = await _measure_baseline_handshake(bl_port)
                rows.append(("baseline", i, ns, is_pi))
                if (i + 1) % 25 == 0:
                    print(f"    baseline: {i + 1}/{iters}")
        finally:
            gc.enable()

        bl_server.close()
        await bl_server.wait_closed()

    # ── ECDH+ASCON server (Stage 2 gateway) ──────────────────────────────
    _ensure_csv()
    sessions = SessionTable()

    async def gw_cb(r, w):
        await handle_connection(r, w, sessions)

    gw_server = await asyncio.start_server(gw_cb, "127.0.0.1", 0)
    gw_port = gw_server.sockets[0].getsockname()[1]

    async with gw_server:
        print(f"  ECDH gateway on port {gw_port}")

        # Warmup
        for _ in range(warmup):
            await _measure_ecdh_handshake(gw_port)

        gc.collect()
        gc.disable()
        try:
            for i in range(iters):
                ns = await _measure_ecdh_handshake(gw_port)
                rows.append(("ecdh_ascon", i, ns, is_pi))
                if (i + 1) % 25 == 0:
                    print(f"    ecdh_ascon: {i + 1}/{iters}")
        finally:
            gc.enable()

        gw_server.close()
        await gw_server.wait_closed()

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end handshake latency benchmark")
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    hostname = platform.node()
    csv_path = os.path.join(RESULTS_DIR, f"e2e_{hostname}.csv")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"bench_e2e: {args.iters} iters, {args.warmup} warmup, host={hostname}\n")

    rows = asyncio.run(_run(args.iters, args.warmup))

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "iter", "handshake_ns", "is_pi"])
        w.writerows(rows)

    print(f"\n  Results → {csv_path}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
