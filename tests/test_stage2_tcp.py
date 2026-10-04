"""
Stage 2 integration tests — client ↔ gateway over TCP (loopback).

Tests run an in-process asyncio gateway and connect one or more
clients to it, exercising the full wire protocol.

Covers:
  1) Handshake + round-trip DATA works
  2) Tampered frame is dropped (not decrypted)
  3) Replayed seq is dropped
  4) Rekey yields a different key
  5) 20 concurrent clients all succeed
"""

from __future__ import annotations

import asyncio
import os
import struct
import sys
import time

import pytest

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

# Import the gateway handler directly to run in-process
from apps.gateway_server import handle_connection, SessionTable, _ensure_csv


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _start_gateway(host: str = "127.0.0.1", port: int = 0):
    """Start a gateway server on an OS-assigned port. Returns (server, port)."""
    _ensure_csv()
    sessions = SessionTable()

    async def cb(r, w):
        await handle_connection(r, w, sessions)

    server = await asyncio.start_server(cb, host, port)
    actual_port = server.sockets[0].getsockname()[1]
    return server, actual_port, sessions


async def _client_handshake(reader, writer, node_id: int):
    """Perform a HELLO/HELLO_ACK exchange; return (c2s, s2c, client_pub, server_pub)."""
    client_priv = X25519PrivateKey.generate()
    client_pub = client_priv.public_key().public_bytes_raw()

    hello = build_frame(FRAME_HELLO, node_id, 0, client_pub)
    writer.write(hello)
    await writer.drain()

    ftype, nid, seq, _nonce, payload = await read_frame(reader)
    assert ftype == FRAME_HELLO_ACK
    assert len(payload) == PUBKEY_LEN

    server_pub = payload
    shared = client_priv.exchange(X25519PublicKey.from_public_bytes(server_pub))
    c2s, s2c = derive_session_keys(shared, client_pub, server_pub)
    return c2s, s2c, client_pub, server_pub


def _encrypt_data(key: bytes, node_id: int, seq: int, plaintext: bytes) -> bytes:
    """Encrypt plaintext into a full DATA frame."""
    nonce = os.urandom(NONCE_LEN)
    ad = make_ad(FRAME_DATA, node_id, seq)
    ct = ascon.encrypt(
        key=key, nonce=nonce, associateddata=ad,
        plaintext=plaintext, variant="Ascon-128",
    )
    return build_frame(FRAME_DATA, node_id, seq, ct, nonce=nonce)


# ── 1) Handshake + round-trip ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handshake_and_roundtrip():
    """Full handshake then send 5 DATA frames; gateway decrypts without error."""
    server, port, sessions = await _start_gateway()

    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        node_id = 1

        c2s, s2c, _, _ = await _client_handshake(reader, writer, node_id)

        for seq in range(5):
            frame = _encrypt_data(c2s, node_id, seq, f"msg-{seq}".encode())
            writer.write(frame)
            await writer.drain()

        # Give gateway a moment to process
        await asyncio.sleep(0.3)

        sess = sessions.get(node_id)
        assert sess is not None
        assert sess.msg_count == 5
        assert sess.last_seq == 4

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


# ── 2) Tampered frame is dropped ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tampered_frame_dropped():
    """A DATA frame with a flipped ciphertext byte must not be accepted."""
    server, port, sessions = await _start_gateway()

    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        node_id = 2

        c2s, _, _, _ = await _client_handshake(reader, writer, node_id)

        # Send a good frame first
        good = _encrypt_data(c2s, node_id, 0, b"legit")
        writer.write(good)
        await writer.drain()
        await asyncio.sleep(0.15)

        # Now send a tampered frame
        tampered_frame = _encrypt_data(c2s, node_id, 1, b"tampered")
        # Flip a byte in the ciphertext region (after the 2-byte length + 7-byte hdr + 16-byte nonce)
        buf = bytearray(tampered_frame)
        buf[-3] ^= 0xFF  # flip byte near end of ciphertext+tag
        writer.write(bytes(buf))
        await writer.drain()
        await asyncio.sleep(0.15)

        # Send another good frame with seq=2
        good2 = _encrypt_data(c2s, node_id, 2, b"after-tamper")
        writer.write(good2)
        await writer.drain()
        await asyncio.sleep(0.3)

        sess = sessions.get(node_id)
        assert sess is not None
        # Only seqs 0 and 2 accepted; tampered seq=1 dropped
        assert sess.msg_count == 2
        assert sess.last_seq == 2

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


