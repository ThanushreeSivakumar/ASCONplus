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

| method | op | side | payload_len | scenario | n | mean_us | std_us | p95_us | p99_us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | decrypt | both | 16 | mid | 100 | 4106.79 | 369.7901751485073 | 4732.349999999999 | 5914.650000000001 |
| baseline | decrypt | both | 64 | mid | 100 | 7381.86 | 788.6742362402179 | 7977.749999999999 | 9424.560000000025 |
| baseline | decrypt | both | 128 | mid | 100 | 12347.22 | 1005.307878666576 | 14317.65 | 16095.450000000003 |
| baseline | decrypt | both | 256 | mid | 100 | 22337.19 | 2850.4797317134344 | 26921.25 | 37781.700000000004 |
| baseline | encrypt | both | 16 | mid | 100 | 4422.6 | 443.27172048509726 | 5174.099999999999 | 6463.680000000002 |
| baseline | encrypt | both | 64 | mid | 100 | 7620.27 | 690.1766697408319 | 8392.65 | 11862.540000000003 |
| baseline | encrypt | both | 128 | mid | 100 | 12319.29 | 1327.8379046062403 | 14028.15 | 17295.120000000024 |
| baseline | encrypt | both | 256 | mid | 100 | 22715.16 | 4148.150367222832 | 30486.149999999998 | 38979.33000000006 |
| baseline | handshake | both | 0 | mid | 100 | 4.08 | 7.174139866791198 | 6.0 | 22.480000000000246 |
| ecdh_ascon | decrypt | both | 16 | mid | 100 | 4546.5 | 319.3343929886891 | 4984.05 | 5843.370000000006 |
| ecdh_ascon | decrypt | both | 64 | mid | 100 | 8092.02 | 422.7759389386469 | 8855.4 | 9751.740000000002 |
| ecdh_ascon | decrypt | both | 128 | mid | 100 | 12876.9 | 571.2107555646402 | 14002.65 | 14569.230000000001 |
| ecdh_ascon | decrypt | both | 256 | mid | 100 | 22411.08 | 1927.5411807887174 | 25605.75 | 30899.22000000001 |
| ecdh_ascon | encrypt | both | 16 | mid | 100 | 4823.19 | 520.0123870902238 | 5153.999999999998 | 6759.000000000009 |
| ecdh_ascon | encrypt | both | 64 | mid | 100 | 8149.2 | 1012.1935675461576 | 9100.199999999999 | 10501.200000000033 |
| ecdh_ascon | encrypt | both | 128 | mid | 100 | 12837.24 | 1010.9028979535617 | 14383.65 | 15639.750000000022 |
| ecdh_ascon | encrypt | both | 256 | mid | 100 | 23918.07 | 3710.385662263058 | 30174.45 | 45119.82000000001 |
| ecdh_ascon | handshake | both | 0 | mid | 100 | 2897.875 | 170.41814847099715 | 3217.875 | 3370.0250000000015 |
| ecdh_ascon | handshake | client | 0 | mid | 100 | 676.475 | 64.31858737424339 | 798.9999999999999 | 940.9750000000005 |
| ecdh_ascon | handshake | server | 0 | mid | 100 | 1419.95 | 129.841579852472 | 1630.6249999999998 | 1982.175000000001 |

## 3. Cryptographic Sensitivity Scenarios (Low, Mid, High)

