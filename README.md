# Cupertino Signal Lab

A reproducible AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. **Historical 2018 demand; not current Cupertino traffic.** Demo timing assumptions are not city signal plans.

**Status: M0–M5 implemented.** M5 fits PM only and freezes the selected plan for night. Evaluation, dashboard and video remain pending; stop at M6 for independent review.

```sh
source .venv/bin/activate
# Fresh environments: uv venv --python 3.12; uv pip install -r requirements.txt
uv pip install -e .
nice -n 15 python -m signal_lab build-net
nice -n 15 python -m signal_lab build-demand
nice -n 15 python -m signal_lab baseline
nice -n 15 python -m signal_lab check-demand
nice -n 15 python -m signal_lab bench
nice -n 15 python -m signal_lab optimize --trials 200
nice -n 15 python -m unittest discover -s tests -v
```

M2 produces both PM/night demand through SUMO routeSampler, fits only 16:30–17:30, and replays that fit hour for holdout. Routes and data are unchanged by M4. The baseline uses Webster seeds, coordinator offsets, engineering clearance inputs, force-offs and detector-based phase skips; night rests in mainline green without a conflicting call.

M4 seed 0: night inserts **439**, with **zero teleports** and **8.341 s** mean time loss. PM inserts **17,091**, with **zero teleports**, **116 running** and **792 waiting to insert** after the drain; completed-trip mean time loss is **170.622 s**. Means exclude warmup departures; unfinished trips are absent. These timing assumptions are not a successful PM calibration.

M3: **42.71% of 96 measured holdout movement-intervals have GEH < 5**, below the 85% target (corrected-route provisional M1 timing: 48.96%). Counts are physical turn-lane detector entries; quarter-hour observations are converted to hourly flows for GEH. This count check establishes neither delay improvement nor a paired Wilcoxon result. [Baseline details](reports/M4-REPORT.md) and [real corridor benchmark](reports/bench.md): **2.334 s per simulation hour**, approximately **21 minutes serial for 200 trials** including warmup/drain, excluding optimizer overhead and rescoring.

M5 completed **200 trials in 587.2 s** including baseline checks, top-five rescoring and night checks; trial 154 was selected. Across seeds 0–2, completed-trip loss falls **160.764 → 130.393 s**, but unfinished fit vehicles rise **52.33 → 284.00** and the penalized objective worsens **439.750 → 673.569**. **No overall improvement was found.** The emitted plan is the best searched candidate, not a recommendation over baseline. Both have zero PM teleports in these three seed runs.

M5 searches cycle 80–150 s, five offsets in [0, cycle), five mainline shares 0.4–0.8, and shared passage 2–4 s. Shares use the cycle minus all movement clearances; each other green reserves at least 10 s and its engineering minimum. Non-mainline green is shared equally, redistributing at input ceilings; all maxima stay at 10–60 s. Ceiling-limited schedules can leave background-cycle slack. These are nominal maxima, not delivered green shares; phase order, rest, skips and full clearances are inherited from M4.

The objective uses only requested 16:30–17:30 departures, retaining the 900 s warmup and 1800 s drain. Holdout departures are removed even during the drain; no holdout counts are read. Baseline and candidates use identical routes and matching SUMO seeds. Score = completed-trip mean timeLoss + (completed insertion delays + 6300 s × (unfinished requested vehicles + cumulative teleports)) / requested vehicles + max(0, side-origin mean timeLoss − 1.2 × same-seed baseline side loss). The per-vehicle penalty is the full simulated horizon; warmup teleports are conservatively charged too. Cohorts use scheduled departures, so late insertion cannot silently drop vehicles from the score. Side origin means the first modeled signal approach is a side street. Missing side completions receive horizon-sized side loss. Completed loss and stop counts still exclude unfinished trips; queue/unfinished/teleport counts are retained separately.

Optuna runs 200 PM trials on seed 0 via process workers and shared SQLite, then selects among the top five using mean objective on seeds 0, 1, 2. SQLite and raw XML are temporary; trial parameters and metrics are retained in CSV/JSON. Parallel scheduling can change subsequent TPE proposals even with fixed sampler seeds; the saved winning parameters and simulation seeds reproduce the selected plan. Night is scored only as an output check and never used to choose parameters. M5 numbers cover the fit hour, so compare them with the fresh M5 baseline rather than the full two-hour M4 numbers above. No holdout evaluation, Wilcoxon test, provisional-M1 comparison or real-city improvement is claimed.

Data: De Anza (Jan 10, 2018) and Stelling (Jan 17, 2018) have measured quarter-hour turns. Mary has newer Apr 25, 2018 hourly observations, preserved separately; its quarter-hour profile is estimated. Bandley and Saich are estimated. Thus **3 of 5 quarter-hour profiles are estimated**. Mary's current OSM topology lacks movements representing 775 vehicles/hour on the sheet; those observations are retained but cannot be simulated. All dates, methods and limits: [source audit](reports/data-source-audit.md), [provenance CSV](data/processed/tmc_sources.csv). The agent visually checked Stelling PDF p.554; independent human sign-off remains pending.

Outputs: [M4 baseline report](reports/M4-REPORT.md), [M2 report](reports/M2-REPORT.md), [M3 holdout report](reports/demand_check.md), [holdout rows](reports/demand_check.csv). Spec: [architecture](docs/ARCHITECTURE.md). M5 outputs: [search evidence](reports/optimize.json), [all trials](reports/optimize_trials.csv), and `reports/timing_{pm_peak,night}.csv`. The full 4.2 command intentionally stops at `eval`.

SUMO jobs run at nice 15, with at most three separate worker processes on AC (one on battery) and a two-hour child timeout; the heat guard may pause them. Follow [laptop limits](reports/bench.md) before long jobs. No dependencies were added for M4/M5. `smoke_test.py` remains unchanged.

Roads © [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). Counts: City of Cupertino / Vallco TIA (Traffic Data Service), Westport CEQAnet appendix (National Data & Surveying Services). VTA sample was audited but does not supply corridor counts.
