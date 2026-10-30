# M2 demand build

197 boundary-to-boundary candidate routes; routeSampler --optimize full, seed 0.
Vehicles including 900 s warmup: PM 17516; night 429.
Fit-only input SHA256: `2ae7dd962d45bb0cb4b44391c2ba541e995e27815a500c87c7abd744195bc24b`.

PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.
Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.
Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; quarter-hour per-movement heavy splits are unavailable. Pedestrians are recorded but not simulated.
Simulation uses the retained textbook coordinated-actuated baseline files; timing is unchanged by this demand rebuild.

| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |
|---|---:|---:|---:|---:|
| pm_peak | 9228 | 1006 | 8288 | 772 |
| night | 429 | 0 | 0 | 0 |

## SUMO and routeSampler output

```
Optimization succeeded
59400: Wrote 1866 routes (35 distinct) achieving total count 3452 (88.29%) at 49 locations. GEH<5 for 79.59%
Warning: underflow locations: count 13, min 3.00 (('317693325#0', '498007414#0')), max 90.00 (('317693325#0', '157747965#0')), mean 35.23, Q1 9.00, median 40.00, Q3 52.00 (total 458)
Optimization succeeded
60300: Wrote 1934 routes (36 distinct) achieving total count 3493 (90.21%) at 49 locations. GEH<5 for 85.71%
Warning: underflow locations: count 12, min 1.00 (('317693325#0', '498007414#0')), max 83.00 (('317693325#0', '157747965#0')), mean 31.58, Q1 5.00, median 36.00, Q3 48.00 (total 379)
Optimization succeeded
61200: Wrote 1947 routes (36 distinct) achieving total count 3679 (89.45%) at 49 locations. GEH<5 for 79.59%
Warning: underflow locations: count 13, min 1.00 (('317693325#0', '498007414#0')), max 102.00 (('317693325#0', '157747965#0')), mean 33.38, Q1 5.00, median 31.00, Q3 48.00 (total 434)
Optimization succeeded
62100: Wrote 2078 routes (36 distinct) achieving total count 3790 (89.07%) at 49 locations. GEH<5 for 81.63%
Warning: underflow locations: count 13, min 2.00 (('317693325#0', '498007414#0')), max 80.00 (('317693325#0', '157747965#0')), mean 35.77, Q1 5.00, median 32.00, Q3 55.00 (total 465)
avg interval input count: count 4, min 3872.00 (60300.0), max 4255.00 (62100.0), mean 4037.50, Q1 3910.00, median 4113.00, Q3 4255.00
avg interval written vehs: count 4, min 1866.00 (59400.0), max 2078.00 (62100.0), mean 1956.25, Q1 1934.00, median 1947.00, Q3 2078.00
avg interval underflow: count 4, min 379.00 (60300.0), max 465.00 (62100.0), mean 434.00, Q1 434.00, median 458.00, Q3 465.00
avg interval overflow: count 4, min 0.00 (59400.0), max 0.00 (59400.0), mean 0.00, Q1 0.00, median 0.00, Q3 0.00
avg interval GEH%: count 4, min 79.59 (59400.0), max 85.71 (60300.0), mean 81.63, Q1 79.59, median 81.63, Q3 85.71

Optimization succeeded
Wrote 342 routes (34 distinct) achieving total count 997 (88.46%) at 49 locations. GEH<5 for 93.88%
Warning: underflow locations: count 13, min 1.00 (('317693326#0', '5031806#0')), max 36.00 (('317693325#0', '157747965#0')), mean 10.00, Q1 2.00, median 5.00, Q3 19.00 (total 130)

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/corridor.net.xml' ... done (8ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/tls_actuated_pm_peak.add.xml' ... done (14ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 58500.00.
Simulation ended at time: 68400.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 21.53s
 Real time factor: 459.845
 UPS: 379524.362488
Vehicles:
 Inserted: 9228 (Loaded: 17516)
 Running: 1006
 Waiting: 8288
 Teleports: 772 (Jam: 193, Yield: 579)
 Emergency Braking: 1
Statistics (avg of 8222):
 RouteLength: 741.83
 Speed: 7.38
 Duration: 430.57
 WaitingTime: 333.42
 TimeLoss: 376.76
 DepartDelay: 35.50

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/tls_actuated_night.add.xml' ... done (14ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/routes_night.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 81900.00.
Simulation ended at time: 88200.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.14s
 Real time factor: 45652.2
 UPS: 250384.057971
Vehicles:
 Inserted: 429
 Running: 0
 Waiting: 0
Statistics (avg of 429):
 RouteLength: 1078.96
 Speed: 13.49
 Duration: 80.54
 WaitingTime: 2.58
 TimeLoss: 9.64
 DepartDelay: 0.49

```