| method | op | side | payload_len | scenario | n | mean_us | std_us | p95_us | p99_us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | decrypt | both | 16 | low | 100 | 2053.395 | 184.89508757425364 | 2366.1749999999997 | 2957.3250000000003 |
| baseline | decrypt | both | 64 | low | 100 | 3690.93 | 394.3371181201089 | 3988.8749999999995 | 4712.2800000000125 |
| baseline | decrypt | both | 128 | low | 100 | 6173.61 | 502.653939333288 | 7158.825 | 8047.725000000001 |
| baseline | decrypt | both | 256 | low | 100 | 11168.595 | 1425.2398658567172 | 13460.625 | 18890.850000000002 |
| baseline | encrypt | both | 16 | low | 100 | 2211.3 | 221.63586024254863 | 2587.0499999999997 | 3231.840000000001 |
| baseline | encrypt | both | 64 | low | 100 | 3810.135 | 345.08833487041596 | 4196.325 | 5931.270000000001 |
| baseline | encrypt | both | 128 | low | 100 | 6159.645 | 663.9189523031201 | 7014.075 | 8647.560000000012 |
| baseline | encrypt | both | 256 | low | 100 | 11357.58 | 2074.075183611416 | 15243.074999999999 | 19489.66500000003 |
| baseline | handshake | both | 0 | low | 100 | 2.04 | 3.587069933395599 | 3.0 | 11.240000000000123 |
| ecdh_ascon | decrypt | both | 16 | low | 100 | 2273.25 | 159.66719649434455 | 2492.025 | 2921.685000000003 |
| ecdh_ascon | decrypt | both | 64 | low | 100 | 4046.01 | 211.38796946932345 | 4427.7 | 4875.870000000001 |
| ecdh_ascon | decrypt | both | 128 | low | 100 | 6438.45 | 285.6053777823201 | 7001.325 | 7284.615000000001 |
| ecdh_ascon | decrypt | both | 256 | low | 100 | 11205.54 | 963.7705903943587 | 12802.875 | 15449.610000000004 |
| ecdh_ascon | encrypt | both | 16 | low | 100 | 2411.595 | 260.0061935451119 | 2576.999999999999 | 3379.5000000000045 |
| ecdh_ascon | encrypt | both | 64 | low | 100 | 4074.6 | 506.0967837730788 | 4550.099999999999 | 5250.600000000017 |
| ecdh_ascon | encrypt | both | 128 | low | 100 | 6418.62 | 505.45144897678085 | 7191.825 | 7819.875000000011 |
| ecdh_ascon | encrypt | both | 256 | low | 100 | 11959.035 | 1855.192831131529 | 15087.225 | 22559.910000000003 |
| ecdh_ascon | handshake | both | 0 | low | 100 | 1159.15 | 68.16725938839886 | 1287.1499999999999 | 1348.0100000000004 |
| ecdh_ascon | handshake | client | 0 | low | 100 | 270.59 | 25.727434949697358 | 319.59999999999997 | 376.3900000000002 |
| ecdh_ascon | handshake | server | 0 | low | 100 | 567.98 | 51.936631940988796 | 652.2499999999999 | 792.8700000000005 |
| baseline | decrypt | both | 16 | mid | 100 | 4106.79 | 369.7901751485073 | 4732.349999999999 | 5914.650000000001 |
| baseline | decrypt | both | 64 | mid | 100 | 7381.86 | 788.6742362402179 | 7977.749999999999 | 9424.560000000025 |
| baseline | decrypt | both | 128 | mid | 100 | 12347.22 | 1005.307878666576 | 14317.65 | 16095.450000000003 |
| baseline | decrypt | both | 256 | mid | 100 | 22337.19 | 2850.4797317134344 | 26921.25 | 37781.700000000004 |
| baseline | encrypt | both | 16 | mid | 100 | 4422.6 | 443.27172048509726 | 5174.099999999999 | 6463.680000000002 |
| baseline | encrypt | both | 64 | mid | 100 | 7620.27 | 690.1766697408319 | 8392.65 | 11862.540000000003 |
| baseline | encrypt | both | 128 | mid | 100 | 12319.29 | 1327.8379046062403 | 14028.15 | 17295.120000000024 |
| baseline | encrypt | both | 256 | mid | 100 | 22715.16 | 4148.150367222832 | 30486.149999999998 | 38979.33000000006 |
| baseline | handshake | both | 0 | mid | 100 | 4.08 | 7.174139866791198 | 6.0 | 22.480000000000246 |
| ecdh_ascon | decrypt | both | 16 | mid | 100 | 4546.5 | 319.3343929886891 | 4984.05 | 5843.370000000006 |
| ecdh_ascon | decrypt | both | 64 | mid | 100 | 8092.02 | 422.7759389386469 | 8855.4 | 9751.740000000002 |
| ecdh_ascon | decrypt | both | 128 | mid | 100 | 12876.9 | 571.2107555646402 | 14002.65 | 14569.230000000001 |
| ecdh_ascon | decrypt | both | 256 | mid | 100 | 22411.08 | 1927.5411807887174 | 25605.75 | 30899.22000000001 |
| ecdh_ascon | encrypt | both | 16 | mid | 100 | 4823.19 | 520.0123870902238 | 5153.999999999998 | 6759.000000000009 |
| ecdh_ascon | encrypt | both | 64 | mid | 100 | 8149.2 | 1012.1935675461576 | 9100.199999999999 | 10501.200000000033 |
| ecdh_ascon | encrypt | both | 128 | mid | 100 | 12837.24 | 1010.9028979535617 | 14383.65 | 15639.750000000022 |
| ecdh_ascon | encrypt | both | 256 | mid | 100 | 23918.07 | 3710.385662263058 | 30174.45 | 45119.82000000001 |
| ecdh_ascon | handshake | both | 0 | mid | 100 | 2897.875 | 170.41814847099715 | 3217.875 | 3370.0250000000015 |
| ecdh_ascon | handshake | client | 0 | mid | 100 | 676.475 | 64.31858737424339 | 798.9999999999999 | 940.9750000000005 |
| ecdh_ascon | handshake | server | 0 | mid | 100 | 1419.95 | 129.841579852472 | 1630.6249999999998 | 1982.175000000001 |
| baseline | decrypt | both | 16 | high | 100 | 8213.58 | 739.5803502970145 | 9464.699999999999 | 11829.300000000001 |
| baseline | decrypt | both | 64 | high | 100 | 14763.72 | 1577.3484724804357 | 15955.499999999998 | 18849.12000000005 |
| baseline | decrypt | both | 128 | high | 100 | 24694.44 | 2010.615757333152 | 28635.3 | 32190.900000000005 |
| baseline | decrypt | both | 256 | high | 100 | 44674.38 | 5700.959463426869 | 53842.5 | 75563.40000000001 |
| baseline | encrypt | both | 16 | high | 100 | 8845.2 | 886.5434409701945 | 10348.199999999999 | 12927.360000000004 |
| baseline | encrypt | both | 64 | high | 100 | 15240.54 | 1380.3533394816639 | 16785.3 | 23725.080000000005 |
| baseline | encrypt | both | 128 | high | 100 | 24638.58 | 2655.6758092124805 | 28056.3 | 34590.24000000005 |
| baseline | encrypt | both | 256 | high | 100 | 45430.32 | 8296.300734445664 | 60972.299999999996 | 77958.66000000012 |
| baseline | handshake | both | 0 | high | 100 | 8.16 | 14.348279733582396 | 12.0 | 44.96000000000049 |
| ecdh_ascon | decrypt | both | 16 | high | 100 | 9093.0 | 638.6687859773782 | 9968.1 | 11686.740000000013 |
| ecdh_ascon | decrypt | both | 64 | high | 100 | 16184.04 | 845.5518778772938 | 17710.8 | 19503.480000000003 |
| ecdh_ascon | decrypt | both | 128 | high | 100 | 25753.8 | 1142.4215111292804 | 28005.3 | 29138.460000000003 |
| ecdh_ascon | decrypt | both | 256 | high | 100 | 44822.16 | 3855.0823615774348 | 51211.5 | 61798.44000000002 |
| ecdh_ascon | encrypt | both | 16 | high | 100 | 9646.38 | 1040.0247741804476 | 10307.999999999996 | 13518.000000000018 |
| ecdh_ascon | encrypt | both | 64 | high | 100 | 16298.4 | 2024.3871350923152 | 18200.399999999998 | 21002.400000000067 |
| ecdh_ascon | encrypt | both | 128 | high | 100 | 25674.48 | 2021.8057959071234 | 28767.3 | 31279.500000000044 |
| ecdh_ascon | encrypt | both | 256 | high | 100 | 47836.14 | 7420.771324526116 | 60348.9 | 90239.64000000001 |
| ecdh_ascon | handshake | both | 0 | high | 100 | 5795.75 | 340.8362969419943 | 6435.75 | 6740.050000000003 |
| ecdh_ascon | handshake | client | 0 | high | 100 | 1352.95 | 128.63717474848679 | 1597.9999999999998 | 1881.950000000001 |
| ecdh_ascon | handshake | server | 0 | high | 100 | 2839.9 | 259.683159704944 | 3261.2499999999995 | 3964.350000000002 |

## 4. End-to-End Handshake Latency

| method | scenario | n | mean_us | std_us | p95_us | p99_us |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | mid | 50 | 4474.64 | 636.8268838546313 | 5711.299999999999 | 6842.499999999996 |
| ecdh_ascon | mid | 50 | 11013.35 | 1462.9069824447877 | 13831.75 | 16245.025 |

## 5. Memory Usage

> **Memory Methodology**: RSS measurements are treated as an unscaled memory proxy representing Python runtime heap allocation and library residency.

| method | n | mean_rss_delta_kb | std_rss_delta_kb | mean_hwm_kb | std_hwm_kb |
| --- | --- | --- | --- | --- | --- |
| baseline | 20 | 7098.9 | 0.5525062514530825 | 8999.05 | 0.5104177855340405 |
| ecdh_ascon | 20 | 4059.7 | 0.47016234598162726 | 4074.85 | 0.36634754853252327 |

> ASCON is pure Python (`ascon` package); absolute times reflect interpreted Python execution. Compare methods relative to each other.
