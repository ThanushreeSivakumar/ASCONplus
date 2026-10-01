"""
HKDF-SHA256 key derivation with transcript binding.

Derives two directional 16-byte ASCON keys from a single ECDH shared
secret, using the following parameters (RFC 5869):

- **salt** = ``SHA-256(client_pub || server_pub)``
- **ikm**  = ``shared_secret || SHA-256(transcript)``
- **info** = ``b"ascon c2s"`` or ``b"ascon s2c"``
- **length** = 16  (ASCON-128 key size)
"""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_keys(
    shared_secret: bytes,
    client_pub: bytes,
    server_pub: bytes,
    transcript: bytes,
) -> tuple[bytes, bytes]:
    """Derive directional 16-byte ASCON keys with transcript binding.

    Parameters
    ----------
    shared_secret : bytes
        Raw 32-byte X25519 Diffie-Hellman output.
    client_pub, server_pub : bytes
        Raw 32-byte public keys — order matters for salt determinism.
    transcript : bytes
        Concatenated serialised handshake messages
        (``ClientHello.to_bytes() || ServerHello.to_bytes()``).

    Returns
    -------
    c2s_key, s2c_key : bytes
        Two distinct 16-byte keys, one per direction.
    """
    salt = hashlib.sha256(client_pub + server_pub).digest()
    transcript_hash = hashlib.sha256(transcript).digest()
    ikm = shared_secret + transcript_hash

    c2s = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        info=b"ascon c2s",
    ).derive(ikm)

    s2c = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        info=b"ascon s2c",
    ).derive(ikm)

    return c2s, s2c
