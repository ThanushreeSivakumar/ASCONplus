#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline: Original single-key ECDH + ASCON flow (for comparison).

This implements the *original* paper's approach:
  - Single ECDH shared secret → single ASCON key (no directional split)
  - No PSK authentication (vulnerable to active MITM)
  - No transcript binding
  - Empty associated data (no node_id / seq_no binding)
  - No sequence numbering or replay protection

Used as a **performance and security comparison baseline** against the
ASCON+ protocol implemented in ``ascon_plus/``.
"""

import os
import time

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import ascon


def baseline_handshake() -> tuple[bytes, bytes, bytes]:
    """Simple unauthenticated ECDH → single shared key.

    Returns (key, client_pub_hex, server_pub_hex) for display.
    """
    client_priv = X25519PrivateKey.generate()
    server_priv = X25519PrivateKey.generate()

    client_pub = client_priv.public_key().public_bytes_raw()
    server_pub = server_priv.public_key().public_bytes_raw()

    shared = client_priv.exchange(server_priv.public_key())

    key = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=None,              # ← no salt
        info=b"ascon-key",      # ← single key, no direction
    ).derive(shared)

    return key, client_pub.hex(), server_pub.hex()


def baseline_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Single-key ASCON-128, empty AD."""
    nonce = os.urandom(16)
    ct = ascon.encrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",     # ← empty (no node_id / seq)
        plaintext=plaintext,
        variant="Ascon-128",
    )
    return nonce + ct


def baseline_decrypt(key: bytes, message: bytes) -> bytes:
    """Single-key ASCON-128 decrypt."""
    nonce, ct = message[:16], message[16:]
    pt = ascon.decrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",
        ciphertext=ct,
        variant="Ascon-128",
    )
    if pt is None:
        raise RuntimeError("Decryption failed")
    return pt


def main() -> None:
    print("=" * 60)
    print("  Baseline: Single-key ECDH + ASCON (original paper flow)")
    print("=" * 60)

    key, cpub, spub = baseline_handshake()
    print(f"\n  Client pub : {cpub}")
    print(f"  Server pub : {spub}")
    print(f"  Shared key : {key.hex()}  (single, bidirectional)")

    payload = b"Sensor Data: 45.2C"
    t0 = time.perf_counter()
    msg = baseline_encrypt(key, payload)
    enc_us = (time.perf_counter() - t0) * 1e6

    t0 = time.perf_counter()
    recovered = baseline_decrypt(key, msg)
    dec_us = (time.perf_counter() - t0) * 1e6

    print(f"\n  Plaintext   : {payload}")
    print(f"  Ciphertext  : {msg.hex()[:48]}...")
    print(f"  Recovered   : {recovered}")
    print(f"\n  Encrypt     : {enc_us:.0f} µs")
    print(f"  Decrypt     : {dec_us:.0f} µs")

    assert recovered == payload

    print("\n  Limitations of this baseline:")
    print("    ✗  No public-key authentication   → active MITM vulnerable")
    print("    ✗  Single key for both directions  → key compromise exposes all")
    print("    ✗  No transcript binding            → session confusion possible")
    print("    ✗  Empty associated data            → no replay / reorder guard")
    print("    ✗  No sequence numbering            → replayed packets accepted")
    print()


if __name__ == "__main__":
    main()
