# M2 demand build

293 boundary-to-boundary candidate routes; routeSampler --optimize full, seed 0.
Vehicles including 900 s warmup: PM 17413; night 369.
Fit-only input SHA256: `bc4b261dd385efd19bae0db39938562636c70be2aacffd94489af9a362bf459c`.

PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.
Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.
Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; interval heavy splits are unavailable. Pedestrians are recorded but not simulated.
Simulation uses M1 generated actuated signals, not the M4 textbook coordinated-actuated baseline (not implemented in this piece).

| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |
|---|---:|---:|---:|---:|
| pm_peak | 10804 | 1249 | 6609 | 1040 |
| night | 369 | 0 | 0 | 0 |

## SUMO and routeSampler output

```
Optimization succeeded
59400: Wrote 1851 routes (32 distinct) achieving total count 3945 (97.24%) at 41 locations. GEH<5 for 95.12%
Warning: underflow locations: count 5, min 2.00 (('1113038413', '8941244#0')), max 66.00 (('1113038413', '198982494#0')), mean 22.40, Q1 6.00, median 14.00, Q3 24.00 (total 112)
Optimization succeeded
60300: Wrote 1823 routes (32 distinct) achieving total count 3859 (97.35%) at 41 locations. GEH<5 for 95.12%
Warning: underflow locations: count 5, min 3.00 (('1113038413', '8941244#0')), max 32.00 (('1113038411', '498007414#0')), mean 21.00, Q1 18.00, median 24.00, Q3 28.00 (total 105)
Optimization succeeded
61200: Wrote 1958 routes (32 distinct) achieving total count 4269 (98.75%) at 41 locations. GEH<5 for 97.56%
Warning: underflow locations: count 5, min 3.00 (('593271036#0', '593271034#0')), max 24.00 (('649530997#0', '393485270')), mean 12.40, Q1 10.00, median 11.00, Q3 14.00 (total 62)
Warning: overflow locations: count 8, min -1.00 (('-714078200#1', '593271034#0')), max -1.00 (('-714078200#1', '593271034#0')), mean -1.00, Q1 -1.00, median -1.00, Q3 -1.00 (total -8)
Optimization succeeded
62100: Wrote 2149 routes (32 distinct) achieving total count 4417 (98.05%) at 41 locations. GEH<5 for 95.12%
Warning: underflow locations: count 5, min 3.00 (('317693326#0', '5031806#0')), max 33.00 (('1113038411', '498007414#0')), mean 17.60, Q1 4.00, median 24.00, Q3 24.00 (total 88)
avg interval input count: count 4, min 3964.00 (60300.0), max 4505.00 (62100.0), mean 4212.25, Q1 4057.00, median 4323.00, Q3 4505.00
avg interval written vehs: count 4, min 1823.00 (60300.0), max 2149.00 (62100.0), mean 1945.25, Q1 1851.00, median 1958.00, Q3 2149.00
avg interval underflow: count 4, min 62.00 (61200.0), max 112.00 (59400.0), mean 91.75, Q1 88.00, median 105.00, Q3 112.00
avg interval overflow: count 4, min -8.00 (61200.0), max 0.00 (59400.0), mean -2.00, Q1 0.00, median 0.00, Q3 0.00
avg interval GEH%: count 4, min 95.12 (59400.0), max 97.56 (61200.0), mean 95.73, Q1 95.12, median 95.12, Q3 97.56

Optimization succeeded
Wrote 300 routes (23 distinct) achieving total count 1038 (88.12%) at 41 locations. GEH<5 for 92.68%
Warning: underflow locations: count 8, min 1.00 (('409235722', '506497762#0')), max 45.00 (('317693325#0', '157747965#0')), mean 17.50, Q1 7.00, median 12.00, Q3 35.00 (total 140)

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/detectors.add.xml' ... done (0ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 58500.00.
Simulation ended at time: 68400.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 22.66s
 Real time factor: 436.893
 UPS: 453354.986761
Vehicles:
 Inserted: 10804 (Loaded: 17413)
 Running: 1249
 Waiting: 6609
 Teleports: 1040 (Jam: 559, Yield: 337, Wrong Lane: 144)
Statistics (avg of 9555):
 RouteLength: 655.96
 Speed: 4.99
 Duration: 415.96
 WaitingTime: 330.87
 TimeLoss: 370.60
 DepartDelay: 679.86

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/corridor.net.xml' ... done (7ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/detectors.add.xml' ... done (0ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/routes_night.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 81900.00.
Simulation ended at time: 88200.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.12s
 Real time factor: 54310.3
 UPS: 408974.137931
Vehicles:
 Inserted: 369
 Running: 0
 Waiting: 0
Statistics (avg of 369):
 RouteLength: 1307.70
 Speed: 10.52
 Duration: 128.57
 WaitingTime: 24.16
 TimeLoss: 42.90
 DepartDelay: 0.49

```
