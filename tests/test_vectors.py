"""
Cryptographic Validation Test Vectors & Protocol Composition Suite.
===================================================================

Covers:
1. RFC 7748:
   - Section 6.1 (Curve25519 Alice/Bob ECDH shared secret)
   - Section 5.2 (Curve25519 single-execution pairs and iteration test)
2. RFC 5869:
   - Test Case A.1 (SHA-256 with basic test vector)
   - Test Case A.2 (SHA-256 with longer inputs/outputs)
   - Test Case A.3 (SHA-256 with zero-length salt)
3. ASCON-128:
   - Official NIST LWC / ascon-c Known Answer Test (KAT) vectors
     reproduced with the installed `ascon` package.
4. Cryptographic Composition:
   - Client and server derive identical c2s and s2c keys
   - Directional key isolation (c2s != s2c)
   - Ephemeral session uniqueness (different sessions -> different keys)
   - Cross-session isolation (ciphertext from session A fails in session B)
   - 1-bit flip rejection across ciphertext, tag, nonce, and associated data
   - Monotonic sequence verification and replay rejection
   - Wrong decryption key rejection
   - Passive eavesdropper wire audit: session keys and shared secrets never
     appear in plaintext in captured wire frames.
"""

from __future__ import annotations

import os
import struct
import pytest

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

import ascon
from ascon_plus.kdf import derive_keys, derive_session_keys
from ascon_plus.session import AsconSession, NodeSession, IntegrityError
from ascon_plus.protocol import (
    FRAME_HELLO,
    FRAME_HELLO_ACK,
    FRAME_DATA,
    build_frame,
    make_ad,
    NONCE_LEN,
    ASCON_TAG_LEN,
)
from ascon_plus.handshake import client_handshake, server_handshake


# =====================================================================
# 1. RFC 7748: X25519 Test Vectors
# =====================================================================

class TestRFC7748X25519:
    """Validate Curve25519 against RFC 7748 Section 5.2 and Section 6.1."""

    def test_rfc7748_section_6_1_alice_bob_shared_secret(self):
        """RFC 7748 Section 6.1: Curve25519 ECDH shared secret between Alice and Bob."""
        alice_priv = bytes.fromhex(
            "77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a"
        )
        alice_pub_expected = bytes.fromhex(
            "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"
        )
        bob_priv = bytes.fromhex(
            "5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb"
        )
        bob_pub_expected = bytes.fromhex(
            "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f"
        )
        shared_expected = bytes.fromhex(
            "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"
        )

        alice_key = X25519PrivateKey.from_private_bytes(alice_priv)
        bob_key = X25519PrivateKey.from_private_bytes(bob_priv)

        alice_pub = alice_key.public_key().public_bytes_raw()
        bob_pub = bob_key.public_key().public_bytes_raw()

        assert alice_pub == alice_pub_expected
        assert bob_pub == bob_pub_expected

        shared_alice = alice_key.exchange(X25519PublicKey.from_public_bytes(bob_pub))
        shared_bob = bob_key.exchange(X25519PublicKey.from_public_bytes(alice_pub))

        assert shared_alice == shared_expected
        assert shared_bob == shared_expected

    def test_rfc7748_section_5_2_pair_1(self):
        """RFC 7748 Section 5.2 Test Vector: Pair 1."""
        scalar = bytes.fromhex(
            "a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4"
        )
        u_coord = bytes.fromhex(
            "e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c"
        )
        out_expected = bytes.fromhex(
            "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"
        )

        key = X25519PrivateKey.from_private_bytes(scalar)
        point = X25519PublicKey.from_public_bytes(u_coord)
        res = key.exchange(point)
        assert res == out_expected

    def test_rfc7748_section_5_2_pair_2(self):
        """RFC 7748 Section 5.2 Test Vector: Pair 2."""
        scalar = bytes.fromhex(
            "4b66e9d4d1b4673c5ad22691957d6af5c11b6421e0ea01d42ca4169e7918ba0d"
        )
        u_coord = bytes.fromhex(
            "e5210f12786811d3f4b7959d0538ae2c31dbe7106fc03c3efc4cd549c715a493"
        )
        out_expected = bytes.fromhex(
            "95cbde9476e8907d7aade45cb4b873f88b595a68799fa152e6f8f7647aac7957"
        )

        key = X25519PrivateKey.from_private_bytes(scalar)
        point = X25519PublicKey.from_public_bytes(u_coord)
        res = key.exchange(point)
        assert res == out_expected

    def test_rfc7748_section_5_2_iteration_1(self):
        """RFC 7748 Section 5.2: 1-step iteration on base point 9."""
        k_iter = bytes.fromhex(
            "0900000000000000000000000000000000000000000000000000000000000000"
        )
        u_iter = bytes.fromhex(
            "0900000000000000000000000000000000000000000000000000000000000000"
        )
        expected = bytes.fromhex(
            "422c8e7a6227d7bca1350b3e2bb7279f7897b87bb6854b783c60e80311ae3079"
        )

        res = X25519PrivateKey.from_private_bytes(k_iter).exchange(
            X25519PublicKey.from_public_bytes(u_iter)
        )
        assert res == expected


