# M3 independent holdout count check

**42.71% of 96 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = historical measured 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 0; running after drain: 116; waiting to insert: 792. Teleports and incomplete trips limit interpretation.
A miss can reflect day-to-day differences (the two sites were counted on different dates), the repeated fit hour, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 73 | 61 | 2.9321 |
| De Anza Blvd / E / R | 17:30 | 79 | 74 | 1.1433 |
| De Anza Blvd / E / T | 17:30 | 152 | 123 | 4.9463 |
| De Anza Blvd / N / L | 17:30 | 118 | 86 | 6.3369 |
| De Anza Blvd / N / R | 17:30 | 102 | 3 | 27.3266 |
| De Anza Blvd / N / T | 17:30 | 460 | 255 | 21.6843 |
| De Anza Blvd / S / L | 17:30 | 108 | 12 | 24.7871 |
| De Anza Blvd / S / R | 17:30 | 52 | 48 | 1.1314 |
| De Anza Blvd / S / T | 17:30 | 170 | 171 | 0.1532 |
| De Anza Blvd / W / L | 17:30 | 51 | 0 | 20.199 |
| De Anza Blvd / W / R | 17:30 | 79 | 128 | 9.6329 |
| De Anza Blvd / W / T | 17:30 | 262 | 132 | 18.5242 |
| De Anza Blvd / E / L | 17:45 | 63 | 63 | 0.0 |
| De Anza Blvd / E / R | 17:45 | 46 | 56 | 2.8006 |
| De Anza Blvd / E / T | 17:45 | 184 | 124 | 9.6699 |
| De Anza Blvd / N / L | 17:45 | 138 | 86 | 9.8271 |
| De Anza Blvd / N / R | 17:45 | 78 | 3 | 23.5702 |
| De Anza Blvd / N / T | 17:45 | 430 | 217 | 23.6849 |
| De Anza Blvd / S / L | 17:45 | 117 | 8 | 27.5751 |
| De Anza Blvd / S / R | 17:45 | 51 | 46 | 1.4359 |
| De Anza Blvd / S / T | 17:45 | 178 | 152 | 4.0482 |
| De Anza Blvd / W / L | 17:45 | 49 | 0 | 19.799 |
| De Anza Blvd / W / R | 17:45 | 80 | 117 | 7.4561 |
| De Anza Blvd / W / T | 17:45 | 246 | 122 | 18.2828 |
| De Anza Blvd / E / L | 18:00 | 69 | 75 | 1.4142 |
| De Anza Blvd / E / R | 18:00 | 63 | 57 | 1.5492 |
| De Anza Blvd / E / T | 18:00 | 141 | 152 | 1.8176 |
| De Anza Blvd / N / L | 18:00 | 135 | 93 | 7.8673 |
| De Anza Blvd / N / R | 18:00 | 92 | 2 | 26.2557 |
| De Anza Blvd / N / T | 18:00 | 449 | 227 | 24.1504 |
| De Anza Blvd / S / L | 18:00 | 89 | 17 | 19.7799 |
| De Anza Blvd / S / R | 18:00 | 60 | 45 | 4.1404 |
| De Anza Blvd / S / T | 18:00 | 196 | 157 | 5.8711 |
| De Anza Blvd / W / L | 18:00 | 50 | 0 | 20.0 |
| De Anza Blvd / W / R | 18:00 | 97 | 103 | 1.2 |
| De Anza Blvd / W / T | 18:00 | 200 | 151 | 7.3975 |
| De Anza Blvd / E / L | 18:15 | 62 | 71 | 2.2073 |
| De Anza Blvd / E / R | 18:15 | 48 | 54 | 1.6803 |
| De Anza Blvd / E / T | 18:15 | 179 | 133 | 7.3659 |
| De Anza Blvd / N / L | 18:15 | 129 | 71 | 11.6 |
| De Anza Blvd / N / R | 18:15 | 95 | 5 | 25.4558 |
| De Anza Blvd / N / T | 18:15 | 382 | 242 | 15.8519 |
| De Anza Blvd / S / L | 18:15 | 75 | 10 | 19.9411 |
| De Anza Blvd / S / R | 18:15 | 39 | 61 | 6.2225 |
| De Anza Blvd / S / T | 18:15 | 158 | 161 | 0.4751 |
| De Anza Blvd / W / L | 18:15 | 72 | 0 | 24.0 |
| De Anza Blvd / W / R | 18:15 | 89 | 101 | 2.4623 |
| De Anza Blvd / W / T | 18:15 | 214 | 124 | 13.8462 |
| Stelling Rd / E / L | 17:30 | 84 | 5 | 23.6852 |
| Stelling Rd / E / R | 17:30 | 41 | 0 | 18.1108 |
| Stelling Rd / E / T | 17:30 | 194 | 140 | 8.3573 |
| Stelling Rd / N / L | 17:30 | 62 | 62 | 0.0 |
| Stelling Rd / N / R | 17:30 | 49 | 29 | 6.4051 |
| Stelling Rd / N / T | 17:30 | 110 | 87 | 4.6349 |
| Stelling Rd / S / L | 17:30 | 54 | 50 | 1.1094 |
| Stelling Rd / S / R | 17:30 | 73 | 50 | 5.8657 |
| Stelling Rd / S / T | 17:30 | 108 | 74 | 7.1283 |
| Stelling Rd / W / L | 17:30 | 97 | 83 | 2.9515 |
| Stelling Rd / W / R | 17:30 | 89 | 84 | 1.0752 |
| Stelling Rd / W / T | 17:30 | 300 | 226 | 9.1261 |
| Stelling Rd / E / L | 17:45 | 103 | 2 | 27.8786 |
| Stelling Rd / E / R | 17:45 | 31 | 0 | 15.748 |
| Stelling Rd / E / T | 17:45 | 209 | 145 | 9.6211 |
| Stelling Rd / N / L | 17:45 | 56 | 63 | 1.815 |
| Stelling Rd / N / R | 17:45 | 49 | 36 | 3.9882 |
| Stelling Rd / N / T | 17:45 | 106 | 83 | 4.732 |
| Stelling Rd / S / L | 17:45 | 45 | 28 | 5.6277 |
| Stelling Rd / S / R | 17:45 | 56 | 43 | 3.6955 |
| Stelling Rd / S / T | 17:45 | 78 | 47 | 7.8424 |
| Stelling Rd / W / L | 17:45 | 101 | 63 | 8.3928 |
| Stelling Rd / W / R | 17:45 | 62 | 74 | 2.9104 |
| Stelling Rd / W / T | 17:45 | 279 | 280 | 0.1196 |
| Stelling Rd / E / L | 18:00 | 106 | 12 | 24.4755 |
| Stelling Rd / E / R | 18:00 | 27 | 0 | 14.6969 |
| Stelling Rd / E / T | 18:00 | 201 | 162 | 5.7897 |
| Stelling Rd / N / L | 18:00 | 82 | 63 | 4.4629 |
| Stelling Rd / N / R | 18:00 | 38 | 43 | 1.5713 |
| Stelling Rd / N / T | 18:00 | 141 | 97 | 8.0669 |
| Stelling Rd / S / L | 18:00 | 46 | 38 | 2.4689 |
| Stelling Rd / S / R | 18:00 | 85 | 45 | 9.9228 |
| Stelling Rd / S / T | 18:00 | 90 | 73 | 3.7662 |
| Stelling Rd / W / L | 18:00 | 88 | 69 | 4.2889 |
| Stelling Rd / W / R | 18:00 | 68 | 92 | 5.3666 |
| Stelling Rd / W / T | 18:00 | 244 | 248 | 0.5101 |
| Stelling Rd / E / L | 18:15 | 116 | 0 | 30.4631 |
| Stelling Rd / E / R | 18:15 | 35 | 0 | 16.7332 |
| Stelling Rd / E / T | 18:15 | 210 | 153 | 8.4619 |
| Stelling Rd / N / L | 18:15 | 85 | 58 | 6.3862 |
| Stelling Rd / N / R | 18:15 | 47 | 38 | 2.7611 |
| Stelling Rd / N / T | 18:15 | 137 | 156 | 3.1395 |
| Stelling Rd / S / L | 18:15 | 55 | 43 | 3.4286 |
| Stelling Rd / S / R | 18:15 | 96 | 56 | 9.1766 |
| Stelling Rd / S / T | 18:15 | 107 | 84 | 4.7071 |
| Stelling Rd / W / L | 18:15 | 77 | 73 | 0.9238 |
| Stelling Rd / W / R | 18:15 | 87 | 52 | 8.3966 |
| Stelling Rd / W / T | 18:15 | 245 | 247 | 0.255 |
