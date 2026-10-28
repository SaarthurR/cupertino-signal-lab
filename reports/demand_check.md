# M3 independent holdout count check

**14.58% of 96 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = historical measured 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
M1 generated actuated plan used; M4 baseline pending. PM teleports: 1040; running after drain: 1249; waiting to insert: 6609. Teleports and incomplete trips limit interpretation.
A miss can reflect day-to-day differences (the two sites were counted on different dates), the repeated fit hour, assumed side-street demand, OSM geometry/connectivity, or queues in the provisional timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 73 | 3 | 22.711 |
| De Anza Blvd / E / R | 17:30 | 79 | 71 | 1.8475 |
| De Anza Blvd / E / T | 17:30 | 152 | 14 | 30.2949 |
| De Anza Blvd / N / L | 17:30 | 118 | 116 | 0.3698 |
| De Anza Blvd / N / R | 17:30 | 102 | 17 | 22.0389 |
| De Anza Blvd / N / T | 17:30 | 460 | 281 | 18.599 |
| De Anza Blvd / S / L | 17:30 | 108 | 0 | 29.3939 |
| De Anza Blvd / S / R | 17:30 | 52 | 49 | 0.8443 |
| De Anza Blvd / S / T | 17:30 | 170 | 148 | 3.4894 |
| De Anza Blvd / W / L | 17:30 | 51 | 3 | 18.4752 |
| De Anza Blvd / W / R | 17:30 | 79 | 5 | 22.8369 |
| De Anza Blvd / W / T | 17:30 | 262 | 20 | 40.7602 |
| De Anza Blvd / E / L | 17:45 | 63 | 5 | 19.8938 |
| De Anza Blvd / E / R | 17:45 | 46 | 65 | 5.1008 |
| De Anza Blvd / E / T | 17:45 | 184 | 7 | 36.2244 |
| De Anza Blvd / N / L | 17:45 | 138 | 31 | 23.2801 |
| De Anza Blvd / N / R | 17:45 | 78 | 1 | 24.5032 |
| De Anza Blvd / N / T | 17:45 | 430 | 83 | 43.3327 |
| De Anza Blvd / S / L | 17:45 | 117 | 0 | 30.5941 |
| De Anza Blvd / S / R | 17:45 | 51 | 47 | 1.1429 |
| De Anza Blvd / S / T | 17:45 | 178 | 157 | 3.2452 |
| De Anza Blvd / W / L | 17:45 | 49 | 1 | 19.2 |
| De Anza Blvd / W / R | 17:45 | 80 | 14 | 19.2542 |
| De Anza Blvd / W / T | 17:45 | 246 | 8 | 42.2382 |
| De Anza Blvd / E / L | 18:00 | 69 | 1 | 22.9882 |
| De Anza Blvd / E / R | 18:00 | 63 | 32 | 8.9959 |
| De Anza Blvd / E / T | 18:00 | 141 | 0 | 33.5857 |
| De Anza Blvd / N / L | 18:00 | 135 | 125 | 1.7541 |
| De Anza Blvd / N / R | 18:00 | 92 | 7 | 24.1627 |
| De Anza Blvd / N / T | 18:00 | 449 | 374 | 7.3945 |
| De Anza Blvd / S / L | 18:00 | 89 | 0 | 26.6833 |
| De Anza Blvd / S / R | 18:00 | 60 | 45 | 4.1404 |
| De Anza Blvd / S / T | 18:00 | 196 | 168 | 4.151 |
| De Anza Blvd / W / L | 18:00 | 50 | 3 | 18.2602 |
| De Anza Blvd / W / R | 18:00 | 97 | 3 | 26.5872 |
| De Anza Blvd / W / T | 18:00 | 200 | 14 | 35.9626 |
| De Anza Blvd / E / L | 18:15 | 62 | 3 | 20.6986 |
| De Anza Blvd / E / R | 18:15 | 48 | 41 | 2.0987 |
| De Anza Blvd / E / T | 18:15 | 179 | 14 | 33.5931 |
| De Anza Blvd / N / L | 18:15 | 129 | 147 | 3.0645 |
| De Anza Blvd / N / R | 18:15 | 95 | 1 | 27.1355 |
| De Anza Blvd / N / T | 18:15 | 382 | 420 | 3.7953 |
| De Anza Blvd / S / L | 18:15 | 75 | 1 | 24.0088 |
| De Anza Blvd / S / R | 18:15 | 39 | 57 | 5.1962 |
| De Anza Blvd / S / T | 18:15 | 158 | 178 | 3.0861 |
| De Anza Blvd / W / L | 18:15 | 72 | 6 | 21.1369 |
| De Anza Blvd / W / R | 18:15 | 89 | 9 | 22.8571 |
| De Anza Blvd / W / T | 18:15 | 214 | 10 | 38.5524 |
| Stelling Rd / E / L | 17:30 | 84 | 0 | 25.923 |
| Stelling Rd / E / R | 17:30 | 41 | 0 | 18.1108 |
| Stelling Rd / E / T | 17:30 | 194 | 17 | 34.4649 |
| Stelling Rd / N / L | 17:30 | 62 | 0 | 22.2711 |
| Stelling Rd / N / R | 17:30 | 49 | 23 | 8.6667 |
| Stelling Rd / N / T | 17:30 | 110 | 111 | 0.1903 |
| Stelling Rd / S / L | 17:30 | 54 | 0 | 20.7846 |
| Stelling Rd / S / R | 17:30 | 73 | 14 | 17.8911 |
| Stelling Rd / S / T | 17:30 | 108 | 22 | 21.334 |
| Stelling Rd / W / L | 17:30 | 97 | 2 | 27.0054 |
| Stelling Rd / W / R | 17:30 | 89 | 6 | 24.0858 |
| Stelling Rd / W / T | 17:30 | 300 | 23 | 43.5937 |
| Stelling Rd / E / L | 17:45 | 103 | 3 | 27.4721 |
| Stelling Rd / E / R | 17:45 | 31 | 0 | 15.748 |
| Stelling Rd / E / T | 17:45 | 209 | 21 | 35.0622 |
| Stelling Rd / N / L | 17:45 | 56 | 0 | 21.166 |
| Stelling Rd / N / R | 17:45 | 49 | 8 | 15.36 |
| Stelling Rd / N / T | 17:45 | 106 | 46 | 13.7649 |
| Stelling Rd / S / L | 17:45 | 45 | 0 | 18.9737 |
| Stelling Rd / S / R | 17:45 | 56 | 2 | 20.0551 |
| Stelling Rd / S / T | 17:45 | 78 | 22 | 15.8392 |
| Stelling Rd / W / L | 17:45 | 101 | 2 | 27.5906 |
| Stelling Rd / W / R | 17:45 | 62 | 14 | 15.5733 |
| Stelling Rd / W / T | 17:45 | 279 | 30 | 40.065 |
| Stelling Rd / E / L | 18:00 | 106 | 2 | 28.3052 |
| Stelling Rd / E / R | 18:00 | 27 | 0 | 14.6969 |
| Stelling Rd / E / T | 18:00 | 201 | 3 | 39.2098 |
| Stelling Rd / N / L | 18:00 | 82 | 1 | 25.1473 |
| Stelling Rd / N / R | 18:00 | 38 | 9 | 11.9645 |
| Stelling Rd / N / T | 18:00 | 141 | 56 | 17.129 |
| Stelling Rd / S / L | 18:00 | 46 | 0 | 19.1833 |
| Stelling Rd / S / R | 18:00 | 85 | 4 | 24.2848 |
| Stelling Rd / S / T | 18:00 | 90 | 7 | 23.8362 |
| Stelling Rd / W / L | 18:00 | 88 | 1 | 26.0837 |
| Stelling Rd / W / R | 18:00 | 68 | 0 | 23.3238 |
| Stelling Rd / W / T | 18:00 | 244 | 3 | 43.3724 |
| Stelling Rd / E / L | 18:15 | 116 | 5 | 28.5414 |
| Stelling Rd / E / R | 18:15 | 35 | 0 | 16.7332 |
| Stelling Rd / E / T | 18:15 | 210 | 3 | 40.1167 |
| Stelling Rd / N / L | 18:15 | 85 | 0 | 26.0768 |
| Stelling Rd / N / R | 18:15 | 47 | 3 | 17.6 |
| Stelling Rd / N / T | 18:15 | 137 | 10 | 29.6272 |
| Stelling Rd / S / L | 18:15 | 55 | 0 | 20.9762 |
| Stelling Rd / S / R | 18:15 | 96 | 10 | 23.626 |
| Stelling Rd / S / T | 18:15 | 107 | 11 | 24.9963 |
| Stelling Rd / W / L | 18:15 | 77 | 2 | 23.8667 |
| Stelling Rd / W / R | 18:15 | 87 | 11 | 21.7143 |
| Stelling Rd / W / T | 18:15 | 245 | 27 | 37.3867 |
