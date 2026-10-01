# Architecture

## System Overview

ASCON+ implements a **gateway-based, star-topology** IoT architecture
where constrained sensor nodes communicate with a central gateway via
PSK-authenticated, ASCON-128 encrypted channels.

```
                        ┌──────────────┐
                        │   Gateway    │
                        │  (Pi 4 / VM) │
                        └──────┬───────┘
                               │ TCP
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
        │  Node 01   │   │  Node 02   │   │  Node N    │
        │ (Pi Zero W)│   │ (Pi Zero W)│   │ (Pi Zero W)│
        └────────────┘   └────────────┘   └────────────┘
```

## Component Map

| Component | Module | Responsibility |
|-----------|--------|----------------|
| Protocol | `ascon_plus/protocol.py` | Wire format, frame encode/decode, `HandshakeMessage` serde |
| Auth | `ascon_plus/auth.py` | PSK-HMAC tag generation and verification |
| KDF | `ascon_plus/kdf.py` | HKDF-SHA256, transcript-bound, directional key derivation |
| Session | `ascon_plus/session.py` | `seal()` / `open()`, sequence numbering, AD binding |
| Handshake | `ascon_plus/handshake.py` | Orchestrates ECDH + auth + KDF → `AsconSession` |
| Node Client | `apps/node_client.py` | TCP client, handshake, sensor read loop |
| Gateway Server | `apps/gateway_server.py` | TCP listener, session table, concurrent handler threads |

## Data Flow

```
Node                                          Gateway
 │                                              │
 │──── ClientHello (pub_c, HMAC_c) ────────────▶│
 │                                              │ verify HMAC_c
 │◀─── ServerHello (pub_s, HMAC_s) ────────────│
 │ verify HMAC_s                                │
 │                                              │
 │ derive c2s, s2c keys                         │ derive c2s, s2c keys
 │                                              │
 │──── seal(payload, c2s_key, AD) ─────────────▶│
 │                                              │ open(ct, c2s_key, AD)
 │◀─── seal(ack, s2c_key, AD) ────────────────│
 │ open(ct, s2c_key, AD)                        │
 │                                              │
```

## Key Design Decisions

1. **X25519 over ECDSA** — smaller keys (32 B), constant-time, no curve-related side channels.
2. **PSK-HMAC over Ed25519** — cheapest MITM fix; avoids certificate infrastructure for constrained networks.
3. **Directional keys** — compromise of c2s key does not expose s2c traffic.
4. **Transcript binding** — keys are bound to the exact handshake, preventing session confusion.
5. **ASCON-128** — NIST lightweight AEAD standard; pure-Python implementation fits the Pi Zero W's 512 MB RAM.
6. **`node_id || seq_no` in AD** — binds every ciphertext to its sender and position in the stream.
