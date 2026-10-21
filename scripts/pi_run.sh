#!/usr/bin/env bash
# pi_run.sh — Raspberry Pi Zero W Hardware Benchmark Runner.
# Executes benchmarks on physical Raspberry Pi hardware, records hardware provenance,
# and writes genuine Measured (Pi Zero W) benchmark results directly into results/raw/.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== ASCON+ Raspberry Pi Benchmark Suite ==="

# 1. Detect hardware platform
MODEL="Raspberry Pi Unknown"
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
elif grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    MODEL=$(grep "Model" /proc/cpuinfo | cut -d: -f2 | xargs)
fi
echo "Hardware Model : $MODEL"

# 2. Configure CPU governor to performance for stable benchmarks
echo "Setting CPU governor to performance..."
for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [ -f "$gov" ]; then
        echo performance | sudo tee "$gov" >/dev/null 2>&1 || true
    fi
done
CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "N/A")
echo "CPU Governor   : $CURRENT_GOV"

# 3. Log SoC temperature
if command -v vcgencmd >/dev/null 2>&1; then
    echo "Core Temp      : $(vcgencmd measure_temp)"
elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    RAW_TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    echo "Core Temp      : $((RAW_TEMP / 1000))'C"
fi

# 4. Execute benchmark suite (ITERS=100)
export ITERS=100
export WARMUP=10
python3 benchmarks/bench_crypto.py --iters "$ITERS" --warmup "$WARMUP"
python3 benchmarks/bench_memory.py --runs 20
python3 benchmarks/bench_e2e.py --iters 50

# 5. Process hardware results
python3 benchmarks/project_pi.py
python3 benchmarks/analyze.py

echo ""
echo "=== Raspberry Pi hardware benchmarks completed successfully ==="
