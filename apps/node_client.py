#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCON+ IoT Node Client (Stage 2 — asyncio TCP)
================================================

Connects to the gateway, performs an X25519 ephemeral handshake,
then sends dummy sensor payloads at a configurable interval.

Rekeys (fresh HELLO on the same TCP connection) when either
``--rekey-msgs`` or ``--rekey-secs`` is reached; this resets seq to 0.

Usage::

    python apps/node_client.py --node-id 1 --host 127.0.0.1 --port 9000 \\
        --count 50 --interval 0.1 --payload-size 64
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

import ascon

log = logging.getLogger("node")


# ── Handshake helper ─────────────────────────────────────────────────────────

async def do_handshake(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    node_id: int,
) -> tuple[bytes, bytes]:
    """Perform HELLO / HELLO_ACK exchange.

    Returns ``(key_c2s, key_s2c)``.
    """
    client_priv = X25519PrivateKey.generate()
    client_pub = client_priv.public_key().public_bytes_raw()

    hello = build_frame(FRAME_HELLO, node_id, 0, client_pub)
    writer.write(hello)
    await writer.drain()

    ftype, nid, seq, _nonce, payload = await read_frame(reader)
    if ftype != FRAME_HELLO_ACK:
        raise RuntimeError(f"Expected HELLO_ACK, got type {ftype}")
    if len(payload) != PUBKEY_LEN:
        raise RuntimeError(f"Bad HELLO_ACK pubkey length {len(payload)}")

    server_pub = payload
    server_pub_obj = X25519PublicKey.from_public_bytes(server_pub)
    shared_secret = client_priv.exchange(server_pub_obj)

    c2s, s2c = derive_session_keys(shared_secret, client_pub, server_pub)
    return c2s, s2c


# ── Main send loop ───────────────────────────────────────────────────────────

async def run_client(
    node_id: int,
    host: str,
    port: int,
    count: int,
    interval: float,
    payload_size: int,
    rekey_msgs: int,
    rekey_secs: float,
) -> None:
    """Connect to the gateway and send *count* sensor payloads."""
    reader, writer = await asyncio.open_connection(host, port)
    log.info("Connected to %s:%d as node %d", host, port, node_id)

    try:
        c2s, s2c = await do_handshake(reader, writer, node_id)
        log.info("Handshake complete")

        seq = 0
        session_start = time.monotonic()
        session_msgs = 0

        for i in range(count):
            # ── Rekey check ──────────────────────────────────────────────
            elapsed = time.monotonic() - session_start
            if session_msgs >= rekey_msgs or elapsed >= rekey_secs:
                log.info("Rekeying (msgs=%d, elapsed=%.1fs)", session_msgs, elapsed)
                c2s, s2c = await do_handshake(reader, writer, node_id)
                seq = 0
                session_start = time.monotonic()
                session_msgs = 0
                log.info("Rekey complete")

            # ── Build DATA frame ─────────────────────────────────────────
            payload = os.urandom(payload_size)
            nonce = os.urandom(NONCE_LEN)
            ad = make_ad(FRAME_DATA, node_id, seq)

            ct = ascon.encrypt(
                key=c2s,
                nonce=nonce,
                associateddata=ad,
                plaintext=payload,
                variant="Ascon-128",
            )

            frame = build_frame(FRAME_DATA, node_id, seq, ct, nonce=nonce)
            writer.write(frame)
            await writer.drain()

            log.debug("Sent seq=%d len=%d", seq, len(payload))

            seq += 1
            session_msgs += 1

            if interval > 0 and i < count - 1:
                await asyncio.sleep(interval)

        log.info("All %d messages sent", count)

    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ASCON+ IoT Node Client")
    parser.add_argument("--node-id", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--count", type=int, default=10,
                        help="Number of messages to send")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Seconds between messages")
    parser.add_argument("--payload-size", type=int, default=64,
                        help="Bytes per dummy payload")
    parser.add_argument("--rekey-msgs", type=int, default=100,
                        help="Rekey after this many messages")
    parser.add_argument("--rekey-secs", type=float, default=60.0,
                        help="Rekey after this many seconds")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(run_client(
        node_id=args.node_id,
        host=args.host,
        port=args.port,
        count=args.count,
        interval=args.interval,
        payload_size=args.payload_size,
        rekey_msgs=args.rekey_msgs,
        rekey_secs=args.rekey_secs,
    ))


if __name__ == "__main__":
    main()
