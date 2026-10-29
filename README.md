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

## Results (preregistered v2)

On the 20 preregistered simulation seeds, v2 met the confirmatory rule by cutting rush-hour holdout all-requested delay 24.7% (790.57 to 595.61 s/vehicle; one-sided paired Wilcoxon p=0.00084495544) while keeping mean side-origin delay within the 1.05 cap (ratio 0.756), but completed-trip loss rose 13.6%, westbound corridor travel rose 38.5%, and teleports rose from 69 to 256 events and exceeded the training cap on 8 of 20 seeds, so no overall feasible winner was established.

The confirmatory one-sided paired Wilcoxon p-value is **0.00084495544** (v2 < textbook, n=20, alpha .05). This is an optimized retiming versus a textbook seed plan in a model using **historical 2018 counts**, with 3 of 5 quarter-hour profiles estimated; it establishes no present-city or field benefit. [Preregistration](docs/PREREGISTRATION.md) was committed before the new runs, including the promise to report either outcome.

Means across final seeds **13–32** (never used for fitting or selection); teleports are event totals across the 20 seeds. Full PM and PM holdout overlap.

| Scenario / window | Plan | All-requested (s) | Completed loss (s) | Side all-requested (s) | Side completed loss (s) | EB / WB travel (s) | Unfinished | Teleports | Side constraint |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| pm_peak / holdout | Textbook | 790.57 | 161.49 | 928.80 | 136.56 | 398.25 / 176.28 | 773.1 | 69 | yes (+0.0%) |
| pm_peak / holdout | v1 | 694.45 | 198.50 | 800.67 | 162.81 | 403.11 / 225.57 | 170.2 | 293 | yes (-13.8%) |
| pm_peak / holdout | v2 | 595.61 | 183.45 | 702.40 | 167.17 | 340.83 / 244.07 | 105.7 | 256 | yes (-24.4%) |
| pm_peak / full | Textbook | 641.64 | 176.63 | 730.03 | 151.02 | 403.33 / 187.68 | 773.1 | 191 | yes (+0.0%) |
| pm_peak / full | v1 | 493.43 | 184.64 | 564.53 | 154.72 | 372.11 / 207.14 | 170.2 | 392 | yes (-22.7%) |
| pm_peak / full | v2 | 419.46 | 168.52 | 487.15 | 155.11 | 308.75 / 234.11 | 105.7 | 568 | yes (-33.3%) |
| night / full | Textbook | 9.15 | 8.64 | 15.52 | 15.01 | 117.26 / 98.94 | 0.0 | 0 | yes (+0.0%) |
| night / full | v1 | 9.18 | 8.66 | 15.34 | 14.83 | 117.37 / 98.93 | 0.0 | 0 | yes (-1.1%) |
| night / full | v2 | 9.15 | 8.63 | 15.52 | 15.02 | 117.39 / 98.89 | 0.0 | 0 | yes (+0.1%) |

The teleport guard passed training and selection but failed to generalize: v2 exceeds textbook +2 cohort teleport events on 8 of 20 final seeds in both full PM and holdout. Full-PM teleport totals rise 191 → 568; holdout totals rise 69 → 256. The selected plan is retained for the preregistered comparison without retuning; no overall feasible winner is established.

Requested / completed trips per seed (textbook / v1 / v2): pm_peak/holdout: requested 7980, completed 7206.9 / 7809.8 / 7874.4; pm_peak/full: requested 15960, completed 15186.9 / 15789.8 / 15854.4; night/full: requested 353, completed 353.0 / 353.0 / 353.0.

Primary all-requested delay (seconds/requested vehicle) = **[sum of completed (timeLoss + departDelay) + 900 × (unfinished vehicles + cohort teleport events)] / requested vehicles**. Side-origin delay uses the same formula with only side-origin IDs and its own requested denominator. Unfinished includes never-inserted and still-running vehicles. The charge is a convention, not measured unfinished delay; completed loss and side completed loss exclude unfinished vehicles. Insertion delay remains separately available in the CSV. The final constraint is the ratio of paired side-origin means, at most 1.05; per-seed flags are also retained.

Sensitivity below changes the charge on **both unfinished vehicles and teleport events**. Each cell is textbook / v1 / v2 seconds per requested vehicle. The legacy `all_vehicle_delay_s` (1800 s) and `all_vehicle_delay_zero_unfinished_s` (zero unfinished charge but 1800 s teleport charge) columns remain for compatibility; the new primary is `all_requested_delay_s`.

