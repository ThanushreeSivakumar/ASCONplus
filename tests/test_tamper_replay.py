"""
Tests: bit-flip detection, replay / sequence checks, nonce uniqueness.

Covers:
  - Flipping any byte (ciphertext, nonce, seq, auth tag) → IntegrityError
  - Wrong sender_node_id in AD → IntegrityError
  - Sequence number monotonicity in wire format
  - Nonce uniqueness across consecutive seals
"""

import os
import struct
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


# ── Bit-flip ─────────────────────────────────────────────────────────────────

class TestBitFlip:
    def test_flip_last_byte(self, paired):
        cli, srv = paired
        msg = bytearray(cli.seal(b"secret"))
        msg[-1] ^= 0xFF
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)

    def test_flip_first_ciphertext_byte(self, paired):
        cli, srv = paired
        msg = bytearray(cli.seal(b"secret"))
        msg[24] ^= 0x01
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)

    def test_flip_nonce_byte(self, paired):
        cli, srv = paired
        msg = bytearray(cli.seal(b"secret"))
        msg[0] ^= 0x01
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)

    def test_flip_sequence_byte(self, paired):
        cli, srv = paired
        msg = bytearray(cli.seal(b"secret"))
        msg[23] ^= 0x01
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)

    def test_flip_auth_tag_region(self, paired):
        cli, srv = paired
        msg = bytearray(cli.seal(b"hello"))
        msg[-8] ^= 0x80
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)


# ── Replay / AD binding ─────────────────────────────────────────────────────

class TestReplayAndAD:
    def test_wrong_sender_node_id_rejected(self, paired):
        cli, srv = paired
        ct = cli.seal(b"payload")
        with pytest.raises(IntegrityError):
            srv.open(ct, sender_node_id=b"wrong-id")

    def test_seq_increments(self, paired):
        cli, _ = paired
        msg0 = cli.seal(b"a")
        msg1 = cli.seal(b"b")
        seq0 = struct.unpack(">Q", msg0[16:24])[0]
        seq1 = struct.unpack(">Q", msg1[16:24])[0]
        assert seq0 == 0
        assert seq1 == 1

    def test_replayed_message_with_edited_seq_rejected(self, paired):
        """Re-transmit a message with a manually altered seq → auth fail."""
        cli, srv = paired
        msg = bytearray(cli.seal(b"original"))
        # Change seq_no from 0 to 99
        msg[16:24] = struct.pack(">Q", 99)
        with pytest.raises(IntegrityError):
            srv.open(bytes(msg), sender_node_id=CLIENT_ID)


# ── Nonce uniqueness ─────────────────────────────────────────────────────────

class TestNonceUniqueness:
    def test_different_nonces(self, paired):
        cli, _ = paired
        msg1 = cli.seal(b"same")
        msg2 = cli.seal(b"same")
        assert msg1[:16] != msg2[:16], "Two seals produced identical nonces"

    def test_same_plaintext_different_ciphertext(self, paired):
        cli, _ = paired
        assert cli.seal(b"identical") != cli.seal(b"identical")

    def test_hundred_nonces_all_unique(self, paired):
        cli, _ = paired
        nonces = {cli.seal(b"x")[:16] for _ in range(100)}
        assert len(nonces) == 100, "Nonce collision in 100 seals"
