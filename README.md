# Cupertino Signal Lab

A reproducible AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. **Historical 2018 demand; not current Cupertino traffic.** Demo timing assumptions are not city signal plans.

**Status: M0–M6 implemented.** M5 fits PM only and freezes the selected plan for night. M6 evaluates the frozen plans; offline dashboard and video are available below.

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
nice -n 15 python -m signal_lab eval
nice -n 15 python -m unittest discover -s tests -v
```

M2 produces both PM/night demand through SUMO routeSampler, fits only 16:30–17:30, and replays that fit hour for holdout. Routes and data are unchanged by M4. The baseline uses Webster seeds, coordinator offsets, engineering clearance inputs, force-offs and detector-based phase skips; night rests in mainline green without a conflicting call.

M4 seed 0: night inserts **439**, with **zero teleports** and **8.341 s** mean time loss. PM inserts **17,091**, with **zero teleports**, **116 running** and **792 waiting to insert** after the drain; completed-trip mean time loss is **170.622 s**. Means exclude warmup departures; unfinished trips are absent. These timing assumptions are not a successful PM calibration.

M3: **42.71% of 96 measured holdout movement-intervals have GEH < 5**, below the 85% target (corrected-route provisional M1 timing: 48.96%). Counts are physical turn-lane detector entries; quarter-hour observations are converted to hourly flows for GEH. This count check establishes neither delay improvement nor a paired Wilcoxon result. [Baseline details](reports/M4-REPORT.md) and [real corridor benchmark](reports/bench.md): **2.334 s per simulation hour**, approximately **21 minutes serial for 200 trials** including warmup/drain, excluding optimizer overhead and rescoring.

M5 completed 200 trials; the corrected scorer selected **trial 146**, as recorded in [search evidence](reports/optimize.json). Earlier piece-3 build prose describes the superseded trial 154. Current M5 preserves bounded Webster side-phase proportions and cycle slack, and enqueues the exact baseline. It searches cycle 80–150 s, five offset fractions, five mainline multipliers 0.6–1.4 and shared passage 2–4 s, preserving phase order, rest, skips and clearances.

M5 scores scheduled fit-hour departures only, with 900 s warmup and 1800 s drain. Objective = completed-trip mean timeLoss + (completed insertion delays + 1800 s × (unfinished requested vehicles + cumulative teleports)) / requested vehicles + max(0, side-origin mean timeLoss − 1.2 × same-seed baseline side loss). On fit seeds 0–2 the corrected objective falls 410.239 → 239.011, with 13 candidate teleports on seed 2. Night never influences selection. Parallel TPE scheduling may change the search; saved plans and simulation seeds reproduce evaluation. M6 below is the independent evaluation of those saved plans.


## Results (M6)

**In the simulated rush-hour holdout, the optimized plan completes 513 more requested trips and cuts eastbound corridor travel time by 9.1%, but completed trips from side streets lose 11.8% more time.** This is a simulation using **2018 historical counts**, with 3 of 5 quarter-hour profiles estimated, not evidence about current Cupertino traffic. Completed-trip mean loss rises 12.1% in the holdout; the all-requested-vehicle delay score falls 25.5% (paired one-sided p=0.000977), including the stated unfinished charge.

The following table averages each metric equally across the ten out-of-sample seeds **3–12**; unfinished is mean vehicles per seed, while teleports are total events across those ten seeds. Direction travel times are means of per-seed means, with sample counts in the CSV. Full and holdout PM rows overlap and must not be added.

| Scenario / window | Controller | Loss (s) | Side loss (s) | Stops | Unfinished | Teleports | EB travel (s) | WB travel (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| pm_peak / holdout | actuated | 167.06 | 137.85 | 5.52 | 696.8 | 61 | 402.13 | 186.28 |
| pm_peak / holdout | optuna | 187.21 | 154.09 | 6.43 | 183.4 | 52 | 365.65 | 175.40 |
| pm_peak / full | actuated | 172.14 | 146.39 | 5.73 | 696.8 | 88 | 393.24 | 180.66 |
| pm_peak / full | optuna | 173.04 | 147.64 | 5.93 | 183.4 | 63 | 340.13 | 172.89 |
| night / full | actuated | 8.51 | 13.94 | 0.29 | 0.0 | 0 | 116.59 | 98.89 |
| night / full | optuna | 8.57 | 14.02 | 0.29 | 0.0 | 0 | 116.76 | 98.91 |

All-requested-vehicle delay score (seconds/requested vehicle) = **[sum of completed-trip (timeLoss + departDelay) + 1800 × (unfinished requested cars + cohort teleport events)] / requested cars**. The 1800 s charge is the M5 one-drain-window rule, a scoring assumption rather than measured unfinished delay. This uses a requested-vehicle denominator for completed loss too; it is not the M5 optimization objective and has no side-origin surcharge. The zero-unfinished version removes only the unfinished charge and retains the teleport charge: a lower bound on this score, not an estimate of actual unfinished delay. Both versions include every requested ID in the denominator.

Means across seeds 3–12 and paired one-sided Wilcoxon p-values (`optuna < actuated`):

| Metric | PM holdout actuated → optuna | p | Full PM actuated → optuna | p | Night actuated → optuna | p |
|---|---:|---:|---:|---:|---:|---:|
| All-requested delay score (s) | 847.78 → 631.52 | 0.000977 | 634.99 → 454.92 | 0.000977 | 9.02 → 9.08 | 0.784180 |
| Zero unfinished charge (s) | 690.61 → 590.15 | 0.001953 | 556.40 → 434.24 | 0.000977 | 9.02 → 9.08 | 0.784180 |
| Unfinished cars | 696.8 → 183.4 | 0.000977 | 696.8 → 183.4 | 0.000977 | 0 → 0 | 1 |
| EB travel (s) | 402.13 → 365.65 | 0.018555 | 393.24 → 340.13 | 0.006836 | 116.59 → 116.76 | 0.903320 |
| WB travel (s) | 186.28 → 175.40 | 0.422852 | 180.66 → 172.89 | 0.539063 | 98.89 → 98.91 | 0.509766 |

The completed-only mean has survivor bias: of 7,980 requested holdout cars per seed, **7,283.2 → 7,796.6 complete**, and **696.8 → 183.4 remain unfinished**. Full PM requests 15,960 and completes **15,263.2 → 15,776.6**. Unfinished combines never-inserted and still-running cars; the saved aggregates do not separate these, so it would be inaccurate to claim all 513 extra completions are extra insertions onto Stevens Creek. The requested-denominator scores can be recovered from saved completed counts and means without rerunning simulations (up to floating-point rounding).

The tradeoff matters: PM holdout mean insertion delay falls **588.31 → 416.16 s** and unfinished demand falls **696.8 → 183.4 vehicles per seed**, while completed-trip time loss and stops rise. In the full PM scenario, insertion delay falls **408.72 → 265.74 s**. Neither controller clears all PM demand within the drain. Out-of-sample PM teleport totals are **88 → 63** for full PM and **61 → 52** for its holdout cohort; night has none. Teleports can distort congestion and completed-trip loss. Completed-trip loss includes trips that teleported, while directional travel times exclude them. These results do not establish an overall better plan or justify field deployment.

Evaluation uses the frozen trial-146 plans, identical scenario route files and paired SUMO seeds **0–12**. Seeds **3–12** were excluded from M5 fitting/selection and are the primary out-of-sample simulation result; seeds 0–2 remain separately labeled in [results.csv](reports/results.csv). Routes themselves are fixed across seeds. PM holdout demand replays the fitted hour, so this tests simulation randomness and later operating conditions, not unseen measured traffic demand.

**Full PM** is scheduled departures 16:30–18:30; **PM holdout** is 17:30–18:30 from the same continuous run, retaining the preceding hour's queues. **Full night** is 23:00–24:00; night has no specified holdout. Each simulation starts 900 s before the scenario and ends after a 1800 s drain, with `time_to_teleport=300`. Warmup departures are excluded using scheduled departure IDs, so delayed or never-inserted demand stays in its cohort. CSV `unfinished` counts requested vehicles without a completed trip after the drain. Mean loss, side loss, stops (`waitingCount`) and insertion delay describe completed trips only; these means can hide unfinished demand. Side origin is the first modeled approach being a side street.

Directional corridor times measure entry into the outer approach edge at Mary/De Anza through exit from the far-side departure edge at the opposite end, including both end signals. Only continuous mainline traversals with observed exits count; teleported vehicles are excluded. The CSV retains EB/WB sample counts and their pooled `mainline_travel_s`. Teleports count events affecting each departure cohort, excluding warmup IDs; the separate run-total column includes warmup. Teleport times need not fall inside the departure window.

The original primary test is paired Wilcoxon signed-rank on per-seed completed-trip mean time loss for PM holdout seeds 3–12: one-sided alternative **optuna < actuated**, alpha 0.05. [Wilcoxon results](reports/wilcoxon.csv) also include all 13 seeds and the additional full PM/night tests. The all-requested, unfinished and directional tests above were added during review after seeing results; all p-values are unadjusted and are exploratory. All-zero differences return p=1. The original test concerns completed-trip loss; none of these tests establishes field benefit.

For piece 5 only, [actuated FCD](reports/fcd_actuated_pm_peak_seed0.xml.gz) and [optuna FCD](reports/fcd_optuna_pm_peak_seed0.xml.gz) contain the same PM seed-0 17:30–17:45 window at 1 s resolution, after continuous simulation from 16:15. They contain local XY coordinates, lane, speed, angle and vehicle IDs. [Evaluation provenance](reports/eval.json) records input hashes, boundary edges, FCD sizes/timestamps and laptop settings. Dashboard and video are not built.

Data: De Anza (Jan 10, 2018) and Stelling (Jan 17, 2018) have measured quarter-hour turns. Mary has newer Apr 25, 2018 hourly observations, preserved separately; its quarter-hour profile is estimated. Bandley and Saich are estimated. Thus **3 of 5 quarter-hour profiles are estimated**. Mary's current OSM topology lacks movements representing 775 vehicles/hour on the sheet; those observations are retained but cannot be simulated. All dates, methods and limits: [source audit](reports/data-source-audit.md), [provenance CSV](data/processed/tmc_sources.csv). The agent visually checked Stelling PDF p.554; independent human sign-off remains pending.

Outputs: [M4 baseline report](reports/M4-REPORT.md), [M2 report](reports/M2-REPORT.md), [M3 holdout report](reports/demand_check.md), [holdout rows](reports/demand_check.csv). Spec: [architecture](docs/ARCHITECTURE.md). M5 outputs: [search evidence](reports/optimize.json), [all trials](reports/optimize_trials.csv), and `reports/timing_{pm_peak,night}.csv`. The full 4.2 command intentionally stops at `eval`.

SUMO jobs run at nice 15, with at most three separate worker processes on AC (one on battery) and a two-hour child timeout; the heat guard may pause them. Follow [laptop limits](reports/bench.md) before long jobs. No dependencies were added for M4/M5. `smoke_test.py` remains unchanged.

Roads © [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). Counts: City of Cupertino / Vallco TIA (Traffic Data Service), Westport CEQAnet appendix (National Data & Surveying Services). VTA sample was audited but does not supply corridor counts.

## Offline judge demo

Run `.venv/bin/python -m signal_lab dashboard` (headless; requires the installed
`ffmpeg` on PATH). This builds `dashboard/index.html`, `reports/side_by_side.mp4`,
`reports/side_by_side_poster.png`, and `reports/time_space.png` from the frozen
results, paired tests, timing CSVs, SUMO network, and the two seed-0 FCD archives.
It also replays the two frozen seed-0 plans serially to recover insertion/arrival
timestamps before the FCD window and writes `reports/video_counts.csv`. Counters
include warmup trips; teleport gaps are not counted as new insertion queues or finishes.
Open `dashboard/index.html` directly in a browser; keep its sibling `reports/`
and `data/processed/` folders with it. No server, CDN, or network is needed.
The 15-minute seed-0 illustration plays at 8×; the page's aggregate evidence uses
seeds 3–12 and shows the gains, side-street cost, unfinished demand, and limits.
The builder runs at low priority; follow the power limits in `reports/bench.md`.
