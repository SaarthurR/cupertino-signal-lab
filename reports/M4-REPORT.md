# M4 baseline

textbook coordinated-actuated baseline (not Cupertino's current timing)

Webster unified-cycle seed uses the first scenario hour; greens are bounded by timing_inputs.csv min/max (60 s ceiling from section 6.4; longer Webster greens are clipped). Yellow/red clearances use the same inputs. The common background cycle is the longest resulting nominal plan including full clearances (Webster seed adjusted to engineering bounds). Forward phase skips have full yellow/all-red clearances; mainline self-successor rests without changing color. Offsets come from tlsCoordinator on the linear nominal schedules, excluding alternative transition branches. SUMO supplies built-in loop actuation with a 0.5 s detector gap: default upstream loops miss vehicles spawned on short boundary lanes; stop-bar loops at 1 m miss cars stopped at red.

Reference: https://sumo.dlr.de/docs/Simulation/Traffic_Lights.html#dynamic_phase_selection_phase_skipping

## Scenario runs (seed 0)

Time loss averages completed trips departing within the scenario, excludes warmup departures, and includes a 30-minute drain. Inserted/teleports include warmup and drain; unfinished trips are absent from the mean.

| Scenario | Inserted | Teleports | Running after drain | Waiting to insert | Mean time loss (s) | Completed after warmup |
|---|---:|---:|---:|---:|---:|---:|
| pm_peak | 17091 | 0 | 116 | 792 | 170.622 | 14000 |
| night | 439 | 0 | 0 | 0 | 8.341 | 353 |

## Tool output
```
Begin time:59400.0
Duration for Phase 2 is from the input file.
Duration for Phase 5 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 7 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 9 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 9 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 7 is from the input file.

number of tls-pairs: 17
operations: newSet=2 addToSet=1 addToSet2=0 addHalfCoordinated=13 mergeSets=1

Warning: The period is less than 1 hour. The flows will be proportionally scaled up to 1-hour flow with the scaling factor 1.000444444444446.
Begin time:82800.0
Duration for Phase 2 is from the input file.
Duration for Phase 5 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 7 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 9 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 9 is from the input file.
Duration for Phase 4 is from the input file.
Duration for Phase 7 is from the input file.

number of tls-pairs: 15
operations: newSet=2 addToSet=1 addToSet2=0 addHalfCoordinated=11 mergeSets=1

```
