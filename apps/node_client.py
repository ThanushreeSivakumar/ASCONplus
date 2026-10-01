#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IoT Sensor Node Client
========================

Performs a PSK-authenticated ECDH handshake with the gateway, then
sends periodic sensor readings over an ASCON-128 encrypted channel.

Configuration via environment variables:
  GATEWAY_HOST   — gateway IP (default: 127.0.0.1)
  GATEWAY_PORT   — gateway TCP port (default: 9000)
  NODE_ID        — this node's identifier (default: sensor-01)
  PSK            — pre-shared key (default: demo value)
  SEND_INTERVAL  — seconds between readings (default: 5.0)

Usage:
  python apps/node_client.py
"""

import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ascon_plus import client_handshake, HandshakeMessage


def _send_msg(sock: socket.socket, data: bytes) -> None:
    """Length-prefixed send: 4-byte big-endian length + payload."""
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_msg(sock: socket.socket) -> bytes:
    """Length-prefixed receive."""
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


def main() -> None:
    host     = os.environ.get("GATEWAY_HOST", "127.0.0.1")
    port     = int(os.environ.get("GATEWAY_PORT", "9000"))
    node_id  = os.environ.get("NODE_ID", "sensor-01").encode()
    psk      = os.environ.get("PSK", "demo-psk-change-in-production").encode()
    interval = float(os.environ.get("SEND_INTERVAL", "5.0"))

    print(f"[node:{node_id.decode()}] Connecting to {host}:{port} ...")

    with socket.create_connection((host, port), timeout=10) as sock:
        # ── Handshake ────────────────────────────────────────────────────
        hello, pending = client_handshake(node_id, psk=psk)
        _send_msg(sock, hello.to_bytes())
        print(f"[node] ClientHello sent ({len(hello.to_bytes())} B)")

        reply_bytes = _recv_msg(sock)
        reply, _ = HandshakeMessage.from_bytes(reply_bytes)
        session = pending.complete(reply)
        print(f"[node] Handshake complete — session established")

        # ── Data loop ────────────────────────────────────────────────────
        seq = 0
        while True:
            reading = f"temp={20 + seq * 0.5:.1f}C humidity=55%"
            ct = session.seal(reading.encode())
            _send_msg(sock, ct)
            print(f"[node] Sent reading #{seq}: {reading} ({len(ct)} B)")
            seq += 1
            time.sleep(interval)


if __name__ == "__main__":
    main()
