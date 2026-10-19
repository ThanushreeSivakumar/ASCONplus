#!/usr/bin/env bash
# pi_run.sh — Raspberry Pi benchmark runner and telemetry packager.
# Target: Raspberry Pi Zero W / Pi 3 / Pi 4 (Linux ARM)

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== ASCON+ Raspberry Pi Automated Benchmark Runner ==="

# 1. Verify target device is a Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "ERROR: scripts/pi_run.sh must be executed directly on Raspberry Pi hardware." >&2
    exit 1
fi

MODEL=$(tr -d '\0' < /proc/device-tree/model)
echo "Hardware Model : $MODEL"

# 2. Set CPU scaling governor to performance if possible
echo "Setting CPU governor to performance..."
for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [ -f "$gov" ]; then
        echo performance | sudo tee "$gov" >/dev/null 2>&1 || true
    fi
done
CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
echo "Active Governor: $CURRENT_GOV"

# 3. Print system core temperature
if command -v vcgencmd >/dev/null 2>&1; then
    echo "Core Temp      : $(vcgencmd measure_temp)"
elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    RAW_TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    echo "Core Temp      : $((RAW_TEMP / 1000))'C"
fi

# 4. Execute master benchmark suite (ITERS=100)
echo ""
echo "Running ASCON+ benchmark suite (ITERS=100)..."
export ITERS=100
bash scripts/run_benchmarks.sh

# 5. Archive raw benchmark outputs into timestamped tarball
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_NAME="pi_results_${DATE_STAMP}.tar.gz"
tar -czf "$ARCHIVE_NAME" -C results raw
echo ""
echo "=== Pi Benchmarks Complete ==="
echo "Raw output archive: $ARCHIVE_NAME"
