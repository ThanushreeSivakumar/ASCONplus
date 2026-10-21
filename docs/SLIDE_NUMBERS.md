# ASCON+ Presentation Slide Figures & Data Reference

> **Presentation Reference Guide**: This document contains the exact numbers, units, and tags for presentation slides.  
> **Tagging Rules**:
> - Benchmark results are tagged: `MEASURED (Pi Zero W)`
> - Simulation results are tagged: `SIMULATED` (with service-time input identified as `MEASURED (Pi Zero W)`)

---

## Slide 1: Introduction & Security Motivation
- **Protocol Objective**: Secure lightweight IoT communication against passive wire eavesdropping and key tampering.
- **Baseline Flaw**: Transmits raw 16-byte symmetric key in cleartext over the wire during session establishment.
- **ASCON+ Mechanism**: Ephemeral Curve25519 (X25519) key exchange + HKDF-SHA256 directional derivation + ASCON-128 AEAD.
- **Wire Audit Finding**: **0 bytes** of secret key material or shared secrets appear on the wire (`DONE`).

---

## Slide 2: Cryptographic Validation Matrix
- **Test Harness Pass Rate**: **67 / 67 tests PASSED (100%)**
- **Formal Test Vectors**: **22 / 22 PASSED** (`[docs/VALIDATION.md](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/docs/VALIDATION.md)`)
  - **RFC 7748 (Curve25519)**: 4/4 passed (Section 6.1 Alice/Bob shared secret, Section 5.2 point multiplication).
  - **RFC 5869 (HKDF-SHA256)**: 3/3 passed (Appendix A.1 basic, A.2 longer inputs, A.3 zero salt).
  - **NIST SP 800-232 / ascon-c KAT**: 4/4 passed (empty/non-empty plaintext and associated data).
  - **Composition & Security Properties**: 11/11 passed (directional key isolation $K_{c2s} \neq K_{s2c}$, session forward secrecy, anti-replay, 1-bit tampering rejection across ciphertext, tag, nonce, and associated data).

---

## Slide 3: Handshake Latency Overhead `[MEASURED (Pi Zero W)]`
- **Baseline Handshake (Plaintext Key)**:
  - Cryptographic Computation: **4.1 µs**
  - End-to-End Handshake (TCP Loopback): **4,474.6 µs** (4.47 ms)
- **ECDH + ASCON Handshake**:
  - Cryptographic Computation (Both Sides): **2,897.9 µs** (2.90 ms)
    - Client Keygen & Serialize: **676.5 µs**
    - Server Keygen, Exchange & HKDF: **1,420.0 µs**
    - Client Exchange & HKDF: **801.4 µs**
  - End-to-End Handshake (TCP Loopback): **11,013.4 µs** (11.01 ms)
- **Comparative Overhead**:
  - Absolute Cryptographic Overhead: **+2,893.8 µs** (+2.89 ms)
  - Absolute End-to-End Overhead: **+6,538.7 µs** (+6.54 ms, **+146.1%**)
  - *Context*: One-time connection establishment cost per session.

---

## Slide 4: ASCON-128 Symmetric AEAD Latency `[MEASURED (Pi Zero W)]`
- **16-byte Payload**:
  - Encrypt: **4,823.2 µs** (4.82 ms)
  - Decrypt: **4,546.5 µs** (4.55 ms)
  - Delta vs Baseline: +400.6 µs (+9.06% Encrypt), +439.7 µs (+10.71% Decrypt)
- **64-byte Payload**:
  - Encrypt: **8,149.2 µs** (8.15 ms)
  - Decrypt: **8,092.0 µs** (8.09 ms)
  - Delta vs Baseline: +528.9 µs (+6.94% Encrypt), +710.2 µs (+9.62% Decrypt)
- **128-byte Payload**:
  - Encrypt: **12,837.2 µs** (12.84 ms)
  - Decrypt: **12,876.9 µs** (12.88 ms)
  - Delta vs Baseline: +517.9 µs (+4.20% Encrypt), +529.7 µs (+4.29% Decrypt)
- **256-byte Payload**:
  - Encrypt: **23,918.1 µs** (23.92 ms)
  - Decrypt: **22,411.1 µs** (22.41 ms)
  - Delta vs Baseline: +1,202.9 µs (+5.30% Encrypt), +73.9 µs (+0.33% Decrypt)

---

## Slide 5: Memory Utilization `[MEASURED (Pi Zero W)]`
- **Methodology**: Unscaled Resident Set Size (RSS) proxy representing runtime heap allocation.
- **Baseline (Plaintext Key)**:
  - Mean RSS Delta: **7,099 KB** (~6.93 MB)
  - Mean High Water Mark (HWM): **8,999 KB** (~8.79 MB)
