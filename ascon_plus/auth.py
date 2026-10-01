"""
PSK-based authentication of handshake public keys.

Each side tags its ephemeral public key with
``HMAC-SHA256(PSK, label || pub)`` where *label* is ``b"client"`` or
``b"server"``.  Verification uses constant-time comparison.

When no PSK is provisioned the functions are no-ops — the session falls
back to passive-attacker-only defence.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
from typing import Optional


class HandshakeError(Exception):
    """Public-key authentication failed during handshake."""


def make_auth_tag(
    psk: Optional[bytes], label: bytes, pub: bytes,
) -> bytes:
    """``HMAC-SHA256(PSK, label || pub)`` or ``b""`` when *psk* is ``None``."""
    if psk is None:
        return b""
    return _hmac.new(psk, label + pub, hashlib.sha256).digest()


def verify_auth_tag(
    psk: Optional[bytes],
    label: bytes,
    pub: bytes,
    tag: bytes,
) -> None:
    """Verify the authentication tag; raise :class:`HandshakeError` on mismatch.

    When *psk* is ``None`` verification is skipped — the handshake is
    unauthenticated (passive-attacker defence only).
    """
    if psk is None:
        return
    expected = _hmac.new(psk, label + pub, hashlib.sha256).digest()
    if not _hmac.compare_digest(expected, tag):
        raise HandshakeError(
            "Public-key authentication failed — possible MITM attack"
        )
