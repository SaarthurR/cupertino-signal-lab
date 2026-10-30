# M3 independent holdout count check

**50.78% of 128 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = 2024-10-09 measured De Anza/Stelling 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 0; running after drain: 144; waiting to insert: 1448. Teleports and incomplete trips limit interpretation.
A miss can reflect the repeated fit hour, mixed-year Mary observations, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 62 | 34 | 8.0829 |
| De Anza Blvd / E / R | 17:30 | 30 | 34 | 1.4142 |
| De Anza Blvd / E / T | 17:30 | 121 | 68 | 10.9041 |
| De Anza Blvd / N / L | 17:30 | 138 | 51 | 17.8992 |
| De Anza Blvd / N / R | 17:30 | 61 | 22 | 12.1079 |
| De Anza Blvd / N / T | 17:30 | 367 | 217 | 17.5562 |
| De Anza Blvd / S / L | 17:30 | 70 | 54 | 4.064 |
| De Anza Blvd / S / R | 17:30 | 60 | 65 | 1.2649 |
| De Anza Blvd / S / T | 17:30 | 169 | 151 | 2.846 |
| De Anza Blvd / W / L | 17:30 | 41 | 33 | 2.6304 |
| De Anza Blvd / W / R | 17:30 | 71 | 68 | 0.7197 |
| De Anza Blvd / W / T | 17:30 | 317 | 202 | 14.2777 |
| De Anza Blvd / E / L | 17:45 | 69 | 25 | 12.8361 |
| De Anza Blvd / E / R | 17:45 | 41 | 34 | 2.2862 |
| De Anza Blvd / E / T | 17:45 | 130 | 69 | 12.2306 |
| De Anza Blvd / N / L | 17:45 | 200 | 44 | 28.2472 |
| De Anza Blvd / N / R | 17:45 | 45 | 29 | 5.2608 |
| De Anza Blvd / N / T | 17:45 | 370 | 252 | 13.3823 |
| De Anza Blvd / S / L | 17:45 | 77 | 43 | 8.7788 |
| De Anza Blvd / S / R | 17:45 | 76 | 71 | 1.1664 |
| De Anza Blvd / S / T | 17:45 | 125 | 169 | 7.2581 |
| De Anza Blvd / W / L | 17:45 | 42 | 26 | 5.488 |
| De Anza Blvd / W / R | 17:45 | 102 | 65 | 8.0982 |
| De Anza Blvd / W / T | 17:45 | 266 | 236 | 3.7872 |
| De Anza Blvd / E / L | 18:00 | 80 | 40 | 10.328 |
| De Anza Blvd / E / R | 18:00 | 32 | 27 | 1.8411 |
| De Anza Blvd / E / T | 18:00 | 160 | 95 | 11.513 |
| De Anza Blvd / N / L | 18:00 | 173 | 56 | 21.8682 |
| De Anza Blvd / N / R | 18:00 | 42 | 27 | 5.1075 |
| De Anza Blvd / N / T | 18:00 | 401 | 243 | 17.61 |
| De Anza Blvd / S / L | 18:00 | 65 | 48 | 4.5233 |
| De Anza Blvd / S / R | 18:00 | 74 | 66 | 1.9124 |
| De Anza Blvd / S / T | 18:00 | 165 | 126 | 6.4664 |
| De Anza Blvd / W / L | 18:00 | 45 | 26 | 6.3778 |
| De Anza Blvd / W / R | 18:00 | 81 | 61 | 4.7471 |
| De Anza Blvd / W / T | 18:00 | 229 | 166 | 8.9658 |
| De Anza Blvd / E / L | 18:15 | 67 | 36 | 8.6395 |
| De Anza Blvd / E / R | 18:15 | 28 | 32 | 1.4606 |
| De Anza Blvd / E / T | 18:15 | 119 | 70 | 10.0812 |
| De Anza Blvd / N / L | 18:15 | 134 | 49 | 17.7721 |
| De Anza Blvd / N / R | 18:15 | 44 | 29 | 4.9656 |
| De Anza Blvd / N / T | 18:15 | 338 | 231 | 12.6874 |
| De Anza Blvd / S / L | 18:15 | 67 | 45 | 5.8797 |
| De Anza Blvd / S / R | 18:15 | 58 | 70 | 3.0 |
| De Anza Blvd / S / T | 18:15 | 129 | 154 | 4.2033 |
| De Anza Blvd / W / L | 18:15 | 42 | 26 | 5.488 |
| De Anza Blvd / W / R | 18:15 | 79 | 70 | 2.0854 |
| De Anza Blvd / W / T | 18:15 | 222 | 214 | 1.0837 |
| Stelling Rd / E / L | 17:30 | 65 | 15 | 15.8114 |
| Stelling Rd / E / R | 17:30 | 35 | 25 | 3.6515 |
| Stelling Rd / E / T | 17:30 | 135 | 103 | 5.8669 |
| Stelling Rd / N / L | 17:30 | 50 | 46 | 1.1547 |
| Stelling Rd / N / R | 17:30 | 36 | 31 | 1.7277 |
| Stelling Rd / N / T | 17:30 | 103 | 103 | 0.0 |
| Stelling Rd / S / L | 17:30 | 50 | 30 | 6.3246 |
| Stelling Rd / S / R | 17:30 | 49 | 26 | 7.5118 |
| Stelling Rd / S / T | 17:30 | 140 | 65 | 14.8159 |
| Stelling Rd / W / L | 17:30 | 75 | 82 | 1.5801 |
| Stelling Rd / W / R | 17:30 | 72 | 104 | 6.8224 |
| Stelling Rd / W / T | 17:30 | 243 | 252 | 1.1442 |
| Stelling Rd / E / L | 17:45 | 83 | 2 | 24.8497 |
| Stelling Rd / E / R | 17:45 | 48 | 28 | 6.4889 |
| Stelling Rd / E / T | 17:45 | 159 | 110 | 8.4502 |
| Stelling Rd / N / L | 17:45 | 50 | 42 | 2.3591 |
| Stelling Rd / N / R | 17:45 | 45 | 34 | 3.5005 |
| Stelling Rd / N / T | 17:45 | 127 | 107 | 3.698 |
| Stelling Rd / S / L | 17:45 | 63 | 38 | 7.036 |
| Stelling Rd / S / R | 17:45 | 48 | 37 | 3.3746 |
| Stelling Rd / S / T | 17:45 | 87 | 61 | 6.0449 |
| Stelling Rd / W / L | 17:45 | 80 | 93 | 2.7955 |
| Stelling Rd / W / R | 17:45 | 65 | 107 | 9.058 |
| Stelling Rd / W / T | 17:45 | 243 | 271 | 3.4932 |
| Stelling Rd / E / L | 18:00 | 62 | 26 | 10.8544 |
| Stelling Rd / E / R | 18:00 | 32 | 15 | 7.0137 |
| Stelling Rd / E / T | 18:00 | 223 | 113 | 16.9734 |
| Stelling Rd / N / L | 18:00 | 40 | 53 | 3.8128 |
| Stelling Rd / N / R | 18:00 | 43 | 29 | 4.6667 |
| Stelling Rd / N / T | 18:00 | 85 | 132 | 9.0243 |
| Stelling Rd / S / L | 18:00 | 51 | 41 | 2.9488 |
| Stelling Rd / S / R | 18:00 | 24 | 42 | 6.2668 |
| Stelling Rd / S / T | 18:00 | 96 | 82 | 2.968 |
| Stelling Rd / W / L | 18:00 | 66 | 59 | 1.7709 |
| Stelling Rd / W / R | 18:00 | 63 | 96 | 7.4022 |
| Stelling Rd / W / T | 18:00 | 201 | 217 | 2.2135 |
| Stelling Rd / E / L | 18:15 | 61 | 34 | 7.8351 |
| Stelling Rd / E / R | 18:15 | 26 | 16 | 4.3644 |
| Stelling Rd / E / T | 18:15 | 152 | 73 | 14.8964 |
| Stelling Rd / N / L | 18:15 | 31 | 50 | 5.9711 |
| Stelling Rd / N / R | 18:15 | 39 | 34 | 1.6552 |
| Stelling Rd / N / T | 18:15 | 118 | 139 | 3.7051 |
| Stelling Rd / S / L | 18:15 | 73 | 33 | 10.9888 |
| Stelling Rd / S / R | 18:15 | 36 | 41 | 1.6116 |
| Stelling Rd / S / T | 18:15 | 87 | 95 | 1.6773 |
| Stelling Rd / W / L | 18:15 | 68 | 79 | 2.5661 |
| Stelling Rd / W / R | 18:15 | 58 | 101 | 9.6453 |
| Stelling Rd / W / T | 18:15 | 202 | 285 | 10.638 |
| De Anza Blvd / W / U | 17:30 | 5 | 1 | 4.6188 |
| De Anza Blvd / E / U | 17:30 | 8 | 7 | 0.7303 |
| De Anza Blvd / S / U | 17:30 | 19 | 20 | 0.4529 |
| De Anza Blvd / N / U | 17:30 | 10 | 1 | 7.6752 |
| De Anza Blvd / W / U | 17:45 | 2 | 2 | 0.0 |
| De Anza Blvd / E / U | 17:45 | 12 | 3 | 6.5727 |
| De Anza Blvd / S / U | 17:45 | 20 | 15 | 2.3905 |
| De Anza Blvd / N / U | 17:45 | 9 | 1 | 7.1554 |
| De Anza Blvd / W / U | 18:00 | 1 | 1 | 0.0 |
| De Anza Blvd / E / U | 18:00 | 7 | 4 | 2.5584 |
| De Anza Blvd / S / U | 18:00 | 17 | 13 | 2.0656 |
| De Anza Blvd / N / U | 18:00 | 5 | 1 | 4.6188 |
| De Anza Blvd / W / U | 18:15 | 2 | 0 | 4.0 |
| De Anza Blvd / E / U | 18:15 | 4 | 2 | 2.3094 |
| De Anza Blvd / S / U | 18:15 | 21 | 13 | 3.8806 |
| De Anza Blvd / N / U | 18:15 | 11 | 2 | 7.0602 |
| Stelling Rd / W / U | 17:30 | 7 | 5 | 1.633 |
| Stelling Rd / E / U | 17:30 | 24 | 10 | 6.791 |
| Stelling Rd / S / U | 17:30 | 1 | 0 | 2.8284 |
| Stelling Rd / N / U | 17:30 | 5 | 15 | 6.3246 |
| Stelling Rd / W / U | 17:45 | 13 | 8 | 3.0861 |
| Stelling Rd / E / U | 17:45 | 23 | 11 | 5.8209 |
| Stelling Rd / S / U | 17:45 | 0 | 0 | 0.0 |
| Stelling Rd / N / U | 17:45 | 13 | 11 | 1.1547 |
| Stelling Rd / W / U | 18:00 | 8 | 2 | 5.3666 |
| Stelling Rd / E / U | 18:00 | 29 | 16 | 5.4813 |
| Stelling Rd / S / U | 18:00 | 4 | 1 | 3.7947 |
| Stelling Rd / N / U | 18:00 | 13 | 15 | 1.069 |
| Stelling Rd / W / U | 18:15 | 9 | 4 | 3.9223 |
| Stelling Rd / E / U | 18:15 | 25 | 8 | 8.3702 |
| Stelling Rd / S / U | 18:15 | 0 | 3 | 4.899 |
| Stelling Rd / N / U | 18:15 | 18 | 19 | 0.465 |
