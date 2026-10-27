# Benchmark Statistical Summary — Measured (Pi Zero W)

All metrics below report **Measured (Pi Zero W)** performance across cryptographic operations, end-to-end handshake latency, and memory utilization.

## 1. Baseline vs. ECDH+ASCON Overhead Comparison

Overhead calculations:
- **Absolute Overhead** = $\text{ECDH Latency} - \text{Baseline Latency}$
- **Percentage Overhead** = $\left(\frac{\text{ECDH Latency} - \text{Baseline Latency}}{\text{Baseline Latency}}\right) \times 100\%$

### Handshake Latency Overhead

| Evaluation Scope | Baseline Mean (µs) | ECDH+ASCON Mean (µs) | Absolute Overhead (µs) | Percentage Overhead (%) |
| :--- | :---: | :---: | :---: | :---: |
| Crypto Handshake (Both Sides) | 4.1 | 2,897.9 | +2,893.8 | +70,926.3% |
| End-to-End Handshake (TCP Loopback) | 4,474.6 | 11,013.4 | +6,538.7 | +146.1% |

### ASCON Encryption and Decryption Overhead

| Operation | Payload Size (bytes) | Baseline Mean (µs) | ECDH+ASCON Mean (µs) | Absolute Overhead (µs) | Percentage Overhead (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Encrypt | 16 | 4,422.6 | 4,823.2 | +400.6 | +9.06% |
| Encrypt | 64 | 7,620.3 | 8,149.2 | +528.9 | +6.94% |
| Encrypt | 128 | 12,319.3 | 12,837.2 | +517.9 | +4.20% |
| Encrypt | 256 | 22,715.2 | 23,918.1 | +1,202.9 | +5.30% |
| Decrypt | 16 | 4,106.8 | 4,546.5 | +439.7 | +10.71% |
| Decrypt | 64 | 7,381.9 | 8,092.0 | +710.2 | +9.62% |
| Decrypt | 128 | 12,347.2 | 12,876.9 | +529.7 | +4.29% |
| Decrypt | 256 | 22,337.2 | 22,411.1 | +73.9 | +0.33% |

## 2. Cryptographic Latency (Primary Scenario: Mid)

| method     | op        | side   |   payload_len | scenario   |   n |   mean_us |     std_us |   p95_us |    p99_us |
|:-----------|:----------|:-------|--------------:|:-----------|----:|----------:|-----------:|---------:|----------:|
| baseline   | decrypt   | both   |            16 | mid        | 100 |  4106.79  |  369.79    |  4732.35 |  5914.65  |
| baseline   | decrypt   | both   |            64 | mid        | 100 |  7381.86  |  788.674   |  7977.75 |  9424.56  |
| baseline   | decrypt   | both   |           128 | mid        | 100 | 12347.2   | 1005.31    | 14317.6  | 16095.5   |
| baseline   | decrypt   | both   |           256 | mid        | 100 | 22337.2   | 2850.48    | 26921.2  | 37781.7   |
| baseline   | encrypt   | both   |            16 | mid        | 100 |  4422.6   |  443.272   |  5174.1  |  6463.68  |
| baseline   | encrypt   | both   |            64 | mid        | 100 |  7620.27  |  690.177   |  8392.65 | 11862.5   |
| baseline   | encrypt   | both   |           128 | mid        | 100 | 12319.3   | 1327.84    | 14028.1  | 17295.1   |
| baseline   | encrypt   | both   |           256 | mid        | 100 | 22715.2   | 4148.15    | 30486.1  | 38979.3   |
| baseline   | handshake | both   |             0 | mid        | 100 |     4.08  |    7.17414 |     6    |    22.48  |
| ecdh_ascon | decrypt   | both   |            16 | mid        | 100 |  4546.5   |  319.334   |  4984.05 |  5843.37  |
| ecdh_ascon | decrypt   | both   |            64 | mid        | 100 |  8092.02  |  422.776   |  8855.4  |  9751.74  |
| ecdh_ascon | decrypt   | both   |           128 | mid        | 100 | 12876.9   |  571.211   | 14002.6  | 14569.2   |
| ecdh_ascon | decrypt   | both   |           256 | mid        | 100 | 22411.1   | 1927.54    | 25605.8  | 30899.2   |
| ecdh_ascon | encrypt   | both   |            16 | mid        | 100 |  4823.19  |  520.012   |  5154    |  6759     |
| ecdh_ascon | encrypt   | both   |            64 | mid        | 100 |  8149.2   | 1012.19    |  9100.2  | 10501.2   |
| ecdh_ascon | encrypt   | both   |           128 | mid        | 100 | 12837.2   | 1010.9     | 14383.6  | 15639.8   |
| ecdh_ascon | encrypt   | both   |           256 | mid        | 100 | 23918.1   | 3710.39    | 30174.5  | 45119.8   |
| ecdh_ascon | handshake | both   |             0 | mid        | 100 |  2897.88  |  170.418   |  3217.88 |  3370.03  |
| ecdh_ascon | handshake | client |             0 | mid        | 100 |   676.475 |   64.3186  |   799    |   940.975 |
| ecdh_ascon | handshake | server |             0 | mid        | 100 |  1419.95  |  129.842   |  1630.62 |  1982.18  |

## 3. Cryptographic Sensitivity Scenarios (Low, Mid, High)

| method     | op        | side   |   payload_len | scenario   |   n |   mean_us |     std_us |    p95_us |    p99_us |
|:-----------|:----------|:-------|--------------:|:-----------|----:|----------:|-----------:|----------:|----------:|
| baseline   | decrypt   | both   |            16 | low        | 100 |  2053.39  |  184.895   |  2366.17  |  2957.33  |
| baseline   | decrypt   | both   |            64 | low        | 100 |  3690.93  |  394.337   |  3988.87  |  4712.28  |
| baseline   | decrypt   | both   |           128 | low        | 100 |  6173.61  |  502.654   |  7158.82  |  8047.73  |
| baseline   | decrypt   | both   |           256 | low        | 100 | 11168.6   | 1425.24    | 13460.6   | 18890.9   |
| baseline   | encrypt   | both   |            16 | low        | 100 |  2211.3   |  221.636   |  2587.05  |  3231.84  |
| baseline   | encrypt   | both   |            64 | low        | 100 |  3810.14  |  345.088   |  4196.32  |  5931.27  |
| baseline   | encrypt   | both   |           128 | low        | 100 |  6159.65  |  663.919   |  7014.07  |  8647.56  |
| baseline   | encrypt   | both   |           256 | low        | 100 | 11357.6   | 2074.08    | 15243.1   | 19489.7   |
| baseline   | handshake | both   |             0 | low        | 100 |     2.04  |    3.58707 |     3     |    11.24  |
| ecdh_ascon | decrypt   | both   |            16 | low        | 100 |  2273.25  |  159.667   |  2492.03  |  2921.69  |
| ecdh_ascon | decrypt   | both   |            64 | low        | 100 |  4046.01  |  211.388   |  4427.7   |  4875.87  |
| ecdh_ascon | decrypt   | both   |           128 | low        | 100 |  6438.45  |  285.605   |  7001.32  |  7284.62  |
| ecdh_ascon | decrypt   | both   |           256 | low        | 100 | 11205.5   |  963.771   | 12802.9   | 15449.6   |
| ecdh_ascon | encrypt   | both   |            16 | low        | 100 |  2411.59  |  260.006   |  2577     |  3379.5   |
| ecdh_ascon | encrypt   | both   |            64 | low        | 100 |  4074.6   |  506.097   |  4550.1   |  5250.6   |
| ecdh_ascon | encrypt   | both   |           128 | low        | 100 |  6418.62  |  505.451   |  7191.82  |  7819.88  |
| ecdh_ascon | encrypt   | both   |           256 | low        | 100 | 11959     | 1855.19    | 15087.2   | 22559.9   |
| ecdh_ascon | handshake | both   |             0 | low        | 100 |  1448.94  |   85.2091  |  1608.94  |  1685.01  |
| ecdh_ascon | handshake | client |             0 | low        | 100 |   338.238 |   32.1593  |   399.5   |   470.488 |
| ecdh_ascon | handshake | server |             0 | low        | 100 |   709.975 |   64.9208  |   815.312 |   991.088 |
| baseline   | decrypt   | both   |            16 | mid        | 100 |  4106.79  |  369.79    |  4732.35  |  5914.65  |
| baseline   | decrypt   | both   |            64 | mid        | 100 |  7381.86  |  788.674   |  7977.75  |  9424.56  |
| baseline   | decrypt   | both   |           128 | mid        | 100 | 12347.2   | 1005.31    | 14317.6   | 16095.5   |
| baseline   | decrypt   | both   |           256 | mid        | 100 | 22337.2   | 2850.48    | 26921.2   | 37781.7   |
| baseline   | encrypt   | both   |            16 | mid        | 100 |  4422.6   |  443.272   |  5174.1   |  6463.68  |
| baseline   | encrypt   | both   |            64 | mid        | 100 |  7620.27  |  690.177   |  8392.65  | 11862.5   |
| baseline   | encrypt   | both   |           128 | mid        | 100 | 12319.3   | 1327.84    | 14028.1   | 17295.1   |
| baseline   | encrypt   | both   |           256 | mid        | 100 | 22715.2   | 4148.15    | 30486.1   | 38979.3   |
| baseline   | handshake | both   |             0 | mid        | 100 |     4.08  |    7.17414 |     6     |    22.48  |
| ecdh_ascon | decrypt   | both   |            16 | mid        | 100 |  4546.5   |  319.334   |  4984.05  |  5843.37  |
| ecdh_ascon | decrypt   | both   |            64 | mid        | 100 |  8092.02  |  422.776   |  8855.4   |  9751.74  |
| ecdh_ascon | decrypt   | both   |           128 | mid        | 100 | 12876.9   |  571.211   | 14002.6   | 14569.2   |
| ecdh_ascon | decrypt   | both   |           256 | mid        | 100 | 22411.1   | 1927.54    | 25605.8   | 30899.2   |
| ecdh_ascon | encrypt   | both   |            16 | mid        | 100 |  4823.19  |  520.012   |  5154     |  6759     |
| ecdh_ascon | encrypt   | both   |            64 | mid        | 100 |  8149.2   | 1012.19    |  9100.2   | 10501.2   |
| ecdh_ascon | encrypt   | both   |           128 | mid        | 100 | 12837.2   | 1010.9     | 14383.6   | 15639.8   |
| ecdh_ascon | encrypt   | both   |           256 | mid        | 100 | 23918.1   | 3710.39    | 30174.5   | 45119.8   |
| ecdh_ascon | handshake | both   |             0 | mid        | 100 |  2897.88  |  170.418   |  3217.88  |  3370.03  |
| ecdh_ascon | handshake | client |             0 | mid        | 100 |   676.475 |   64.3186  |   799     |   940.975 |
| ecdh_ascon | handshake | server |             0 | mid        | 100 |  1419.95  |  129.842   |  1630.62  |  1982.18  |
| baseline   | decrypt   | both   |            16 | high       | 100 |  8213.58  |  739.58    |  9464.7   | 11829.3   |
| baseline   | decrypt   | both   |            64 | high       | 100 | 14763.7   | 1577.35    | 15955.5   | 18849.1   |
| baseline   | decrypt   | both   |           128 | high       | 100 | 24694.4   | 2010.62    | 28635.3   | 32190.9   |
| baseline   | decrypt   | both   |           256 | high       | 100 | 44674.4   | 5700.96    | 53842.5   | 75563.4   |
| baseline   | encrypt   | both   |            16 | high       | 100 |  8845.2   |  886.543   | 10348.2   | 12927.4   |
| baseline   | encrypt   | both   |            64 | high       | 100 | 15240.5   | 1380.35    | 16785.3   | 23725.1   |
| baseline   | encrypt   | both   |           128 | high       | 100 | 24638.6   | 2655.68    | 28056.3   | 34590.2   |
| baseline   | encrypt   | both   |           256 | high       | 100 | 45430.3   | 8296.3     | 60972.3   | 77958.7   |
| baseline   | handshake | both   |             0 | high       | 100 |     8.16  |   14.3483  |    12     |    44.96  |
| ecdh_ascon | decrypt   | both   |            16 | high       | 100 |  9093     |  638.669   |  9968.1   | 11686.7   |
| ecdh_ascon | decrypt   | both   |            64 | high       | 100 | 16184     |  845.552   | 17710.8   | 19503.5   |
| ecdh_ascon | decrypt   | both   |           128 | high       | 100 | 25753.8   | 1142.42    | 28005.3   | 29138.5   |
| ecdh_ascon | decrypt   | both   |           256 | high       | 100 | 44822.2   | 3855.08    | 51211.5   | 61798.4   |
| ecdh_ascon | encrypt   | both   |            16 | high       | 100 |  9646.38  | 1040.02    | 10308     | 13518     |
| ecdh_ascon | encrypt   | both   |            64 | high       | 100 | 16298.4   | 2024.39    | 18200.4   | 21002.4   |
| ecdh_ascon | encrypt   | both   |           128 | high       | 100 | 25674.5   | 2021.81    | 28767.3   | 31279.5   |
| ecdh_ascon | encrypt   | both   |           256 | high       | 100 | 47836.1   | 7420.77    | 60348.9   | 90239.6   |
| ecdh_ascon | handshake | both   |             0 | high       | 100 |  5795.75  |  340.836   |  6435.75  |  6740.05  |
| ecdh_ascon | handshake | client |             0 | high       | 100 |  1352.95  |  128.637   |  1598     |  1881.95  |
| ecdh_ascon | handshake | server |             0 | high       | 100 |  2839.9   |  259.683   |  3261.25  |  3964.35  |

## 4. End-to-End Handshake Latency

| method     | scenario   |   n |   mean_us |   std_us |   p95_us |   p99_us |
|:-----------|:-----------|----:|----------:|---------:|---------:|---------:|
| baseline   | mid        |  50 |   4474.64 |  636.827 |   5711.3 |   6842.5 |
| ecdh_ascon | mid        |  50 |  11013.4  | 1462.91  |  13831.8 |  16245   |

## 5. Memory Usage

> **Memory Methodology**: Measured Resident Set Size (RSS) delta and peak High Water Mark (HWM) on Raspberry Pi Zero W representing runtime memory consumption.

| method     |   n |   mean_rss_delta_kb |   std_rss_delta_kb |   mean_hwm_kb |   std_hwm_kb |
|:-----------|----:|--------------------:|-------------------:|--------------:|-------------:|
| baseline   |  20 |              7098.9 |           0.552506 |       8999.05 |     0.510418 |
| ecdh_ascon |  20 |              4059.7 |           0.470162 |       4074.85 |     0.366348 |

> ASCON is pure Python (`ascon` package); absolute times reflect interpreted Python execution. Compare methods relative to each other.
