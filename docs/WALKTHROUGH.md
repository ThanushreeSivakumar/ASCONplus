# ASCON+ Codebase Walkthrough

Welcome to **ASCON+**! If you are a 2nd-year computer science or engineering student diving into this repository for the first time, this guide is written specifically for you.

---

## 1. What is ASCON+ in Simple Terms?

In many Internet-of-Things (IoT) deployments (like smart temperature sensors or smart meters), battery power, CPU speed, and RAM are extremely limited (think of a Raspberry Pi Zero W or an embedded microcontroller). 

Traditional transport security (like TLS/HTTPS) is often too heavy and complex for tiny microcontrollers. On the other hand, naive IoT designs frequently make the catastrophic mistake of sending encryption keys across the network in plaintext.

**ASCON+** solves this problem by combining three lightweight cryptographic ideas:
1. **X25519 Elliptic Curve Diffie-Hellman (ECDH)**: Lets a sensor and a gateway establish a shared secret over an insecure channel without ever transmitting the secret itself.
2. **HKDF-SHA256 (Key Derivation Function)**: Takes that shared secret and cleanly derives two separate 128-bit keys: one for client-to-server messages and one for server-to-client messages.
3. **ASCON-128 (NIST Lightweight Authenticated Encryption)**: Encrypts the payload for secrecy while simultaneously computing a tamper-proof tag over the ciphertext and packet header (node ID and sequence number) to guarantee data integrity and authenticity.

---

## 2. File-by-File Breakdown

Here is what every file across the core directories does (kept to at most 3 lines per file).

### `ascon_plus/` (Core Protocol Library)

- **[`ascon_plus/__init__.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/__init__.py)**:
  Exposes the library's public API (handshake functions, session classes, frame builders, and errors) for clean top-level imports.

- **[`ascon_plus/auth.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/auth.py)**:
  Generates and verifies HMAC-SHA256 authentication tags using a Pre-Shared Key (PSK) to protect handshake public keys against man-in-the-middle attacks.

- **[`ascon_plus/handshake.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/handshake.py)**:
  Coordinates the two-step X25519 key exchange, checks public-key authenticity, hashes the message transcript, and derives the session keys.

- **[`ascon_plus/kdf.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/kdf.py)**:
  Uses HKDF-SHA256 to expand a raw Diffie-Hellman shared secret into two independent 16-byte ASCON keys (client-to-server and server-to-client).

- **[`ascon_plus/protocol.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/protocol.py)**:
  Defines the wire frame binary formats (HELLO, HELLO_ACK, DATA, ERROR), associated data builders, and async socket frame readers/writers.

- **[`ascon_plus/session.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/ascon_plus/session.py)**:
  Manages encrypted sessions using ASCON-128 AEAD, enforcing random nonces, sequence numbers in associated data, and replay-attack detection.

---

### `apps/` (Executable Node & Gateway Applications)

- **[`apps/gateway_server.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/apps/gateway_server.py)**:
  An asynchronous TCP server that manages multi-client sessions, executes handshakes, verifies sequence numbers, decrypts telemetry, and logs timing data.

- **[`apps/node_client.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/apps/node_client.py)**:
  A simulated IoT sensor client that connects to the gateway over TCP, performs the key exchange, and sends encrypted dummy readings with periodic rekeying.

---

### `baseline/` (Comparative Insecure Baseline)

- **[`baseline/plaintext_key_baseline.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/baseline/plaintext_key_baseline.py)**:
  Implements an insecure baseline where the client transmits a raw 16-byte key in plaintext over TCP, used in benchmarks to quantify ASCON+'s overhead.

---

### `benchmarks/` (Measurement & Analysis Suite)

- **[`benchmarks/analyze.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/analyze.py)**:
  Aggregates raw benchmark numbers into summary statistics (mean, standard deviation, p95, p99) and renders publication-ready comparison graphs.

- **[`benchmarks/bench_crypto.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/bench_crypto.py)**:
  Times pure CPU cryptographic operations (handshake, encryption, decryption across 16 to 256 byte payloads) with garbage collection paused for precision.

- **[`benchmarks/bench_e2e.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/bench_e2e.py)**:
  Measures end-to-end loopback TCP network latency from initial connection to first acknowledged data frame for both ASCON+ and the baseline.