- **ECDH + ASCON**:
  - Mean RSS Delta: **4,060 KB** (~3.96 MB)
  - Mean High Water Mark (HWM): **4,075 KB** (~3.98 MB)
- **Resource Boundary**: Requires under 5 MB of memory, consuming less than **1.0%** of the 512 MB RAM available on the Raspberry Pi Zero W.

---

## Slide 6: Network Scalability & Saturation Bottleneck `[SIMULATED]`
- **Simulation Setup**: SimPy discrete-event queue model, 30 replications, 300s duration.
- **Service Time Input**: **8.092 ms** (ASCON-128 Decryption, 64-byte payload) `[MEASURED (Pi Zero W)]`
- **Normal Load Scenario (1 msg/s per node)**:
  - Star Saturation Threshold: **$N^* = 123.6$ nodes**
  - $N=5$: Utilization = **0.041**, p99 Latency = **14.5 ms**, Max Queue = **1.7**, Throughput = **5.03 msg/s**
  - $N=10$: Utilization = **0.081**, p99 Latency = **15.5 ms**, Max Queue = **2.2**, Throughput = **10.00 msg/s**
  - $N=25$: Utilization = **0.202**, p99 Latency = **19.9 ms**, Max Queue = **3.7**, Throughput = **24.99 msg/s**
  - $N=50$: Utilization = **0.403**, p99 Latency = **28.7 ms**, Max Queue = **6.0**, Throughput = **49.79 msg/s**
  - $N=100$: Utilization = **0.808**, p99 Latency = **95.9 ms**, Max Queue = **20.5**, Throughput = **99.87 msg/s**
- **High Load Scenario (5 msg/s per node)**:
  - Star Saturation Threshold: **$N^* = 24.7$ nodes**
  - $N=5$: Utilization = **0.202**, p99 Latency = **19.6 ms**, Max Queue = **3.6**, Throughput = **24.93 msg/s**
  - $N=10$: Utilization = **0.405**, p99 Latency = **28.6 ms**, Max Queue = **5.9**, Throughput = **50.04 msg/s**
  - $N=25$: Threshold Boundary ($N \approx N^*$): Utilization = **0.999**, p99 Latency = **4,089.6 ms** (4.09 s), Max Queue = **533.3**, Throughput = **123.44 msg/s**
  - $N=50$: Saturation Bottleneck! Utilization = **1.000**, p99 Latency = **150.3 s**, Queue backlog = **37,971.8**, Throughput ceiling = **123.58 msg/s**
  - $N=100$: Saturation Bottleneck! Utilization = **1.000**, p99 Latency = **223.6 s**, Queue backlog = **112,936.9**, Throughput ceiling = **123.58 msg/s**

---

## Slide 7: Hierarchical Mitigation & Topology Comparison `[SIMULATED]`
- **Hierarchical Architecture**: $k = 4$ secondary gateways partition incoming traffic before forwarding to root.
- **Effective Saturation Threshold**: **$N^*_{\text{hier}} = 4 \times N^* = 98.8$ nodes** (at 5 msg/s).
- **Comparison at $N = 50$ (5 msg/s)**:
  - **Star Central Gateway**: **100% utilized**, severe queue backlog (37,971 packets), p99 latency = **150.3 s**, throughput = **123.58 msg/s**.
  - **Hierarchical Gateways**: **50.6% utilized**, queue depth = **8.6 packets**, p99 latency bounded at **36.6 ms**, throughput = **250.14 msg/s** (2x Star capacity).
- **Comparison at $N = 100$ (5 msg/s)**:
  - **Star Gateway**: Severely bottlenecked, throughput capped at **123.58 msg/s**.
  - **Hierarchical Gateways**: High throughput = **493.76 msg/s** (4x Star throughput).
- **Conclusion**: Decoupling edge decryption from central aggregation restores network scalability up to 100+ nodes.

---

## Slide 8: Summary of Outcomes & Verification
- **All 8 Primary Deliverables Completed**:
  - Outcome 1 (Eliminate plaintext key): `DONE`
  - Outcome 2 (Cryptographic correctness): `DONE`
  - Outcome 3 (Pi Zero W latency overhead): `DONE-MEASURED`
  - Outcome 4 (Extended topologies): `DONE`
  - Outcome 5 (Gateway bottleneck identified): `SIMULATED`
  - Outcome 6 (Degradation characterized): `SIMULATED`
  - Outcome 7 (Key agreement + lightweight encryption): `DONE`
  - Outcome 8 (Unified evaluation framework): `DONE-MEASURED`
