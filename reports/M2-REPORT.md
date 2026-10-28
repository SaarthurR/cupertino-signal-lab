# M2 demand build

98 boundary-to-boundary candidate routes; routeSampler --optimize full, seed 0.
Vehicles including 900 s warmup: PM 17883; night 439.
Fit-only input SHA256: `bc4b261dd385efd19bae0db39938562636c70be2aacffd94489af9a362bf459c`.

PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.
Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.
Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; interval heavy splits are unavailable. Pedestrians are recorded but not simulated.
Simulation uses M1 generated actuated signals, not the M4 textbook coordinated-actuated baseline (not implemented in this piece).

| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |
|---|---:|---:|---:|---:|
| pm_peak | 17883 | 0 | 0 | 0 |
| night | 439 | 0 | 0 | 0 |

## SUMO and routeSampler output

```
Optimization succeeded
59400: Wrote 1923 routes (30 distinct) achieving total count 3656 (90.12%) at 41 locations. GEH<5 for 82.93%
Warning: underflow locations: count 11, min 2.00 (('1528009844#0', '506497762#0')), max 89.00 (('317693325#0', '506499370#0')), mean 36.45, Q1 13.00, median 17.00, Q3 63.00 (total 401)
Optimization succeeded
60300: Wrote 1886 routes (29 distinct) achieving total count 3505 (88.42%) at 41 locations. GEH<5 for 80.49%
Warning: underflow locations: count 12, min 1.00 (('593271036#0', '593271034#0')), max 91.00 (('317693332#0', '8963319#0')), mean 38.25, Q1 8.00, median 37.00, Q3 81.00 (total 459)
Optimization succeeded
61200: Wrote 1992 routes (30 distinct) achieving total count 3901 (90.24%) at 41 locations. GEH<5 for 82.93%
Warning: underflow locations: count 11, min 3.00 (('317693326#0', '5031806#0')), max 107.00 (('317693325#0', '506499370#0')), mean 38.36, Q1 5.00, median 35.00, Q3 68.00 (total 422)
Optimization succeeded
62100: Wrote 2179 routes (29 distinct) achieving total count 4006 (88.92%) at 41 locations. GEH<5 for 80.49%
Warning: underflow locations: count 12, min 2.00 (('317693331#0', '317693329#0')), max 108.00 (('317693332#0', '8963319#0')), mean 41.58, Q1 5.00, median 29.00, Q3 104.00 (total 499)
avg interval input count: count 4, min 3964.00 (60300.0), max 4505.00 (62100.0), mean 4212.25, Q1 4057.00, median 4323.00, Q3 4505.00
avg interval written vehs: count 4, min 1886.00 (60300.0), max 2179.00 (62100.0), mean 1995.00, Q1 1923.00, median 1992.00, Q3 2179.00
avg interval underflow: count 4, min 401.00 (59400.0), max 499.00 (62100.0), mean 445.25, Q1 422.00, median 459.00, Q3 499.00
avg interval overflow: count 4, min 0.00 (59400.0), max 0.00 (59400.0), mean 0.00, Q1 0.00, median 0.00, Q3 0.00
avg interval GEH%: count 4, min 80.49 (60300.0), max 82.93 (59400.0), mean 81.71, Q1 80.49, median 82.93, Q3 82.93

Optimization succeeded
Wrote 353 routes (29 distinct) achieving total count 1061 (90.07%) at 41 locations. GEH<5 for 95.12%
Warning: underflow locations: count 9, min 1.00 (('317693323#0', '498007414#0')), max 38.00 (('317693325#0', '506499370#0')), mean 13.00, Q1 2.00, median 8.00, Q3 18.00 (total 117)

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/corridor.net.xml' ... done (8ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/detectors.add.xml' ... done (1ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 58500.00.
Simulation ended at time: 68400.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 3.31s
 Real time factor: 2988.23
 UPS: 626191.971023
Vehicles:
 Inserted: 17883
 Running: 0
 Waiting: 0
Statistics (avg of 17883):
 RouteLength: 797.59
 Speed: 7.97
 Duration: 116.01
 WaitingTime: 44.75
 TimeLoss: 65.03
 DepartDelay: 0.79

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/detectors.add.xml' ... done (1ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/routes_night.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 81900.00.
Simulation ended at time: 88200.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.12s
 Real time factor: 53846.2
 UPS: 411076.923077
Vehicles:
 Inserted: 439
 Running: 0
 Waiting: 0
Statistics (avg of 439):
 RouteLength: 1108.78
 Speed: 10.52
 Duration: 109.56
 WaitingTime: 20.74
 TimeLoss: 36.94
 DepartDelay: 0.51

```