# ── 3) Replayed seq is dropped ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_replayed_seq_dropped():
    """Re-sending a frame with a previously-seen seq must be dropped."""
    server, port, sessions = await _start_gateway()

    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        node_id = 3

        c2s, _, _, _ = await _client_handshake(reader, writer, node_id)

        frame0 = _encrypt_data(c2s, node_id, 0, b"first")
        frame1 = _encrypt_data(c2s, node_id, 1, b"second")

        # Send seq 0, 1, then replay seq 0
        writer.write(frame0)
        writer.write(frame1)
        await writer.drain()
        await asyncio.sleep(0.15)

        # Replay: send frame0 again (seq=0, already seen)
        writer.write(frame0)
        await writer.drain()
        await asyncio.sleep(0.15)

        # Send seq 2 (fresh)
        frame2 = _encrypt_data(c2s, node_id, 2, b"third")
        writer.write(frame2)
        await writer.drain()
        await asyncio.sleep(0.3)

        sess = sessions.get(node_id)
        assert sess is not None
        # seq 0, 1, 2 accepted; replayed seq 0 dropped → 3 total
        assert sess.msg_count == 3
        assert sess.last_seq == 2

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


# ── 4) Rekey yields a different key ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_rekey_yields_different_key():
    """A second HELLO on the same connection produces different session keys."""
    server, port, sessions = await _start_gateway()

    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        node_id = 4

        c2s_1, s2c_1, _, _ = await _client_handshake(reader, writer, node_id)

        # Send one DATA with old keys
        frame = _encrypt_data(c2s_1, node_id, 0, b"before-rekey")
        writer.write(frame)
        await writer.drain()
        await asyncio.sleep(0.15)

        # Rekey: new HELLO on the same connection
        c2s_2, s2c_2, _, _ = await _client_handshake(reader, writer, node_id)

        # Keys must differ
        assert c2s_1 != c2s_2
        assert s2c_1 != s2c_2

        # Send DATA with new keys, seq resets to 0
        frame2 = _encrypt_data(c2s_2, node_id, 0, b"after-rekey")
        writer.write(frame2)
        await writer.drain()
        await asyncio.sleep(0.3)

        sess = sessions.get(node_id)
        assert sess is not None
        # After rekey, only the post-rekey message counts (session reset)
        assert sess.msg_count == 1
        assert sess.last_seq == 0

        # Old key must NOT decrypt with new session
        old_frame = _encrypt_data(c2s_1, node_id, 1, b"stale")
        writer.write(old_frame)
        await writer.drain()
        await asyncio.sleep(0.3)
        # msg_count should still be 1 (stale frame rejected)
        assert sessions.get(node_id).msg_count == 1

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


# ── 5) 20 concurrent clients all succeed ────────────────────────────────────

@pytest.mark.asyncio
async def test_20_concurrent_clients():
    """20 clients connect concurrently, each sends 10 DATA frames."""
    server, port, sessions = await _start_gateway()
    num_clients = 20
    msgs_per_client = 10

    async def one_client(nid: int) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        c2s, _, _, _ = await _client_handshake(reader, writer, nid)

        for seq in range(msgs_per_client):
            frame = _encrypt_data(c2s, nid, seq, f"c{nid}-{seq}".encode())
            writer.write(frame)
            await writer.drain()
            # Tiny yield so tasks interleave
            await asyncio.sleep(0)

        # Small delay so server processes everything before we close
        await asyncio.sleep(0.2)
        writer.close()
        await writer.wait_closed()

    async with server:
        tasks = [asyncio.create_task(one_client(nid))
                 for nid in range(100, 100 + num_clients)]
        await asyncio.gather(*tasks)

        # Give server a moment to flush
        await asyncio.sleep(0.5)

        # Verify all 20 nodes registered and received all messages
        for nid in range(100, 100 + num_clients):
            sess = sessions.get(nid)
            assert sess is not None, f"Node {nid} has no session"
            assert sess.msg_count == msgs_per_client, (
                f"Node {nid}: expected {msgs_per_client} msgs, got {sess.msg_count}"
            )
            assert sess.last_seq == msgs_per_client - 1

        server.close()
        await server.wait_closed()
