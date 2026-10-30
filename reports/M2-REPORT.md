# M2 demand build

98 boundary-to-boundary candidate routes; routeSampler --optimize full, seed 0.
Vehicles including 900 s warmup: PM 16962; night 415.
Fit-only input SHA256: `e5a32a4257976cab394c806290b7c7f5136b7fa30f9b12ef5af523c385d161c7`.

PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.
Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.
Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; quarter-hour per-movement heavy splits are unavailable. Pedestrians are recorded but not simulated.
Simulation uses the retained textbook coordinated-actuated baseline files; timing is unchanged by this demand rebuild.

| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |
|---|---:|---:|---:|---:|
| pm_peak | 16315 | 105 | 647 | 0 |
| night | 415 | 0 | 0 | 0 |

## SUMO and routeSampler output

```
Optimization succeeded
59400: Wrote 1808 routes (29 distinct) achieving total count 3396 (88.35%) at 41 locations. GEH<5 for 75.61%
Warning: underflow locations: count 12, min 5.00 (('317693326#0', '-1528009844#2')), max 110.00 (('317693325#0', '506499370#0')), mean 37.33, Q1 13.00, median 40.00, Q3 57.00 (total 448)
Optimization succeeded
60300: Wrote 1882 routes (30 distinct) achieving total count 3449 (90.43%) at 41 locations. GEH<5 for 80.49%
Warning: underflow locations: count 11, min 2.00 (('-714078200#1', '317693329#0')), max 76.00 (('317693325#0', '506499370#0')), mean 33.18, Q1 5.00, median 35.00, Q3 55.00 (total 365)
Optimization succeeded
61200: Wrote 1885 routes (29 distinct) achieving total count 3631 (89.70%) at 41 locations. GEH<5 for 78.05%
Warning: underflow locations: count 12, min 4.00 (('593271036#0', '593271034#0')), max 127.00 (('317693325#0', '506499370#0')), mean 34.75, Q1 11.00, median 33.00, Q3 46.00 (total 417)
Optimization succeeded
62100: Wrote 2002 routes (29 distinct) achieving total count 3724 (89.26%) at 41 locations. GEH<5 for 78.05%
Warning: underflow locations: count 12, min 5.00 (('317693326#0', '-1528009844#2')), max 93.00 (('317693325#0', '506499370#0')), mean 37.33, Q1 17.00, median 41.00, Q3 56.00 (total 448)
avg interval input count: count 4, min 3814.00 (60300.0), max 4172.00 (62100.0), mean 3969.50, Q1 3844.00, median 4048.00, Q3 4172.00
avg interval written vehs: count 4, min 1808.00 (59400.0), max 2002.00 (62100.0), mean 1894.25, Q1 1882.00, median 1885.00, Q3 2002.00
avg interval underflow: count 4, min 365.00 (60300.0), max 448.00 (59400.0), mean 419.50, Q1 417.00, median 448.00, Q3 448.00
avg interval overflow: count 4, min 0.00 (59400.0), max 0.00 (59400.0), mean 0.00, Q1 0.00, median 0.00, Q3 0.00
avg interval GEH%: count 4, min 75.61 (59400.0), max 80.49 (60300.0), mean 78.05, Q1 78.05, median 78.05, Q3 80.49

Optimization succeeded
Wrote 333 routes (29 distinct) achieving total count 980 (88.53%) at 41 locations. GEH<5 for 92.68%
Warning: underflow locations: count 12, min 1.00 (('317693326#0', '5031806#0')), max 40.00 (('317693325#0', '506499370#0')), mean 10.58, Q1 2.00, median 11.00, Q3 15.00 (total 127)

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/tls_actuated_pm_peak.add.xml' ... done (13ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 58500.00.
Simulation ended at time: 68400.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 5.65s
 Real time factor: 1751.9
 UPS: 488293.930278
Vehicles:
 Inserted: 16315 (Loaded: 16962)
 Running: 105
 Waiting: 647
 Emergency Braking: 3
Statistics (avg of 16210):
 RouteLength: 812.17
 Speed: 6.73
 Duration: 169.18
 WaitingTime: 72.87
 TimeLoss: 117.25
 DepartDelay: 347.52

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/detectors.add.xml' ... done (0ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/tls_actuated_night.add.xml' ... done (17ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-counts/sim/routes_night.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 81900.00.
Simulation ended at time: 88200.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.13s
 Real time factor: 48461.5
 UPS: 257861.538462
Vehicles:
 Inserted: 415
 Running: 0
 Waiting: 0
Statistics (avg of 415):
 RouteLength: 1102.99
 Speed: 13.76
 Duration: 80.78
 WaitingTime: 1.73
 TimeLoss: 8.37
 DepartDelay: 0.49

```