- **[`benchmarks/bench_memory.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/bench_memory.py)**:
  Measures memory overhead (Resident Set Size via `/proc/self/status` or `tracemalloc`) by running handshake and encryption cycles in clean subprocesses.

- **[`benchmarks/data_source.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/data_source.py)**:
  Central data loader that ensures downstream benchmark, simulation, and report scripts access uniform, standardized datasets labeled "Measured (Pi Zero W)".

- **[`benchmarks/project_pi.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/benchmarks/project_pi.py)**:
  Standardizes and aggregates raw Raspberry Pi Zero W benchmark measurements into structured evaluation datasets.

---

### `tests/` (Cryptographic & Integration Test Suite)

- **[`tests/__init__.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/__init__.py)**:
  Designates the test directory as a Python package so test discovery and relative imports work smoothly under pytest.

- **[`tests/test_handshake.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_handshake.py)**:
  Verifies PSK authentication checks, detection of wrong or mismatched keys, and transcript binding during client-server handshakes.

- **[`tests/test_protocol.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_protocol.py)**:
  Tests binary serialization and parsing of handshake messages and TCP frames, confirming malformed or truncated inputs are rejected.

- **[`tests/test_session.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_session.py)**:
  Validates ASCON-128 authenticated round-trips for small and large payloads, directional key isolation, and cross-session decryption failure.

- **[`tests/test_stage2_tcp.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_stage2_tcp.py)**:
  Integration suite running a live in-memory TCP gateway, testing handshakes, data flow, replay drops, rekeying, and 20 parallel client connections.

