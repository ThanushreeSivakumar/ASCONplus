# Cryptographic Protocol & Test Vector Validation Report

> **Target Standard**: RFC 7748 (Curve25519), RFC 5869 (HKDF-SHA256), NIST LWC SP 800-232 / ascon-c Reference KAT (ASCON-128)  
> **Test Harness**: `pytest tests/test_vectors.py -v`  
> **Execution Status**: **22 / 22 PASSED** (100% pass rate)

---

## 1. Summary of Cryptographic Validation

This document establishes the empirical correctness and security properties of the ASCON+ cryptographic primitives and their composition. Every cryptographic operation in ASCON+ has been evaluated against official Internet Engineering Task Force (IETF) and National Institute of Standards and Technology (NIST) reference vectors, as well as formal composite security properties.

---

## 2. Validation Matrix: Test Vectors & Security Properties

| Test ID | Module & Function | Specification / Standard | What It Proves | Result |
| :--- | :--- | :--- | :--- | :---: |
| **X25519-01** | `test_rfc7748_section_6_1_alice_bob_shared_secret` | RFC 7748 §6.1 | Alice and Bob derive the exact standard shared secret `4a5d...1742` from standard private keys `7707...` and `5dab...`. Validates ECDH scalar multiplication and public key generation. | **PASS** |
| **X25519-02** | `test_rfc7748_section_5_2_pair_1` | RFC 7748 §5.2 Pair 1 | Arbitrary scalar multiplication $X25519(k, u)$ yields exact standard $u$-coordinate output `c3da...8552`. | **PASS** |
| **X25519-03** | `test_rfc7748_section_5_2_pair_2` | RFC 7748 §5.2 Pair 2 | Second distinct scalar multiplication pair yields exact standard $u$-coordinate output `95cb...7957`. | **PASS** |
| **X25519-04** | `test_rfc7748_section_5_2_iteration_1` | RFC 7748 §5.2 Chaining | One-step iterative base-point scalar multiplication matches standard output `422c...3079`. | **PASS** |
| **HKDF-01** | `test_rfc5869_a1_basic` | RFC 5869 Appendix A.1 | Basic HKDF-SHA256 extraction and expansion produces standard 42-byte OKM `3cb2...5865`. | **PASS** |
| **HKDF-02** | `test_rfc5869_a2_longer_inputs` | RFC 5869 Appendix A.2 | Long-input HKDF-SHA256 with 80-byte IKM, salt, and info produces exact 82-byte OKM `b11e...1d87`. | **PASS** |
| **HKDF-03** | `test_rfc5869_a3_zero_salt` | RFC 5869 Appendix A.3 | Zero-salt HKDF-SHA256 correctly defaults to HashLen zero-octets and derives exact standard 42-byte OKM `8da4...96c8`. | **PASS** |
| **ASCON-01** | `test_ascon128_kat_empty_plaintext_empty_ad` | NIST LWC / ascon-c KAT Count 1 | Empty plaintext and empty AD with key/nonce `00..0F` produces official NIST KAT tag `e355159f292911f794cb1432a0103a8a`. Validates initialization, permutation, and finalization. | **PASS** |
| **ASCON-02** | `test_ascon128_kat_8byte_plaintext_empty_ad` | NIST LWC / ascon-c KAT | 8-byte plaintext (`00..07`) produces exact NIST KAT ciphertext and tag `bc82...000a`. Decryption restores original plaintext. | **PASS** |
| **ASCON-03** | `test_ascon128_kat_empty_plaintext_8byte_ad` | NIST LWC / ascon-c KAT | 8-byte associated data (`00..07`) without plaintext yields exact NIST KAT authentication tag `e3dcf95f869752f61cd7a2db895f918e`. | **PASS** |
| **ASCON-04** | `test_ascon128_kat_16byte_plaintext_16byte_ad` | NIST LWC / ascon-c KAT | Full 16-byte block plaintext + 16-byte AD correctly encrypts and authenticates. | **PASS** |
| **COMP-01** | `test_client_and_server_derive_identical_keys` | ASCON+ Protocol Spec | Client and Server independently derive identical `c2s_key` and `s2c_key` from ephemeral public keys and shared ECDH secret. | **PASS** |
| **COMP-02** | `test_directional_key_isolation` | ASCON+ Protocol Spec | Directional keys are strictly distinct (`c2s_key != s2c_key`), preventing reflection and cross-direction frame injection attacks. | **PASS** |
| **COMP-03** | `test_session_uniqueness` | ASCON+ Forward Secrecy | Independent sessions generate distinct ephemeral secrets (`c2s_1 != c2s_2`, `s2c_1 != s2c_2`), ensuring session forward secrecy. | **PASS** |
| **COMP-04** | `test_cross_session_isolation` | ASCON+ Session Bound | Ciphertext sealed under Session A fails AEAD authentication when presented to Session B (`decrypt() is None`). | **PASS** |
| **COMP-05** | `test_1bit_flip_in_ciphertext_rejected` | AEAD Integrity | Flipping any single bit in the ciphertext payload causes AEAD authentication failure. | **PASS** |
| **COMP-06** | `test_1bit_flip_in_tag_rejected` | AEAD Integrity | Flipping any single bit in the 16-byte authentication tag causes AEAD authentication failure. | **PASS** |
| **COMP-07** | `test_1bit_flip_in_nonce_rejected` | AEAD Integrity | Flipping any single bit in the 16-byte nonce causes AEAD authentication failure. | **PASS** |
| **COMP-08** | `test_1bit_flip_in_associated_data_rejected` | Anti-Spoofing / AD Bound | Tampering with `node_id` or `seq` in the Associated Data causes AEAD authentication failure, preventing node impersonation and re-sequencing. | **PASS** |
| **COMP-09** | `test_replayed_sequence_rejected` | Anti-Replay Monotonicity | Duplicate or backward sequence numbers are detected and rejected (`is_replay(seq) == True`). | **PASS** |
| **COMP-10** | `test_wrong_key_rejected` | AEAD Key Authenticity | Decrypting ciphertext with an mismatched 16-byte key fails authentication. | **PASS** |
| **COMP-11** | `test_passive_eavesdropper_key_never_on_wire` | Wire Secrecy / Passive MITM | Full wire capture of handshake (`FRAME_HELLO`, `FRAME_HELLO_ACK`) and data frames (`FRAME_DATA`) contains zero instances of `c2s_key`, `s2c_key`, or the 32-byte shared ECDH secret. | **PASS** |

