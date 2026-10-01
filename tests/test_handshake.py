"""
Tests: handshake authentication, transcript binding, key agreement.

Covers:
  - PSK verification (correct, wrong, mismatched, absent)
  - Both sides derive the same secret (implicit in round-trip)
  - Transcript binding (replayed hello → different keys)
  - Unauthenticated handshake mode
"""

import pytest

from ascon_plus import (
    HandshakeError,
    IntegrityError,
    client_handshake,
    make_auth_tag,
    server_handshake,
)
from ascon_plus.protocol import HandshakeMessage
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

PSK = b"test-pre-shared-key-32-bytes!!"
CLIENT_ID = b"sensor-node-01"
SERVER_ID = b"gateway-01"


# ── PSK authentication ────────────────────────────────────────────────────────

class TestPSKAuthentication:
    """PSK tags must be verified on both sides."""

    def test_correct_psk_succeeds(self):
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
        cli = pending.complete(reply)
        # Round-trip proves keys match
        ct = cli.seal(b"ping")
        assert srv.open(ct, sender_node_id=CLIENT_ID) == b"ping"

    def test_wrong_psk_on_server_side(self):
        hello, _ = client_handshake(CLIENT_ID, psk=PSK)
        with pytest.raises(HandshakeError):
            server_handshake(SERVER_ID, hello, psk=b"wrong-psk")

    def test_wrong_psk_on_client_side(self):
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        server_handshake(SERVER_ID, hello, psk=PSK)
        # Forge a reply signed with the wrong PSK
        fake_priv = X25519PrivateKey.generate()
        fake_pub = fake_priv.public_key().public_bytes_raw()
        bad_tag = make_auth_tag(b"wrong-psk", b"server", fake_pub)
        fake_reply = HandshakeMessage(public_key=fake_pub, auth_tag=bad_tag)
        with pytest.raises(HandshakeError):
            pending.complete(fake_reply)

    def test_psk_vs_no_psk_mismatch(self):
        """Client uses PSK; server uses None → server skips check, but
        its empty tag fails client-side verification."""
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        reply, _ = server_handshake(SERVER_ID, hello, psk=None)
        with pytest.raises(HandshakeError):
            pending.complete(reply)

    def test_no_psk_both_sides(self):
        hello, pending = client_handshake(CLIENT_ID, psk=None)
        reply, srv = server_handshake(SERVER_ID, hello, psk=None)
        cli = pending.complete(reply)
        ct = cli.seal(b"unauthenticated but encrypted")
        assert srv.open(ct, sender_node_id=CLIENT_ID) == b"unauthenticated but encrypted"


# ── Transcript binding ────────────────────────────────────────────────────────

class TestTranscriptBinding:
    """Keys must be bound to the exact handshake that produced them."""

    def test_replayed_client_hello_yields_different_keys(self):
        """Same client hello to two servers → different session keys."""
        hello, p1 = client_handshake(CLIENT_ID, psk=PSK)

        reply1, srv1 = server_handshake(SERVER_ID, hello, psk=PSK)
        reply2, srv2 = server_handshake(SERVER_ID, hello, psk=PSK)

        assert srv1._send_key != srv2._send_key
        assert srv1._recv_key != srv2._recv_key

        cli1 = p1.complete(reply1)
        ct = cli1.seal(b"bound to session 1")
        assert srv1.open(ct, sender_node_id=CLIENT_ID) == b"bound to session 1"
        with pytest.raises(IntegrityError):
            srv2.open(ct, sender_node_id=CLIENT_ID)

    def test_directional_keys_are_distinct(self):
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        reply, srv = server_handshake(SERVER_ID, hello, psk=PSK)
        cli = pending.complete(reply)
        # c2s ≠ s2c
        assert cli._send_key != cli._recv_key
        # client's send = server's recv (and vice versa)
        assert cli._send_key == srv._recv_key
        assert cli._recv_key == srv._send_key
