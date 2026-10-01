#!/usr/bin/env bash
# capture_traffic.sh — tcpdump wrapper for Wireshark analysis.
#
# Captures TCP traffic between IoT nodes and the gateway server for
# protocol analysis and encrypted-payload demonstration.
#
# Usage:
#   sudo ./scripts/capture_traffic.sh               # defaults: port 9000, 60 s
#   sudo ./scripts/capture_traffic.sh 9000 120       # custom port, duration
#
# Output: results/raw/ascon_capture_<timestamp>.pcap

set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${1:-9000}"
DURATION="${2:-60}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="results/raw"
OUT_FILE="${OUT_DIR}/ascon_capture_${TIMESTAMP}.pcap"

mkdir -p "${OUT_DIR}"

echo "=== ASCON+ Traffic Capture ==="
echo "  Interface : any"
echo "  Port      : ${PORT}"
echo "  Duration  : ${DURATION}s"
echo "  Output    : ${OUT_FILE}"
echo ""
echo "Starting capture (Ctrl+C to stop early)..."

timeout "${DURATION}" tcpdump -i any -w "${OUT_FILE}" "tcp port ${PORT}" 2>/dev/null || true

echo ""
echo "Capture complete: ${OUT_FILE}"
echo "Open in Wireshark:  wireshark ${OUT_FILE}"
