# M3 independent holdout count check

**39.58% of 96 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = historical measured 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 32; running after drain: 117; waiting to insert: 571. Teleports and incomplete trips limit interpretation.
A miss can reflect day-to-day differences (the two sites were counted on different dates), the repeated fit hour, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 73 | 61 | 2.9321 |
| De Anza Blvd / E / R | 17:30 | 79 | 71 | 1.8475 |
| De Anza Blvd / E / T | 17:30 | 152 | 120 | 5.488 |
| De Anza Blvd / N / L | 17:30 | 118 | 95 | 4.4574 |
| De Anza Blvd / N / R | 17:30 | 102 | 3 | 27.3266 |
| De Anza Blvd / N / T | 17:30 | 460 | 328 | 13.3001 |
| De Anza Blvd / S / L | 17:30 | 108 | 12 | 24.7871 |
| De Anza Blvd / S / R | 17:30 | 52 | 50 | 0.5601 |
| De Anza Blvd / S / T | 17:30 | 170 | 173 | 0.4582 |
| De Anza Blvd / W / L | 17:30 | 51 | 0 | 20.199 |
| De Anza Blvd / W / R | 17:30 | 79 | 112 | 6.7537 |
| De Anza Blvd / W / T | 17:30 | 262 | 115 | 21.4137 |
| De Anza Blvd / E / L | 17:45 | 63 | 63 | 0.0 |
| De Anza Blvd / E / R | 17:45 | 46 | 56 | 2.8006 |
| De Anza Blvd / E / T | 17:45 | 184 | 123 | 9.847 |
| De Anza Blvd / N / L | 17:45 | 138 | 97 | 7.5648 |
| De Anza Blvd / N / R | 17:45 | 78 | 4 | 23.1137 |
| De Anza Blvd / N / T | 17:45 | 430 | 247 | 19.8931 |
| De Anza Blvd / S / L | 17:45 | 117 | 8 | 27.5751 |
| De Anza Blvd / S / R | 17:45 | 51 | 48 | 0.8528 |
| De Anza Blvd / S / T | 17:45 | 178 | 159 | 2.9274 |
| De Anza Blvd / W / L | 17:45 | 49 | 0 | 19.799 |
| De Anza Blvd / W / R | 17:45 | 80 | 83 | 0.6646 |
| De Anza Blvd / W / T | 17:45 | 246 | 93 | 23.5037 |
| De Anza Blvd / E / L | 18:00 | 69 | 72 | 0.7146 |
| De Anza Blvd / E / R | 18:00 | 63 | 55 | 2.083 |
| De Anza Blvd / E / T | 18:00 | 141 | 155 | 2.3016 |
| De Anza Blvd / N / L | 18:00 | 135 | 87 | 9.1119 |
| De Anza Blvd / N / R | 18:00 | 92 | 3 | 25.827 |
| De Anza Blvd / N / T | 18:00 | 449 | 264 | 19.5962 |
| De Anza Blvd / S / L | 18:00 | 89 | 17 | 19.7799 |
| De Anza Blvd / S / R | 18:00 | 60 | 49 | 2.9801 |
| De Anza Blvd / S / T | 18:00 | 196 | 174 | 3.2349 |
| De Anza Blvd / W / L | 18:00 | 50 | 0 | 20.0 |
| De Anza Blvd / W / R | 18:00 | 97 | 95 | 0.4082 |
| De Anza Blvd / W / T | 18:00 | 200 | 66 | 23.2385 |
| De Anza Blvd / E / L | 18:15 | 62 | 74 | 2.9104 |
| De Anza Blvd / E / R | 18:15 | 48 | 58 | 2.7472 |
| De Anza Blvd / E / T | 18:15 | 179 | 140 | 6.1761 |
| De Anza Blvd / N / L | 18:15 | 129 | 93 | 6.8339 |
| De Anza Blvd / N / R | 18:15 | 95 | 5 | 25.4558 |
| De Anza Blvd / N / T | 18:15 | 382 | 240 | 16.1042 |
| De Anza Blvd / S / L | 18:15 | 75 | 10 | 19.9411 |
| De Anza Blvd / S / R | 18:15 | 39 | 54 | 4.3994 |
| De Anza Blvd / S / T | 18:15 | 158 | 168 | 1.5665 |
| De Anza Blvd / W / L | 18:15 | 72 | 0 | 24.0 |
| De Anza Blvd / W / R | 18:15 | 89 | 102 | 2.6606 |
| De Anza Blvd / W / T | 18:15 | 214 | 126 | 13.4986 |
| Stelling Rd / E / L | 17:30 | 84 | 5 | 23.6852 |
| Stelling Rd / E / R | 17:30 | 41 | 0 | 18.1108 |
| Stelling Rd / E / T | 17:30 | 194 | 113 | 13.0756 |
| Stelling Rd / N / L | 17:30 | 62 | 51 | 2.9268 |
| Stelling Rd / N / R | 17:30 | 49 | 21 | 9.4657 |
| Stelling Rd / N / T | 17:30 | 110 | 65 | 9.6214 |
| Stelling Rd / S / L | 17:30 | 54 | 38 | 4.7181 |
| Stelling Rd / S / R | 17:30 | 73 | 47 | 6.7132 |
| Stelling Rd / S / T | 17:30 | 108 | 63 | 9.7333 |
| Stelling Rd / W / L | 17:30 | 97 | 69 | 6.1468 |
| Stelling Rd / W / R | 17:30 | 89 | 69 | 4.5004 |
| Stelling Rd / W / T | 17:30 | 300 | 222 | 9.6562 |
| Stelling Rd / E / L | 17:45 | 103 | 2 | 27.8786 |
| Stelling Rd / E / R | 17:45 | 31 | 0 | 15.748 |
| Stelling Rd / E / T | 17:45 | 209 | 174 | 5.0584 |
| Stelling Rd / N / L | 17:45 | 56 | 74 | 4.4653 |
| Stelling Rd / N / R | 17:45 | 49 | 43 | 1.7693 |
| Stelling Rd / N / T | 17:45 | 106 | 100 | 1.1824 |
| Stelling Rd / S / L | 17:45 | 45 | 39 | 1.8516 |
| Stelling Rd / S / R | 17:45 | 56 | 46 | 2.8006 |
| Stelling Rd / S / T | 17:45 | 78 | 57 | 5.1121 |
| Stelling Rd / W / L | 17:45 | 101 | 54 | 10.6777 |
| Stelling Rd / W / R | 17:45 | 62 | 66 | 1.0 |
| Stelling Rd / W / T | 17:45 | 279 | 199 | 10.3495 |
| Stelling Rd / E / L | 18:00 | 106 | 12 | 24.4755 |
| Stelling Rd / E / R | 18:00 | 27 | 0 | 14.6969 |
| Stelling Rd / E / T | 18:00 | 201 | 123 | 12.2565 |
| Stelling Rd / N / L | 18:00 | 82 | 59 | 5.4785 |
| Stelling Rd / N / R | 18:00 | 38 | 36 | 0.6576 |
| Stelling Rd / N / T | 18:00 | 141 | 80 | 11.6059 |
| Stelling Rd / S / L | 18:00 | 46 | 38 | 2.4689 |
| Stelling Rd / S / R | 18:00 | 85 | 45 | 9.9228 |
| Stelling Rd / S / T | 18:00 | 90 | 69 | 4.7105 |
| Stelling Rd / W / L | 18:00 | 88 | 46 | 10.2622 |
| Stelling Rd / W / R | 18:00 | 68 | 32 | 10.1823 |
| Stelling Rd / W / T | 18:00 | 244 | 117 | 18.9058 |
| Stelling Rd / E / L | 18:15 | 116 | 0 | 30.4631 |
| Stelling Rd / E / R | 18:15 | 35 | 0 | 16.7332 |
| Stelling Rd / E / T | 18:15 | 210 | 178 | 4.5949 |
| Stelling Rd / N / L | 18:15 | 85 | 63 | 5.1149 |
| Stelling Rd / N / R | 18:15 | 47 | 46 | 0.2933 |
| Stelling Rd / N / T | 18:15 | 137 | 175 | 6.0849 |
| Stelling Rd / S / L | 18:15 | 55 | 44 | 3.1269 |
| Stelling Rd / S / R | 18:15 | 96 | 56 | 9.1766 |
| Stelling Rd / S / T | 18:15 | 107 | 89 | 3.6365 |
| Stelling Rd / W / L | 18:15 | 77 | 69 | 1.8727 |
| Stelling Rd / W / R | 18:15 | 87 | 45 | 10.3397 |
| Stelling Rd / W / T | 18:15 | 245 | 206 | 5.1942 |
