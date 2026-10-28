# M4 corridor benchmark

One simulation hour: 2.334 wall seconds.

textbook coordinated-actuated baseline (not Cupertino's current timing). Actual corridor, unchanged PM routes, seed 0, headless SUMO 1.28.0, 16:30–17:30 (exactly 3600 simulated seconds; no warmup or drain). Wall time includes process startup. This replaces the synthetic-grid M0 number.

200 Optuna trials: approximately 1283.9 seconds (21.40 minutes) serial for 2 h demand + 900 s warmup + 1800 s drain per trial, extrapolated at 2.334 s/sim-hour. Ideal three-process lower bound 428.0 seconds; concurrent scaling is unmeasured. Excludes Optuna/SQLite/Python objective overhead, top-five rescoring and eval; queue-heavy candidate plans may run slower. No optimization has been run.

## Laptop limits

- Every SUMO / Optuna / eval / video child: `nice -n 15`, enforced by the shared launcher.
- At most 3 simultaneous simulations; this benchmark and production validation are serial (one).
- No job over two hours; child timeout 7200 s. Split longer work.
- Before an expected run over ten minutes: `pmset -g batt`; one worker on battery. No such run started here.
- Keep reports + sim below 2 GB; remove large XML after extracting aggregates.
- Close sumo-gui after video. No GUI opened; heat guard untouched.

```text
Loading net-file from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/corridor.net.xml' ... done (5ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/detectors.add.xml' ... done (1ms).
Loading additional-files from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/tls_actuated_pm_peak.add.xml' ... done (14ms).
Loading route-files incrementally from '/Users/saarthranka/Documents/school/ai-club-hackathon/sim/routes_pm_peak.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 59400.00.
Simulation ended at time: 63000.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 2.25s
 Real time factor: 1597.16
 UPS: 620928.127773
Vehicles:
 Inserted: 7195 (Loaded: 7993)
 Running: 511
 Waiting: 783
 Emergency Braking: 1
Statistics (avg of 6684):
 RouteLength: 807.92
 Speed: 6.41
 Duration: 196.08
 WaitingTime: 84.98
 TimeLoss: 144.22
 DepartDelay: 78.25
```
