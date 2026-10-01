#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway queueing model — SimPy discrete-event simulation.

Models the gateway as an M/D/1 queue where:
  - Arrival process  : Poisson (configurable λ per node × N nodes)
  - Service time     : deterministic, measured on the Raspberry Pi
  - Queue discipline : FIFO

Outputs:
  - Mean / p95 / p99 queueing delay
  - Queue length over time
  - Throughput at saturation
  - CSV to results/raw/gateway_sim.csv

Usage:
  pip install simpy
  python simulation/queue_model/gateway_sim.py
"""

import csv
import os
import sys

try:
    import simpy
except ImportError:
    print("SimPy not installed. Run: pip install simpy")
    sys.exit(1)

import random
import statistics

# ── Configuration ────────────────────────────────────────────────────────────

N_NODES = 25                       # number of IoT sensor nodes
MSG_INTERVAL = 5.0                 # seconds between messages per node
SERVICE_TIME_MS = 2.5              # measured seal+open time on Pi Zero W (ms)
SERVICE_TIME_S = SERVICE_TIME_MS / 1000
SIM_DURATION = 300                 # seconds of simulated time

# Derived
ARRIVAL_RATE = N_NODES / MSG_INTERVAL   # aggregate λ (messages/sec)


# ── Simulation ───────────────────────────────────────────────────────────────

delays: list[float] = []
queue_lengths: list[tuple[float, int]] = []


def message_source(env: simpy.Environment, gateway: simpy.Resource):
    """Generate Poisson arrivals from all nodes."""
    msg_id = 0
    while True:
        # Inter-arrival time: exponential with rate = ARRIVAL_RATE
        yield env.timeout(random.expovariate(ARRIVAL_RATE))
        msg_id += 1
        env.process(process_message(env, gateway, msg_id))


def process_message(env: simpy.Environment, gateway: simpy.Resource, msg_id: int):
    """A single message arriving at the gateway queue."""
    arrival = env.now
    queue_lengths.append((arrival, len(gateway.queue) + gateway.count))

    with gateway.request() as req:
        yield req
        wait = env.now - arrival
        delays.append(wait)
        # Service (deterministic)
        yield env.timeout(SERVICE_TIME_S)


def main():
    random.seed(42)
    env = simpy.Environment()
    gateway = simpy.Resource(env, capacity=1)   # single-threaded gateway
    env.process(message_source(env, gateway))
    env.run(until=SIM_DURATION)

    ms_delays = [d * 1000 for d in delays]
    sorted_d = sorted(ms_delays)

    print(f"ASCON+ Gateway Queueing Simulation\n")
    print(f"  Nodes            : {N_NODES}")
    print(f"  Msg interval     : {MSG_INTERVAL} s/node")
    print(f"  Aggregate λ      : {ARRIVAL_RATE:.1f} msg/s")
    print(f"  Service time     : {SERVICE_TIME_MS} ms")
    print(f"  Sim duration     : {SIM_DURATION} s")
    print(f"  Messages handled : {len(delays)}")
    print()
    print(f"  Queueing delay:")
    print(f"    Mean  : {statistics.mean(ms_delays):.3f} ms")
    print(f"    p95   : {sorted_d[int(len(sorted_d)*0.95)]:.3f} ms")
    print(f"    p99   : {sorted_d[int(len(sorted_d)*0.99)]:.3f} ms")
    print(f"    Max   : {max(ms_delays):.3f} ms")

    utilisation = ARRIVAL_RATE * SERVICE_TIME_S
    print(f"\n  Server utilisation: {utilisation:.1%}")

    # Write CSV
    out = os.path.join(os.path.dirname(__file__), "..", "..", "results", "raw", "gateway_sim.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["message_id", "queueing_delay_ms"])
        for i, d in enumerate(ms_delays):
            w.writerow([i, f"{d:.4f}"])
    print(f"\n  Results → {out}")


if __name__ == "__main__":
    main()