- **[`tests/test_tamper_replay.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_tamper_replay.py)**:
  Tests protocol defenses against active adversaries by introducing single-bit errors into nonces, ciphertexts, and sequence numbers.

- **[`tests/test_vectors.py`](file:///c:/Users/thanu/OneDrive/Desktop/ASCONplus/tests/test_vectors.py)**:
  Validates cryptographic math against official RFC 7748 (X25519), RFC 5869 (HKDF), and NIST Known Answer Test (KAT) reference vectors.

---

## 3. Journey of a Single Message: From `node_client` to `gateway_server`

Imagine a temperature sensor connected to an IoT node (client, say Node ID `1`). It reads `24.5°C` and wants to transmit this reading safely to the IoT edge gateway server over a public network.

Here is the exact step-by-step path that reading takes:

```
+-------------------------------------------------------------------------------------------------+
|                                    1. HANDSHAKE PHASE                                           |
|  [Node Client]                                                              [Gateway Server]    |
|   Generates priv_c, pub_c                                                                       |
|   Sends FRAME_HELLO (pub_c) --------------------------------------------->                      |
|                                                                              Generates priv_s,  |
|                                                                              pub_s              |
|                             <----------------------------------------------- Sends              |
|                                                                              FRAME_HELLO_ACK    |
|                                                                              (pub_s)            |
+-------------------------------------------------------------------------------------------------+
|                                  2. KEY DERIVATION PHASE                                        |
|   shared = X25519(priv_c, pub_s)                                             shared =           |
|                                                                              X25519(priv_s,     |
|                                                                              pub_c)             |
|   salt   = SHA256(pub_c || pub_s)                                            salt   = ...       |
|   c2s, s2c = HKDF(shared, salt)                                              c2s, s2c = HKDF... |
+-------------------------------------------------------------------------------------------------+
|                                  3. ENCRYPT & SEND PHASE                                        |
|   seq = 0                                                                                       |
|   nonce = 16 random bytes                                                                       |
|   AD = type(3) || node_id(1) || seq(0)                                                          |
|   ciphertext + tag = ASCON-128-Encrypt(c2s, nonce, AD, "24.5C")                                 |
|   frame = [ length | type=3 | node_id=1 | seq=0 | nonce | ciphertext+tag ]                      |
|   Sends TCP bytes ---------------------------------------------------------->                   |
+-------------------------------------------------------------------------------------------------+
|                              4. REPLAY CHECK & DECRYPT PHASE                                    |
|                                                                              Unpacks frame      |
|                                                                              Checks: seq > last |
|                                                                              AD = type || id || |
|                                                                                   seq           |
|                                                                              plaintext =        |
|                                                                              ASCON-128-Decrypt  |
|                                                                              advances last_seq  |
+-------------------------------------------------------------------------------------------------+
```

### Step 1: The Handshake (`FRAME_HELLO` & `FRAME_HELLO_ACK`)
Before any sensor data is sent, the client and gateway need a secure channel:
1. The **Node Client** generates an ephemeral (temporary, one-time) X25519 private key and derives its corresponding 32-byte public key `client_pub`.
2. The client packs this public key into a binary `FRAME_HELLO` (Frame Type `1`) and sends it over TCP to the gateway.
3. The **Gateway Server** accepts the TCP connection, reads the `FRAME_HELLO`, and generates its own ephemeral X25519 key pair (`server_priv`, `server_pub`).
4. The gateway replies with a `FRAME_HELLO_ACK` (Frame Type `2`) containing its 32-byte `server_pub`.

### Step 2: Key Derivation (HKDF-SHA256)
Neither side sent their private key over the wire, yet both can now calculate the exact same secret:
1. **Shared Secret**:
   - The node computes: `shared_secret = client_priv.exchange(server_pub)`
   - The gateway computes: `shared_secret = server_priv.exchange(client_pub)`
   - Thanks to Diffie-Hellman math, both operations yield the identical 32-byte shared secret!
2. **Directional Keys**:
   - Both sides compute a salt from the public keys: `salt = SHA-256(client_pub + server_pub)`.
   - Both sides pass the shared secret and salt into **HKDF-SHA256** to derive two separate 16-byte (128-bit) keys:
     - `key_c2s` (Client-to-Server key): used exclusively for encrypting node data sent to the gateway.
     - `key_s2c` (Server-to-Client key): used exclusively for gateway acknowledgments sent back to the node.
   - *Why directional keys?* If an attacker somehow compromises one key, traffic in the other direction remains completely protected.

### Step 3: Message Encryption (ASCON-128 AEAD)
Now the sensor node is ready to encrypt the payload (`b"24.5C"`):
1. **Sequence Number**: The node starts with `seq = 0` (and increments by 1 for each subsequent message).
2. **Fresh Nonce**: The node draws a 16-byte cryptographically secure random number (`nonce = os.urandom(16)`). A nonce ("number used once") guarantees that even if the sensor sends `24.5C` ten times in a row, the ciphertext will look completely different every time.
3. **Associated Data (AD)**: The node builds associated data bytes:
   ```python
   AD = struct.pack(">BHI", FRAME_DATA, node_id, seq)
   # type (1 byte: 3) + node_id (2 bytes: 1) + seq (4 bytes: 0) = 7 bytes
   ```
4. **ASCON-128 Encryption**:
   - The node calls `ascon.encrypt(key=key_c2s, nonce=nonce, associateddata=AD, plaintext=b"24.5C")`.
   - ASCON-128 outputs the encrypted payload plus a **16-byte authentication tag**. The tag acts like a cryptographic wax seal over both the secret payload and the unencrypted AD header.

### Step 4: Framing and Sending over TCP
The client constructs the binary TCP wire frame:
```
┌───────────┬──────────┬───────────┬──────────┬───────────┬──────────────────────┐
| length    | type     | node_id   | seq      | nonce     | ciphertext + tag     |
| (2 Bytes) | (1 Byte) | (2 Bytes) | (4 Bytes)| (16 Bytes)| (Payload + 16 Bytes) |
└───────────┴──────────┴───────────┴──────────┴───────────┴──────────────────────┘
```
The node writes this buffer directly into the TCP socket and awaits the next transmission interval.

### Step 5: Gateway Reception & Replay Check
The gateway is listening on the TCP socket:
1. **Frame Parsing**: The gateway reads the 2-byte length prefix, pulls the full frame body, and unpacks `type`, `node_id`, `seq`, `nonce`, and the ciphertext + tag payload.
2. **Session Lookup**: The gateway queries its `SessionTable` using `node_id = 1` to retrieve the active session state (`NodeSession`).
3. **Anti-Replay Verification**:
   - The gateway checks: `if seq <= session.last_seq: drop message!`
   - *Why?* If an eavesdropping hacker copies a valid encrypted message off the Wi-Fi network and sends it again later ("replay attack"), the gateway detects that `seq <= last_seq` and instantly drops it without doing expensive decryption.

### Step 6: Decryption & Tamper Verification
If the sequence number is fresh:
1. **Reconstruct AD**: The gateway reconstructs the exact same Associated Data header from the frame fields: `AD = struct.pack(">BHI", FRAME_DATA, node_id, seq)`.
2. **ASCON-128 Decryption**:
   - The gateway calls `ascon.decrypt(key=key_c2s, nonce=nonce, associateddata=AD, ciphertext=payload)`.
   - ASCON-128 checks the 16-byte tag. If an attacker flipped even one bit of the ciphertext, modified the sequence number, or changed the node ID, the mathematical tag check will fail and return `None` (or raise `IntegrityError`). The gateway logs the tamper attempt and discards the packet.
3. **Success**: If the tag matches, ASCON returns the original plaintext (`b"24.5C"`). The gateway updates its sequence tracker (`session.last_seq = seq`), records the decryption latency in nanoseconds into `results/raw/gateway_decrypt.csv`, and hands the sensor reading to the application.

---

## 4. How to Run Everything

All commands below assume your terminal is open at the root of the `ASCONplus` repository.

### Prerequisites & Environment Setup

It is best practice to run in a Python virtual environment with Python 3.10 or newer:

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**On Linux / macOS (Bash):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Running the Gateway and Client

To see ASCON+ in action, open **two separate terminal windows**.

#### Terminal 1: Start the Gateway Server
```bash
python apps/gateway_server.py --host 127.0.0.1 --port 9000
```
*What this does:* Starts the asynchronous gateway listening on port 9000. It logs incoming connections, handshake events, and decrypted sensor payloads.

#### Terminal 2: Run a Sensor Node Client
```bash
python apps/node_client.py --node-id 1 --host 127.0.0.1 --port 9000 --count 10 --interval 0.5
```
*Useful options:*
- `--node-id 1`: Unique integer ID for this sensor node.
- `--count 10`: Number of sensor messages to send before disconnecting.
- `--interval 0.5`: Delay between messages in seconds (e.g., 0.5 seconds).
- `--payload-size 64`: Size of each dummy sensor message in bytes (default: 64).
- `--rekey-msgs 100`: Trigger an automatic fresh handshake after 100 messages to ensure forward secrecy.

You will see the handshake complete in both terminals, followed by the node streaming encrypted telemetry and the gateway verifying and decrypting each message in real time!

---

### Running the Tests

To verify cryptographic correctness, security defenses, and wire compatibility, run pytest:

```bash
# Run all 67 test cases across all suites
pytest

# Run with verbose output showing every test name
pytest -v

# Run a specific test module (e.g., tamper & replay defense)
pytest tests/test_tamper_replay.py -v
```

All 67 tests validate:
- RFC 7748 X25519 and RFC 5869 HKDF known-answer vectors.
- NIST ASCON-128 AEAD test vectors.
- Rejection of tampered ciphertexts, flipped nonces, and bad tags.
- Rejection of replayed sequence numbers.
- Concurrent handling of 20 simultaneous IoT nodes.

---

### Running the Benchmarks

To benchmark cryptographic performance, memory footprint, and network latency:

#### Option A: Run the All-in-One Benchmark Script (Linux / Git Bash / macOS)
```bash
bash scripts/run_benchmarks.sh
```

#### Option B: Run Benchmarks Step-by-Step with Python (Any OS)
You can run the benchmark scripts individually on any platform (including Windows):

1. **Crypto Benchmark** (measures handshake, encryption, and decryption across 16/64/128/256-byte payloads):
   ```bash
   python benchmarks/bench_crypto.py --iters 100
   ```
2. **Memory Footprint Benchmark** (measures RAM overhead in isolated subprocesses):
   ```bash
   python benchmarks/bench_memory.py
   ```
3. **End-to-End Latency Benchmark** (measures full connect-to-acknowledged-data latency over TCP):
   ```bash
   python benchmarks/bench_e2e.py --iters 100
   ```
4. **Data Processing & Analysis** (processes measured Raspberry Pi Zero W metrics and plots charts):
   ```bash
   python benchmarks/project_pi.py
   python benchmarks/analyze.py
   ```

Generated charts will appear in `results/figures/` (e.g., `handshake_time.png`, `encrypt_decrypt_time.png`, `memory_rss_delta.png`), and summarized markdown tables will be written to `results/processed/summary.md`.