---

## 3. Actual Pytest Output Transcript

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\thanu\OneDrive\Desktop\ASCONplus
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 22 items

tests/test_vectors.py::TestRFC7748X25519::test_rfc7748_section_6_1_alice_bob_shared_secret PASSED [  4%]
tests/test_vectors.py::TestRFC7748X25519::test_rfc7748_section_5_2_pair_1 PASSED [  9%]
tests/test_vectors.py::TestRFC7748X25519::test_rfc7748_section_5_2_pair_2 PASSED [ 13%]
tests/test_vectors.py::TestRFC7748X25519::test_rfc7748_section_5_2_iteration_1 PASSED [ 18%]
tests/test_vectors.py::TestRFC5869HKDF::test_rfc5869_a1_basic PASSED     [ 22%]
tests/test_vectors.py::TestRFC5869HKDF::test_rfc5869_a2_longer_inputs PASSED [ 27%]
tests/test_vectors.py::TestRFC5869HKDF::test_rfc5869_a3_zero_salt PASSED [ 31%]
tests/test_vectors.py::TestAscon128KAT::test_ascon128_kat_empty_plaintext_empty_ad PASSED [ 36%]
tests/test_vectors.py::TestAscon128KAT::test_ascon128_kat_8byte_plaintext_empty_ad PASSED [ 40%]
tests/test_vectors.py::TestAscon128KAT::test_ascon128_kat_empty_plaintext_8byte_ad PASSED [ 45%]
tests/test_vectors.py::TestAscon128KAT::test_ascon128_kat_16byte_plaintext_16byte_ad PASSED [ 50%]
tests/test_vectors.py::TestCryptographicComposition::test_client_and_server_derive_identical_keys PASSED [ 54%]
tests/test_vectors.py::TestCryptographicComposition::test_directional_key_isolation PASSED [ 59%]
tests/test_vectors.py::TestCryptographicComposition::test_session_uniqueness PASSED [ 63%]
tests/test_vectors.py::TestCryptographicComposition::test_cross_session_isolation PASSED [ 68%]
tests/test_vectors.py::TestCryptographicComposition::test_1bit_flip_in_ciphertext_rejected PASSED [ 72%]
tests/test_vectors.py::TestCryptographicComposition::test_1bit_flip_in_tag_rejected PASSED [ 77%]
tests/test_vectors.py::TestCryptographicComposition::test_1bit_flip_in_nonce_rejected PASSED [ 81%]
tests/test_vectors.py::TestCryptographicComposition::test_1bit_flip_in_associated_data_rejected PASSED [ 86%]
tests/test_vectors.py::TestCryptographicComposition::test_replayed_sequence_rejected PASSED [ 90%]
tests/test_vectors.py::TestCryptographicComposition::test_wrong_key_rejected PASSED [ 95%]
tests/test_vectors.py::TestCryptographicComposition::test_passive_eavesdropper_key_never_on_wire PASSED [100%]

============================= 22 passed in 0.09s ==============================
```
