# Protocol Specification

## 1. Handshake

### 1.1 Message Format

Each handshake message is length-prefixed on the wire:

```
┌──────────┬──────────────┬──────────┬───────────┐
│ pk_len   │ public_key   │ tag_len  │ auth_tag  │
│ (2 B BE) │ (32 B)       │ (2 B BE) │ (0 or 32) │
└──────────┴──────────────┴──────────┴───────────┘
```

- **pk_len**: big-endian uint16, always 32 for X25519.
- **public_key**: raw X25519 public key bytes.
- **tag_len**: 32 when PSK is used, 0 otherwise.
- **auth_tag**: `HMAC-SHA256(PSK, label || public_key)` where label is `b"client"` or `b"server"`.

### 1.2 Steps

```
1. Client → Server:  ClientHello { pub_c, HMAC(PSK, "client" || pub_c) }
2. Server:           verify HMAC, generate ephemeral key pair
3. Server → Client:  ServerHello { pub_s, HMAC(PSK, "server" || pub_s) }
4. Client:           verify HMAC
5. Both:             compute shared_secret = X25519(priv, remote_pub)
6. Both:             derive keys (see §2)
```

### 1.3 Authentication

| Mode | PSK | Defence |
|------|-----|---------|
| Authenticated | Pre-provisioned PSK | Passive + active MITM |
| Unauthenticated | `None` | Passive eavesdropping only |

## 2. Key Derivation

```
salt       = SHA-256(client_pub || server_pub)
transcript = ClientHello.to_bytes() || ServerHello.to_bytes()
ikm        = shared_secret || SHA-256(transcript)

c2s_key    = HKDF-SHA256(salt, ikm, info="ascon c2s", length=16)
s2c_key    = HKDF-SHA256(salt, ikm, info="ascon s2c", length=16)
```

## 3. Data Frame Format

```
┌────────────┬──────────┬──────────────────────┐
│ nonce      │ seq_no   │ ciphertext + tag      │
│ (16 B)     │ (8 B BE) │ (N + 16 B)           │
└────────────┴──────────┴──────────────────────┘
```

**Total frame size**: `24 + plaintext_len + 16` bytes.

### 3.1 Associated Data

```
AD = node_id || seq_no (8 B, big-endian)
```

The AD is **not** transmitted in the frame (the receiver reconstructs it
from known `sender_node_id` and the `seq_no` field).

### 3.2 ASCON-128 Parameters

| Parameter | Value |
|-----------|-------|
| Variant | Ascon-128 |
| Key size | 16 bytes (128 bits) |
| Nonce size | 16 bytes |
| Tag size | 16 bytes |

## 4. Sequence Numbers

- **Monotonically increasing** uint64, starts at 0.
- Sender increments after each `seal()`.
- Receiver checks that ASCON authentication succeeds (which implicitly validates the seq in AD).

## 5. Rekey (Future Work)

Planned: after 2³² messages or a configurable time interval, both sides
trigger a new handshake within the existing TCP connection to derive
fresh session keys.
