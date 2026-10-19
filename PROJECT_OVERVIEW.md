# ASCON+: Scalable Multi-Node ASCON-Secured IoT Communication with Dynamic Key Exchange

> **Comprehensive Project Documentation & Repository Reference**  
> *Target Platforms: Resource-constrained IoT edge devices (e.g., Raspberry Pi Zero W, ARMv6, 512 MB RAM) communicating with a central Gateway (e.g., Raspberry Pi 4, Linux server, VM).*

---

## Table of Contents
1. [Executive Summary & Motivation](#1-executive-summary--motivation)
2. [Architectural Overview](#2-architectural-overview)
3. [Cryptographic & Network Protocol Specification](#3-cryptographic--network-protocol-specification)
4. [Threat Model & Security Defenses](#4-threat-model--security-defenses)
5. [Complete Repository Breakdown (Folder & File Reference)](#5-complete-repository-breakdown-folder--file-reference)
   - [5.1 Root Project Files](#51-root-project-files)
   - [5.2 ascon_plus/ (Core Cryptographic Library)](#52-ascon_plus-core-cryptographic-library)
   - [5.3 apps/ (Production Client & Gateway Applications)](#53-apps-production-client--gateway-applications)
   - [5.4 baseline/ (Insecure Baseline for Empirical Comparison)](#54-baseline-insecure-baseline-for-empirical-comparison)
   - [5.5 benchmarks/ (Empirical Performance & Evaluation Suite)](#55-benchmarks-empirical-performance--evaluation-suite)
   - [5.6 docs/ (Architecture, Protocol & Threat Model Documentation)](#56-docs-architecture-protocol--threat-model-documentation)
   - [5.7 examples/ (Interactive Demonstrations)](#57-examples-interactive-demonstrations)
   - [5.8 results/ (Data Logs, Statistics & Visualizations)](#58-results-data-logs-statistics--visualizations)
   - [5.9 scripts/ (Hardware Setup, Automation & Packet Capture)](#59-scripts-hardware-setup-automation--packet-capture)
   - [5.10 simulation/ (Queueing Models & CupCarbon Scenarios)](#510-simulation-queueing-models--cupcarbon-scenarios)
   - [5.11 tests/ (Complete Verification Suite)](#511-tests-complete-verification-suite)
6. [Summary of Completed Work & Verification Milestones](#6-summary-of-completed-work--verification-milestones)
7. [Quick Start & Reproduction Commands](#7-quick-start--reproduction-commands)

---

## 1. Executive Summary & Motivation

The Internet of Things (IoT) is increasingly dominated by battery-operated, highly resource-constrained micro-controllers and single-board computers (such as the Raspberry Pi Zero W with an ARMv6 single-core processor and 512 MB RAM). Traditional enterprise security suites (such as standard TLS with RSA/ECDSA certificates and AES-GCM) are often prohibitively heavy for these devices, causing memory exhaustion, high power consumption, and excessive handshake latency.

Conversely, naïve lightweight approaches found in baseline literature often resort to hardcoded static keys, symmetric pre-shared keys without forward secrecy, or transmitting raw symmetric session keys in plaintext over the network.

**ASCON+** solves this challenge by engineering an end-to-end authenticated, lightweight session protocol that combines:
1. **NIST-Standardized Lightweight Cryptography**: **ASCON-128 AEAD** (Authenticated Encryption with Associated Data), which provides authenticated confidentiality with minimal computational and memory footprints.
2. **Ephemeral Key Agreement (Forward Secrecy)**: Ephemeral **X25519 Elliptic Curve Diffie-Hellman (ECDH)** for generating short-lived per-session secrets.
3. **Active Man-in-the-Middle (MITM) Defense**: Lightweight **PSK-HMAC-SHA256** tags binding public keys without the operational overhead of X.509 PKI certificates.
4. **Transcript Binding & Directional Isolation**: **HKDF-SHA256** key derivation binding the full handshake exchange into independent client-to-server (`c2s`) and server-to-client (`s2c`) 128-bit keys.
5. **Replay & Frame Spoofing Protection**: Monotonically increasing sequence numbers bound directly into the ASCON Associated Data (`AD = frame_type || node_id || seq`).

---

## 2. Architectural Overview

ASCON+ adopts a **star topology** where multiple distributed IoT sensor nodes communicate over TCP with a central multi-client IoT Gateway.

```
                         ┌─────────────────────────┐
                         │      IoT Gateway        │
                         │   (Raspberry Pi 4 / VM) │
                         │   apps/gateway_server.py│
                         └────────────┬────────────┘
                                      │ TCP (Port 9000)
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
        ┌──────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐
        │ Sensor S1   │        │ Sensor S2   │        │ Sensor SN   │
        │(Pi Zero W)  │        │(Pi Zero W)  │        │(Pi Zero W)  │
        │node_client  │        │node_client  │        │node_client  │
        └─────────────┘        └─────────────┘        └─────────────┘
```

The system operates across two developmental tiers:
- **Stage 1 (In-Memory Core Engine)**: Defined in `ascon_plus/handshake.py` and `ascon_plus/session.py`. Handles in-memory session transitions, full transcript binding, and bidirectional encrypted channels.
- **Stage 2 (Asynchronous Networked Engine)**: Implemented in `apps/gateway_server.py`, `apps/node_client.py`, and `ascon_plus/protocol.py`. Features an event-driven `asyncio` network architecture supporting concurrent node sessions, streaming TCP framing, periodic rekeying, and telemetry logging.

---

## 3. Cryptographic & Network Protocol Specification

### 3.1 Handshake Flow & Message Exchange

```
Client (Sensor Node)                                    Server (Gateway)
      │                                                         │
      │ 1. Generate ephemeral priv_c, pub_c                     │
      │    Compute tag_c = HMAC(PSK, "client" || pub_c)         │
      │                                                         │
      │ ────── FRAME_HELLO (pub_c, tag_c) ────────────────────> │
      │                                                         │ 2. Verify tag_c with PSK
      │                                                         │    Generate priv_s, pub_s
      │                                                         │    Compute shared = X25519(priv_s, pub_c)
      │                                                         │    Derive c2s_key, s2c_key via HKDF
      │                                                         │    Compute tag_s = HMAC(PSK, "server" || pub_s)
      │                                                         │
      │ <───── FRAME_HELLO_ACK (pub_s, tag_s) ───────────────── │
      │                                                         │
      │ 3. Verify tag_s with PSK                                │
      │    Compute shared = X25519(priv_c, pub_s)               │
      │    Derive c2s_key, s2c_key via HKDF                     │
      │                                                         │
      │ ──[ Established Session: c2s_key & s2c_key Active ]──── │
      │                                                         │
      │ 4. Build AD = DATA(3) || node_id || seq                 │
      │    ct, tag = ASCON-128-Encrypt(c2s_key, nonce, AD, pt)  │
      │ ────── FRAME_DATA (seq, nonce, ct+tag) ───────────────> │
      │                                                         │ 5. Verify seq > last_seq (anti-replay)
      │                                                         │    Build AD = DATA(3) || node_id || seq
      │                                                         │    pt = ASCON-128-Decrypt(c2s_key, nonce, AD, ct)
```

### 3.2 Wire Frame Layouts

#### Stage 2 TCP Streaming Binary Frame (Big-Endian):
```
┌───────────────┬──────────────┬───────────────┬──────────────┬────────────────┬──────────────────────┐
│  length (2B)  │  type (1B)   │  node_id (2B) │   seq (4B)   │   nonce (16B)  │  ciphertext + tag    │
│  uint16_be    │  uint8       │  uint16_be    │   uint32_be  │   (DATA only)  │  (payload + 16B)     │
└───────────────┴──────────────┴───────────────┴──────────────┴────────────────┴──────────────────────┘
```

- **Frame Types**:
  - `1 = FRAME_HELLO`: Ephemeral public key exchange from client to gateway.
  - `2 = FRAME_HELLO_ACK`: Ephemeral public key exchange response from gateway.
  - `3 = FRAME_DATA`: Authenticated encrypted sensor telemetry or command.
  - `4 = FRAME_ERROR`: Diagnostic plaintext notification before connection teardown.

#### Associated Data (AD) Binding:
In ASCON+, Associated Data is never transmitted across the wire (preserving network bandwidth). Both parties reconstruct AD deterministically from context:
$$\text{AD} = \text{type} \,(1\text{B}) \parallel \text{node\_id} \,(2\text{B}) \parallel \text{seq} \,(4\text{B})$$
If an adversary attempts to tamper with the frame type, spoof the sender's node ID, or inject an out-of-order sequence number, the ASCON AEAD tag verification fails immediately and the packet is discarded.

---

## 4. Threat Model & Security Defenses

| Threat Category | Attack Vector | ASCON+ Mitigation Mechanism |
| :--- | :--- | :--- |
| **Passive Eavesdropping** | Sniffing plaintext over air or wire | All application payloads encrypted with **ASCON-128**; ephemeral X25519 ensures **Perfect Forward Secrecy (PFS)**. |
| **Active MITM** | Intercepting public keys and inserting rogue keys | **PSK-HMAC-SHA256** tags authenticate public keys during handshake. Attackers cannot forge tags without the pre-shared secret. |
| **Packet Tampering** | Bit-flipping ciphertext, header, or metadata | 128-bit authentication tag generated by ASCON permutation detects any single bit modification. |
| **Replay Attacks** | Capturing valid encrypted frames and re-transmitting | `seq` is monotonically incremented and authenticated inside Associated Data; Gateway rejects any frame where $\text{seq} \le \text{last\_seq}$. |
| **Session Confusion** | Replaying old handshakes across sessions | **Transcript Binding**: HKDF derivation injects the SHA-256 hash of the complete handshake exchange into the key material. |
| **Directional Cross-Talk** | Using client-sent packets to spoof gateway responses | Key separation: HKDF derives independent, cryptographically isolated `c2s` and `s2c` keys using explicit info strings (`b"ascon c2s"` vs `b"ascon s2c"`). |
| **Frame Truncation** | Dropping trailing bytes of a ciphertext | Strict length validations against minimum frame size (`FRAME_HDR_LEN + NONCE_LEN + ASCON_TAG_LEN`). |

---

## 5. Complete Repository Breakdown (Folder & File Reference)

Below is an exhaustive explanation of every file and folder currently present in the repository.

### 5.1 Root Project Files

```
ASCONplus/
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

- **`LICENSE`**  
  Contains the full text of the **GNU General Public License version 3 (GPLv3)**. Dictates the terms under which this research and software suite can be distributed, modified, and used.
- **`pyproject.toml`**  
  The modern Python project build specification conforming to PEP 517/PEP 621. Declares:
  - Project metadata: `name = "ascon-plus"`, `version = "0.1.0"`.
  - Core dependencies: `cryptography`, `ascon`.
  - Optional dependency groups: `dev` (`pytest>=7.0`), `bench` (`simpy`, `pandas`, `matplotlib`).
  - Pytest configuration paths (`testpaths = ["tests"]`, `pythonpath = ["."]`).
- **`README.md`**  
  The top-level markdown document introducing the repository title and core project mission.
- **`requirements.txt`**  
  Standard pip requirement manifest listing all packages required to run, test, benchmark, and simulate the project: `cryptography`, `ascon`, `pytest>=7.0`, `simpy`, `pandas`, `matplotlib`.

---

### 5.2 `ascon_plus/` (Core Cryptographic Library)

```
ascon_plus/
├── __init__.py
├── auth.py
├── handshake.py
├── kdf.py
├── protocol.py
└── session.py
```

- **`ascon_plus/__init__.py`**  
  Top-level package initialization file. Exposes a clean, high-level public interface for importing core classes and functions (`client_handshake`, `server_handshake`, `AsconSession`, `NodeSession`, `HandshakeMessage`, `FRAME_DATA`, etc.).
- **`ascon_plus/auth.py`**  
  Implements the Pre-Shared Key (PSK) authentication layer:
  - `make_auth_tag(psk, label, pub)`: Generates $\text{HMAC-SHA256}(\text{PSK}, \text{label} \parallel \text{pub})$ over the ephemeral public key.
  - `verify_auth_tag(psk, label, pub, tag)`: Performs constant-time comparison (`hmac.compare_digest`) against expected tag; raises `HandshakeError` upon mismatch. Allows unauthenticated fallback if `psk=None`.
  - `HandshakeError`: Custom exception indicating MITM or tag validation failure.
- **`ascon_plus/handshake.py`**  
  Orchestrates the X25519 ephemeral key agreement protocol:
  - `PendingClientHandshake`: Client-side state container holding the private key, sent `ClientHello`, and node ID while awaiting server response.
  - `client_handshake(node_id, psk)`: Generates client ephemeral keypair, tags public key with PSK-HMAC, and returns `HandshakeMessage` and pending state.
  - `server_handshake(node_id, client_hello, psk)`: Validates client tag, generates server keypair, computes shared Diffie-Hellman secret, binds full handshake transcript, derives session keys, and returns `ServerHello` and `AsconSession`.
- **`ascon_plus/kdf.py`**  
  Key Derivation Functions using HKDF-SHA256:
  - `derive_keys(shared_secret, client_pub, server_pub, transcript)`: Stage 1 transcript-bound KDF. Hashes `client_pub || server_pub` as salt, and `shared_secret || SHA-256(transcript)` as input key material (IKM), returning two 16-byte keys (`c2s` and `s2c`).
  - `derive_session_keys(shared_secret, client_pub, server_pub)`: Stage 2 streamlined KDF for live TCP streams using deterministic salt and directional info tags (`b"ascon c2s"`, `b"ascon s2c"`).
- **`ascon_plus/protocol.py`**  
  Defines binary framing structures, wire constants, and serialisation utilities:
  - Frame type constants: `FRAME_HELLO (1)`, `FRAME_HELLO_ACK (2)`, `FRAME_DATA (3)`, `FRAME_ERROR (4)`.
  - Constants: `FRAME_HDR_LEN = 9`, `NONCE_LEN = 16`, `ASCON_TAG_LEN = 16`, `PUBKEY_LEN = 32`.
  - `build_frame(frame_type, node_id, seq, payload, nonce)`: Packs binary header `>H` (body length), `>BHI` (type, node_id, seq) plus nonce and payload.
  - `read_frame(reader)`: Async reader parsing frames from `asyncio.StreamReader` with length checks and payload extraction.
  - `make_ad(frame_type, node_id, seq)`: Formats Associated Data bytes.
  - `HandshakeMessage`: Dataclass for serialising and deserialising public key + auth tag structures.
  - Legacy helpers: `encode_frame_legacy`, `decode_frame_legacy` for backward compatibility with Stage 1 tests.
- **`ascon_plus/session.py`**  
  Manages authenticated encryption sessions and sequence numbers:
  - `AsconSession`: Stage 1 bidirectional AEAD channel using ASCON-128. Handles `seal(plaintext)` and `open(message, sender_node_id)` with internal sequence tracking.
  - `NodeSession`: Stage 2 state machine representing a connected sensor node on the gateway. Tracks directional keys, last processed sequence number, message counters, and session creation timestamps. Exposes `encrypt()` and `decrypt()` with built-in replay verification via `is_replay(seq)` and `advance(seq)`.
  - `IntegrityError`: Custom exception raised when ASCON authentication tag verification fails (indicating data corruption, tampering, or incorrect keys).

---

### 5.3 `apps/` (Production Client & Gateway Applications)

```
apps/
├── gateway_server.py
└── node_client.py
```

- **`apps/gateway_server.py`**  
  An asynchronous, multi-client TCP server engineered with `asyncio.start_server`.
  - Functions as the central IoT Gateway on port 9000.
  - Manages concurrent sensor connections using coroutine workers.
  - Holds an in-memory `SessionTable` mapping `node_id` to `NodeSession`.
  - Performs live X25519 handshake on incoming connection, derives session keys, and verifies incoming frames.
  - Enforces anti-replay checking, verifies ASCON-128 AEAD tags, and logs high-resolution decryption timing benchmarks to `results/raw/gateway_decrypt.csv`.
- **`apps/node_client.py`**  
  An asynchronous IoT sensor client simulating edge hardware.
  - Connects to the gateway, transmits `FRAME_HELLO` with its ephemeral public key, and completes key agreement upon receiving `FRAME_HELLO_ACK`.
  - Periodically transmits encrypted sensor payloads (dummy telemetry readings) at configurable intervals (`--interval`) and payload sizes (`--payload-size`).
  - Implements **dynamic session rekeying**: automatically re-initiates an ephemeral handshake over the existing TCP stream when `--rekey-msgs` or `--rekey-secs` limits are hit.

---

### 5.4 `baseline/` (Insecure Baseline for Empirical Comparison)

```
baseline/
└── plaintext_key_baseline.py
```

- **`baseline/plaintext_key_baseline.py`**  
  Implements the unauthenticated, plaintext-key protocol modeled from naive IoT literature to serve as an experimental control baseline:
  - Client generates a random 16-byte symmetric key using `os.urandom(16)` and transmits it across the wire in plaintext inside `FRAME_HELLO`.
  - Server accepts the plaintext key without authentication or forward secrecy.
  - Subsequent data frames use ASCON-128 with empty Associated Data (`AD = b""`).
  - Provides compute-level benchmarks (`baseline_keygen`, `baseline_encrypt`, `baseline_decrypt`) and an asyncio TCP test server/client to measure the performance penalty and latency overhead introduced by ASCON+'s secure ECDH+HKDF handshake.

---

### 5.5 `benchmarks/` (Empirical Performance & Evaluation Suite)

```
benchmarks/
├── analyze.py
├── bench_crypto.py
├── bench_e2e.py
└── bench_memory.py
```

- **`benchmarks/bench_crypto.py`**  
  Isolates pure cryptographic compute performance without network overhead:
  - Compares `baseline` vs `ecdh_ascon` across four distinct payload sizes: 16 B, 64 B, 128 B, and 256 B.
  - Measures key generation, handshake computation, encryption, and decryption in nanoseconds (`time.perf_counter_ns`).
  - Controls for garbage collection distortion via `gc.collect()` before and `gc.disable()` during benchmark loops.
  - Captures hardware metadata (CPU governor, machine architecture, device model, OS temperature) into `results/raw/ENVIRONMENT.md` and dumps timings to `results/raw/crypto_<hostname>.csv`.
- **`benchmarks/bench_e2e.py`**  
  Evaluates loopback TCP end-to-end latency:
  - Measures total elapsed time from initial socket connection through ephemeral handshake to the first acknowledged encrypted `FRAME_DATA` payload.
  - Compares the ASCON+ gateway against the baseline server.
  - Exports statistical distributions to `results/raw/e2e_<hostname>.csv`.
- **`benchmarks/bench_memory.py`**  
  Subprocess memory profiler:
  - Executes isolated subprocesses for both baseline and ASCON+ handshakes and message encryptions to prevent memory caching artifacts.
  - Measures peak resident memory ($VmRSS$) and high water mark ($VmHWM$) from Linux `/proc/self/status` (with portable fallback to `tracemalloc`).
  - Repeats runs 20 times per scenario and exports memory delta footprints to `results/raw/memory_<hostname>.csv`.
- **`benchmarks/analyze.py`**  
  Data aggregation and visualization pipeline:
  - Ingests raw benchmark files (`crypto_*.csv`, `e2e_*.csv`, `memory_*.csv`).
  - Calculates descriptive statistics (mean, median, standard deviation, p95, p99 percentiles).
  - Generates `results/processed/summary.csv` and a GitHub-flavored Markdown report `results/processed/summary.md`.
  - Generates publication-ready comparative visualization charts in `results/figures/`:
    - `handshake_time.png`
    - `encrypt_decrypt_time.png`
    - `memory_rss_delta.png`

---

### 5.6 `docs/` (Architecture, Protocol & Threat Model Documentation)

```
docs/
├── architecture.md
├── protocol.md
└── threat_model.md
```

- **`docs/architecture.md`**  
  Detailed system architecture document describing component responsibilities, star topology network layout, sequence diagrams, and key engineering trade-offs (e.g., X25519 vs ECDSA, PSK-HMAC vs full X.509 PKI certificates).
- **`docs/protocol.md`**  
  Low-level protocol specification covering wire-level message byte layouts, handshake message format, HKDF input key material construction, associated data reconstruction, and monotonic sequence number invariants.
- **`docs/threat_model.md`**  
  Exhaustive cryptographic threat model articulating the adversary capabilities, assets, trust assumptions, formal defenses (mitigating passive eavesdropping, active MITM, bit tampering, frame truncation, replay attacks, session confusion), and out-of-scope risks.

---

### 5.7 `examples/` (Interactive Demonstrations)

```
examples/
└── demo_handshake.py
```

- **`examples/demo_handshake.py`**  
  A standalone, interactive CLI demonstration:
  - Executes Phase 1 (PSK-authenticated X25519 handshake between client `sensor-node-01` and server `gateway-01`).
  - Displays ephemeral public keys, hex auth tags, and derived session keys.
  - Demonstrates Phase 2 (bidirectional encrypted sensor telemetry transmission with sequence verification).
  - Exercises tamper resistance by flipping a bit in the ciphertext and showing that `IntegrityError` is triggered.

---

### 5.8 `results/` (Data Logs, Statistics & Visualizations)

```
results/
├── figures/
│   └── .gitkeep
├── processed/
│   └── .gitkeep
└── raw/
    ├── .gitkeep
    └── gateway_decrypt.csv
```

- **`results/raw/`**  
  Storage directory for raw benchmark outputs and runtime telemetry. Contains `gateway_decrypt.csv` (recording `node_id`, `seq`, `payload_len`, and `decrypt_ns` timing logs from live gateway executions).
- **`results/processed/`**  
  Output directory for statistical aggregations (`summary.csv`, `summary.md`).
- **`results/figures/`**  
  Output directory for high-resolution matplotlib benchmark comparison plots.

---

### 5.9 `scripts/` (Hardware Setup, Automation & Packet Capture)

```
scripts/
├── capture_traffic.sh
├── run_benchmarks.sh
└── setup_pi.sh
```

- **`scripts/setup_pi.sh`**  
  Target hardware provisioning script for the **Raspberry Pi Zero W** (ARMv6, 512 MB RAM):
  - Solves the critical Raspberry Pi compilation issue: standard `pip install cryptography` compiles Rust code, which triggers out-of-memory kernel kills on 512 MB devices.
  - Installs pre-compiled system binaries via `apt-get install python3-cryptography`.
  - Builds a Python virtual environment with `--system-site-packages` to inherit the pre-compiled cryptography engine without compiling.
  - Installs pure-Python `ascon` via pip and executes verification tests.
- **`scripts/run_benchmarks.sh`**  
  Master test automation script that runs the entire benchmark suite sequentially:
  1. `bench_crypto.py`
  2. `bench_memory.py`
  3. `bench_e2e.py`
  4. `analyze.py`
- **`scripts/capture_traffic.sh`**  
  A wrapper around `tcpdump` that captures live TCP traffic between sensor nodes and gateway on port 9000, saving output to `.pcap` files for deep-packet inspection in Wireshark.

---

### 5.10 `simulation/` (Queueing Models & CupCarbon Scenarios)

```
simulation/
├── queue_model/
│   └── gateway_sim.py
└── cupcarbon/
    ├── generate_scenarios.py
    ├── template/
    │   ├── template.cup
    │   └── config/
    │       └── session.cfg
    └── scenarios/
        ├── star_5/
        ├── star_10/
        ├── star_25/
        └── star_50/
```

- **`simulation/queue_model/gateway_sim.py`**  
  A discrete-event queueing simulation built on **SimPy**:
  - Models the central IoT Gateway as an $M/D/1$ queue (Poisson arrivals from $N$ distributed sensor nodes, deterministic service time based on empirical Pi Zero W decryption benchmarks).
  - Evaluates queueing latency, queue length progression, p95/p99 delays, and saturation throughput across different network loads.
- **`simulation/cupcarbon/generate_scenarios.py`**  
  A Python 3 standard-library scenario generator cloning the project format of **CupCarbon Klaines 8.2**:
  - Automatically synthesizes complete CupCarbon simulation project directories for star topologies: 1 Gateway + $N$ Sensors ($N \in \{5, 10, 25, 50\}$).
  - Accurately computes geographic coordinates: Gateway at template origin (`25.3080° N, 55.4425° E`), sensors evenly positioned along a circle with radius 50.0 m (well within the ZigBee 100.0 m radio range) using great-circle Haversine trigonometry.
  - Replicates CupCarbon node configs (`config/nodes/sensor_<id>`, `config/nodes/basestation_<id>`), radio parameters (`config/sensor_radios/`), SenScript routines (`scripts/sensor.csc`, `scripts/gateway.csc`), and Python IoT scripts (`scripts/sensor.py`, `scripts/gateway.py`).
  - Idempotent and self-validating: runs internal integrity checks and prints pass/fail reports.
- **`simulation/cupcarbon/template/`**  
  The base CupCarbon reference project directory containing:
  - `template.cup`: Project definition file defining map coordinates, zoom level, and simulation properties.
  - `config/session.cfg`: Session configuration tracking window geometries.
- **`simulation/cupcarbon/scenarios/`**  
  Complete, standalone CupCarbon simulation project folders generated by `generate_scenarios.py`:
  - **`star_5/`**: Complete 6-node network project (1 gateway `G` + 5 sensors `S1..S5`).
  - **`star_10/`**: Complete 11-node network project (1 gateway `G` + 10 sensors `S1..S10`).
  - **`star_25/`**: Complete 26-node network project (1 gateway `G` + 25 sensors `S1..S25`).
  - **`star_50/`**: Complete 51-node network project (1 gateway `G` + 50 sensors `S1..S50`).
  *Each project folder contains the full CupCarbon directory hierarchy (`agents/`, `config/nodes/`, `config/sensor_radios/`, `gps/`, `logs/`, `natevents/`, `network/`, `results/`, `scripts/`, `tmp/`, `xbee/`, and `<scenario>.cup`) and opens directly in the CupCarbon simulator.*

---

### 5.11 `tests/` (Complete Verification Suite)

```
tests/
├── __init__.py
├── test_handshake.py
├── test_protocol.py
├── test_session.py
├── test_stage2_tcp.py
└── test_tamper_replay.py
```

The test suite contains **45 comprehensive automated tests**, all of which pass:

- **`tests/__init__.py`**: Test package marker.
- **`tests/test_handshake.py` (7 tests)**:
  - Validates PSK authentication success and detects wrong PSK on server or client.
  - Verifies mismatched PSK configurations and unauthenticated handshake mode.
  - Proves that replaying a `ClientHello` yields completely different derived keys (transcript binding).
  - Confirms that directional keys `c2s` and `s2c` are cryptographically distinct.
- **`tests/test_protocol.py` (8 tests)**:
  - Tests binary serialization and deserialization of `HandshakeMessage` with and without auth tags.
  - Validates preservation of trailing bytes and concatenated messages.
  - Tests frame encode and decode routines, sequence number binary packings, and rejection of undersized frames.
- **`tests/test_session.py` (14 tests)**:
  - Validates bidirectional encryption and decryption round-trips for empty, small, large, and sequential payloads.
  - Verifies cross-session isolation (packets encrypted in Session A cannot be opened in Session B).
  - Confirms directional isolation (clients cannot decrypt packets encrypted with their own send key).
  - Verifies robust error handling on truncated messages and malformed headers.
- **`tests/test_stage2_tcp.py` (5 tests)**:
  - Full end-to-end integration tests over live TCP sockets.
  - Verifies ephemeral handshake followed by authenticated `FRAME_DATA` exchange.
  - Verifies that tampered frames are dropped by the gateway server.
  - Proves replay protection (replayed sequence numbers are detected and dropped).
  - Validates live in-stream rekeying (generating new keys on the fly).
  - Stresses concurrent capacity: 20 simultaneous sensor clients communicating with the gateway without deadlocks or packet loss.
- **`tests/test_tamper_replay.py` (11 tests)**:
  - Single-bit flipping tests across every segment of the frame (ciphertext, nonce, sequence number, and auth tag regions) confirming that any alteration triggers `IntegrityError`.
  - Verifies Associated Data binding (transmitting a frame under an unauthorized `sender_node_id` is rejected).
  - Validates sequence number monotonicity and confirms 100% nonce uniqueness across consecutive encryption operations.

---

## 6. Summary of Completed Work & Verification Milestones

1. **Stage 1 Cryptographic Protocol**:
   - Engineered ephemeral X25519 ECDH key agreement with PSK-HMAC authentication.
   - Built HKDF-SHA256 key derivation with full transcript binding and directional isolation (`c2s` vs `s2c`).
   - Implemented ASCON-128 AEAD session wrapper with implicit Associated Data binding (`node_id || seq`).
2. **Stage 2 Asyncio Networking Engine**:
   - Designed streaming binary TCP frame format (`length`, `type`, `node_id`, `seq`, `nonce`, `ciphertext+tag`).
   - Developed `apps/gateway_server.py` supporting concurrent node sessions and real-time decryption timing logs.
   - Developed `apps/node_client.py` supporting telemetry transmission and dynamic in-stream rekeying.
3. **Insecure Baseline & Benchmark Suite**:
   - Implemented `baseline/plaintext_key_baseline.py` modeling naive IoT key exchange.
   - Built microbenchmarking tools (`bench_crypto.py`, `bench_e2e.py`, `bench_memory.py`) measuring execution latency, memory footprint ($VmRSS$), and network throughput.
   - Implemented data analysis pipeline (`analyze.py`) for automated summary generation and graphical charting.
4. **Hardware Deployment & Network Capture**:
   - Developed `scripts/setup_pi.sh` utilizing pre-compiled APT packages to prevent memory exhaustion on Raspberry Pi Zero W devices.
   - Created `scripts/capture_traffic.sh` for Wireshark protocol verification.
5. **Network Simulation & Scalability Models**:
   - Implemented `simulation/queue_model/gateway_sim.py` evaluating gateway queue dynamics under Poisson traffic loads using SimPy.
   - Reverse-engineered CupCarbon Klaines 8.2 engine internals and implemented `simulation/cupcarbon/generate_scenarios.py`.
   - Successfully generated and validated complete CupCarbon star topology projects for 5, 10, 25, and 50 nodes (`star_5/`, `star_10/`, `star_25/`, `star_50/`) positioned within 50 meters of the central gateway.
   - Validated CupCarbon scenario projects using native Java classpath invocation (`device.DeviceList.open()` and `initForSimulation()`), confirming 0 errors.
6. **Testing & Quality Assurance**:
   - Developed 45 automated unit and integration tests across 5 test modules.
   - Attained **100% test pass rate** (`45 passed in 4.01s`).

---

## 7. Quick Start & Reproduction Commands

### Run the Test Suite
```bash
python -m pytest -v
```

### Run the Interactive Handshake & Encryption Demo
```bash
python examples/demo_handshake.py
```

### Run the Asyncio Gateway Server & Sensor Client
Terminal 1 (Start Gateway):
```bash
python apps/gateway_server.py --host 127.0.0.1 --port 9000
```

Terminal 2 (Start Sensor Node):
```bash
python apps/node_client.py --node-id 1 --host 127.0.0.1 --port 9000 --count 20 --interval 0.5
```

### Generate CupCarbon Simulation Scenarios
```bash
python simulation/cupcarbon/generate_scenarios.py --n-list 5 10 25 50
```

### Run the Discrete-Event Queueing Model
```bash
python simulation/queue_model/gateway_sim.py
```

### Run the Cryptographic & Memory Benchmarks
```bash
python benchmarks/bench_crypto.py --iters 100
python benchmarks/bench_memory.py
python benchmarks/bench_e2e.py --iters 50
python benchmarks/analyze.py
```

---
*Documentation compiled and verified for the ASCON+ Project.*
