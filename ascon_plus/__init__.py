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
from ascon_plus.kdf import derive_keys, derive_session_keys
from ascon_plus.protocol import (
    HandshakeMessage,
    FRAME_HELLO,
    FRAME_HELLO_ACK,
    FRAME_DATA,
    FRAME_ERROR,
    build_frame,
    read_frame,
    make_ad,
)
from ascon_plus.session import AsconSession, IntegrityError, NodeSession

__all__ = [
    "AsconSession",
    "HandshakeError",
    "HandshakeMessage",
    "IntegrityError",
    "NodeSession",
    "PendingClientHandshake",
    "client_handshake",
    "derive_keys",
    "derive_session_keys",
    "make_auth_tag",
    "server_handshake",
    "FRAME_HELLO",
    "FRAME_HELLO_ACK",
    "FRAME_DATA",
    "FRAME_ERROR",
    "build_frame",
    "read_frame",
    "make_ad",
]