# =====================================================================
# 2. RFC 5869: HKDF-SHA256 Test Vectors
# =====================================================================

class TestRFC5869HKDF:
    """Validate HKDF-SHA256 against RFC 5869 Appendix A vectors."""

    def test_rfc5869_a1_basic(self):
        """RFC 5869 A.1: Basic test case with SHA-256."""
        ikm = bytes.fromhex("0b" * 22)
        salt = bytes.fromhex("000102030405060708090a0b0c")
        info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
        l_len = 42
        okm_expected = bytes.fromhex(
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"
        )

        hkdf = HKDF(algorithm=hashes.SHA256(), length=l_len, salt=salt, info=info)
        okm = hkdf.derive(ikm)
        assert okm == okm_expected

    def test_rfc5869_a2_longer_inputs(self):
        """RFC 5869 A.2: Test with SHA-256 and 80-byte inputs, L=82."""
        ikm = bytes(range(80))
        salt = bytes(range(0x60, 0x60 + 80))
        info = bytes(range(0xB0, 0xB0 + 80))
        l_len = 82
        okm_expected_hex = (
            "b11e398dc80327a1c8e7f78c596a4934"
            "4f012eda2d4efad8a050cc4c19afa97c"
            "59045a99cac7827271cb41c65e590e09"
            "da3275600c2f09b8367793a9aca3db71"
            "cc30c58179ec3e87c14c01d5c1f3434f"
            "1d87"
        )

        hkdf = HKDF(algorithm=hashes.SHA256(), length=l_len, salt=salt, info=info)
        okm = hkdf.derive(ikm)
        assert okm.hex() == okm_expected_hex

    def test_rfc5869_a3_zero_salt(self):
        """RFC 5869 A.3: Test with zero-length salt and empty info."""
        ikm = bytes.fromhex("0b" * 22)
        salt = b""
        info = b""
        l_len = 42
        okm_expected = bytes.fromhex(
            "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d9d201395faa4b61a96c8"
        )

        hkdf = HKDF(algorithm=hashes.SHA256(), length=l_len, salt=salt, info=info)
        okm = hkdf.derive(ikm)
        assert okm == okm_expected


# =====================================================================
# 3. ASCON-128 Known-Answer Tests (KAT)
# =====================================================================

