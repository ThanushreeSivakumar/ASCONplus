#!/usr/bin/env bash
# run_sim.sh — Run ASCON+ Gateway queueing scalability simulation (SimPy).
#
# Usage:  chmod +x scripts/run_sim.sh && ./scripts/run_sim.sh
# Output: results/raw/sim_<label>.csv
#         results/processed/sim_summary.md
#         results/figures/sim_p99_vs_N.png, sim_utilization_vs_N.png

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== ASCON+ Gateway Queue Simulation Suite ==="
echo ""

# Use venv if present, otherwise system python
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

if [ -z "${PYTHON:-}" ]; then
    if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" 2>/dev/null; then
        PYTHON=python3
    else
        PYTHON=python
    fi
fi
REPS=${REPS:-30}
DURATION=${DURATION:-300}

echo "[1/1] Running discrete-event SimPy gateway scaling study (${REPS} reps, ${DURATION}s duration)..."
$PYTHON simulation/queue_model/gateway_sim.py --replications "$REPS" --sim-duration "$DURATION"

echo ""
echo "=== Simulation complete. Results saved to results/ ==="
