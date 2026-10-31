# Cupertino Signal Lab

A reproducible AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. **Current demand inputs mix 2024 De Anza/Stelling counts with 2018 Mary observations and estimates; not current Cupertino traffic.** Demo timing assumptions are not city signal plans.

**Result:** in this fixed-demand simulation on 2024 VTA counts, a tuned plan cut rush-hour delay 40.7% against a textbook timing plan (829 → 491 s, 30 unseen rush hours, p = 9.31e-10), while several trip-start groups waited longer and westbound got slightly slower (140 → 145 s). The night plan was not a confirmed win. This is not a comparison with the city's or VTA's timing, and nothing has been tested on the street. Thank you to Kia Sharifi, P.E., and Larissa Sanderfer at VTA for the 2024 counts.

Demo: [deck](dashboard/deck.html), [page](dashboard/index.html), [video](reports/side_by_side.mp4). Details below.

```sh
source .venv/bin/activate
# Fresh environments: uv venv --python 3.12; uv pip install -r requirements.txt
uv pip install -e .
export PYTHONPATH=src  # Keep shared virtual environments on this worktree.
nice -n 15 python -m signal_lab build-net
nice -n 15 python -m signal_lab build-demand
nice -n 15 python -m signal_lab baseline
nice -n 15 python -m signal_lab check-demand
nice -n 15 python -m signal_lab bench
nice -n 15 python -m signal_lab optimize --version 5 --scenario night
nice -n 15 python -m signal_lab optimize --version 5
nice -n 15 python -m signal_lab eval --version 5
nice -n 15 python -m unittest discover -s tests -v
```

M2 produces both PM/night demand through nonnegative least-squares route fitting, fits only 16:30–17:30, and replays that fit hour for holdout. Routes and data are unchanged by M4. The baseline uses Webster seeds, coordinator offsets, engineering clearance inputs, force-offs and detector-based phase skips; night rests in mainline green without a conflicting call.

The current physical count check remains below the calibration target; the 2024 timing results and limits are reported first below. [Count check](reports/demand_check.md).

## Results (2024 model, preregistered v5)

v5 is one policy with two plans: the v5 rush-hour plan runs in PM, the v5 night plan at night. **The switch between them is not simulated.** On brand-new paired seeds **73–102** (30 seeds), v5 changed PM-holdout all-requested delay by **-40.73%** versus textbook (one-sided paired Wilcoxon **p=9.31e-10**, alpha .05, confirmed); frozen v4 changed it by -31.25%. At night, v5 side-origin delay was **+2.98%** versus textbook (19.46 → 20.04 s), inside the 5% cap, but the preregistered non-inferiority test (v5 side − 1.05 × textbook side < 0) gave **p=0.079**, so the night result is **not confirmed**. v5 passed every hard constraint in every window; frozen v4 also passed them all on these seeds (night side +4.41%).

Rush-hour search: v4 space, seeds 0–4, textbook/v3/v4 enqueued, three workers. The preregistered 600 trials hit the existing 6500 s timeout at **585** after the laptop slept and switched to battery; selection then ran on those 585 under a contingency written down before the outcome (logged in the [preregistration](docs/PREREGISTRATION.md), with a SQLite queued-trial double-claim bug fix and a restart before any selection). Trial **561** (cycle 171.99 s vs v4 167.00 s) beat v4 on seeds 0–4 (224.88 vs 272.58 s) and 5–12 (230.09 vs 258.81 s), so v4 was not kept; its worst origin-group change on 5–12 was +20.6 s (v4 +20.7 s). Night search: 200 trials on night demand, cycle 66.9–180 s, textbook enqueued; trial **147** (cycle 97.4 s) chosen by the 1% origin-group tiebreak. [Rush-hour search](reports/optimize_v5.json), [night search](reports/optimize_v5_night.json), [per-seed results](reports/results_v5.csv), [tests and provenance](reports/eval_v5.json).

Means over 30 seeds; delay/EB/WB/side are seconds, 900 s charge. Unfinished and teleports are **totals over 30 runs**.

