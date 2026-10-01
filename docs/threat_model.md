# Threat Model

## Scope

ASCON+ secures the communication channel between IoT sensor nodes and a
central gateway in a star-topology deployment.

## Assets

| Asset | Description |
|-------|-------------|
| Sensor data | Temperature, humidity, and other readings in transit |
| Session keys | Ephemeral ASCON-128 keys derived per handshake |
| PSK | Pre-shared key stored on each node and the gateway |
| Node identity | `node_id` bound into ASCON associated data |

## Adversary Model

### What we defend against ✓

| Threat | Mitigation |
|--------|------------|
| **Passive eavesdropping** | All data encrypted with ASCON-128 AEAD; ephemeral X25519 provides forward secrecy |
| **Active MITM (with PSK)** | PSK-HMAC authenticates both public keys; attacker cannot forge tags without the PSK |
| **Message tampering** | ASCON-128 authentication tag detects any modification |
| **Message truncation** | Minimum frame size check + ASCON tag verification |
| **Replay attacks** | `node_id || seq_no` in associated data; replayed frames fail AD check |
| **Session confusion** | Transcript binding: keys are derived from the full handshake transcript |
| **Key reuse across directions** | Separate c2s and s2c keys via distinct HKDF info labels |

### What we do NOT defend against ✗

| Threat | Status | Notes |
|--------|--------|-------|
| **Active MITM (no PSK)** | ✗ Not defended | Without PSK, handshake is unauthenticated — plain ECDH stops only passive attackers |
| **PSK compromise** | ✗ Limited | If the PSK is leaked, attacker can impersonate any node. Rotate PSKs regularly |
| **Physical node compromise** | ✗ Out of scope | Attacker with physical access to a node can extract the PSK and session keys |
| **Denial of service** | ✗ Out of scope | No rate limiting or connection throttling implemented |
| **Side-channel attacks** | ✗ Partially | X25519 is constant-time; ASCON pure-Python may leak timing information |
| **Traffic analysis** | ✗ Not defended | Message sizes and timing are visible; no padding or cover traffic |
| **Key exhaustion** | ✗ Future work | Rekeying after 2³² messages not yet implemented |

## Trust Assumptions

1. **PSK provisioning is secure**: PSKs are loaded onto nodes before deployment via a secure, out-of-band channel.
2. **Platform integrity**: The Raspberry Pi OS and Python runtime are not compromised.
3. **Random number generator**: `os.urandom()` provides cryptographically secure randomness.
4. **Network layer**: TCP provides reliable, ordered delivery (but is not trusted for confidentiality or integrity — ASCON provides those).

## Comparison with Baseline

| Property | Baseline (original paper) | ASCON+ |
|----------|--------------------------|--------|
| MITM defence | ✗ None | ✓ PSK-HMAC |
| Forward secrecy | ✓ Ephemeral ECDH | ✓ Ephemeral ECDH |
| Directional keys | ✗ Single key | ✓ c2s ≠ s2c |
| Transcript binding | ✗ None | ✓ SHA-256(transcript) in IKM |
| Replay protection | ✗ None | ✓ seq_no in AD |
| Associated data | ✗ Empty | ✓ node_id ‖ seq_no |
