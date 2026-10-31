# Signal Advisor closed-loop preregistration

Registered before any piece-3 simulation or test run. Synthetic counts only.

- Scenarios: `calm`, `east_surge`, and temporary `drop` exactly as in
  `feed.scenario_routes`; lasting `all_drop` exactly as in
  `tools/drift_check.py` (25% fewer requests throughout, including warmup).
- Arms: fixed v5 PM versus closed-loop advisor, paired by seed and demand.
  Both start from v5 PM. Test seeds 103–122 inclusive, never used before.
  First run sanity and development checks on seeds 0–4 only.
- Primary: `evaluate.metrics` full scheduled PM cohort (16:30–18:30)
  `all_requested_delay_s`, with the existing 900-second unfinished/teleport
  charges, existing warmup and 1800-second drain. No completed-only headline.
- Test: one-sided paired Wilcoxon (advisor minus fixed, alternative less,
  zero_method wilcox, method auto); all-zero differences give p=1.
  Holm correction across the four scenario p-values; alpha .05.
- Secondary, descriptive: unfinished requests, teleport events, completed
  EB and WB corridor travel, side all-requested delay, worst origin-group
  all-requested delay, recommendations and switches, and false switches
  (every switch on calm). Report paired arm means and changes.
- Read 300-second detector windows from running TraCI. Call the unchanged
  advisor rule on trailing 15 minutes. Simulated approval takes 300 seconds.
  Track actual approved plan and last actual switch separately from advisory
  state; no switch before approval, and at least 900 seconds between switches.
- Load only the existing library plus `sim/tls_advisor_light.add.xml`.
  Fit its all_drop profile using v5 detector feeds from seeds 0–4 only,
  using the existing profile/range/margin fitting procedure. No new thresholds,
  candidate search, retuning, or rule changes after inspecting test seeds.
- Switch all five signals to the approved program at one simulation time.
  Retain each program's configured offset and coordinated actuated settings,
  but explicitly restart at phase zero with its nominal duration. Log
  before/after phases and remaining durations. This loses phase continuity
  and does not promise immediate offset coordination. Abrupt transitions
  can truncate greens or clearance intervals;
  this simulator operation is not a deployable field-controller transition.
  All consequences remain in trip metrics. No real signals or network touched.
- Sanity gates: one short real run compares TraCI counts and occupancy against
  piece-1 XML extraction, allowing only XML decimal-rounding error; full fixed
  v5 TraCI metrics must equal existing simulate on the same fit seed. Stop on
  failure. Unit checks cover phase/offset selection and approval delay.
- Amendment before any test seed ran: the first sanity run failed because TraCI's
  interval occupancy leaves out vehicles still on a loop, and SUMO buffers the
  detector file so it cannot be read live. Live occupancy is now the per-step mean.
  It only approximates the file measure that the profiles use, so the occupancy gate
  is now at most 3 percentage points per approach and at most 1 on average. The count
  gate stays exact. This is a known limit of the test, and the advisor rule is unchanged.
- Run the final cohort once, no reruns to improve findings. Preserve frozen
  plans and old results. Save per-run logs, results_advisor.csv and
  eval_advisor.json with provenance. Null or harmful results stand.