| Window | Plan | All-requested delay | Unfinished | Teleports | EB | WB | Side |
|---|---|---:|---:|---:|---:|---:|---:|
| PM holdout | Textbook | 829.14 | 21847 | 0 | 348.61 | 139.86 | 995.40 |
| PM holdout | v4 | 570.04 | 1166 | 0 | 174.27 | 142.58 | 695.65 |
| PM holdout | v5 | 491.44 | 189 | 0 | 177.89 | 145.36 | 576.53 |
| Full PM | Textbook | 654.93 | 21847 | 0 | 317.19 | 139.38 | 772.28 |
| Full PM | v4 | 429.51 | 1166 | 0 | 175.61 | 142.36 | 506.55 |
| Full PM | v5 | 375.73 | 189 | 0 | 178.18 | 144.34 | 425.66 |
| Estimated night | Textbook | 10.38 | 0 | 0 | 116.34 | 99.19 | 19.46 |
| Estimated night | v4 | 10.50 | 0 | 0 | 116.45 | 99.10 | 20.32 |
| Estimated night | v5 | 10.31 | 0 | 0 | 116.53 | 99.59 | 20.04 |

v5 mean ratios versus textbook (side / EB / WB): PM holdout 0.579 / 0.510 / 1.039, full PM 0.551 / 0.562 / 1.036, night 1.030 / 1.002 / 1.004; every seed within textbook+2 teleports. WB is the tightest PM constraint: v5 passes on the mean, and 23/30 holdout seeds individually. Delay with 0 s / 1800 s charges, textbook/v4/v5: holdout 745.83/565.59/490.72 and 912.45/574.48/492.16; night is unchanged by charge (nothing unfinished).

Per origin group (first modeled approach edge), PM-holdout mean all-requested delay, textbook → v5, 30 seeds ([file](reports/origin_v5.csv)): better for North De Anza (1933.8 → 979.8 s), Stevens Creek entry 526011476 (367.1 → 59.6), Mary (136.7 → 40.9), Stevens Creek entry 1113038418 (76.8 → 38.6) and South De Anza (81.2 → 75.0); worse for Stevens Creek entry 593271049#0 (1033.9 → 1082.5), North Stelling (651.8 → 683.4), South Stelling (72.6 → 100.0), Saich (34.8 → 43.1), Bandley (71.5 → 78.7) and Stevens Creek entry 1113038412#0 (53.2 → 57.0). At night, North and South De Anza each rise about 2.7–2.8 s; other groups change by under 2.5 s. The aggregate gain does not mean every group benefits. Same limits as v4 below: not fully calibrated, fixed replayed demand, estimated night, weak textbook comparator, no field-benefit claim. **The dashboard, deck, page and video still show earlier results.**

## Earlier results (2024 model, preregistered v4)

On brand-new paired seeds **53–72**, v4 changed PM-holdout all-requested delay by **-30.28%** versus textbook (one-sided paired Wilcoxon **p=9.53674316e-07**, alpha .05). v4 passed all PM constraints but failed the night side-origin constraint (**+6.67%**, above the +5% cap; 18.99 → 20.26 s). Textbook remains the feasible fallback. Significance and feasibility are judged separately.

The preregistered **60 trials** used seeds 0–2 on one worker; seeds 3–4 stayed unused. The ten best training-feasible trials plus textbook were rescored on seeds 5–12. Trial **39** was selected after **17.58 minutes** and frozen before final testing. Its shared cycle is **167.00 s**, versus **137.11 s** for frozen v3 and **117.90 s** for textbook; offsets, phase shares, passage gaps and mainline minima were retuned. Final evaluation took **13.33 minutes**. [Preregistration](docs/PREREGISTRATION.md), [search evidence](reports/optimize_v4.json), [trials](reports/optimize_v4_trials.csv).

Means over 20 seeds; delay/EB/WB/side are seconds. Unfinished and teleports are **totals over 20 runs**, not averages. Delay and side use the preregistered 900 s charge per unfinished vehicle and teleport event.

