# Signal Advisor (piece 2)

This is advice from simulated counts. It does not approve or apply timing changes.
No real controller or network connection is used. Closed-loop testing belongs to piece 3.

```
PYTHONPATH=src .venv/bin/python -m signal_lab advise --feed reports/feed/calm_seed0/feed.csv
```

The CSV interface is in [FEED.md](FEED.md). Column order may vary. Counts must be
nonnegative integers, occupancy must be finite and between 0 and 100, and `ok`
must be 0 or 1. Timestamps need an explicit timezone. Duplicate approach/windows,
missing columns, invalid values and empty files are errors. Rows may arrive in any
order in an offline file; replay sorts them. No simulator-specific columns are read.

The CLI prints recommendations and writes every window's decision/refusal to
`<feed-stem>.advisor.jsonl` beside the CSV. Replay uses the recorded window clock,
so the synthetic date does not make a historical replay stale. The pure
`recommend(rows, state, now, calibration)` function takes an explicit aware clock;
a live consumer must pass its actual clock. A latest window older than five
minutes, or in the future, is refused. Missing windows cannot build the required
three-window signal. The first two windows are warmup, not recommendations.

`advisor.py` uses only the Python standard library. `read_feed` validates the CSV;
`smooth` averages three good rows per approach (count per five minutes and occupancy
percent). Suspect rows never contribute. Missing approaches count as bad rows.
More than 25% bad/missing rows in any of the three windows refuses advice. At or
below that limit, only approaches with three good measurements are compared.
An unrecognized approach is refused because it has no calibrated profile.

`advisor_profiles.json` holds all fitted numbers in one place. For each approach,
the count and occupancy distance is scaled by its observed training range.
The closest profile wins only when its distance advantage exceeds every adverse
advantage seen in the source profile's training windows. Equality holds steady.
This margin is a fit-data envelope, not a probability or statistical confidence.
Two consecutive five-minute decisions must agree, and at least 15 minutes must
pass after the previous recommendation. A quality refusal or a gap resets the
streak. Reasons name the two largest approach departures and their measured and
reference numbers. Distance, margin, threshold and bad-row fraction are logged
because the rule uses them.

`State.plan` and `last_change` track the last recommendation for offline replay.
They do not imply approval or an actual signal switch. A future approval consumer
must supply the approved plan and actual switch time in that state. No approval
delay or switching disruption is simulated here.

The library contains frozen textbook PM (`tls_actuated_pm_peak.add.xml`), v5 PM,
and v5 night. Textbook and v5 PM were tuned for the same PM demand. They share a
profile; a demand-only rule cannot choose between them, so ties keep v5/current.
Night has its separately estimated demand profile. A 30% drop is detectable but
is not assumed to be night demand. East surge is a diagnostic profile even if its
candidate plan fails validation; in that case it logs "no validated plan".
South surge has no repeatable separation during the change and is excluded.

Reproduction (run in this order, at most three SUMO processes total):

1. Generate each of the five feed scenarios with seeds 0–4 using the feed CLI.
2. Run `.venv/bin/python tools/advisor_separation.py` for the paired seeds 1–4 table.
3. Run `caffeinate -i nice -n 15 env PYTHONPATH=src .venv/bin/python tools/advisor_surge.py`.
   This runs 20 trials, seeds 0–4, on derived east-surge routes. It selects one
   candidate before seeds 5–12 and keeps it only if it lowers requested-vehicle
   delay and passes the optimizer's existing constraints on those same routes.
4. After that finishes, run `caffeinate -i nice -n 15 env PYTHONPATH=src .venv/bin/python tools/advisor_profiles.py`.
   This generates v5 night feeds on seeds 0–4 and freezes profiles and margins.

Surge scoring uses the original optimizer's 16:30–17:30 requested cohort, plus
warmup/drain, on the changed routes for both candidate and v5. It does not measure
an applied switch or establish benefits later in the evening. Calibration uses
full calm PM, full night, and 17:15–17:30 east-surge windows, all seeds 0–4 only.
These are fit-data checks, not independent advisor evaluation. The seed-0
fixtures preserve full real SUMO feeds for reproducible replay tests.

See [separation](../reports/advisor_separation.md) and
[surge search](../reports/advisor_surge.json) for outcomes. Neither a nearest
profile nor an open-loop plan gain proves closed-loop benefit.