| Scenario / window | 0 s charge | 900 s charge (primary) | 1800 s charge |
|---|---:|---:|---:|
| pm_peak / holdout | 702.99 / 673.61 / 582.25 | 790.57 / 694.45 / 595.61 | 878.16 / 715.30 / 608.97 |
| pm_peak / full | 597.50 / 482.73 / 411.90 | 641.64 / 493.43 / 419.46 | 685.77 / 504.14 / 427.02 |
| night / full | 9.15 / 9.18 / 9.15 | 9.15 / 9.18 / 9.15 | 9.15 / 9.18 / 9.15 |

One-sided paired Wilcoxon p-values (candidate < textbook). Only v2 PM holdout primary is confirmatory; all other comparisons and sensitivities are descriptive, unadjusted. All-zero differences give p=1. The CSV retains `all` and `out_of_sample` groups for compatibility; both refer to the same 20 final seeds here.

| Scenario / window | Candidate | Primary | Completed loss | Side completed loss | EB travel | WB travel | Unfinished | Teleports |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| pm_peak / holdout | v1 | 0.00319481 | 0.999998 | 0.999982 | 0.521835 | 0.99396 | 9.53674e-07 | 0.997867 |
| pm_peak / holdout | v2 | 0.000844955 | 0.923177 | 0.999803 | 0.0265846 | 0.977973 | 6.00468e-05 | 0.971809 |
| pm_peak / full | v1 | 6.67572e-06 | 0.968139 | 0.928547 | 0.0076561 | 0.951346 | 9.53674e-07 | 0.957052 |
| pm_peak / full | v2 | 1.33514e-05 | 0.0768232 | 0.337111 | 0.000992775 | 0.981883 | 6.00468e-05 | 0.855676 |
| night / full | v1 | 0.784783 | 0.784783 | 0.0085907 | 0.847749 | 0.571873 | 1 | 1 |
| night / full | v2 | 0.215217 | 0.215217 | 0.378083 | 0.949004 | 0.138474 | 1 | 1 |

Every plan uses identical fixed routes, paired SUMO seeds, 900 s warmup, 1800 s drain and a 300 s teleport timeout. Full PM is scheduled departures 16:30–18:30; holdout is 17:30–18:30 from that continuous run, retaining earlier queues. Night is estimated 23:00–24:00. Warmup IDs are excluded by scheduled departure. Side origin means the first modeled approach is a side street. Teleports count events for cohort IDs, regardless of event time; run totals including warmup are separate. Teleports may distort congestion and completed-trip loss. EB/WB times cover the outer approach entry through the opposite departure-edge exit, include both end signals, exclude pre-insertion delay and teleported vehicles, and retain sample counts in the CSV.

Fixed holdout demand replays the fitted hour: the test evaluates simulation randomness and later queues, not unseen measured demand. Neither controller comparison validates current traffic or field deployment.

v1 is the frozen original trial-146 plan, preserved byte for byte as `sim/tls_optuna_v1_*.add.xml`, with [archived search evidence](reports/optimize_v1.json). v2 completed **200 trials** in **43.15 minutes** on common seeds **0–2**, then rescored the top ten on **3–12**, selecting trial **185**. It tunes one shared cycle (80–150 s), one offset per signal, bounded phase-specific green multipliers (0.6–1.4), and passage time per signal (2–4 s). Bounds, clearance, phase order, rest/skip logic and cycle slack remain; there are no separate EB/WB offsets. The exact textbook plan is trial 0 and a feasible selection fallback. A steep penalty enforces the +5% mean side-origin constraint and candidates exceeding textbook cohort teleports by more than two on any paired seed are rejected. Selection never uses night or final seeds; PM parameters are frozen for night. Final evaluation and FCD export took **13.29 minutes**.

[Results CSV](reports/results.csv) identifies textbook as `actuated`, v1 as `optuna_v1`, and v2 as `optuna`. [Paired tests](reports/wilcoxon.csv) retains its original columns and adds `controller` to identify the candidate plus aggregate side-constraint fields; `optuna_mean` is that candidate mean and `actuated_mean` is textbook. Consumers must filter `controller` when looking up a p-value. [Evaluation provenance](reports/eval.json) records input hashes, seeds, boundaries and laptop settings; [v2 search evidence](reports/optimize.json) and [all trials](reports/optimize_trials.csv) retain training and selection metrics.

[Textbook seed-13 FCD](reports/fcd_actuated_pm_peak_seed13.xml.gz) and [selected v2 seed-13 FCD](reports/fcd_optuna_pm_peak_seed13.xml.gz) cover 17:30–17:45 at 1 s resolution after continuous simulation from 16:15. Each has 900 steps; they illustrate one seed, not the aggregate result. Dashboard/video integration is handled on the separate design branch; the existing seed-0 illustration remains unchanged.

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
