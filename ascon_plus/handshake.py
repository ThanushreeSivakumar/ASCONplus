"""
X25519 ephemeral key exchange with optional PSK authentication.

Public API
----------
- :func:`client_handshake` — begin client-side key exchange.
- :func:`server_handshake` — complete server-side in one step.
- :class:`PendingClientHandshake` — intermediate state held by the
  client between sending its hello and receiving the server's reply.
"""

from __future__ import annotations

from typing import Optional

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from ascon_plus.auth import make_auth_tag, verify_auth_tag
from ascon_plus.kdf import derive_keys
from ascon_plus.protocol import HandshakeMessage
from ascon_plus.session import AsconSession


# ─────────────────────────────────────────────────────────────────────────────
# Client pending state
# ─────────────────────────────────────────────────────────────────────────────

class PendingClientHandshake:
    """Intermediate state the client holds between hello and complete.

    Do **not** construct directly; use :func:`client_handshake`.
    """

    def __init__(
        self,
        node_id: bytes,
        private_key: X25519PrivateKey,
        hello: HandshakeMessage,
        psk: Optional[bytes],
    ) -> None:
        self._node_id = node_id
        self._private_key = private_key
        self.hello = hello
        self._psk = psk

    def complete(self, server_hello: HandshakeMessage) -> AsconSession:
        """Verify the server's reply and derive session keys.

        Raises
        ------
        HandshakeError
            If the server's public-key authentication tag is invalid.
        """
        verify_auth_tag(
            self._psk,
            b"server",
            server_hello.public_key,
            server_hello.auth_tag,
        )

        server_pub_obj = X25519PublicKey.from_public_bytes(server_hello.public_key)
        shared_secret = self._private_key.exchange(server_pub_obj)

        client_pub = self._private_key.public_key().public_bytes_raw()

        # Transcript = ClientHello || ServerHello  (full wire bytes)
        transcript = self.hello.to_bytes() + server_hello.to_bytes()

        c2s, s2c = derive_keys(
            shared_secret, client_pub, server_hello.public_key, transcript,
        )
        # Client sends with c2s, receives with s2c
        return AsconSession(send_key=c2s, recv_key=s2c, node_id=self._node_id)


# ─────────────────────────────────────────────────────────────────────────────
# Top-level handshake functions
# ─────────────────────────────────────────────────────────────────────────────

def client_handshake(
    node_id: bytes,
    psk: Optional[bytes] = None,
) -> tuple[HandshakeMessage, PendingClientHandshake]:
    """Begin the client side of the key exchange.

    Parameters
    ----------
    node_id : bytes
        Identifier for this node (included in ASCON associated data).
    psk : bytes, optional
        Pre-shared key for public-key authentication.  If ``None``, the
        handshake is unauthenticated (passive-attacker defence only).

    Returns
    -------
    hello : HandshakeMessage
        Send this to the server.
    pending : PendingClientHandshake
        Call ``pending.complete(server_hello)`` when the reply arrives.
    """
    priv = X25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    tag = make_auth_tag(psk, b"client", pub)
    hello = HandshakeMessage(public_key=pub, auth_tag=tag)
    return hello, PendingClientHandshake(node_id, priv, hello, psk)


def server_handshake(
    node_id: bytes,
    client_hello: HandshakeMessage,
    psk: Optional[bytes] = None,
) -> tuple[HandshakeMessage, AsconSession]:
    """Complete the server side of the key exchange.

    Parameters
    ----------
    node_id : bytes
        Identifier for this node.
    client_hello : HandshakeMessage
        The message received from the client.
    psk : bytes, optional
        Must match the client's PSK (or both must be ``None``).

    Returns
    -------
    reply : HandshakeMessage
        Send this back to the client.
    session : AsconSession
        Ready-to-use encrypted channel (server sends with s2c key,
        receives with c2s key).

    Raises
    ------
    HandshakeError
        If the client's public-key authentication tag is invalid.
    """
    verify_auth_tag(
        psk, b"client", client_hello.public_key, client_hello.auth_tag,
    )

    priv = X25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()

    client_pub_obj = X25519PublicKey.from_public_bytes(client_hello.public_key)
    shared_secret = priv.exchange(client_pub_obj)

    tag = make_auth_tag(psk, b"server", pub)
    reply = HandshakeMessage(public_key=pub, auth_tag=tag)

    # Transcript = ClientHello || ServerHello  (full wire bytes)
    transcript = client_hello.to_bytes() + reply.to_bytes()

    c2s, s2c = derive_keys(
        shared_secret, client_hello.public_key, pub, transcript,
    )
    # Server sends with s2c, receives with c2s
    session = AsconSession(send_key=s2c, recv_key=c2s, node_id=node_id)
    return reply, session
