# Benchmark Summary

## Crypto Benchmarks

| method | op | side | payload_len | n | mean_us | std_us | p95_us | p99_us | bench |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | decrypt | both | 16 | 100 | 136.893 | 12.326339171616906 | 157.74499999999998 | 197.15500000000003 | crypto |
| baseline | decrypt | both | 64 | 100 | 246.06199999999998 | 26.28914120800726 | 265.925 | 314.15200000000084 | crypto |
| baseline | decrypt | both | 128 | 100 | 411.57399999999996 | 33.51026262221919 | 477.25499999999994 | 536.5150000000001 | crypto |
| baseline | decrypt | both | 256 | 100 | 744.573 | 95.01599105711448 | 897.375 | 1259.3900000000003 | crypto |
| baseline | encrypt | both | 16 | 100 | 147.42 | 14.775724016169905 | 172.47 | 215.4560000000001 | crypto |
| baseline | encrypt | both | 64 | 100 | 254.00900000000001 | 23.00588899136107 | 279.755 | 395.41800000000006 | crypto |
| baseline | encrypt | both | 128 | 100 | 410.64300000000003 | 44.261263486874675 | 467.605 | 576.5040000000008 | crypto |
| baseline | encrypt | both | 256 | 100 | 757.1720000000001 | 138.2716789074277 | 1016.2049999999999 | 1299.3110000000022 | crypto |
| baseline | handshake | both | 0 | 100 | 0.204 | 0.35870699333955997 | 0.3 | 1.1240000000000123 | crypto |
| ecdh_ascon | decrypt | both | 16 | 100 | 151.55 | 10.64447976628964 | 166.135 | 194.7790000000002 | crypto |
| ecdh_ascon | decrypt | both | 64 | 100 | 269.7339999999999 | 14.0925312979549 | 295.18 | 325.05800000000005 | crypto |
| ecdh_ascon | decrypt | both | 128 | 100 | 429.23 | 19.040358518821346 | 466.755 | 485.641 | crypto |
| ecdh_ascon | decrypt | both | 256 | 100 | 747.0360000000001 | 64.25137269295725 | 853.525 | 1029.9740000000002 | crypto |
| ecdh_ascon | encrypt | both | 16 | 100 | 160.773 | 17.33374623634079 | 171.79999999999995 | 225.3000000000003 | crypto |
| ecdh_ascon | encrypt | both | 64 | 100 | 271.64 | 33.739785584871925 | 303.34 | 350.0400000000011 | crypto |
| ecdh_ascon | encrypt | both | 128 | 100 | 427.908 | 33.69676326511872 | 479.455 | 521.3250000000007 | crypto |
| ecdh_ascon | encrypt | both | 256 | 100 | 797.2690000000001 | 123.67952207543529 | 1005.815 | 1503.9940000000001 | crypto |
| ecdh_ascon | handshake | both | 0 | 100 | 115.91499999999998 | 6.8167259388398875 | 128.71499999999997 | 134.80100000000004 | crypto |
| ecdh_ascon | handshake | client | 0 | 100 | 27.059 | 2.572743494969736 | 31.959999999999994 | 37.639000000000024 | crypto |
| ecdh_ascon | handshake | server | 0 | 100 | 56.797999999999995 | 5.19366319409888 | 65.225 | 79.28700000000005 | crypto |

## End-to-End Handshake Latency

| method | n | mean_us | std_us | p95_us | p99_us | bench |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 50 | 223.73199999999997 | 31.841344192731558 | 285.56499999999994 | 342.1249999999998 | e2e |
| ecdh_ascon | 50 | 440.53399999999993 | 58.516279297791506 | 553.27 | 649.801 | e2e |

## Memory Usage

| method | n | mean_rss_delta_kb | std_rss_delta_kb | mean_hwm_kb | std_hwm_kb | bench |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 20 | 7098.9 | 0.5525062514530825 | 8999.05 | 0.5104177855340405 | memory |
| ecdh_ascon | 20 | 4059.7 | 0.47016234598162726 | 4074.85 | 0.36634754853252327 | memory |


> ASCON is pure Python (`ascon` package); absolute times are much slower than C implementations. Compare methods relative to each other.
