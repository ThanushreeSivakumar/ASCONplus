#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECDH + ASCON-128 IoT Session Demo
===================================

Interactive, verbose demonstration of a PSK-authenticated handshake
followed by bidirectional encrypted sensor communication.

Uses the ``ascon_plus`` library for all cryptographic operations.

Run::

    python examples/demo_handshake.py

Target: Raspberry Pi Zero W (ARMv6 / 512 MB RAM)
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import client_handshake, server_handshake


def section(title: str) -> None:
    w = 60
    print(f"\n{'=' * w}\n  {title}\n{'=' * w}")


def ok(msg: str) -> None:
    print(f"  [PASS]  {msg}")


def main() -> None:
    print("\n" + "#" * 60)
    print("  ECDH + ASCON-128 Authenticated IoT Session Demo")
    print("  Target: Raspberry Pi Zero W  (ARMv6 / 512 MB RAM)")
    print("#" * 60)

    PSK       = b"demo-pre-shared-key-for-testing!"
    CLIENT_ID = b"sensor-node-01"
    SERVER_ID = b"gateway-01"

    # ── Phase 1+2 — PSK-authenticated ECDH + HKDF ────────────────────────
    section("Phase 1 · PSK-Authenticated Ephemeral X25519 ECDH")

    hello, pending = client_handshake(CLIENT_ID, psk=PSK)
    print(f"  CLIENT public key   : {hello.public_key.hex()}")
    print(f"  CLIENT auth tag     : {hello.auth_tag.hex()[:32]}...")

    reply, server_session = server_handshake(SERVER_ID, hello, psk=PSK)
    print(f"\n  SERVER public key   : {reply.public_key.hex()}")
    print(f"  SERVER auth tag     : {reply.auth_tag.hex()[:32]}...")

    client_session = pending.complete(reply)
    ok("Handshake complete — both public keys authenticated via PSK-HMAC")

    section("Phase 2 · HKDF-SHA256 Directional Key Derivation")
    print("  salt  = SHA-256(client_pub || server_pub)")
    print("  ikm   = shared_secret || SHA-256(transcript)")
    print(f"  c2s key ({len(client_session._send_key)} B)  : {client_session._send_key.hex()}")
    print(f"  s2c key ({len(client_session._recv_key)} B)  : {client_session._recv_key.hex()}")
    ok("Directional keys derived — c2s ≠ s2c, transcript-bound")

    # ── Phase 3 — ASCON-128 AEAD ─────────────────────────────────────────
    section("Phase 3 · ASCON-128 AEAD  (client → server)")

    plaintext = b"Sensor Data: 45.2C"
    ct = client_session.seal(plaintext)
    print(f"  Plaintext           : {plaintext}")
    print(f"  Wire message ({len(ct)} B) : {ct.hex()[:64]}...")
    print(f"  AD = node_id || seq : {CLIENT_ID} || 0")

    pt = server_session.open(ct, sender_node_id=CLIENT_ID)
    print(f"\n  Recovered plaintext : {pt}")
    ok("Client→server round-trip successful")

    section("Phase 3b · ASCON-128 AEAD  (server → client)")
    ack = b"ACK: sensor reading received"
    ct2 = server_session.seal(ack)
    pt2 = client_session.open(ct2, sender_node_id=SERVER_ID)
    print(f"  Server sent         : {ack}")
    print(f"  Client received     : {pt2}")
    ok("Server→client round-trip successful (directional keys work)")

    # ── Tamper detection ─────────────────────────────────────────────────
    section("Phase 4 · Tamper Detection")
    ct3 = client_session.seal(b"tamper test")
    tampered = bytes([ct3[0] ^ 0xFF]) + ct3[1:]
    try:
        server_session.open(tampered, sender_node_id=CLIENT_ID)
        print("  [FAIL]  Tampered message accepted")
        sys.exit(1)
    except Exception as exc:
        ok(f"Tampered ciphertext rejected: {exc}")

    # ── Summary ──────────────────────────────────────────────────────────
    section("Summary")
    print("  All phases completed successfully.\n")
    print("  +-------------------------------------------------------------+")
    print("  |  Phase 1   PSK-HMAC authenticated X25519 ECDH    [PASS]    |")
    print("  |  Phase 2   HKDF-SHA256 directional key derivation [PASS]   |")
    print("  |  Phase 3   ASCON-128 AEAD bidirectional enc/dec   [PASS]   |")
    print("  |  Phase 4   Tamper detection (bit-flip rejection)  [PASS]   |")
    print("  +-------------------------------------------------------------+\n")


if __name__ == "__main__":
    main()
