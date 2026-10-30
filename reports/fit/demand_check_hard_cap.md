# M3 independent holdout count check

**16.41% of 128 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = 2024-10-09 measured De Anza/Stelling 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 772; running after drain: 1006; waiting to insert: 8288. Teleports and incomplete trips limit interpretation.
A miss can reflect the repeated fit hour, mixed-year Mary observations, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 62 | 4 | 20.193 |
| De Anza Blvd / E / R | 17:30 | 30 | 0 | 15.4919 |
| De Anza Blvd / E / T | 17:30 | 121 | 0 | 31.1127 |
| De Anza Blvd / N / L | 17:30 | 138 | 2 | 32.5102 |
| De Anza Blvd / N / R | 17:30 | 61 | 0 | 22.0907 |
| De Anza Blvd / N / T | 17:30 | 367 | 0 | 54.1849 |
| De Anza Blvd / S / L | 17:30 | 70 | 3 | 22.1798 |
| De Anza Blvd / S / R | 17:30 | 60 | 62 | 0.5121 |
| De Anza Blvd / S / T | 17:30 | 169 | 0 | 36.7696 |
| De Anza Blvd / W / L | 17:30 | 41 | 3 | 16.2033 |
| De Anza Blvd / W / R | 17:30 | 71 | 0 | 23.8328 |
| De Anza Blvd / W / T | 17:30 | 317 | 0 | 50.3587 |
| De Anza Blvd / E / L | 17:45 | 69 | 3 | 22.0 |
| De Anza Blvd / E / R | 17:45 | 41 | 0 | 18.1108 |
| De Anza Blvd / E / T | 17:45 | 130 | 0 | 32.249 |
| De Anza Blvd / N / L | 17:45 | 200 | 3 | 39.1078 |
| De Anza Blvd / N / R | 17:45 | 45 | 1 | 18.3493 |
| De Anza Blvd / N / T | 17:45 | 370 | 0 | 54.4059 |
| De Anza Blvd / S / L | 17:45 | 77 | 3 | 23.4009 |
| De Anza Blvd / S / R | 17:45 | 76 | 61 | 3.6247 |
| De Anza Blvd / S / T | 17:45 | 125 | 0 | 31.6228 |
| De Anza Blvd / W / L | 17:45 | 42 | 3 | 16.4438 |
| De Anza Blvd / W / R | 17:45 | 102 | 0 | 28.5657 |
| De Anza Blvd / W / T | 17:45 | 266 | 0 | 46.1303 |
| De Anza Blvd / E / L | 18:00 | 80 | 4 | 23.4541 |
| De Anza Blvd / E / R | 18:00 | 32 | 3 | 13.8647 |
| De Anza Blvd / E / T | 18:00 | 160 | 0 | 35.7771 |
| De Anza Blvd / N / L | 18:00 | 173 | 3 | 36.2441 |
| De Anza Blvd / N / R | 18:00 | 42 | 1 | 17.6846 |
| De Anza Blvd / N / T | 18:00 | 401 | 0 | 56.6392 |
| De Anza Blvd / S / L | 18:00 | 65 | 3 | 21.2658 |
| De Anza Blvd / S / R | 18:00 | 74 | 68 | 1.4241 |
| De Anza Blvd / S / T | 18:00 | 165 | 0 | 36.3318 |
| De Anza Blvd / W / L | 18:00 | 45 | 3 | 17.1464 |
| De Anza Blvd / W / R | 18:00 | 81 | 0 | 25.4558 |
| De Anza Blvd / W / T | 18:00 | 229 | 0 | 42.8019 |
| De Anza Blvd / E / L | 18:15 | 67 | 3 | 21.6359 |
| De Anza Blvd / E / R | 18:15 | 28 | 0 | 14.9666 |
| De Anza Blvd / E / T | 18:15 | 119 | 0 | 30.8545 |
| De Anza Blvd / N / L | 18:15 | 134 | 3 | 31.656 |
| De Anza Blvd / N / R | 18:15 | 44 | 0 | 18.7617 |
| De Anza Blvd / N / T | 18:15 | 338 | 0 | 52.0 |
| De Anza Blvd / S / L | 18:15 | 67 | 3 | 21.6359 |
| De Anza Blvd / S / R | 18:15 | 58 | 63 | 1.2856 |
| De Anza Blvd / S / T | 18:15 | 129 | 0 | 32.1248 |
| De Anza Blvd / W / L | 18:15 | 42 | 3 | 16.4438 |
| De Anza Blvd / W / R | 18:15 | 79 | 0 | 25.1396 |
| De Anza Blvd / W / T | 18:15 | 222 | 0 | 42.1426 |
| Stelling Rd / E / L | 17:30 | 65 | 0 | 22.8035 |
| Stelling Rd / E / R | 17:30 | 35 | 0 | 16.7332 |
| Stelling Rd / E / T | 17:30 | 135 | 10 | 29.361 |
| Stelling Rd / N / L | 17:30 | 50 | 4 | 17.7054 |
| Stelling Rd / N / R | 17:30 | 36 | 33 | 1.0215 |
| Stelling Rd / N / T | 17:30 | 103 | 107 | 0.7807 |
| Stelling Rd / S / L | 17:30 | 50 | 32 | 5.6223 |
| Stelling Rd / S / R | 17:30 | 49 | 1 | 19.2 |
| Stelling Rd / S / T | 17:30 | 140 | 70 | 13.6626 |
| Stelling Rd / W / L | 17:30 | 75 | 2 | 23.53 |
| Stelling Rd / W / R | 17:30 | 72 | 1 | 23.504 |
| Stelling Rd / W / T | 17:30 | 243 | 3 | 43.2801 |
| Stelling Rd / E / L | 17:45 | 83 | 0 | 25.7682 |
| Stelling Rd / E / R | 17:45 | 48 | 0 | 19.5959 |
| Stelling Rd / E / T | 17:45 | 159 | 14 | 31.181 |
| Stelling Rd / N / L | 17:45 | 50 | 3 | 18.2602 |
| Stelling Rd / N / R | 17:45 | 45 | 35 | 3.1623 |
| Stelling Rd / N / T | 17:45 | 127 | 110 | 3.1233 |
| Stelling Rd / S / L | 17:45 | 63 | 41 | 6.1017 |
| Stelling Rd / S / R | 17:45 | 48 | 3 | 17.8227 |
| Stelling Rd / S / T | 17:45 | 87 | 59 | 6.5543 |
| Stelling Rd / W / L | 17:45 | 80 | 4 | 23.4541 |
| Stelling Rd / W / R | 17:45 | 65 | 0 | 22.8035 |
| Stelling Rd / W / T | 17:45 | 243 | 1 | 43.8193 |
| Stelling Rd / E / L | 18:00 | 62 | 0 | 22.2711 |
| Stelling Rd / E / R | 18:00 | 32 | 0 | 16.0 |
| Stelling Rd / E / T | 18:00 | 223 | 9 | 39.7388 |
| Stelling Rd / N / L | 18:00 | 40 | 1 | 17.2273 |
| Stelling Rd / N / R | 18:00 | 43 | 28 | 5.0351 |
| Stelling Rd / N / T | 18:00 | 85 | 134 | 9.3652 |
| Stelling Rd / S / L | 18:00 | 51 | 38 | 3.8976 |
| Stelling Rd / S / R | 18:00 | 24 | 5 | 9.9793 |
| Stelling Rd / S / T | 18:00 | 96 | 82 | 2.968 |
| Stelling Rd / W / L | 18:00 | 66 | 5 | 20.476 |
| Stelling Rd / W / R | 18:00 | 63 | 4 | 20.3873 |
| Stelling Rd / W / T | 18:00 | 201 | 2 | 39.5048 |
| Stelling Rd / E / L | 18:15 | 61 | 0 | 22.0907 |
| Stelling Rd / E / R | 18:15 | 26 | 0 | 14.4222 |
| Stelling Rd / E / T | 18:15 | 152 | 12 | 30.9208 |
| Stelling Rd / N / L | 18:15 | 31 | 1 | 15.0 |
| Stelling Rd / N / R | 18:15 | 39 | 28 | 3.801 |
| Stelling Rd / N / T | 18:15 | 118 | 126 | 1.4486 |
| Stelling Rd / S / L | 18:15 | 73 | 33 | 10.9888 |
| Stelling Rd / S / R | 18:15 | 36 | 1 | 16.2747 |
| Stelling Rd / S / T | 18:15 | 87 | 92 | 1.057 |
| Stelling Rd / W / L | 18:15 | 68 | 4 | 21.3333 |
| Stelling Rd / W / R | 18:15 | 58 | 1 | 20.9891 |
| Stelling Rd / W / T | 18:15 | 202 | 5 | 38.7281 |
| De Anza Blvd / W / U | 17:30 | 5 | 0 | 6.3246 |
| De Anza Blvd / E / U | 17:30 | 8 | 0 | 8.0 |
| De Anza Blvd / S / U | 17:30 | 19 | 2 | 10.4926 |
| De Anza Blvd / N / U | 17:30 | 10 | 0 | 8.9443 |
| De Anza Blvd / W / U | 17:45 | 2 | 0 | 4.0 |
| De Anza Blvd / E / U | 17:45 | 12 | 0 | 9.798 |
| De Anza Blvd / S / U | 17:45 | 20 | 5 | 8.4853 |
| De Anza Blvd / N / U | 17:45 | 9 | 0 | 8.4853 |
| De Anza Blvd / W / U | 18:00 | 1 | 0 | 2.8284 |
| De Anza Blvd / E / U | 18:00 | 7 | 0 | 7.4833 |
| De Anza Blvd / S / U | 18:00 | 17 | 8 | 5.0912 |
| De Anza Blvd / N / U | 18:00 | 5 | 0 | 6.3246 |
| De Anza Blvd / W / U | 18:15 | 2 | 0 | 4.0 |
| De Anza Blvd / E / U | 18:15 | 4 | 0 | 5.6569 |
| De Anza Blvd / S / U | 18:15 | 21 | 3 | 10.3923 |
| De Anza Blvd / N / U | 18:15 | 11 | 1 | 8.165 |
| Stelling Rd / W / U | 17:30 | 7 | 0 | 7.4833 |
| Stelling Rd / E / U | 17:30 | 24 | 0 | 13.8564 |
| Stelling Rd / S / U | 17:30 | 1 | 1 | 0.0 |
| Stelling Rd / N / U | 17:30 | 5 | 2 | 3.2071 |
| Stelling Rd / W / U | 17:45 | 13 | 0 | 10.198 |
| Stelling Rd / E / U | 17:45 | 23 | 0 | 13.5647 |
| Stelling Rd / S / U | 17:45 | 0 | 0 | 0.0 |
| Stelling Rd / N / U | 17:45 | 13 | 0 | 10.198 |
| Stelling Rd / W / U | 18:00 | 8 | 1 | 6.5997 |
| Stelling Rd / E / U | 18:00 | 29 | 2 | 13.716 |
| Stelling Rd / S / U | 18:00 | 4 | 1 | 3.7947 |
| Stelling Rd / N / U | 18:00 | 13 | 0 | 10.198 |
| Stelling Rd / W / U | 18:15 | 9 | 0 | 8.4853 |
| Stelling Rd / E / U | 18:15 | 25 | 1 | 13.3128 |
| Stelling Rd / S / U | 18:15 | 0 | 2 | 4.0 |
| Stelling Rd / N / U | 18:15 | 18 | 1 | 11.0311 |
