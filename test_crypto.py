#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECDH + ASCON Cryptographic Handshake Simulation
Target: Raspberry Pi Zero W (ARMv6, 512MB RAM)

Architecture:
  Phase 1: Ephemeral X25519 ECDH key exchange
  Phase 2: HKDF-SHA256 key derivation  -> 16-byte symmetric key
  Phase 3: ASCON-128 AEAD encrypt/decrypt of sensor payload

Author : IoT Security Demo
"""

import os
import sys

# Force UTF-8 stdout so Unicode box-drawing characters render correctly on
# Windows consoles that default to cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Phase 1 & 2 dependencies (from system apt or pip) ────────────────────────
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

# ── Phase 3 dependency (pure-Python, pip install ascon) ──────────────────────
import ascon


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def section(title: str) -> None:
    """Print a clearly delimited section header."""
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def pass_label(description: str) -> None:
    print(f"  [PASS]  {description}")


def fail_label(description: str) -> None:
    print(f"  [FAIL]  {description}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Ephemeral ECDH Key Exchange (X25519)
# ─────────────────────────────────────────────────────────────────────────────

def phase1_ecdh() -> tuple[bytes, bytes]:
    """
    Simulate an ephemeral X25519 handshake between a CLIENT and SERVER.

    Both parties:
      1. Generate a fresh ephemeral private key (discarded after this session).
      2. Derive their public key.
      3. Exchange public keys (simulated in-process).
      4. Compute the Diffie-Hellman shared secret independently.

    Returns
    -------
    client_secret, server_secret : bytes
        The raw 32-byte shared secrets computed by each party.
        They MUST be equal for the handshake to succeed.
    """
    section("Phase 1 · Ephemeral X25519 ECDH Key Exchange")

    # --- Client side ---
    client_private = X25519PrivateKey.generate()
    client_public  = client_private.public_key()
    print(f"  CLIENT private key generated  (ephemeral, in-memory only)")
    print(f"  CLIENT public  key  : {client_public.public_bytes_raw().hex()}")

    # --- Server side ---
    server_private = X25519PrivateKey.generate()
    server_public  = server_private.public_key()
    print(f"\n  SERVER private key generated  (ephemeral, in-memory only)")
    print(f"  SERVER public  key  : {server_public.public_bytes_raw().hex()}")

    # --- DH computation ---
    #   client computes:  client_private  × server_public
    #   server computes:  server_private  × client_public
    client_secret = client_private.exchange(server_public)
    server_secret = server_private.exchange(client_public)

    print(f"\n  CLIENT shared secret: {client_secret.hex()}")
    print(f"  SERVER shared secret: {server_secret.hex()}")

    # Sanity check: both sides must arrive at the same secret
    if client_secret == server_secret:
        pass_label("Shared secrets match — ECDH handshake successful")
    else:
        fail_label("Shared secrets DO NOT match — aborting")

    return client_secret, server_secret


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — HKDF-SHA256 Key Derivation
# ─────────────────────────────────────────────────────────────────────────────

def phase2_hkdf(client_secret: bytes, server_secret: bytes) -> tuple[bytes, bytes]:
    """
    Derive a 16-byte symmetric key from the raw ECDH shared secret using HKDF.

    Parameters  (RFC 5869)
    ----------
    salt : None   — no salt (acceptable when the input keying material already
                    has high entropy, as X25519 output does)
    info : b"ascon-key"  — context string binding this key to the ASCON cipher
    length : 16  — ASCON-128 uses a 128-bit (16-byte) key

    Both client and server derive their key independently from their own copy of
    the shared secret; the derived keys MUST be identical.

    Returns
    -------
    client_key, server_key : bytes  (each 16 bytes)
    """
    section("Phase 2 · HKDF-SHA256 Key Derivation  →  16-byte ASCON Key")

    def derive(raw_secret: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=None,
            info=b"ascon-key",
        ).derive(raw_secret)

    client_key = derive(client_secret)
    server_key = derive(server_secret)

    print(f"  CLIENT derived key  : {client_key.hex()}  ({len(client_key)} bytes)")
    print(f"  SERVER derived key  : {server_key.hex()}  ({len(server_key)} bytes)")

    if client_key == server_key:
        pass_label("Derived keys are identical — HKDF derivation successful")
    else:
        fail_label("Derived keys differ — aborting")

    return client_key, server_key


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — ASCON-128 AEAD Encrypt / Decrypt
# ─────────────────────────────────────────────────────────────────────────────

def phase3_ascon(key: bytes) -> None:
    """
    Encrypt and decrypt a simulated sensor payload using ASCON-128.

    ASCON-128 is a NIST-standardised lightweight AEAD cipher (FIPS 202),
    optimised for constrained devices such as the Raspberry Pi Zero W.

    Nonce       : 16 random bytes (os.urandom — unique per message)
    Associated  : b""  (empty in this demo; use session-ID in production)
    Plaintext   : b"Sensor Data: 45.2C"
    Variant     : "Ascon-128"
    """
    section("Phase 3 · ASCON-128 AEAD Encrypt → Transmit → Decrypt")

    plaintext       = b"Sensor Data: 45.2C"
    associated_data = b""                        # bind to context in production
    nonce           = os.urandom(16)             # must be unique per encryption

    print(f"  Payload (plaintext) : {plaintext}")
    print(f"  Key                 : {key.hex()}  ({len(key)} bytes)")
    print(f"  Nonce               : {nonce.hex()}  ({len(nonce)} bytes)")

    # --- Encrypt (CLIENT side) ---
    ciphertext = ascon.encrypt(
        key=key,
        nonce=nonce,
        associateddata=associated_data,
        plaintext=plaintext,
        variant="Ascon-128",
    )
    print(f"\n  Ciphertext (hex)    : {ciphertext.hex()}")
    print(f"  Ciphertext length   : {len(ciphertext)} bytes "
          f"(plaintext {len(plaintext)} + 16-byte auth tag)")

    # --- Decrypt (SERVER side, using same key & nonce) ---
    recovered = ascon.decrypt(
        key=key,
        nonce=nonce,
        associateddata=associated_data,
        ciphertext=ciphertext,
        variant="Ascon-128",
    )
    print(f"\n  Recovered plaintext : {recovered}")

    if recovered == plaintext:
        pass_label("Decrypted payload matches original — ASCON-128 round-trip successful")
    else:
        fail_label("Decryption mismatch — aborting")

    # Extra guard: tamper with ciphertext and verify authentication failure.
    # NOTE: ascon.decrypt returns None (not an exception) when the
    # authentication tag verification fails — this is the library's API contract.
    tampered = bytes([ciphertext[0] ^ 0xFF]) + ciphertext[1:]
    tamper_result = ascon.decrypt(
        key=key,
        nonce=nonce,
        associateddata=associated_data,
        ciphertext=tampered,
        variant="Ascon-128",
    )
    if tamper_result is None:
        pass_label("Tampered ciphertext correctly rejected (decrypt returned None — auth tag invalid)")
    else:
        fail_label("Authentication should have failed on tampered ciphertext — aborting")


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "#" * 60)
    print("  ECDH + ASCON Cryptographic Handshake - IoT Node Demo")
    print("  Target: Raspberry Pi Zero W  (ARMv6 / 512 MB RAM)")
    print("#" * 60)

    # Phase 1 — ECDH
    client_secret, server_secret = phase1_ecdh()

    # Phase 2 — HKDF
    client_key, _ = phase2_hkdf(client_secret, server_secret)

    # Phase 3 — ASCON (use client's derived key; server's is identical)
    phase3_ascon(client_key)

    section("Summary")
    print("  All three phases completed successfully.\n")
    print("  +-----------------------------------------------------+")
    print("  |  Phase 1  Ephemeral X25519 ECDH     [PASS]         |")
    print("  |  Phase 2  HKDF-SHA256 derivation    [PASS]         |")
    print("  |  Phase 3  ASCON-128 AEAD enc/dec    [PASS]         |")
    print("  +-----------------------------------------------------+\n")


if __name__ == "__main__":
    main()
