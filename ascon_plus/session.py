"""
ASCON-128 AEAD encrypted session with sequence numbering.

Provides :meth:`seal` and :meth:`open` methods that handle nonce
generation, wire framing, and associated-data construction
(``node_id || seq_no``).

The ``NodeSession`` class is the Stage 2 variant that works with the
new TCP frame format (type|node_id|seq in AD).
"""

from __future__ import annotations

import os
import struct
import time
from dataclasses import dataclass, field
from typing import Optional

import ascon

from ascon_plus.protocol import (
    NONCE_LEN,
    ASCON_TAG_LEN,
    MIN_MESSAGE_LEN,
    FRAME_DATA,
    build_frame,
    make_ad,
    encode_frame,
    decode_frame,
)


class IntegrityError(Exception):
    """ASCON-128 AEAD verification failed (tampered / wrong key / truncated)."""


class AsconSession:
    """Bidirectional ASCON-128 AEAD channel with sequence numbering.

    Wire format produced by :meth:`seal`::

        nonce (16 B) || seq_no (8 B, big-endian) || ciphertext+tag

    Associated data fed into ASCON::

        node_id || seq_no (8 B, big-endian)
    """

    def __init__(
        self,
        send_key: bytes,
        recv_key: bytes,
        node_id: bytes,
    ) -> None:
        if len(send_key) != 16 or len(recv_key) != 16:
            raise ValueError("ASCON-128 keys must be exactly 16 bytes")
        self._send_key = send_key
        self._recv_key = recv_key
        self.node_id = node_id
        self._send_seq: int = 0
        self._recv_seq: int = 0

    # ── Encrypt ───────────────────────────────────────────────────────────

    def seal(self, plaintext: bytes) -> bytes:
        """Encrypt *plaintext*; return the complete wire-format message."""
        nonce = os.urandom(NONCE_LEN)
        seq = self._send_seq
        ad = self.node_id + struct.pack(">Q", seq)

        ct = ascon.encrypt(
            key=self._send_key,
            nonce=nonce,
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )
        self._send_seq += 1
        return encode_frame(nonce, seq, ct)

    # ── Decrypt ───────────────────────────────────────────────────────────

    def open(
        self,
        message: bytes,
        *,
        sender_node_id: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt and authenticate *message*.

        Parameters
        ----------
        sender_node_id : bytes, optional
            The sending node's ID (used to reconstruct associated data).
            Defaults to ``self.node_id`` when both sides share the same
            ID or in symmetric demos.

        Raises
        ------
        IntegrityError
            If the message is truncated, tampered, or encrypted with the
            wrong key.
        """
        if len(message) < MIN_MESSAGE_LEN:
            raise IntegrityError(
                f"Message too short ({len(message)} B); minimum is "
                f"{MIN_MESSAGE_LEN} B (nonce + seq + ASCON tag)"
            )

        nonce, seq, ct = decode_frame(message)

        nid = sender_node_id if sender_node_id is not None else self.node_id
        ad = nid + struct.pack(">Q", seq)

        pt = ascon.decrypt(
            key=self._recv_key,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ct,
            variant="Ascon-128",
        )
        if pt is None:
            raise IntegrityError(
                "ASCON-128 authentication failed — "
                "ciphertext tampered, wrong key, or mismatched associated data"
            )
        self._recv_seq = seq + 1
        return pt


# ── Stage 2: TCP session with frame-level AD ─────────────────────────────────

@dataclass
class NodeSession:
    """Server-side session state for a single node (Stage 2 TCP).

    Tracks directional keys, last sequence seen, message count,
    and creation time for rekey policy enforcement.
    """

    key_c2s: bytes
    key_s2c: bytes
    last_seq: int = -1
    msg_count: int = 0
    created_at: float = field(default_factory=time.monotonic)

    def encrypt(self, node_id: int, plaintext: bytes) -> bytes:
        """Encrypt a server→client DATA frame (returns full TCP frame bytes)."""
        nonce = os.urandom(NONCE_LEN)
        seq = self.msg_count  # server-side seq for s2c direction
        ad = make_ad(FRAME_DATA, node_id, seq)

        ct = ascon.encrypt(
            key=self.key_s2c,
            nonce=nonce,
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )
        return build_frame(FRAME_DATA, node_id, seq, ct, nonce=nonce)

    def decrypt(
        self,
        node_id: int,
        seq: int,
        nonce: bytes,
        ciphertext: bytes,
    ) -> Optional[bytes]:
        """Decrypt a client→server DATA payload.

        Returns plaintext on success, ``None`` on AEAD failure.
        """
        ad = make_ad(FRAME_DATA, node_id, seq)
        pt = ascon.decrypt(
            key=self.key_c2s,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ciphertext,
            variant="Ascon-128",
        )
        return pt

    def is_replay(self, seq: int) -> bool:
        """Return True if *seq* has already been seen (replay attack)."""
        return seq <= self.last_seq

    def advance(self, seq: int) -> None:
        """Record that *seq* was successfully processed."""
        self.last_seq = seq
        self.msg_count += 1