| Window | Plan | All-requested delay | Unfinished | Teleports | EB | WB | Side |
|---|---|---:|---:|---:|---:|---:|---:|
| PM holdout | Textbook | 826.23 | 14344 | 3 | 350.93 | 139.41 | 985.39 |
| PM holdout | Frozen v3 | 729.53 | 6734 | 0 | 298.15 | 142.00 | 876.80 |
| PM holdout | v4 | 576.04 | 703 | 0 | 173.14 | 142.26 | 704.80 |
| PM holdout | existing_vta (projection) | 623.35 | 26599 | 1861 | 987.19 | 1350.84 | 443.44 |
| Full PM | Textbook | 654.85 | 14344 | 3 | 318.37 | 138.76 | 763.77 |
| Full PM | Frozen v3 | 557.16 | 6734 | 0 | 279.02 | 141.50 | 651.74 |
| Full PM | v4 | 433.26 | 703 | 0 | 175.08 | 142.26 | 513.02 |
| Full PM | existing_vta (projection) | 688.92 | 35829 | 2594 | 758.71 | 756.85 | 495.70 |
| Estimated night | Textbook | 10.44 | 0 | 0 | 116.45 | 98.26 | 18.99 |
| Estimated night | Frozen v3 | 10.44 | 0 | 0 | 116.16 | 98.14 | 19.88 |
| Estimated night | v4 | 10.61 | 0 | 0 | 116.55 | 98.68 | 20.26 |
| Estimated night | existing_vta (projection) | 17.40 | 0 | 0 | 125.90 | 108.58 | 25.49 |

Hard constraints: paired **mean** side/EB/WB must each be ≤105% of textbook, and teleports must be ≤textbook+2 **on every seed**. Per-seed side/EB/WB pass counts below are descriptive; their hard rules use cohort means.

| v4 window | Mean side / EB / WB / every-seed teleport | Per-seed side / EB / WB / teleport passes |
|---|---|---|
| PM holdout | PASS / PASS / PASS / PASS | 20/20 / 20/20 / 19/20 / 20/20 |
| Full PM | PASS / PASS / PASS / PASS | 20/20 / 20/20 / 20/20 / 20/20 |
| Estimated night | FAIL / PASS / PASS / PASS | 9/20 / 20/20 / 20/20 / 20/20 |

Sensitivity: delay vectors list **textbook / v3 / v4 / existing_vta projection**. Zero charge omits unfinished/teleport charges and can reward noncompletion; 1800 s is another scoring convention.

| Window | Delay, 0 s | Delay, 1800 s | v4 change / p, 0 s | v4 change / p, 1800 s |
|---|---|---|---|---|
| PM holdout | 744.16 / 691.01 / 572.02 / 460.56 | 908.30 / 768.05 / 580.06 / 786.15 | -23.13% / 9.53674316e-07 | -36.14% / 9.53674316e-07 |
| Full PM | 613.82 / 537.90 / 431.25 / 579.03 | 695.88 / 576.42 / 435.27 / 798.81 | -29.74% / 9.53674316e-07 | -37.45% / 9.53674316e-07 |
| Estimated night | 10.44 / 10.44 / 10.61 / 17.40 | 10.44 / 10.44 / 10.61 / 17.40 | +1.71% / 0.968138695 | +1.71% / 0.968138695 |

At 0 s, v4 mean-side/EB/WB/every-seed-teleport constraints: PM holdout: PASS/PASS/PASS/PASS, side 20/20 seeds; Full PM: PASS/PASS/PASS/PASS, side 20/20 seeds; Estimated night: FAIL/PASS/PASS/PASS, side 9/20 seeds. EB/WB/teleport per-seed counts are unchanged by charge.

At 1800 s, v4 mean-side/EB/WB/every-seed-teleport constraints: PM holdout: PASS/PASS/PASS/PASS, side 20/20 seeds; Full PM: PASS/PASS/PASS/PASS, side 20/20 seeds; Estimated night: FAIL/PASS/PASS/PASS, side 9/20 seeds. EB/WB/teleport per-seed counts are unchanged by charge.

The PM primary comparison alone is confirmatory. Full PM, night, frozen v3, existing_vta and sensitivity tests are descriptive and unadjusted. Full PM and holdout overlap. `existing_vta` is a secondary controller **projection**, including assumed U-turn service; its PM plan is reused unchanged at estimated night because no independent night projection exists.

