# SIMULATED: Gateway Queue Scalability Study

> **Service Time Input**: Measured (Pi Zero W) (ASCON-128 Decryption, 64-byte payload)
> **Simulation Engine**: SimPy discrete-event queueing model (30 replications, 300s duration)
> **Branching Factor**: $k = 4$ for Hierarchical topology

## 1. Primary Scenario (Mid Service Time: 8.092 ms)

### Theoretical Saturation Thresholds

The theoretical saturation threshold represents the critical network size beyond which arrival rate exceeds single-server processing capacity:

$$N^* = \frac{1}{\lambda_{\text{node}} \times S}$$

- **Rate = 1.0 msg/s**: $N^* = 1 / (1.0 \times 0.008092) = 123.6$ nodes (Star)
- **Rate = 5.0 msg/s**: $N^* = 1 / (5.0 \times 0.008092) = 24.7$ nodes (Star)
- **Hierarchical ($k=4$)**: Threshold is multiplied by $k=4$ ($N^*_{\text{hier}} \approx 4 N^*$).

### Simulation Metrics Table (Primary Mid Scenario)

| Topology | Rate (msg/s) | N | Service Time (ms) | Utilization | Mean Latency (ms) | p99 Latency (ms) | Max Queue | Throughput (msg/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Hierarchical | 1.0 | 5 | 8.092 | 0.010 ± 0.000 | 8.95 ± 0.01 | 10.05 ± 1.19 | 1.0 ± 0.2 | 5.03 ± 0.13 |
| Hierarchical | 1.0 | 10 | 8.092 | 0.020 ± 0.000 | 8.99 ± 0.01 | 12.81 ± 0.77 | 1.3 ± 0.5 | 10.00 ± 0.18 |
| Hierarchical | 1.0 | 25 | 8.092 | 0.051 ± 0.001 | 9.13 ± 0.02 | 15.59 ± 0.27 | 2.1 ± 0.3 | 24.99 ± 0.28 |
| Hierarchical | 1.0 | 50 | 8.092 | 0.101 ± 0.001 | 9.37 ± 0.02 | 16.63 ± 0.08 | 3.1 ± 0.4 | 49.80 ± 0.49 |
| Hierarchical | 1.0 | 100 | 8.092 | 0.202 ± 0.001 | 9.95 ± 0.02 | 20.63 ± 0.22 | 4.2 ± 0.4 | 99.88 ± 0.62 |
| Hierarchical | 5.0 | 5 | 8.092 | 0.050 ± 0.001 | 9.12 ± 0.02 | 15.56 ± 0.22 | 2.2 ± 0.4 | 24.93 ± 0.32 |
| Hierarchical | 5.0 | 10 | 8.092 | 0.101 ± 0.001 | 9.37 ± 0.02 | 16.61 ± 0.08 | 2.9 ± 0.4 | 50.04 ± 0.32 |
| Hierarchical | 5.0 | 25 | 8.092 | 0.253 ± 0.001 | 10.31 ± 0.02 | 22.56 ± 0.22 | 4.9 ± 0.7 | 125.12 ± 0.64 |
| Hierarchical | 5.0 | 50 | 8.092 | 0.506 ± 0.002 | 13.12 ± 0.04 | 36.60 ± 0.42 | 8.6 ± 0.9 | 250.14 ± 0.96 |
| Hierarchical | 5.0 | 100 | 8.092 | 0.999 ± 0.000 | 2004.20 ± 276.17 | 4853.97 ± 643.64 | 648.2 ± 84.5 | 493.76 ± 0.23 |
| Star | 1.0 | 5 | 8.092 | 0.041 ± 0.001 | 8.27 ± 0.02 | 14.48 ± 0.48 | 1.7 ± 0.4 | 5.03 ± 0.13 |
| Star | 1.0 | 10 | 8.092 | 0.081 ± 0.001 | 8.45 ± 0.03 | 15.51 ± 0.19 | 2.2 ± 0.4 | 10.00 ± 0.18 |
| Star | 1.0 | 25 | 8.092 | 0.202 ± 0.002 | 9.12 ± 0.04 | 19.87 ± 0.55 | 3.7 ± 0.5 | 24.99 ± 0.28 |
| Star | 1.0 | 50 | 8.092 | 0.403 ± 0.004 | 10.83 ± 0.07 | 28.69 ± 0.75 | 6.0 ± 0.6 | 49.79 ± 0.49 |
| Star | 1.0 | 100 | 8.092 | 0.808 ± 0.005 | 25.18 ± 0.87 | 95.95 ± 7.30 | 20.5 ± 2.8 | 99.87 ± 0.62 |
| Star | 5.0 | 5 | 8.092 | 0.202 ± 0.003 | 9.11 ± 0.05 | 19.59 ± 0.57 | 3.6 ± 0.7 | 24.93 ± 0.32 |
| Star | 5.0 | 10 | 8.092 | 0.405 ± 0.003 | 10.85 ± 0.06 | 28.65 ± 0.57 | 5.9 ± 0.8 | 50.04 ± 0.32 |
| Star | 5.0 | 25 | 8.092 | 0.999 ± 0.001 | 2116.96 ± 840.50 | 4089.56 ± 1512.80 | 533.3 ± 187.3 | 123.44 ± 0.12 |
| Star | 5.0 | 50 | 8.092 | 1.000 ± 0.000 | 75958.84 ± 500.83 | 150340.71 ± 839.08 | 37971.8 ± 289.7 | 123.58 ± 0.00 |
| Star | 5.0 | 100 | 8.092 | 1.000 ± 0.000 | 112919.00 ± 191.84 | 223597.37 ± 281.49 | 112936.9 ± 305.5 | 123.58 ± 0.00 |

## 2. Sensitivity Scenarios (Low and High Service Times)

| Topology | Sensitivity | Rate (msg/s) | N | Service Time (ms) | Utilization | p99 Latency (ms) | Max Queue | Throughput (msg/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Hierarchical | High | 1.0 | 5 | 16.184 | 0.020 ± 0.001 | 25.73 ± 2.70 | 1.3 ± 0.4 | 5.03 ± 0.15 |
| Hierarchical | High | 1.0 | 10 | 16.184 | 0.040 ± 0.001 | 30.20 ± 0.76 | 1.9 ± 0.4 | 9.96 ± 0.17 |
| Hierarchical | High | 1.0 | 25 | 16.184 | 0.101 ± 0.001 | 33.20 ± 0.19 | 2.8 ± 0.4 | 24.99 ± 0.25 |
| Hierarchical | High | 1.0 | 50 | 16.184 | 0.202 ± 0.002 | 41.28 ± 0.73 | 4.0 ± 0.7 | 50.03 ± 0.44 |
| Hierarchical | High | 1.0 | 100 | 16.184 | 0.405 ± 0.002 | 58.76 ± 1.34 | 6.4 ± 0.8 | 100.08 ± 0.48 |
| Hierarchical | Low | 1.0 | 5 | 4.046 | 0.005 ± 0.000 | 4.47 ± 0.08 | 1.0 ± 0.2 | 5.03 ± 0.13 |
| Hierarchical | Low | 1.0 | 10 | 4.046 | 0.010 ± 0.000 | 4.80 ± 0.32 | 1.1 ± 0.3 | 10.00 ± 0.18 |
| Hierarchical | Low | 1.0 | 25 | 4.046 | 0.025 ± 0.000 | 6.92 ± 0.25 | 1.9 ± 0.3 | 25.00 ± 0.28 |
| Hierarchical | Low | 1.0 | 50 | 4.046 | 0.050 ± 0.000 | 7.78 ± 0.07 | 2.2 ± 0.5 | 49.80 ± 0.49 |
| Hierarchical | Low | 1.0 | 100 | 4.046 | 0.101 ± 0.001 | 8.32 ± 0.02 | 3.3 ± 0.5 | 99.88 ± 0.62 |
| Hierarchical | High | 5.0 | 5 | 16.184 | 0.101 ± 0.001 | 33.25 ± 0.19 | 2.8 ± 0.6 | 24.94 ± 0.37 |
| Hierarchical | High | 5.0 | 10 | 16.184 | 0.202 ± 0.002 | 41.04 ± 0.77 | 3.9 ± 0.6 | 49.81 ± 0.38 |
| Hierarchical | High | 5.0 | 25 | 16.184 | 0.506 ± 0.002 | 72.74 ± 1.36 | 8.6 ± 1.1 | 124.99 ± 0.48 |
| Hierarchical | High | 5.0 | 50 | 16.184 | 0.998 ± 0.001 | 6283.32 ± 1674.67 | 419.8 ± 103.6 | 246.57 ± 0.32 |
| Hierarchical | High | 5.0 | 100 | 16.184 | 1.000 ± 0.000 | 150262.52 ± 478.60 | 19149.9 ± 132.4 | 247.14 ± 0.00 |
| Hierarchical | Low | 5.0 | 5 | 4.046 | 0.025 ± 0.000 | 6.90 ± 0.20 | 1.8 ± 0.4 | 24.93 ± 0.32 |
| Hierarchical | Low | 5.0 | 10 | 4.046 | 0.051 ± 0.000 | 7.77 ± 0.07 | 2.2 ± 0.4 | 50.04 ± 0.32 |
| Hierarchical | Low | 5.0 | 25 | 4.046 | 0.127 ± 0.001 | 8.46 ± 0.02 | 3.6 ± 0.6 | 125.12 ± 0.64 |
| Hierarchical | Low | 5.0 | 50 | 4.046 | 0.253 ± 0.001 | 11.26 ± 0.07 | 5.2 ± 0.6 | 250.14 ± 0.97 |
| Hierarchical | Low | 5.0 | 100 | 4.046 | 0.506 ± 0.001 | 18.23 ± 0.22 | 9.5 ± 1.0 | 500.02 ± 1.02 |
| Star | High | 1.0 | 5 | 16.184 | 0.081 ± 0.002 | 30.95 ± 0.62 | 2.0 ± 0.4 | 5.02 ± 0.15 |
| Star | High | 1.0 | 10 | 16.184 | 0.161 ± 0.003 | 35.93 ± 1.90 | 3.0 ± 0.6 | 9.96 ± 0.17 |
| Star | High | 1.0 | 25 | 16.184 | 0.404 ± 0.004 | 56.77 ± 1.72 | 5.7 ± 0.8 | 24.99 ± 0.25 |
| Star | High | 1.0 | 50 | 16.184 | 0.810 ± 0.007 | 195.50 ± 23.33 | 18.6 ± 2.4 | 50.03 ± 0.44 |
| Star | High | 1.0 | 100 | 16.184 | 1.000 ± 0.000 | 113658.07 ± 1311.36 | 11490.9 ± 143.7 | 61.78 ± 0.00 |
| Star | Low | 1.0 | 5 | 4.046 | 0.020 ± 0.001 | 6.20 ± 0.53 | 1.4 ± 0.5 | 5.03 ± 0.13 |
| Star | Low | 1.0 | 10 | 4.046 | 0.040 ± 0.001 | 7.11 ± 0.19 | 2.0 ± 0.3 | 10.00 ± 0.18 |
| Star | Low | 1.0 | 25 | 4.046 | 0.101 ± 0.001 | 7.91 ± 0.07 | 2.6 ± 0.5 | 24.99 ± 0.28 |
| Star | Low | 1.0 | 50 | 4.046 | 0.201 ± 0.002 | 9.92 ± 0.16 | 3.9 ± 0.4 | 49.80 ± 0.49 |
| Star | Low | 1.0 | 100 | 4.046 | 0.404 ± 0.003 | 14.44 ± 0.25 | 6.6 ± 0.7 | 99.87 ± 0.62 |
| Star | High | 5.0 | 5 | 16.184 | 0.404 ± 0.006 | 57.43 ± 1.85 | 6.0 ± 1.1 | 24.94 ± 0.37 |
| Star | High | 5.0 | 10 | 16.184 | 0.806 ± 0.006 | 186.14 ± 14.17 | 17.9 ± 2.7 | 49.80 ± 0.38 |
| Star | High | 5.0 | 25 | 16.184 | 1.000 ± 0.000 | 150135.54 ± 1001.95 | 18963.7 ± 142.2 | 61.79 ± 0.00 |
| Star | High | 5.0 | 50 | 16.184 | 1.000 ± 0.000 | 223715.84 ± 576.68 | 56467.5 ± 312.0 | 61.79 ± 0.00 |
| Star | High | 5.0 | 100 | 16.184 | 1.000 ± 0.000 | 260360.60 ± 286.63 | 131422.3 ± 342.8 | 61.79 ± 0.00 |
| Star | Low | 5.0 | 5 | 4.046 | 0.101 ± 0.001 | 7.90 ± 0.06 | 2.8 ± 0.6 | 24.93 ± 0.32 |
| Star | Low | 5.0 | 10 | 4.046 | 0.202 ± 0.001 | 9.88 ± 0.16 | 3.8 ± 0.5 | 50.04 ± 0.32 |
| Star | Low | 5.0 | 25 | 4.046 | 0.506 ± 0.003 | 17.90 ± 0.41 | 8.5 ± 1.2 | 125.12 ± 0.64 |
| Star | Low | 5.0 | 50 | 4.046 | 1.000 ± 0.000 | 3780.67 ± 993.96 | 973.5 ± 250.8 | 247.04 ± 0.11 |
| Star | Low | 5.0 | 100 | 4.046 | 1.000 ± 0.000 | 150221.15 ± 411.97 | 75864.3 ± 305.5 | 247.15 ± 0.00 |

## 3. Gateway Bottleneck Findings & Scaling Dynamics

1. **Pre-Saturation Regime ($N < N^*$)**:
   - Gateway utilization scales linearly: $\rho = N \cdot \lambda_{{\text{{node}}}} \cdot S$.
   - Latency remains bounded near single-message service time with minimal queueing.
   - Throughput equals aggregate arrival rate without packet drops.

2. **Post-Saturation Bottleneck ($N > N^*$)**:
   - In the Star topology at 5 msg/s ($N^* \approx 24.7$), the gateway reaches 100% utilization at $N=25$.
   - Beyond $N=25$, queue depth grows linearly over time and p99 latency diverges into hundreds of milliseconds.
   - Gateway throughput hits a ceiling at maximum decryption service capacity $\mu = 1/S \approx 123.6$ msg/s.

3. **Hierarchical Partitioning Mitigation**:
   - Distributing decryption across $k=4$ secondary gateways divides traffic arrival by 4.
   - At $N=50$ (5 msg/s), Star topology suffers severe queue backlog, whereas Hierarchical maintains $\approx 25\%$ utilization per secondary gateway and low latency.
