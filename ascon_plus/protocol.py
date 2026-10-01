"""
Wire-level frame formats and constants for the ASCON+ protocol.

Data frame (produced by :meth:`AsconSession.seal`)::

    nonce (16 B) ║ seq_no (8 B, big-endian) ║ ciphertext + tag

Handshake message (serialised by :meth:`HandshakeMessage.to_bytes`)::

    pk_len (2 B) ║ public_key ║ tag_len (2 B) ║ auth_tag
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# ── ASCON-128 wire constants ─────────────────────────────────────────────────

ASCON_TAG_LEN: int = 16       # authentication tag appended by ASCON-128
NONCE_LEN: int = 16
SEQ_LEN: int = 8              # uint64 big-endian
HEADER_LEN: int = NONCE_LEN + SEQ_LEN             # 24
MIN_MESSAGE_LEN: int = HEADER_LEN + ASCON_TAG_LEN  # 40 (empty plaintext)


# ── Handshake message ────────────────────────────────────────────────────────

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


# ── Data frame helpers ───────────────────────────────────────────────────────

def encode_frame(nonce: bytes, seq: int, ciphertext: bytes) -> bytes:
    """Encode a data frame: ``nonce (16) || seq (8) || ciphertext+tag``."""
    return nonce + struct.pack(">Q", seq) + ciphertext


def decode_frame(message: bytes) -> tuple[bytes, int, bytes]:
    """Decode a data frame.

    Returns ``(nonce, seq, ciphertext+tag)``.

    Raises
    ------
    ValueError
        If *message* is shorter than :data:`MIN_MESSAGE_LEN`.
    """
    if len(message) < MIN_MESSAGE_LEN:
        raise ValueError(
            f"Frame too short ({len(message)} B); "
            f"minimum is {MIN_MESSAGE_LEN} B"
        )
    nonce = message[:NONCE_LEN]
    seq = struct.unpack(">Q", message[NONCE_LEN:HEADER_LEN])[0]
    ct = message[HEADER_LEN:]
    return nonce, seq, ct
