# M3 independent holdout count check

**58.59% of 128 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = 2024-10-09 measured De Anza/Stelling 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 0; running after drain: 159; waiting to insert: 542. Teleports and incomplete trips limit interpretation.
A miss can reflect the repeated fit hour, mixed-year Mary observations, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

| movement | interval | observed | simulated | geh |
|---|---|---:|---:|---:|
| De Anza Blvd / E / L | 17:30 | 62 | 29 | 9.7845 |
| De Anza Blvd / E / R | 17:30 | 30 | 34 | 1.4142 |
| De Anza Blvd / E / T | 17:30 | 121 | 68 | 10.9041 |
| De Anza Blvd / N / L | 17:30 | 138 | 99 | 7.1653 |
| De Anza Blvd / N / R | 17:30 | 61 | 33 | 8.1684 |
| De Anza Blvd / N / T | 17:30 | 367 | 290 | 8.4968 |
| De Anza Blvd / S / L | 17:30 | 70 | 47 | 6.0142 |
| De Anza Blvd / S / R | 17:30 | 60 | 72 | 2.9542 |
| De Anza Blvd / S / T | 17:30 | 169 | 159 | 1.5617 |
| De Anza Blvd / W / L | 17:30 | 41 | 28 | 4.4265 |
| De Anza Blvd / W / R | 17:30 | 71 | 61 | 2.4618 |
| De Anza Blvd / W / T | 17:30 | 317 | 208 | 13.4553 |
| De Anza Blvd / E / L | 17:45 | 69 | 30 | 11.0864 |
| De Anza Blvd / E / R | 17:45 | 41 | 34 | 2.2862 |
| De Anza Blvd / E / T | 17:45 | 130 | 72 | 11.5424 |
| De Anza Blvd / N / L | 17:45 | 200 | 95 | 17.2911 |
| De Anza Blvd / N / R | 17:45 | 45 | 31 | 4.5422 |
| De Anza Blvd / N / T | 17:45 | 370 | 261 | 12.2732 |
| De Anza Blvd / S / L | 17:45 | 77 | 49 | 7.0553 |
| De Anza Blvd / S / R | 17:45 | 76 | 47 | 7.3959 |
| De Anza Blvd / S / T | 17:45 | 125 | 147 | 3.773 |
| De Anza Blvd / W / L | 17:45 | 42 | 22 | 7.0711 |
| De Anza Blvd / W / R | 17:45 | 102 | 66 | 7.8558 |
| De Anza Blvd / W / T | 17:45 | 266 | 152 | 15.7711 |
| De Anza Blvd / E / L | 18:00 | 80 | 32 | 12.8285 |
| De Anza Blvd / E / R | 18:00 | 32 | 29 | 1.0864 |
| De Anza Blvd / E / T | 18:00 | 160 | 101 | 10.3294 |
| De Anza Blvd / N / L | 18:00 | 173 | 97 | 13.0821 |
| De Anza Blvd / N / R | 18:00 | 42 | 33 | 2.9394 |
| De Anza Blvd / N / T | 18:00 | 401 | 247 | 17.1111 |
| De Anza Blvd / S / L | 18:00 | 65 | 35 | 8.4853 |
| De Anza Blvd / S / R | 18:00 | 74 | 66 | 1.9124 |
| De Anza Blvd / S / T | 18:00 | 165 | 136 | 4.7278 |
| De Anza Blvd / W / L | 18:00 | 45 | 19 | 9.1924 |
| De Anza Blvd / W / R | 18:00 | 81 | 45 | 9.0711 |
| De Anza Blvd / W / T | 18:00 | 229 | 199 | 4.1015 |
| De Anza Blvd / E / L | 18:15 | 67 | 23 | 13.1183 |
| De Anza Blvd / E / R | 18:15 | 28 | 30 | 0.7428 |
| De Anza Blvd / E / T | 18:15 | 119 | 65 | 11.2598 |
| De Anza Blvd / N / L | 18:15 | 134 | 94 | 7.4927 |
| De Anza Blvd / N / R | 18:15 | 44 | 23 | 7.2565 |
| De Anza Blvd / N / T | 18:15 | 338 | 262 | 8.7757 |
| De Anza Blvd / S / L | 18:15 | 67 | 50 | 4.4453 |
| De Anza Blvd / S / R | 18:15 | 58 | 74 | 3.9389 |
| De Anza Blvd / S / T | 18:15 | 129 | 154 | 4.2033 |
| De Anza Blvd / W / L | 18:15 | 42 | 35 | 2.2563 |
| De Anza Blvd / W / R | 18:15 | 79 | 47 | 8.0632 |
| De Anza Blvd / W / T | 18:15 | 222 | 198 | 3.3123 |
| Stelling Rd / E / L | 17:30 | 65 | 7 | 19.3333 |
| Stelling Rd / E / R | 17:30 | 35 | 28 | 2.4944 |
| Stelling Rd / E / T | 17:30 | 135 | 116 | 3.392 |
| Stelling Rd / N / L | 17:30 | 50 | 39 | 3.2979 |
| Stelling Rd / N / R | 17:30 | 36 | 29 | 2.4558 |
| Stelling Rd / N / T | 17:30 | 103 | 88 | 3.0699 |
| Stelling Rd / S / L | 17:30 | 50 | 36 | 4.27 |
| Stelling Rd / S / R | 17:30 | 49 | 24 | 8.2761 |
| Stelling Rd / S / T | 17:30 | 140 | 61 | 15.7606 |
| Stelling Rd / W / L | 17:30 | 75 | 84 | 2.0188 |
| Stelling Rd / W / R | 17:30 | 72 | 101 | 6.2362 |
| Stelling Rd / W / T | 17:30 | 243 | 242 | 0.1284 |
| Stelling Rd / E / L | 17:45 | 83 | 5 | 23.5179 |
| Stelling Rd / E / R | 17:45 | 48 | 22 | 8.7896 |
| Stelling Rd / E / T | 17:45 | 159 | 123 | 6.0635 |
| Stelling Rd / N / L | 17:45 | 50 | 43 | 2.0531 |
| Stelling Rd / N / R | 17:45 | 45 | 39 | 1.8516 |
| Stelling Rd / N / T | 17:45 | 127 | 134 | 1.2255 |
| Stelling Rd / S / L | 17:45 | 63 | 34 | 8.3283 |
| Stelling Rd / S / R | 17:45 | 48 | 39 | 2.7292 |
| Stelling Rd / S / T | 17:45 | 87 | 67 | 4.5584 |
| Stelling Rd / W / L | 17:45 | 80 | 62 | 4.2724 |
| Stelling Rd / W / R | 17:45 | 65 | 88 | 5.2593 |
| Stelling Rd / W / T | 17:45 | 243 | 211 | 4.2478 |
| Stelling Rd / E / L | 18:00 | 62 | 36 | 7.4286 |
| Stelling Rd / E / R | 18:00 | 32 | 8 | 10.7331 |
| Stelling Rd / E / T | 18:00 | 223 | 90 | 21.263 |
| Stelling Rd / N / L | 18:00 | 40 | 34 | 1.9728 |
| Stelling Rd / N / R | 18:00 | 43 | 29 | 4.6667 |
| Stelling Rd / N / T | 18:00 | 85 | 133 | 9.1951 |
| Stelling Rd / S / L | 18:00 | 51 | 40 | 3.2615 |
| Stelling Rd / S / R | 18:00 | 24 | 43 | 6.5654 |
| Stelling Rd / S / T | 18:00 | 96 | 83 | 2.7483 |
| Stelling Rd / W / L | 18:00 | 66 | 70 | 0.9701 |
| Stelling Rd / W / R | 18:00 | 63 | 90 | 6.1739 |
| Stelling Rd / W / T | 18:00 | 201 | 238 | 4.9948 |
| Stelling Rd / E / L | 18:15 | 61 | 43 | 4.9923 |
| Stelling Rd / E / R | 18:15 | 26 | 18 | 3.4112 |
| Stelling Rd / E / T | 18:15 | 152 | 62 | 17.4013 |
| Stelling Rd / N / L | 18:15 | 31 | 30 | 0.3621 |
| Stelling Rd / N / R | 18:15 | 39 | 30 | 3.0645 |
| Stelling Rd / N / T | 18:15 | 118 | 118 | 0.0 |
| Stelling Rd / S / L | 18:15 | 73 | 33 | 10.9888 |
| Stelling Rd / S / R | 18:15 | 36 | 39 | 0.9798 |
| Stelling Rd / S / T | 18:15 | 87 | 89 | 0.4264 |
| Stelling Rd / W / L | 18:15 | 68 | 77 | 2.114 |
| Stelling Rd / W / R | 18:15 | 58 | 110 | 11.3473 |
| Stelling Rd / W / T | 18:15 | 202 | 269 | 8.7319 |
| De Anza Blvd / W / U | 17:30 | 5 | 2 | 3.2071 |
| De Anza Blvd / E / U | 17:30 | 8 | 1 | 6.5997 |
| De Anza Blvd / S / U | 17:30 | 19 | 20 | 0.4529 |
| De Anza Blvd / N / U | 17:30 | 10 | 6 | 2.8284 |
| De Anza Blvd / W / U | 17:45 | 2 | 1 | 1.633 |
| De Anza Blvd / E / U | 17:45 | 12 | 6 | 4.0 |
| De Anza Blvd / S / U | 17:45 | 20 | 15 | 2.3905 |
| De Anza Blvd / N / U | 17:45 | 9 | 8 | 0.686 |
| De Anza Blvd / W / U | 18:00 | 1 | 0 | 2.8284 |
| De Anza Blvd / E / U | 18:00 | 7 | 5 | 1.633 |
| De Anza Blvd / S / U | 18:00 | 17 | 12 | 2.6261 |
| De Anza Blvd / N / U | 18:00 | 5 | 4 | 0.9428 |
| De Anza Blvd / W / U | 18:15 | 2 | 1 | 1.633 |
| De Anza Blvd / E / U | 18:15 | 4 | 4 | 0.0 |
| De Anza Blvd / S / U | 18:15 | 21 | 13 | 3.8806 |
| De Anza Blvd / N / U | 18:15 | 11 | 3 | 6.0474 |
| Stelling Rd / W / U | 17:30 | 7 | 5 | 1.633 |
| Stelling Rd / E / U | 17:30 | 24 | 8 | 8.0 |
| Stelling Rd / S / U | 17:30 | 1 | 1 | 0.0 |
| Stelling Rd / N / U | 17:30 | 5 | 12 | 4.802 |
| Stelling Rd / W / U | 17:45 | 13 | 6 | 4.5422 |
| Stelling Rd / E / U | 17:45 | 23 | 14 | 4.1849 |
| Stelling Rd / S / U | 17:45 | 0 | 0 | 0.0 |
| Stelling Rd / N / U | 17:45 | 13 | 15 | 1.069 |
| Stelling Rd / W / U | 18:00 | 8 | 3 | 4.264 |
| Stelling Rd / E / U | 18:00 | 29 | 11 | 8.0498 |
| Stelling Rd / S / U | 18:00 | 4 | 1 | 3.7947 |
| Stelling Rd / N / U | 18:00 | 13 | 11 | 1.1547 |
| Stelling Rd / W / U | 18:15 | 9 | 4 | 3.9223 |
| Stelling Rd / E / U | 18:15 | 25 | 9 | 7.7611 |
| Stelling Rd / S / U | 18:15 | 0 | 3 | 4.899 |
| Stelling Rd / N / U | 18:15 | 18 | 10 | 4.2762 |
