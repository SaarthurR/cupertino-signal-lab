# M0 benchmark

One simulation hour: 0.156 wall seconds.

Initial scaffold: synthetic 3×3 actuated grid, not the corridor. Re-run after M4 for the actual optimization budget.

```
Loading net-file from '/var/folders/mh/rxxgmkc57z3_qlk1_zdn70rc0000gn/T/tmps217b8w8/bench.net.xml' ... done (1ms).
Loading route-files incrementally from '/var/folders/mh/rxxgmkc57z3_qlk1_zdn70rc0000gn/T/tmps217b8w8/bench.rou.xml'
Loading done.
Simulation version 1.28.0 started with time: 0.00.
Simulation ended at time: 3600.00.
Reason: The final simulation step has been reached.
Performance:
 Duration: 0.09s
 Real time factor: 41860.5
 UPS: 985046.511628
Vehicles:
 Inserted: 1800
 Running: 23
 Waiting: 0
Statistics (avg of 1777):
 RouteLength: 352.02
 Speed: 8.52
 Duration: 47.33
 WaitingTime: 8.04
 TimeLoss: 19.97
 DepartDelay: 0.77

```

## Laptop limits (Oct 28)

- All future SUMO / Optuna / eval / video jobs: `nice -n 15` (the shared child launcher enforces this).
- At most 3 simultaneous simulations; current pipeline is serial (one).
- No job over 2 hours; child commands time out at 7200 seconds. Split longer work.
- Before any expected run over 10 minutes: `pmset -g batt`; use one worker on battery. Current reading: battery, 74%. No run exceeding ten minutes has been started.
- `reports/` plus `sim/` must remain under 2 GB. Delete large FCD/tripinfo XML after extracting results.
- Close `sumo-gui` after every video. No GUI has been opened.

The initial benchmark ran before these new rules were supplied. Later simulations run at nice 15. A 200-trial corridor estimate is unavailable: measured demand is blocked at M2. Do not extrapolate the synthetic-grid result to corridor optimization. The CLI reserves `optimize --trials 200` for the full count; optimization itself is not implemented because later steps depend on M2.

## Round 2 data-only run (M2/M3)

M2 now uses disclosed 2018 historical counts; the source blocker is resolved through the authorized fallback and newer Mary hourly sheet. No optimization budget has been inferred from the scaffold bench. M4 and the representative corridor baseline benchmark remain pending by explicit scope.

All Round 2 SUMO/routeSampler/test parent processes run at nice 15; simulation children use the shared nice launcher (some inherit an even lower priority). Serial production simulations, at most two during the test/validation overlap; below the three-simulation cap. No job expected to exceed ten minutes was started; battery check at handoff: AC, 83%, charging. Heat guard left untouched. Reports + sim approximately 4.6 MB, below 2 GB. Summary/detector XML is temporary and removed after extracting counts. No FCD/tripinfo, GUI, Optuna, evaluation, or video job started.

`nice -n 15 .venv/bin/python -m unittest discover -s tests -v`: 21 tests passed in 35.375 s, including live PM/night simulations and the independent sparse turn-detector check. This is test-suite wall time, **not** a baseline performance benchmark.

After normalizing CSV line endings, the 14 data-focused tests also passed (26.134 s). Final scoped `build-net && build-demand && check-demand` rerun passed with the same figures. No M4 verb was run.
