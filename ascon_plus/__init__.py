"""
ascon_plus — ECDH + ASCON-128 Authenticated Session Layer
==========================================================

Convenience re-exports so callers can write::

    from ascon_plus import client_handshake, server_handshake
"""

from ascon_plus.auth import HandshakeError, make_auth_tag, verify_auth_tag
from ascon_plus.handshake import (
    PendingClientHandshake,
    client_handshake,
    server_handshake,
)
from ascon_plus.kdf import derive_keys
from ascon_plus.protocol import HandshakeMessage
from ascon_plus.session import AsconSession, IntegrityError

__all__ = [
    "AsconSession",
    "HandshakeError",
    "HandshakeMessage",
    "IntegrityError",
    "PendingClientHandshake",
    "client_handshake",
    "derive_keys",
    "make_auth_tag",
    "server_handshake",
    "verify_auth_tag",
]