This model retains the supplied 2024 De Anza/Stelling movements but remains incompletely calibrated: physical L/T/R GEH<5 is **48/96** on seed 0 (45/96 on seeds 1–2), versus **41/96** on the old model. Mixed-year Mary data, estimated neighbour/night demand, unverified internal waiting positions, lane storage, U-turn greens and controller semantics limit interpretation. Holdout demand replays the fitted hour, testing simulation randomness and later queues rather than unseen measured traffic. EB/WB use completed nonteleported corridor crossings and omit insertion delay; completed-only loss is survivor-biased. **These are simulation results, not field benefit estimates.** [Source dates and methods](data/processed/tmc_sources.csv); [2024 raw transcription](data/processed/vta_counts_2024.csv).

A review rerun of final seed 53 reproduced textbook and v4 metrics exactly, but exposed uneven benefits: all 595 South Stelling-origin holdout trips finished under both plans, but their mean delay rose **68.7 → 173.1 s**. Completed-trip delay (time loss plus insertion delay) for South Stelling → Stevens Creek rose **94.79 → 539.80 s** (78 trips), and South Stelling → Mary rose **177.41 → 518.69 s** (63 trips). These are origin–destination groups from one seed, not 20-seed movement estimates. The aggregate side-origin rule does not protect each origin or trip group; the longer cycle is not evidence that every movement benefits.

[2024 per-seed results](reports/results_2024.csv) include requested/completed counts, completed-only loss, insertion delay, corridor sample counts and constraint checks. [Final provenance and paired tests](reports/eval_v4.json) contain input/plan hashes and all secondary tests. [Frozen PM](sim/tls_optuna_v4_pm_peak.add.xml) and [night](sim/tls_optuna_v4_night.add.xml) plans preserve the selected parameters. Legacy results and frozen v3 artifacts remain unchanged. **The dashboard, deck, page and video still show archived 2018 results.**

## Archived results (2018 demand, v2 and v3)

Archived M4 seed 0 on **2018 demand**: night inserts **439**, with **zero teleports** and **8.341 s** mean time loss. PM inserts **17,091**, with **zero teleports**, **116 running** and **792 waiting to insert** after the drain; completed-trip mean time loss is **170.622 s**. Means exclude warmup departures; unfinished trips are absent. These timing assumptions are not a successful PM calibration.

On brand-new seeds 33–52, v3 cut PM-holdout all-requested delay 22.7% (836.77 to 646.74 s/vehicle), EB travel 16.5%, WB travel 35.6%, and teleports from 185 to 17 (one-sided paired Wilcoxon primary p=0.0000524521), but it exceeded textbook +2 teleports on seed 37, so it was not a feasible winner under the preregistered rule.

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

Outputs: [M4 baseline report](reports/M4-REPORT.md), [M2 report](reports/M2-REPORT.md), [M3 holdout report](reports/demand_check.md), [holdout rows](reports/demand_check.csv). Spec: [architecture](docs/ARCHITECTURE.md). M5 outputs: [search evidence](reports/optimize.json), [all trials](reports/optimize_trials.csv), and `reports/timing_{pm_peak,night}.csv`. The full 4.2 command intentionally stops at `eval`.

SUMO jobs run at nice 15, with at most three separate worker processes on AC (one on battery) and a two-hour child timeout; the heat guard may pause them. Follow [laptop limits](reports/bench.md) before long jobs. No dependencies were added for M4/M5. `smoke_test.py` remains unchanged.

Roads © [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). 2024 counts and timing reports: VTA (IDAX, Oct 9, 2024), shared by Kia Sharifi, P.E., and Larissa Sanderfer. 2018 counts: City of Cupertino / Vallco TIA (Traffic Data Service), Westport CEQAnet appendix (National Data & Surveying Services). VTA sample was audited but does not supply corridor counts.

## Offline judge demo

Run `.venv/bin/python -m signal_lab dashboard` (headless; requires the installed
`ffmpeg` on PATH). This builds `dashboard/index.html`, `reports/side_by_side.mp4`,
`reports/side_by_side_poster.png`, and `reports/time_space.png` from the frozen
results and seed 73, the first final-test seed. The seed 73 traffic files are not in git; `reports/video73/generation.json` has the command that remakes them.
Open `dashboard/index.html` directly in a browser; keep its sibling `reports/`
and `data/processed/` folders with it. No server, CDN, or network is needed.
The 15-minute seed-0 illustration plays at 8×; the page's aggregate evidence uses
seeds 3–12 and shows the gains, side-street cost, unfinished demand, and limits.
The builder runs at low priority; follow the power limits in `reports/bench.md`.
