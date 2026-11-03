# Fresh synthetic checks — 2026-11-02

**Run completed; validation did not pass. No new timing recommendation or field benefit was demonstrated.** Scientific source was frozen at commit `52e7809`. Inputs and source were hashed before observation and rechecked before finalization. This was a local freeze, not public or independently registered preregistration. Source thresholds were not tuned after these outcomes.

## What happened

- **Bubb:** preparation failed on an internal campus-loop turn with no boundary-to-boundary route. This road was retained as an unsupported-geometry failure, not counted as a successful test.
- **Stelling:** ten different synthetic observation profiles produced 100% GEH-under-5 count comparisons, but occupancy mean absolute error was 30.004 points and maximum unresolved turn-share width was 1.0. The limits were 10 points and 0.2. Both TPE and random search abstained, each spending **0 of its 150-trial budget**. There is no empirical optimizer comparison.
- **Rollback:** zero triggers in 30 designated degraded-plan runs and zero in 30 harmless-plan controls, across three fixed profiles. The degraded plan actually worsened the paired held-plan score in 18 runs; **all 18 were missed**. All three profiles failed the fixed rollback criteria. No trigger latency exists; it must not be reported as zero. The rule is experimental and is not a safety mechanism.

The deliberately degraded plan was not worse in every run, so its design label is not treated as proof of harm. The harmful subset above compares its held-plan score against the paired harmless held plan. These are descriptive simulated results, not independent field observations or a calibrated detection rate.

## Fixed-profile delay scores

Each row averages the same ten paired driver seeds. The score adds 900 seconds per unfinished trip and divides by all requested trips; it is not a travel-time measurement. Both abstaining strategies select old timing, so their exact old-plan evaluations are reused.

| Synthetic profile | Old / selected TPE / selected random | Fresh textbook timing | Harmful degraded-plan runs missed |
|---|---:|---:|---:|
| 6000 | 1285.43 | 1229.03 | 7 / 7 |
| 6001 | 1317.13 | 1267.28 | 4 / 4 |
| 6002 | 1183.77 | 1226.99 | 7 / 7 |

Fresh textbook timing has access to the true synthetic demand. It is a descriptive comparator, not an equal-information learner. Per-seed differences, origin groups, penalties 0/900/1800, unfinished trips and teleports are retained in `results.json` and the archive. No benefit is inferred from unrun optimization. More varied observation profiles did not establish a reliable rollback rule.

## Evidence and replay

`protocol.json` records intended/prepared roads, preparation failures, seeds, thresholds and hashes. `results.json` and `validation_stelling.json` expose results without unpacking. `evidence.json` records the archive checksum; all 36 frozen input hashes were checked against its members. `evidence.tar.gz` contains all 150 generated run files, including prepared road/world inputs, observation feeds, copy evidence, both strategy outputs and raw evaluation/rollback metrics. Geometry derives from OpenStreetMap contributors; the original network inputs are preserved by hash.

For inspection, extract the archive into a **separate empty directory** with `tar -xzf evidence.tar.gz -C <empty-directory>`. For source inspection use commit `52e7809` and its pinned Python 3.12 requirements. The runner intentionally refuses to overwrite or repeat existing inputs/outputs. Do not retune on these profiles and then call a rerun independent validation.

An earlier preparation attempt stopped on Bubb before any learner observations or results. Its original protocol and failure are retained in `initial_preparation_failure/`. The completed run changed preparation handling to record the geometry error and continue to Stelling. Both intended geometries are disclosed; none was dropped after a performance outcome.

After the frozen run, card text was corrected to warn that rollback can miss harmful changes or undo harmless ones. This changed presentation wording, not the selection or monitoring policy. Historical study artifacts were not overwritten or rerun. The new results do not revalidate the old Wolfe benefit.

Still required: usable contemporary inputs, actual city timing, independent queue/travel-time validation, engineer review and controller/safety validation before any operational claim. Human presentation rehearsal remains a team task.
