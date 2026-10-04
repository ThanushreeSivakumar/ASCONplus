#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline: plaintext-key ASCON-128 (original paper's flow).

The client generates a random 16-byte key, sends it IN PLAINTEXT to the
server over TCP (no ECDH, no HKDF).  Both sides then use that key for
ASCON-128 AEAD.  This is the insecure baseline against which the full
ECDH+ASCON protocol is compared.

Provides:
  - Pure-compute helpers: keygen, encrypt, decrypt
  - A tiny asyncio TCP server/client using the same Stage-2 frame format
    (``build_frame`` / ``read_frame``) with no handshake crypto
"""

from __future__ import annotations

import asyncio
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ascon

from ascon_plus.protocol import (
    FRAME_HELLO,
    FRAME_HELLO_ACK,
    FRAME_DATA,
    NONCE_LEN,
    ASCON_TAG_LEN,
    build_frame,
    read_frame,
    make_ad,
)

# ── Compute helpers ──────────────────────────────────────────────────────────

ASCON_KEY_LEN = 16


def baseline_keygen() -> bytes:
    """Generate a random 16-byte ASCON-128 key (client side)."""
    return os.urandom(ASCON_KEY_LEN)


def baseline_encrypt(key: bytes, plaintext: bytes, nonce: bytes | None = None) -> tuple[bytes, bytes]:
    """Encrypt with ASCON-128, empty AD.

    Returns ``(nonce, ciphertext_with_tag)``.
    """
    if nonce is None:
        nonce = os.urandom(NONCE_LEN)
    ct = ascon.encrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",
        plaintext=plaintext,
        variant="Ascon-128",
    )
    return nonce, ct


def baseline_decrypt(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """Decrypt with ASCON-128, empty AD."""
    pt = ascon.decrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",
        ciphertext=ciphertext,
        variant="Ascon-128",
    )
    if pt is None:
        raise RuntimeError("ASCON-128 baseline decryption failed")
    return pt


# ── Tiny asyncio TCP server ─────────────────────────────────────────────────

async def baseline_server_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    on_session=None,
) -> None:
    """Handle one baseline client: receive plaintext key, then DATA loop."""
    try:
        # 1. Receive HELLO carrying the plaintext 16-byte key
        ftype, node_id, seq, _nonce, payload = await read_frame(reader)
        if ftype != FRAME_HELLO or len(payload) != ASCON_KEY_LEN:
            writer.close()
            return

        key = payload  # ← plaintext key!

        # 2. Send HELLO_ACK (empty payload — just an acknowledgement)
        ack = build_frame(FRAME_HELLO_ACK, node_id, 0, b"")
        writer.write(ack)
        await writer.drain()

        if on_session is not None:
            on_session(node_id, key)

        # 3. DATA receive loop
        while True:
            ftype, nid, seq, nonce, ct = await read_frame(reader)
            if ftype != FRAME_DATA:
                continue
            pt = baseline_decrypt(key, nonce, ct)
            # (in benchmark mode the server just consumes)

    except (asyncio.IncompleteReadError, ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def start_baseline_server(host: str = "127.0.0.1", port: int = 0, on_session=None):
    """Start an asyncio baseline server. Returns ``(server, actual_port)``."""

    async def cb(r, w):
        await baseline_server_handler(r, w, on_session=on_session)

    server = await asyncio.start_server(cb, host, port)
    actual_port = server.sockets[0].getsockname()[1]
    return server, actual_port


# ── Tiny asyncio TCP client ─────────────────────────────────────────────────

async def baseline_client_handshake(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    node_id: int,
) -> bytes:
    """Send a plaintext key in a HELLO frame, wait for HELLO_ACK.

    Returns the 16-byte key.
    """
    key = baseline_keygen()

    hello = build_frame(FRAME_HELLO, node_id, 0, key)
    writer.write(hello)
    await writer.drain()

    ftype, _nid, _seq, _nonce, _payload = await read_frame(reader)
    if ftype != FRAME_HELLO_ACK:
        raise RuntimeError(f"Baseline: expected HELLO_ACK, got {ftype}")

    return key


async def baseline_send_data(
    writer: asyncio.StreamWriter,
    key: bytes,
    node_id: int,
    seq: int,
    plaintext: bytes,
) -> None:
    """Encrypt and send one DATA frame with baseline (empty-AD) ASCON."""
    nonce = os.urandom(NONCE_LEN)
    ct = ascon.encrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",
        plaintext=plaintext,
        variant="Ascon-128",
    )
    frame = build_frame(FRAME_DATA, node_id, seq, ct, nonce=nonce)
    writer.write(frame)
    await writer.drain()


# ── Demo / smoke-test ────────────────────────────────────────────────────────

async def _smoke_test() -> None:
    import time

    server, port = await start_baseline_server()
    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        node_id = 42

        t0 = time.perf_counter_ns()
        key = await baseline_client_handshake(reader, writer, node_id)
        hs_ns = time.perf_counter_ns() - t0

        payload = b"Sensor: 23.5C humidity=60%"
        t0 = time.perf_counter_ns()
        await baseline_send_data(writer, key, node_id, 0, payload)
        enc_ns = time.perf_counter_ns() - t0

        print(f"Baseline smoke test:")
        print(f"  Key (plaintext): {key.hex()}")
        print(f"  Handshake:       {hs_ns / 1000:.0f} µs")
        print(f"  Encrypt+send:    {enc_ns / 1000:.0f} µs")
        print(f"  OK")

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(_smoke_test())