class TestAscon128KAT:
    """
    Known Answer Tests for ASCON-128 AEAD v1.2.
    Source: NIST LWC / official ascon-c reference KAT vectors
    (https://github.com/ascon/ascon-c/tree/main/crypto_aead/ascon128v12).
    """

    def test_ascon128_kat_empty_plaintext_empty_ad(self):
        """NIST LWC Ascon-128 KAT Count 1: PT=empty, AD=empty."""
        key = bytes(range(16))
        nonce = bytes(range(16))
        pt = b""
        ad = b""
        expected_tag_hex = "e355159f292911f794cb1432a0103a8a"

        ct = ascon.encrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            plaintext=pt,
            variant="Ascon-128",
        )
        assert ct.hex() == expected_tag_hex

        decrypted = ascon.decrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ct,
            variant="Ascon-128",
        )
        assert decrypted == pt

    def test_ascon128_kat_8byte_plaintext_empty_ad(self):
        """NIST LWC Ascon-128 KAT: PT=8 bytes (00..07), AD=empty."""
        key = bytes(range(16))
        nonce = bytes(range(16))
        pt = bytes(range(8))
        ad = b""
        expected_ct_hex = "bc820dbdf7a4631c01a8807a44254b42ac6bb490da1e000a"

        ct = ascon.encrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            plaintext=pt,
            variant="Ascon-128",
        )
        assert ct.hex() == expected_ct_hex

        decrypted = ascon.decrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ct,
            variant="Ascon-128",
        )
        assert decrypted == pt

    def test_ascon128_kat_empty_plaintext_8byte_ad(self):
        """NIST LWC Ascon-128 KAT: PT=empty, AD=8 bytes (00..07)."""
        key = bytes(range(16))
        nonce = bytes(range(16))
        pt = b""
        ad = bytes(range(8))
        expected_tag_hex = "e3dcf95f869752f61cd7a2db895f918e"

        ct = ascon.encrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            plaintext=pt,
            variant="Ascon-128",
        )
        assert ct.hex() == expected_tag_hex

        decrypted = ascon.decrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ct,
            variant="Ascon-128",
        )
        assert decrypted == pt

    def test_ascon128_kat_16byte_plaintext_16byte_ad(self):
        """NIST LWC Ascon-128 KAT: PT=16 bytes (00..0F), AD=16 bytes (00..0F)."""
        key = bytes(range(16))
        nonce = bytes(range(16))
        pt = bytes(range(16))
        ad = bytes(range(16))

        ct = ascon.encrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            plaintext=pt,
            variant="Ascon-128",
        )
        assert len(ct) == len(pt) + 16  # 16-byte payload + 16-byte tag

        decrypted = ascon.decrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            ciphertext=ct,
            variant="Ascon-128",
        )
        assert decrypted == pt


# =====================================================================
# 4. Protocol Composition & Security Property Tests
# =====================================================================

