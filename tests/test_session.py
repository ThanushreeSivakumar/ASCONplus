"""
Tests: seal/open round-trip, wrong key, truncated messages.

Covers:
  - Client→server and server→client round-trips
  - Empty, large, and sequential payloads
  - Cross-session decryption failure
  - Directional key isolation
  - Truncated / malformed wire messages
"""

import os
import pytest

from ascon_plus import (
    IntegrityError,
    client_handshake,
    server_handshake,
)

PSK = b"test-pre-shared-key-32-bytes!!"
CLIENT_ID = b"sensor-node-01"
SERVER_ID = b"gateway-01"


@pytest.fixture
def paired():
    hello, pending = client_handshake(CLIENT_ID, psk=PSK)
    reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
    cli = pending.complete(reply)
    return cli, srv


# ── Round-trip ────────────────────────────────────────────────────────────────

class TestRoundTrip:
    def test_client_to_server(self, paired):
        cli, srv = paired
        ct = cli.seal(b"Sensor Data: 45.2C")
        assert srv.open(ct, sender_node_id=CLIENT_ID) == b"Sensor Data: 45.2C"

    def test_server_to_client(self, paired):
        cli, srv = paired
        ct = srv.seal(b"ACK: received")
        assert cli.open(ct, sender_node_id=SERVER_ID) == b"ACK: received"

    def test_empty_payload(self, paired):
        cli, srv = paired
        ct = cli.seal(b"")
        assert srv.open(ct, sender_node_id=CLIENT_ID) == b""

    def test_large_payload(self, paired):
        cli, srv = paired
        data = os.urandom(4096)
        ct = cli.seal(data)
        assert srv.open(ct, sender_node_id=CLIENT_ID) == data

    def test_multiple_sequential(self, paired):
        cli, srv = paired
        for i in range(10):
            data = f"reading-{i}: {i * 1.1:.1f}C".encode()
            ct = cli.seal(data)
            assert srv.open(ct, sender_node_id=CLIENT_ID) == data

    def test_bidirectional(self, paired):
        cli, srv = paired
        ct1 = cli.seal(b"ping")
        assert srv.open(ct1, sender_node_id=CLIENT_ID) == b"ping"
        ct2 = srv.seal(b"pong")
        assert cli.open(ct2, sender_node_id=SERVER_ID) == b"pong"


# ── Wrong key / cross-session ────────────────────────────────────────────────

class TestWrongKey:
    def test_cross_session_decrypt_fails(self):
        h1, p1 = client_handshake(CLIENT_ID, psk=PSK)
        r1, s1 = server_handshake(SERVER_ID, h1, psk=PSK)
        c1 = p1.complete(r1)

        h2, p2 = client_handshake(CLIENT_ID, psk=PSK)
        r2, s2 = server_handshake(SERVER_ID, h2, psk=PSK)
        p2.complete(r2)

        ct = c1.seal(b"session-1 data")
        with pytest.raises(IntegrityError):
            s2.open(ct, sender_node_id=CLIENT_ID)

    def test_client_cannot_open_own_message(self, paired):
        cli, _ = paired
        ct = cli.seal(b"self-test")
        with pytest.raises(IntegrityError):
            cli.open(ct, sender_node_id=CLIENT_ID)

    def test_server_cannot_open_own_message(self, paired):
        _, srv = paired
        ct = srv.seal(b"self-test")
        with pytest.raises(IntegrityError):
            srv.open(ct, sender_node_id=SERVER_ID)


# ── Truncated messages ───────────────────────────────────────────────────────

class TestTruncatedMessage:
    def test_empty_bytes(self, paired):
        _, srv = paired
        with pytest.raises(IntegrityError, match="too short"):
            srv.open(b"", sender_node_id=CLIENT_ID)

    def test_only_nonce(self, paired):
        _, srv = paired
        with pytest.raises(IntegrityError, match="too short"):
            srv.open(os.urandom(16), sender_node_id=CLIENT_ID)

    def test_nonce_plus_partial_seq(self, paired):
        _, srv = paired
        with pytest.raises(IntegrityError, match="too short"):
            srv.open(os.urandom(20), sender_node_id=CLIENT_ID)

    def test_header_only_no_ciphertext(self, paired):
        _, srv = paired
        with pytest.raises(IntegrityError, match="too short"):
            srv.open(os.urandom(24), sender_node_id=CLIENT_ID)

    def test_truncated_ciphertext(self, paired):
        cli, srv = paired
        ct = cli.seal(b"some longer sensor data here")
        with pytest.raises(IntegrityError):
            srv.open(ct[:-5], sender_node_id=CLIENT_ID)
