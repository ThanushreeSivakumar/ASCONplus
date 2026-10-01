"""
Tests: wire-level frame and HandshakeMessage encode / decode.

Covers:
  - HandshakeMessage round-trip (with/without tag, trailing bytes)
  - Data frame encode_frame / decode_frame
  - Frame rejection when too short
"""

import os
import struct
import pytest

from ascon_plus.protocol import (
    HandshakeMessage,
    MIN_MESSAGE_LEN,
    encode_frame,
    decode_frame,
)


# ── HandshakeMessage serde ───────────────────────────────────────────────────

class TestHandshakeMessageSerde:
    def test_round_trip_with_tag(self):
        pub = os.urandom(32)
        tag = os.urandom(32)
        msg = HandshakeMessage(public_key=pub, auth_tag=tag)
        raw = msg.to_bytes()
        recovered, rest = HandshakeMessage.from_bytes(raw)
        assert recovered == msg
        assert rest == b""

    def test_round_trip_without_tag(self):
        pub = os.urandom(32)
        msg = HandshakeMessage(public_key=pub, auth_tag=b"")
        raw = msg.to_bytes()
        recovered, rest = HandshakeMessage.from_bytes(raw)
        assert recovered == msg

    def test_trailing_bytes_preserved(self):
        pub = os.urandom(32)
        msg = HandshakeMessage(public_key=pub, auth_tag=b"")
        raw = msg.to_bytes() + b"EXTRA"
        recovered, rest = HandshakeMessage.from_bytes(raw)
        assert recovered == msg
        assert rest == b"EXTRA"

    def test_two_messages_concatenated(self):
        m1 = HandshakeMessage(public_key=os.urandom(32), auth_tag=os.urandom(32))
        m2 = HandshakeMessage(public_key=os.urandom(32), auth_tag=b"")
        raw = m1.to_bytes() + m2.to_bytes()
        r1, rest = HandshakeMessage.from_bytes(raw)
        r2, rest2 = HandshakeMessage.from_bytes(rest)
        assert r1 == m1
        assert r2 == m2
        assert rest2 == b""


# ── Data frame encode / decode ───────────────────────────────────────────────

class TestFrameCodec:
    def test_round_trip(self):
        nonce = os.urandom(16)
        seq = 42
        ct = os.urandom(48)  # 32-byte plaintext + 16-byte tag
        frame = encode_frame(nonce, seq, ct)
        r_nonce, r_seq, r_ct = decode_frame(frame)
        assert r_nonce == nonce
        assert r_seq == seq
        assert r_ct == ct

    def test_seq_encoding(self):
        frame = encode_frame(b"\x00" * 16, 0xDEAD, b"\x00" * 16)
        _, seq, _ = decode_frame(frame)
        assert seq == 0xDEAD

    def test_reject_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            decode_frame(os.urandom(MIN_MESSAGE_LEN - 1))

    def test_minimum_valid_length(self):
        """Exactly MIN_MESSAGE_LEN bytes should not raise."""
        frame = encode_frame(os.urandom(16), 0, os.urandom(16))
        assert len(frame) == MIN_MESSAGE_LEN
        nonce, seq, ct = decode_frame(frame)
        assert seq == 0
        assert len(ct) == 16
