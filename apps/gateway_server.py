#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCON+ Gateway Server
======================

Concurrent TCP server that accepts sensor-node connections, performs
PSK-authenticated handshakes, and manages a session table.

Configuration via environment variables:
  GATEWAY_HOST   — bind address (default: 0.0.0.0)
  GATEWAY_PORT   — listen port (default: 9000)
  PSK            — pre-shared key (default: demo value)

Usage:
  python apps/gateway_server.py
"""

import os
import socket
import struct
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import server_handshake, HandshakeMessage, HandshakeError


# ── Session table ────────────────────────────────────────────────────────────

class SessionTable:
    """Thread-safe registry of active node sessions."""

    def __init__(self) -> None:
        self._sessions: dict[bytes, object] = {}
        self._lock = threading.Lock()

    def add(self, node_id: bytes, session: object) -> None:
        with self._lock:
            self._sessions[node_id] = session
            print(f"[gw] Session added for {node_id!r} (total: {len(self._sessions)})")

    def remove(self, node_id: bytes) -> None:
        with self._lock:
            self._sessions.pop(node_id, None)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._sessions)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _send_msg(sock: socket.socket, data: bytes) -> None:
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_msg(sock: socket.socket) -> bytes:
    raw_len = _recvall(sock, 4)
    if not raw_len:
        raise ConnectionError("Connection closed")
    length = struct.unpack(">I", raw_len)[0]
    return _recvall(sock, length)


def _recvall(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed mid-receive")
        buf.extend(chunk)
    return bytes(buf)


# ── Client handler ───────────────────────────────────────────────────────────

SERVER_ID = b"gateway-01"


def handle_client(
    conn: socket.socket,
    addr: tuple,
    sessions: SessionTable,
    psk: bytes,
) -> None:
    """Handle a single client connection: handshake then receive loop."""
    try:
        # ── Handshake ────────────────────────────────────────────────────
        hello_bytes = _recv_msg(conn)
        client_hello, _ = HandshakeMessage.from_bytes(hello_bytes)

        reply, session = server_handshake(SERVER_ID, client_hello, psk=psk)
        _send_msg(conn, reply.to_bytes())

        node_id = f"node@{addr[0]}:{addr[1]}".encode()
        sessions.add(node_id, session)
        print(f"[gw] Handshake with {addr} complete")

        # ── Receive loop ─────────────────────────────────────────────────
        while True:
            ct = _recv_msg(conn)
            pt = session.open(ct, sender_node_id=node_id)
            print(f"[gw] ← {addr}: {pt.decode(errors='replace')}")

    except (ConnectionError, OSError) as e:
        print(f"[gw] {addr} disconnected: {e}")
    except HandshakeError as e:
        print(f"[gw] {addr} handshake failed: {e}")
    finally:
        conn.close()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "9000"))
    psk  = os.environ.get("PSK", "demo-psk-change-in-production").encode()

    sessions = SessionTable()

    print(f"[gw] ASCON+ Gateway Server starting on {host}:{port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(50)
        print(f"[gw] Listening... (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = srv.accept()
                print(f"[gw] New connection from {addr}")
                t = threading.Thread(
                    target=handle_client,
                    args=(conn, addr, sessions, psk),
                    daemon=True,
                )
                t.start()
        except KeyboardInterrupt:
            print(f"\n[gw] Shutting down ({sessions.count} active sessions)")


if __name__ == "__main__":
    main()
