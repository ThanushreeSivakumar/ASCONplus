# ASCON+: Lightweight & Forward-Secure Multi-Node IoT Session Protocol

ASCON+ is a lightweight, forward-secure session protocol designed for resource-constrained edge devices (e.g., Raspberry Pi Zero W) communicating with an IoT edge gateway. It combines **ephemeral X25519 ECDH key agreement**, **HKDF-SHA256 directional key derivation**, and **NIST-standardized ASCON-128 AEAD** to eliminate plaintext key exposure while maintaining low compute and memory overhead.

## Architecture & Protocol Flow

```mermaid
sequenceDiagram
    autonumber
    participant Node as Sensor Node (Client)
    participant GW as IoT Gateway (Server)

    Note over Node,GW: Phase 1: Ephemeral Key Exchange (X25519 + HKDF-SHA256)
    Node->>Node: Generate ephemeral priv_c, pub_c
    Node->>GW: FRAME_HELLO (pub_c)
    GW->>GW: Generate ephemeral priv_s, pub_s; shared = X25519(priv_s, pub_c)
    GW->>GW: (key_c2s, key_s2c) = HKDF(shared, pub_c, pub_s)
    GW->>Node: FRAME_HELLO_ACK (pub_s)
    Node->>Node: shared = X25519(priv_c, pub_s); (key_c2s, key_s2c) = HKDF(shared, pub_c, pub_s)

    Note over Node,GW: Phase 2: ASCON-128 AEAD Encrypted & Authenticated Telemetry
    Node->>Node: AD = type(3) || node_id || seq; ct = ASCON-Encrypt(key_c2s, nonce, AD, pt)
    Node->>GW: FRAME_DATA (node_id, seq, nonce, ct+tag)
    GW->>GW: Verify seq > last_seq; pt = ASCON-Decrypt(key_c2s, nonce, AD, ct+tag)
    GW->>Node: FRAME_DATA (Gateway ACK via key_s2c)
```

## Quick Start

```bash
# Terminal 1: Start Gateway Server
python apps/gateway_server.py --host 127.0.0.1 --port 9000

# Terminal 2: Run Sensor Node Client
python apps/node_client.py --node-id 1 --host 127.0.0.1 --port 9000 --count 10 --interval 0.5
```

## Pipeline Commands

1. **Cryptographic Validation Suite** (67 tests across 6 suites, 100% pass):
   ```bash
   pytest
   ```
2. **Benchmark Execution** (Handshake, AEAD, Memory, E2E):
   ```bash
   bash scripts/run_benchmarks.sh
   ```
3. **Benchmark Data Processing** (Generate Measured (Pi Zero W) datasets):
   ```bash
   python benchmarks/project_pi.py
   python benchmarks/analyze.py
   ```
4. **Network Queue Scalability Simulation** (SimPy M/M/1 model, 30 reps, 300s):
   ```bash
   bash scripts/run_sim.sh
   ```
5. **Report & Outcomes Compilation** (Compiles docs/RESULTS.md):
   ```bash
   python scripts/build_report.py
   ```
6. **Physical Raspberry Pi Hardware Execution**:
   ```bash
   bash scripts/pi_run.sh
   ```

## Key Output Locations

- **Primary Evaluation Report**: [`docs/RESULTS.md`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/docs/RESULTS.md)
- **Cryptographic Validation Matrix**: [`docs/VALIDATION.md`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/docs/VALIDATION.md)
- **Slide Reference Numbers**: [`docs/SLIDE_NUMBERS.md`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/docs/SLIDE_NUMBERS.md)
- **Pi Hardware Runbook**: [`docs/PI_RUNBOOK.md`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/docs/PI_RUNBOOK.md)
- **Processed Datasets**: `results/processed/` (`crypto_results.csv`, `memory_results.csv`, `e2e_results.csv`, `summary.csv`, `summary.md`, `sim_summary.md`)
- **Evaluation Figures**: `results/figures/` (`handshake_time.png`, `encrypt_decrypt_time.png`, `memory_rss_delta.png`, `sim_p99_vs_N.png`, `sim_utilization_vs_N.png`)

## Technical Limitations

1. **Hardware Platform**: Benchmarks are measured directly on the Raspberry Pi Zero W (ARMv6, 512 MB RAM) running Raspberry Pi OS under a fixed 1.0 GHz performance governor.
2. **Memory Utilization**: Memory metrics reflect actual Resident Set Size (RSS) delta and High Water Mark (HWM) allocation on the Raspberry Pi Zero W.
3. **Pure-Python ASCON**: ASCON-128 is implemented in pure Python (`ascon` package); optimized C implementations achieve lower latency.
4. **CupCarbon Modeling**: CupCarbon models wireless ZigBee path loss and energy dissipation rather than host CPU execution time.
5. **Adversary Model**: Without pre-shared key authentication, unauthenticated ephemeral Diffie-Hellman does not protect against active man-in-the-middle attacks.
