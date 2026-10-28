# M3 independent holdout count check

**48.96% of 96 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = historical measured 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
M1 generated actuated plan used; M4 baseline pending. PM teleports: 0; running after drain: 0; waiting to insert: 0. Teleports and incomplete trips limit interpretation.
A miss can reflect day-to-day differences (the two sites were counted on different dates), the repeated fit hour, assumed side-street demand, OSM geometry/connectivity, or queues in the provisional timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 73 | 62 | 2.6778 |
| De Anza Blvd / E / R | 17:30 | 79 | 74 | 1.1433 |
| De Anza Blvd / E / T | 17:30 | 152 | 133 | 3.1833 |
| De Anza Blvd / N / L | 17:30 | 118 | 135 | 3.023 |
| De Anza Blvd / N / R | 17:30 | 102 | 5 | 26.5231 |
| De Anza Blvd / N / T | 17:30 | 460 | 405 | 5.2893 |
| De Anza Blvd / S / L | 17:30 | 108 | 12 | 24.7871 |
| De Anza Blvd / S / R | 17:30 | 52 | 51 | 0.2787 |
| De Anza Blvd / S / T | 17:30 | 170 | 154 | 2.5142 |
| De Anza Blvd / W / L | 17:30 | 51 | 0 | 20.199 |
| De Anza Blvd / W / R | 17:30 | 79 | 122 | 8.5786 |
| De Anza Blvd / W / T | 17:30 | 262 | 131 | 18.6905 |
| De Anza Blvd / E / L | 17:45 | 63 | 64 | 0.251 |
| De Anza Blvd / E / R | 17:45 | 46 | 62 | 4.3546 |
| De Anza Blvd / E / T | 17:45 | 184 | 131 | 8.4463 |
| De Anza Blvd / N / L | 17:45 | 138 | 140 | 0.3393 |
| De Anza Blvd / N / R | 17:45 | 78 | 5 | 22.6636 |
| De Anza Blvd / N / T | 17:45 | 430 | 343 | 8.8506 |
| De Anza Blvd / S / L | 17:45 | 117 | 8 | 27.5751 |
| De Anza Blvd / S / R | 17:45 | 51 | 45 | 1.7321 |
| De Anza Blvd / S / T | 17:45 | 178 | 150 | 4.3729 |
| De Anza Blvd / W / L | 17:45 | 49 | 0 | 19.799 |
| De Anza Blvd / W / R | 17:45 | 80 | 119 | 7.8196 |
| De Anza Blvd / W / T | 17:45 | 246 | 122 | 18.2828 |
| De Anza Blvd / E / L | 18:00 | 69 | 71 | 0.4781 |
| De Anza Blvd / E / R | 18:00 | 63 | 52 | 2.9013 |
| De Anza Blvd / E / T | 18:00 | 141 | 145 | 0.669 |
| De Anza Blvd / N / L | 18:00 | 135 | 135 | 0.0 |
| De Anza Blvd / N / R | 18:00 | 92 | 5 | 24.9849 |
| De Anza Blvd / N / T | 18:00 | 449 | 416 | 3.1736 |
| De Anza Blvd / S / L | 18:00 | 89 | 17 | 19.7799 |
| De Anza Blvd / S / R | 18:00 | 60 | 51 | 2.4162 |
| De Anza Blvd / S / T | 18:00 | 196 | 179 | 2.483 |
| De Anza Blvd / W / L | 18:00 | 50 | 0 | 20.0 |
| De Anza Blvd / W / R | 18:00 | 97 | 107 | 1.9803 |
| De Anza Blvd / W / T | 18:00 | 200 | 148 | 7.8842 |
| De Anza Blvd / E / L | 18:15 | 62 | 73 | 2.6778 |
| De Anza Blvd / E / R | 18:15 | 48 | 52 | 1.1314 |
| De Anza Blvd / E / T | 18:15 | 179 | 123 | 9.1144 |
| De Anza Blvd / N / L | 18:15 | 129 | 170 | 6.7065 |
| De Anza Blvd / N / R | 18:15 | 95 | 5 | 25.4558 |
| De Anza Blvd / N / T | 18:15 | 382 | 417 | 3.5022 |
| De Anza Blvd / S / L | 18:15 | 75 | 10 | 19.9411 |
| De Anza Blvd / S / R | 18:15 | 39 | 53 | 4.1284 |
| De Anza Blvd / S / T | 18:15 | 158 | 175 | 2.6349 |
| De Anza Blvd / W / L | 18:15 | 72 | 0 | 24.0 |
| De Anza Blvd / W / R | 18:15 | 89 | 94 | 1.0454 |
| De Anza Blvd / W / T | 18:15 | 214 | 129 | 12.9813 |
| Stelling Rd / E / L | 17:30 | 84 | 5 | 23.6852 |
| Stelling Rd / E / R | 17:30 | 41 | 0 | 18.1108 |
| Stelling Rd / E / T | 17:30 | 194 | 126 | 10.7517 |
| Stelling Rd / N / L | 17:30 | 62 | 65 | 0.7529 |
| Stelling Rd / N / R | 17:30 | 49 | 26 | 7.5118 |
| Stelling Rd / N / T | 17:30 | 110 | 84 | 5.2798 |
| Stelling Rd / S / L | 17:30 | 54 | 51 | 0.8281 |
| Stelling Rd / S / R | 17:30 | 73 | 50 | 5.8657 |
| Stelling Rd / S / T | 17:30 | 108 | 73 | 7.3582 |
| Stelling Rd / W / L | 17:30 | 97 | 67 | 6.6259 |
| Stelling Rd / W / R | 17:30 | 89 | 100 | 2.2631 |
| Stelling Rd / W / T | 17:30 | 300 | 263 | 4.4105 |
| Stelling Rd / E / L | 17:45 | 103 | 2 | 27.8786 |
| Stelling Rd / E / R | 17:45 | 31 | 0 | 15.748 |
| Stelling Rd / E / T | 17:45 | 209 | 153 | 8.3249 |
| Stelling Rd / N / L | 17:45 | 56 | 62 | 1.5623 |
| Stelling Rd / N / R | 17:45 | 49 | 39 | 3.0151 |
| Stelling Rd / N / T | 17:45 | 106 | 85 | 4.2978 |
| Stelling Rd / S / L | 17:45 | 45 | 27 | 6.0 |
| Stelling Rd / S / R | 17:45 | 56 | 43 | 3.6955 |
| Stelling Rd / S / T | 17:45 | 78 | 47 | 7.8424 |
| Stelling Rd / W / L | 17:45 | 101 | 69 | 6.9418 |
| Stelling Rd / W / R | 17:45 | 62 | 97 | 7.8508 |
| Stelling Rd / W / T | 17:45 | 279 | 300 | 2.4685 |
| Stelling Rd / E / L | 18:00 | 106 | 12 | 24.4755 |
| Stelling Rd / E / R | 18:00 | 27 | 0 | 14.6969 |
| Stelling Rd / E / T | 18:00 | 201 | 170 | 4.5522 |
| Stelling Rd / N / L | 18:00 | 82 | 62 | 4.714 |
| Stelling Rd / N / R | 18:00 | 38 | 42 | 1.2649 |
| Stelling Rd / N / T | 18:00 | 141 | 94 | 8.6718 |
| Stelling Rd / S / L | 18:00 | 46 | 33 | 4.1369 |
| Stelling Rd / S / R | 18:00 | 85 | 44 | 10.2102 |
| Stelling Rd / S / T | 18:00 | 90 | 74 | 3.5338 |
| Stelling Rd / W / L | 18:00 | 88 | 79 | 1.9698 |
| Stelling Rd / W / R | 18:00 | 68 | 110 | 8.904 |
| Stelling Rd / W / T | 18:00 | 244 | 264 | 2.5098 |
| Stelling Rd / E / L | 18:15 | 116 | 0 | 30.4631 |
| Stelling Rd / E / R | 18:15 | 35 | 0 | 16.7332 |
| Stelling Rd / E / T | 18:15 | 210 | 141 | 10.4169 |
| Stelling Rd / N / L | 18:15 | 85 | 58 | 6.3862 |
| Stelling Rd / N / R | 18:15 | 47 | 37 | 3.0861 |
| Stelling Rd / N / T | 18:15 | 137 | 153 | 2.6575 |
| Stelling Rd / S / L | 18:15 | 55 | 47 | 2.2404 |
| Stelling Rd / S / R | 18:15 | 96 | 57 | 8.9179 |
| Stelling Rd / S / T | 18:15 | 107 | 82 | 5.1434 |
| Stelling Rd / W / L | 18:15 | 77 | 77 | 0.0 |
| Stelling Rd / W / R | 18:15 | 87 | 102 | 3.0861 |
| Stelling Rd / W / T | 18:15 | 245 | 254 | 1.1396 |