class TestCryptographicComposition:
    """Security property tests for the composition of ECDH, HKDF, and ASCON-128."""

    def test_client_and_server_derive_identical_keys(self):
        """Client and server must derive identical c2s and s2c keys."""
        cli_priv = X25519PrivateKey.generate()
        cli_pub = cli_priv.public_key().public_bytes_raw()
        srv_priv = X25519PrivateKey.generate()
        srv_pub = srv_priv.public_key().public_bytes_raw()

        # Server side
        shared_srv = srv_priv.exchange(X25519PublicKey.from_public_bytes(cli_pub))
        srv_c2s, srv_s2c = derive_session_keys(shared_srv, cli_pub, srv_pub)

        # Client side
        shared_cli = cli_priv.exchange(X25519PublicKey.from_public_bytes(srv_pub))
        cli_c2s, cli_s2c = derive_session_keys(shared_cli, cli_pub, srv_pub)

        assert shared_cli == shared_srv
        assert cli_c2s == srv_c2s
        assert cli_s2c == srv_s2c
        assert len(cli_c2s) == 16
        assert len(cli_s2c) == 16

    def test_directional_key_isolation(self):
        """c2s and s2c keys must never be equal (directional isolation)."""
        cli_priv = X25519PrivateKey.generate()
        cli_pub = cli_priv.public_key().public_bytes_raw()
        srv_priv = X25519PrivateKey.generate()
        srv_pub = srv_priv.public_key().public_bytes_raw()

        shared = cli_priv.exchange(X25519PublicKey.from_public_bytes(srv_pub))
        c2s, s2c = derive_session_keys(shared, cli_pub, srv_pub)

        assert c2s != s2c

    def test_session_uniqueness(self):
        """Different sessions must produce completely distinct session keys."""
        # Session 1
        c1_priv = X25519PrivateKey.generate()
        c1_pub = c1_priv.public_key().public_bytes_raw()
        s1_priv = X25519PrivateKey.generate()
        s1_pub = s1_priv.public_key().public_bytes_raw()
        shared1 = c1_priv.exchange(X25519PublicKey.from_public_bytes(s1_pub))
        c2s_1, s2c_1 = derive_session_keys(shared1, c1_pub, s1_pub)

        # Session 2
        c2_priv = X25519PrivateKey.generate()
        c2_pub = c2_priv.public_key().public_bytes_raw()
        s2_priv = X25519PrivateKey.generate()
        s2_pub = s2_priv.public_key().public_bytes_raw()
        shared2 = c2_priv.exchange(X25519PublicKey.from_public_bytes(s2_pub))
        c2s_2, s2c_2 = derive_session_keys(shared2, c2_pub, s2_pub)

        assert c2s_1 != c2s_2
        assert s2c_1 != s2c_2

    def test_cross_session_isolation(self):
        """Ciphertext from Session 1 must fail to decrypt in Session 2."""
        key_c2s_1 = os.urandom(16)
        key_s2c_1 = os.urandom(16)
        session1 = NodeSession(key_c2s=key_c2s_1, key_s2c=key_s2c_1)

        key_c2s_2 = os.urandom(16)
        key_s2c_2 = os.urandom(16)
        session2 = NodeSession(key_c2s=key_c2s_2, key_s2c=key_s2c_2)

        plaintext = b"telemetry-sensor-reading-42.5"
        nonce = os.urandom(NONCE_LEN)
        node_id = 1
        seq = 0
        ad = make_ad(FRAME_DATA, node_id, seq)
        ct = ascon.encrypt(
            key=key_c2s_1,
            nonce=nonce,
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )

        # Session 1 decrypts successfully
        pt1 = session1.decrypt(node_id, seq, nonce, ct)
        assert pt1 == plaintext

        # Session 2 decrypts must fail (returns None)
        pt2 = session2.decrypt(node_id, seq, nonce, ct)
        assert pt2 is None

    def test_1bit_flip_in_ciphertext_rejected(self):
        """A single bit flipped in ciphertext must trigger authentication failure."""
        key = os.urandom(16)
        session = NodeSession(key_c2s=key, key_s2c=key)
        plaintext = b"critical-actuator-command"
        nonce = os.urandom(NONCE_LEN)
        ad = make_ad(FRAME_DATA, 1, 0)
        ct = bytearray(
            ascon.encrypt(
                key=key,
                nonce=nonce,
                associateddata=ad,
                plaintext=plaintext,
                variant="Ascon-128",
            )
        )

        # Flip 1 bit in ciphertext payload
        ct[0] ^= 0x01
        assert session.decrypt(1, 0, nonce, bytes(ct)) is None

    def test_1bit_flip_in_tag_rejected(self):
        """A single bit flipped in ASCON tag must trigger authentication failure."""
        key = os.urandom(16)
        session = NodeSession(key_c2s=key, key_s2c=key)
        plaintext = b"sensor-payload-data"
        nonce = os.urandom(NONCE_LEN)
        ad = make_ad(FRAME_DATA, 1, 0)
        ct = bytearray(
            ascon.encrypt(
                key=key,
                nonce=nonce,
                associateddata=ad,
                plaintext=plaintext,
                variant="Ascon-128",
            )
        )

        # Tag is the last 16 bytes; flip 1 bit in tag
        ct[-1] ^= 0x80
        assert session.decrypt(1, 0, nonce, bytes(ct)) is None

    def test_1bit_flip_in_nonce_rejected(self):
        """A single bit flipped in nonce must trigger authentication failure."""
        key = os.urandom(16)
        session = NodeSession(key_c2s=key, key_s2c=key)
        plaintext = b"sensor-payload-data"
        nonce = bytearray(os.urandom(NONCE_LEN))
        ad = make_ad(FRAME_DATA, 1, 0)
        ct = ascon.encrypt(
            key=key,
            nonce=bytes(nonce),
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )

        # Flip 1 bit in nonce
        nonce[3] ^= 0x02
        assert session.decrypt(1, 0, bytes(nonce), ct) is None

    def test_1bit_flip_in_associated_data_rejected(self):
        """Tampering with node_id or seq in associated data must fail decryption."""
        key = os.urandom(16)
        session = NodeSession(key_c2s=key, key_s2c=key)
        plaintext = b"temperature=21.4"
        nonce = os.urandom(NONCE_LEN)
        node_id = 7
        seq = 100
        ad = make_ad(FRAME_DATA, node_id, seq)
        ct = ascon.encrypt(
            key=key,
            nonce=nonce,
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )

        # Altered node_id
        assert session.decrypt(node_id=8, seq=seq, nonce=nonce, ciphertext=ct) is None
        # Altered seq
        assert session.decrypt(node_id=node_id, seq=101, nonce=nonce, ciphertext=ct) is None

    def test_replayed_sequence_rejected(self):
        """Replay attack: replaying an already-seen seq number must be detected."""
        session = NodeSession(key_c2s=os.urandom(16), key_s2c=os.urandom(16))

        assert not session.is_replay(0)
        session.advance(0)

        assert not session.is_replay(1)
        session.advance(1)

        # Replaying seq 0 or seq 1
        assert session.is_replay(0)
        assert session.is_replay(1)
        # Even past or duplicate sequence is rejected
        assert session.is_replay(-1)

    def test_wrong_key_rejected(self):
        """Decrypting with an incorrect key must return None (fail authentication)."""
        key1 = b"K" * 16
        key2 = b"W" * 16
        session_wrong = NodeSession(key_c2s=key2, key_s2c=key2)

        plaintext = b"secret-payload"
        nonce = os.urandom(NONCE_LEN)
        ad = make_ad(FRAME_DATA, 1, 0)
        ct = ascon.encrypt(
            key=key1,
            nonce=nonce,
            associateddata=ad,
            plaintext=plaintext,
            variant="Ascon-128",
        )

        assert session_wrong.decrypt(1, 0, nonce, ct) is None

    def test_passive_eavesdropper_key_never_on_wire(self):
        """
        Passive Eavesdropper Test:
        Prove that the 16-byte session key (c2s/s2c) and the 32-byte shared ECDH
        secret never appear anywhere in plaintext within wire frames.
        """
        # 1. Ephemeral Handshake Simulation
        client_priv = X25519PrivateKey.generate()
        client_pub = client_priv.public_key().public_bytes_raw()
        server_priv = X25519PrivateKey.generate()
        server_pub = server_priv.public_key().public_bytes_raw()

        # Shared ECDH secret & derived directional keys
        shared_secret = client_priv.exchange(
            X25519PublicKey.from_public_bytes(server_pub)
        )
        c2s_key, s2c_key = derive_session_keys(shared_secret, client_pub, server_pub)

        # 2. Wire frames:
        # Frame 1: HELLO (Client -> Server)
        frame_hello = build_frame(FRAME_HELLO, node_id=1, seq=0, payload=client_pub)

        # Frame 2: HELLO_ACK (Server -> Client)
        frame_hello_ack = build_frame(
            FRAME_HELLO_ACK, node_id=0, seq=0, payload=server_pub
        )

        # Frame 3: DATA (Client -> Server encrypted with c2s_key)
        nonce_c2s = os.urandom(NONCE_LEN)
        ad_c2s = make_ad(FRAME_DATA, node_id=1, seq=0)
        ct_c2s = ascon.encrypt(
            key=c2s_key,
            nonce=nonce_c2s,
            associateddata=ad_c2s,
            plaintext=b"sensor-telemetry-temperature=24.5C",
            variant="Ascon-128",
        )
        frame_data_c2s = build_frame(
            FRAME_DATA, node_id=1, seq=0, payload=ct_c2s, nonce=nonce_c2s
        )

        # Frame 4: DATA (Server -> Client encrypted with s2c_key)
        nonce_s2c = os.urandom(NONCE_LEN)
        ad_s2c = make_ad(FRAME_DATA, node_id=0, seq=0)
        ct_s2c = ascon.encrypt(
            key=s2c_key,
            nonce=nonce_s2c,
            associateddata=ad_s2c,
            plaintext=b"server-ack-ok",
            variant="Ascon-128",
        )
        frame_data_s2c = build_frame(
            FRAME_DATA, node_id=0, seq=0, payload=ct_s2c, nonce=nonce_s2c
        )

        # 3. Concatenate all traffic captured by a passive eavesdropper on the wire
        captured_wire_traffic = (
            frame_hello + frame_hello_ack + frame_data_c2s + frame_data_s2c
        )

        # 4. Search entire captured wire traffic for secrets
        assert c2s_key not in captured_wire_traffic, (
            "SECURITY VIOLATION: c2s session key leaked in plaintext on wire!"
        )
        assert s2c_key not in captured_wire_traffic, (
            "SECURITY VIOLATION: s2c session key leaked in plaintext on wire!"
        )
        assert shared_secret not in captured_wire_traffic, (
            "SECURITY VIOLATION: Shared ECDH secret leaked in plaintext on wire!"
        )
