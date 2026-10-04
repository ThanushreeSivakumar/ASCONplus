#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCON+ Gateway Server (Stage 2 — asyncio TCP)
===============================================

Concurrent TCP server using ``asyncio.start_server``.  Handles many
sensor nodes concurrently via per-connection coroutines.

Frame wire format (big-endian)::

    len(2) | type(1) | node_id(2) | seq(4) | nonce(16) | ciphertext+tag

Usage::

    python apps/gateway_server.py [--host 0.0.0.0] [--port 9000]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
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
    FRAME_ERROR,
    PUBKEY_LEN,
    build_frame,
    read_frame,
)
from ascon_plus.session import NodeSession

log = logging.getLogger("gateway")

# ── CSV logger ───────────────────────────────────────────────────────────────

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")
CSV_PATH = os.path.join(CSV_DIR, "gateway_decrypt.csv")

_csv_lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None  # set in main


def _ensure_csv() -> None:
    """Create CSV directory and header if not present."""
    os.makedirs(CSV_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["node_id", "seq", "payload_len", "decrypt_ns"])


async def _log_csv(node_id: int, seq: int, payload_len: int, ns: int) -> None:
    """Append one row to the decrypt-timing CSV (async-safe)."""
    global _csv_lock
    if _csv_lock is None:
        _csv_lock = asyncio.Lock()
    async with _csv_lock:
        with open(CSV_PATH, "a", newline="") as f:
            csv.writer(f).writerow([node_id, seq, payload_len, ns])


# ── Session table ────────────────────────────────────────────────────────────

class SessionTable:
    """In-memory registry of active node sessions."""

    def __init__(self) -> None:
        self._sessions: dict[int, NodeSession] = {}

    def put(self, node_id: int, session: NodeSession) -> None:
        self._sessions[node_id] = session
        log.info("Session added for node %d (total: %d)",
                 node_id, len(self._sessions))

    def get(self, node_id: int) -> NodeSession | None:
        return self._sessions.get(node_id)

    def remove(self, node_id: int) -> None:
        self._sessions.pop(node_id, None)

    @property
    def count(self) -> int:
        return len(self._sessions)


# ── Per-connection handler ───────────────────────────────────────────────────

async def _send_error(
    writer: asyncio.StreamWriter, node_id: int, msg: str,
) -> None:
    """Send an ERROR frame and log it."""
    frame = build_frame(FRAME_ERROR, node_id, 0, msg.encode())
    writer.write(frame)
    await writer.drain()


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    sessions: SessionTable,
) -> None:
    """Handle a single node connection: handshake → receive loop."""
    peer = writer.get_extra_info("peername")
    node_id = 0  # until HELLO arrives
    try:
        # ── Wait for HELLO ───────────────────────────────────────────────
        ftype, nid, seq, _nonce, payload = await read_frame(reader)
        node_id = nid

        if ftype != FRAME_HELLO:
            log.warning("[%s] Expected HELLO, got type %d", peer, ftype)
            await _send_error(writer, node_id, "expected HELLO")
            return

        if len(payload) != PUBKEY_LEN:
            log.warning("[%s] Bad HELLO pubkey length %d", peer, len(payload))
            await _send_error(writer, node_id, "bad pubkey length")
            return

        client_pub = payload
        log.info("[%s] HELLO from node %d", peer, node_id)

        # ── Generate server keypair and derive keys ──────────────────────
        session = await _do_handshake(writer, node_id, client_pub)
        sessions.put(node_id, session)
        log.info("[%s] Handshake complete for node %d", peer, node_id)

        # ── Receive loop ─────────────────────────────────────────────────
        while True:
            ftype, nid, seq, nonce, payload = await read_frame(reader)

            if ftype == FRAME_HELLO:
                # Rekey: new handshake on the same connection
                if len(payload) != PUBKEY_LEN:
                    log.warning("[%s] Bad rekey HELLO pubkey", peer)
                    continue
                client_pub = payload
                session = await _do_handshake(writer, nid, client_pub)
                sessions.put(nid, session)
                node_id = nid
                log.info("[%s] Rekeyed node %d", peer, node_id)
                continue

            if ftype != FRAME_DATA:
                log.warning("[%s] Unexpected frame type %d", peer, ftype)
                continue

            # Check current session matches node_id
            cur = sessions.get(nid)
            if cur is None:
                log.warning("[%s] DATA for unknown node %d", peer, nid)
                continue

            # Replay check
            if cur.is_replay(seq):
                log.warning("[%s] Replay detected: node=%d seq=%d (last=%d)",
                            peer, nid, seq, cur.last_seq)
                continue

            # Decrypt + time
            t0 = time.perf_counter_ns()
            pt = cur.decrypt(nid, seq, nonce, payload)
            elapsed = time.perf_counter_ns() - t0

            if pt is None:
                log.warning("[%s] AEAD failed: node=%d seq=%d", peer, nid, seq)
                continue

            cur.advance(seq)
            await _log_csv(nid, seq, len(pt), elapsed)
            log.debug("[%s] node=%d seq=%d len=%d dt=%dns",
                      peer, nid, seq, len(pt), elapsed)

    except (asyncio.IncompleteReadError, ConnectionError, OSError) as exc:
        log.info("[%s] node=%d disconnected: %s", peer, node_id, exc)
    except Exception as exc:
        log.error("[%s] node=%d unexpected error: %s", peer, node_id, exc,
                  exc_info=True)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _do_handshake(
    writer: asyncio.StreamWriter,
    node_id: int,
    client_pub_bytes: bytes,
) -> NodeSession:
    """Generate server keypair, send HELLO_ACK, derive session keys."""
    server_priv = X25519PrivateKey.generate()
    server_pub = server_priv.public_key().public_bytes_raw()

    client_pub_obj = X25519PublicKey.from_public_bytes(client_pub_bytes)
    shared_secret = server_priv.exchange(client_pub_obj)

    c2s, s2c = derive_session_keys(shared_secret, client_pub_bytes, server_pub)

    ack = build_frame(FRAME_HELLO_ACK, node_id, 0, server_pub)
    writer.write(ack)
    await writer.drain()

    return NodeSession(key_c2s=c2s, key_s2c=s2c)


# ── Main ─────────────────────────────────────────────────────────────────────

async def run_server(host: str = "0.0.0.0", port: int = 9000) -> None:
    """Start the gateway server (call from ``asyncio.run``)."""
    global _csv_lock
    _csv_lock = asyncio.Lock()
    _ensure_csv()

    sessions = SessionTable()

    async def cb(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        await handle_connection(r, w, sessions)

    server = await asyncio.start_server(cb, host, port)
    addrs = [s.getsockname() for s in server.sockets]
    log.info("ASCON+ Gateway listening on %s", addrs)

    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="ASCON+ Gateway Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(run_server(args.host, args.port))
    except KeyboardInterrupt:
        log.info("Shutting down")


if __name__ == "__main__":
    main()
