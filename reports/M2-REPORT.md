# M2 demand build

197 boundary-to-boundary candidate routes; symmetric nonnegative count fit, seed 0 rounding.
Vehicles including 900 s warmup: PM 17621; night 460.
Fit-only input SHA256: `2ae7dd962d45bb0cb4b44391c2ba541e995e27815a500c87c7abd744195bc24b`.

PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.
Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.
Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; quarter-hour per-movement heavy splits are unavailable. Pedestrians are recorded but not simulated.
Simulation uses the retained textbook coordinated-actuated baseline files; timing is unchanged by this demand rebuild.

| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |
|---|---:|---:|---:|---:|
| pm_peak | 16173 | 144 | 1448 | 0 |
| night | 460 | 0 | 0 | 0 |

## SUMO and routeSampler output

```
59400: symmetric count fit; 1887 vehicles; GEH<5 42/49
60300: symmetric count fit; 1934 vehicles; GEH<5 44/49
61200: symmetric count fit; 1966 vehicles; GEH<5 44/49
62100: symmetric count fit; 2080 vehicles; GEH<5 44/49
82800: symmetric count fit; 378 vehicles; GEH<5 49/49
Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/tls_actuated_pm_peak.add.xml' ... done (13ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 58500.00.
Simulation ended at time: 68400.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 8.05s
 Real time factor: 1230.43
 UPS: 465909.644544
Vehicles:
 Inserted: 16173 (Loaded: 17621)
 Running: 144
 Waiting: 1448
 Emergency Braking: 1
Statistics (avg of 16029):
 RouteLength: 843.42
 Speed: 5.72
 Duration: 232.67
 WaitingTime: 110.63
 TimeLoss: 178.81
 DepartDelay: 505.96

Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/corridor.net.xml' ... done (6ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/tls_actuated_night.add.xml' ... done (13ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon-vta2024/sim/routes_night.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 81900.00.
Simulation ended at time: 88200.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.14s
 Real time factor: 46323.5
 UPS: 276007.352941
Vehicles:
 Inserted: 460
 Running: 0
 Waiting: 0
Statistics (avg of 460):
 RouteLength: 1095.83
 Speed: 13.41
 Duration: 81.60
 WaitingTime: 2.38
 TimeLoss: 9.54
 DepartDelay: 0.39

```
