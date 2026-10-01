#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark: end-to-end latency over real loopback sockets.

Spawns a gateway server thread and a client thread, performs a full
handshake over TCP, and measures round-trip message latency.

Output: results/raw/bench_e2e.csv
"""

import csv
import os
import socket
import statistics
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import client_handshake, server_handshake, HandshakeMessage

PSK = b"benchmark-psk"
CLIENT_ID = b"bench-client"
SERVER_ID = b"bench-server"
N_MESSAGES = 100
PAYLOAD_SIZE = 128


def _send(sock, data):
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv(sock):
    raw = b""
    while len(raw) < 4:
        raw += sock.recv(4 - len(raw))
    n = struct.unpack(">I", raw)[0]
    buf = b""
    while len(buf) < n:
        buf += sock.recv(n - len(buf))
    return buf


def _server_thread(port, barrier, results):
    """Accept one connection, handshake, echo back each message."""
    with socket.socket() as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
        barrier.wait()  # signal ready
        conn, _ = srv.accept()
        with conn:
            hello_bytes = _recv(conn)
            hello, _ = HandshakeMessage.from_bytes(hello_bytes)
            reply, session = server_handshake(SERVER_ID, hello, psk=PSK)
            _send(conn, reply.to_bytes())

            for _ in range(N_MESSAGES):
                ct = _recv(conn)
                pt = session.open(ct, sender_node_id=CLIENT_ID)
                echo_ct = session.seal(pt)
                _send(conn, echo_ct)


def main():
    port = 19876
    barrier = threading.Barrier(2)
    results = {}

    t = threading.Thread(target=_server_thread, args=(port, barrier, results), daemon=True)
    t.start()
    barrier.wait()  # wait for server
    time.sleep(0.05)

    with socket.create_connection(("127.0.0.1", port)) as sock:
        hello, pending = client_handshake(CLIENT_ID, psk=PSK)
        _send(sock, hello.to_bytes())
        reply_bytes = _recv(sock)
        reply, _ = HandshakeMessage.from_bytes(reply_bytes)
        session = pending.complete(reply)

        payload = os.urandom(PAYLOAD_SIZE)
        rtts = []
        for _ in range(N_MESSAGES):
            t0 = time.perf_counter()
            _send(sock, session.seal(payload))
            echo_ct = _recv(sock)
            session.open(echo_ct, sender_node_id=SERVER_ID)
            rtts.append(time.perf_counter() - t0)

    t.join(timeout=5)

    ms = [r * 1000 for r in rtts]
    print(f"ASCON+ End-to-End Benchmark  (loopback, {N_MESSAGES} round-trips)\n")
    print(f"  RTT mean    : {statistics.mean(ms):.3f} ms")
    print(f"  RTT stdev   : {statistics.stdev(ms):.3f} ms")
    print(f"  RTT p95     : {sorted(ms)[int(len(ms)*0.95)]:.3f} ms")
    print(f"  RTT p99     : {sorted(ms)[int(len(ms)*0.99)]:.3f} ms")

    out = os.path.join(os.path.dirname(__file__), "..", "results", "raw", "bench_e2e.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rtt_ms"])
        for m in ms:
            w.writerow([f"{m:.4f}"])
    print(f"\n  Results → {out}")


if __name__ == "__main__":
    main()
