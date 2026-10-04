"""
Wire-level frame formats for the ASCON+ TCP protocol (Stage 2).

TCP Frame (big-endian)::

    length  (2 B) | type (1 B) | node_id (2 B) | seq (4 B)
                  | nonce (16 B) | ciphertext + tag

Frame types:
    1 = HELLO       — payload = 32-byte client X25519 public key (unencrypted)
    2 = HELLO_ACK   — payload = 32-byte server X25519 public key (unencrypted)
    3 = DATA        — ASCON-128 encrypted; AD = type|node_id|seq
    4 = ERROR       — plaintext error description

Legacy HandshakeMessage is preserved for in-memory handshake logic.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

# ── Frame types ──────────────────────────────────────────────────────────────

FRAME_HELLO: int = 1
FRAME_HELLO_ACK: int = 2
FRAME_DATA: int = 3
FRAME_ERROR: int = 4

# ── Wire constants ───────────────────────────────────────────────────────────

FRAME_HDR_LEN: int = 2 + 1 + 2 + 4  # length(2) + type(1) + node_id(2) + seq(4) = 9
NONCE_LEN: int = 16
ASCON_TAG_LEN: int = 16
PUBKEY_LEN: int = 32

# Minimum DATA frame body = HDR(9) + nonce(16) + tag(16) - length(2) = 7+16+16 = 39
# (length field is part of the outer framing but the body starts after it)

# Legacy constants kept for existing tests
SEQ_LEN: int = 8
HEADER_LEN: int = NONCE_LEN + SEQ_LEN
MIN_MESSAGE_LEN: int = HEADER_LEN + ASCON_TAG_LEN


# ── TCP frame encode / decode ────────────────────────────────────────────────

def build_frame(
    frame_type: int,
    node_id: int,
    seq: int,
    payload: bytes,
    nonce: bytes = b"",
) -> bytes:
    """Build a complete TCP frame ready for ``writer.write()``.

    For HELLO / HELLO_ACK / ERROR the *nonce* is omitted (zero-length)
    and *payload* is sent in the clear.
    For DATA, *nonce* is the 16-byte ASCON nonce and *payload* is
    ciphertext+tag.
    """
    body = struct.pack(">BHI", frame_type, node_id, seq) + nonce + payload
    return struct.pack(">H", len(body)) + body


async def read_frame(reader) -> tuple[int, int, int, bytes, bytes]:
    """Read one frame from an ``asyncio.StreamReader``.

    Returns ``(frame_type, node_id, seq, nonce, payload)``.
    *nonce* is empty for non-DATA frames; caller must check type.

    Raises ``ConnectionError`` on EOF.
    """
    raw_len = await reader.readexactly(2)
    body_len = struct.unpack(">H", raw_len)[0]
    body = await reader.readexactly(body_len)

    if len(body) < 7:  # type(1) + node_id(2) + seq(4)
        raise ValueError(f"Frame body too short ({len(body)} B)")

    frame_type = body[0]
    node_id, seq = struct.unpack(">HI", body[1:7])
    rest = body[7:]

    if frame_type == FRAME_DATA:
        if len(rest) < NONCE_LEN + ASCON_TAG_LEN:
            raise ValueError("DATA frame too short for nonce + tag")
        nonce = rest[:NONCE_LEN]
        ct = rest[NONCE_LEN:]
        return frame_type, node_id, seq, nonce, ct
    else:
        # HELLO, HELLO_ACK, ERROR: payload is plain
        return frame_type, node_id, seq, b"", rest


def make_ad(frame_type: int, node_id: int, seq: int) -> bytes:
    """Construct associated data: ``type(1) | node_id(2) | seq(4)``."""
    return struct.pack(">BHI", frame_type, node_id, seq)


# ── Legacy HandshakeMessage (kept for existing handshake module) ─────────────

@dataclass(frozen=True)
class HandshakeMessage:
    """One leg of the handshake: public key + optional auth tag."""

    public_key: bytes   # 32-byte raw X25519 public key
    auth_tag: bytes     # HMAC-SHA256 tag, or b"" when no PSK

    def to_bytes(self) -> bytes:
        """Serialise for transcript hashing and wire transmission."""
        return (
            struct.pack(">H", len(self.public_key))
            + self.public_key
            + struct.pack(">H", len(self.auth_tag))
            + self.auth_tag
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> tuple["HandshakeMessage", bytes]:
        """Deserialise; returns ``(message, remaining_bytes)``."""
        pk_len = struct.unpack(">H", data[:2])[0]
        pk = data[2 : 2 + pk_len]
        off = 2 + pk_len
        tag_len = struct.unpack(">H", data[off : off + 2])[0]
        tag = data[off + 2 : off + 2 + tag_len]
        return cls(public_key=pk, auth_tag=tag), data[off + 2 + tag_len :]


# ── Legacy data frame helpers (kept for existing session / tests) ────────────

def encode_frame_legacy(nonce: bytes, seq: int, ciphertext: bytes) -> bytes:
    """Encode a legacy data frame: ``nonce (16) || seq (8) || ciphertext+tag``."""
    return nonce + struct.pack(">Q", seq) + ciphertext


def decode_frame_legacy(message: bytes) -> tuple[bytes, int, bytes]:
    """Decode a legacy data frame → ``(nonce, seq, ciphertext+tag)``."""
    if len(message) < MIN_MESSAGE_LEN:
        raise ValueError(
            f"Frame too short ({len(message)} B); "
            f"minimum is {MIN_MESSAGE_LEN} B"
        )
    nonce = message[:NONCE_LEN]
    seq = struct.unpack(">Q", message[NONCE_LEN:HEADER_LEN])[0]
    ct = message[HEADER_LEN:]
    return nonce, seq, ct


# Aliases so existing code that imports encode_frame / decode_frame still works
encode_frame = encode_frame_legacy
decode_frame = decode_frame_legacy
