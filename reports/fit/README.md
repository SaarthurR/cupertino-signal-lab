# VTA demand and timing diagnostics

Historical fit/review evidence below. The later targeted model repair and current results are in [../model/README.md](../model/README.md); comparison logs and movement_diagnosis.csv here were refreshed by that required rerun.

All runs are serial, nice 15, training seed 0 unless a CSV lists seeds 0–2. No signal optimization or final-seed evaluation.
Before files are copied from commit 47c9090. `reports/runs/fit` contains temporary raw run files (ignored); aggregate evidence is retained here.

Demand trials, identical source counts after adding 272 measured fit-hour U-turns:
- hard cap: original routeSampler full allocation; 197 candidates; 772 PM teleports, 8288 waiting after drain; 21/128 measured holdout GEH<5.
- symmetric: nonnegative least squares of `(scheduled-observed)/sqrt(max(observed,1))`, every observation retained; 649 PM teleports, 7879 waiting; 23/128 GEH<5 on original network. Rejected as an improvement on its own.
- no U: diagnostic removal of 551 U-turn vehicles from symmetric replay, 653 teleports, 8151 waiting. Not production demand and not a calibration score.
- no U and no De Anza EB left: further diagnostic removal of 230 vehicles, 0 teleports, 352 waiting. Not production demand and not a calibration score.
- all-stopline: netconvert `--default.connection.cont-pos 0`, identical symmetric routes, 27 teleports, 1482 waiting. External edge lengths/speeds/lane counts/shapes and all five TLS lane/link mappings were unchanged; review found two lane-change restrictions lost in the netconvert round trip (restored below). Diagnostic only; broader than required.

The jam snapshot at 61000 s contains stopped De Anza left-turn vehicles on internal lanes 16 and 23 while other left turns enter lanes 4 and 10. The first yield teleport is at 61229 s on WB through. This isolates a trapped permissive-left conflict triggered by restoring the previously omitted EB left; it is not evidence that the real street gridlocks. A stop-line waiting model is an inferred geometry correction, not field-verified lane storage.

## Retained result

The narrower correction, four De Anza left connections with `contPos=0`, gives **0 teleports, 144 running, 1448 waiting** in textbook seed 0. It avoids the broad all-stopline change. The change leaves external lane geometry and TLS lane/link mapping intact and is reapplied by `build-net`; it changes internal waiting and response priorities, so it can affect controllers differently. It is not evidence of improved capacity. `jam_state.xml.gz` preserves the pre-fix state; `sim/vta_stopline.con.xml` is the correction input.

No counts were edited. All 328 preexisting rows remain byte-equivalent in their fields; 64 source-labeled U-turn rows were appended. All 49 modeled movements remain in every fit interval. Exact route-incidence feasibility fails in all four quarters (`count_feasibility.csv`): no flag can exactly satisfy this combination of observed and estimated counts with these boundary routes. No signal optimization was run. SciPy was already installed for routeSampler.

The best retained count check is **43/96 L/T/R (44.79%) vs 37/96 (38.54%) before**; adding U-turns gives **65/128 (50.78%)**, below 85%. Measured fit-period physical matches: De Anza 39/64, Stelling 54/64; count-check matches: De Anza 31/64, Stelling 34/64. These are count checks, not held-out performance evaluation.

| Cause | Evidence / remaining uncertainty |
|---|---|
| routeSampler hard ceilings | Original positive De Anza EB L / Stelling WB L,R received zero fit-hour vehicles despite legal candidate coverage. Symmetric residuals restore them; no observation or movement is discarded. |
| estimated Bandley/Saich | Unmeasured 5/quarter side turns and interpolated through counts constrain corridor flow. Their residuals are retained and labeled, not silently fitted as measurements. Their individual contribution is not experimentally isolated. |
| Mary 2018 mismatch | Mixed-year boundary totals and only five modeled Mary movements remain; original audit documents missing topology and incompatible boundary totals. No count, quarter estimate or missing movement was fabricated. |
| connectivity | The three zero movements already have legal lane connections. All 32 source-site movements now cross under both plans, seeds 0–2. No missing turn connector was needed. |
| internal waiting geometry | Restored De Anza EB left exposes trapped permissive-left conflicts; removal and stop-line controls isolate this model mechanism. Corrected waiting position remains a field-unverified inference. |
| insertion capacity | Final textbook seed 0 still has 1448 waiting to insert and 144 running after drain. This is real simulated unmet demand, not removed from the requested denominator. |
| clock / measure point | Counts describe junction crossings, sampled departures start at boundaries, and the fit hour is replayed. Quarter shifts, queues and travel lag remain confounded. E1 tests confirm 3 physical entries per formerly missing/U movement; no detector count inflation. |

`movement_diagnosis.csv` retains every intersection, quarter, movement, source, observed/scheduled/physical count and residual; `movement_summary.csv` aggregates by intersection, fit/check period and movement and includes original / hard-ceiling allocations. Cause labels distinguish demonstrated mechanisms from unresolved combined effects.

U-turn inputs: 272 fit / 345 check vehicles; final scheduled replay: 245 / 245; physical textbook seed-0 crossings: 215 / 214. Source labels stay measured. Coverage is repaired, exact U-turn count matching is not achieved. All source U movements have observed local crossings in every final comparison run. No U-turn is merged with a left.

## Full PM comparison: means of training seeds 0–2

| Demand/network | Plan | Requests | All-requested delay s | Unfinished | Teleports | EB s | WB s |
|---|---|---:|---:|---:|---:|---:|---:|
| Before | textbook | 15154 | 517.24 | 727.67 | 0 | 220.80 | 149.79 |
| Before | existing_vta | 15154 | 545.93 | 1567.33 | 86 | 457.25 | 162.79 |
| Repaired | textbook | 15734 | 783.47 | 1489.33 | 10 | 346.30 | 148.38 |
| Repaired | existing_vta | 15734 | 694.39 | 1741.67 | 135 | 740.79 | 764.03 |

Before/after demand and network differ, so this is not a timing benefit estimate. All-requested delay charges 900 s per unfinished/teleport event; departure waiting can exceed that charge, so fewer observed delays do not imply fewer failures. EB/WB samples contain completed nonteleported corridor traversals only; sample sizes remain in CSV. The plan labels now correctly distinguish textbook rows from VTA-model inputs.

## EB causal probes: seed 0, same repaired demand/network

| Temporary change from existing_vta | EB s | WB s | Unfinished | Teleports |
|---|---:|---:|---:|---:|
| None (comparison) | 757.02 | 804.28 | 1755 | 135 |
| Textbook only at De Anza | 276.44 | 1126.89 | 2058 | 78 |
| Textbook only at Stelling | 856.34 | 172.08 | 1161 | 33 |
| Longer EW pairs, restoring EB split allowance | 804.05 | 1041.30 | 1944 | 156 |
| Half-cycle offset shift at other three signals | 760.28 | 600.07 | 1625 | 114 |

The De Anza projection strongly affects EB; Stelling strongly affects WB. The simple lost 6/8 seconds of EW paired split does not explain or repair EB, and the tested neighbour offset shift barely changes it. This does **not** identify the 180/140/117.9-s cycle mismatch separately from De Anza's ring order, lead/lag and paired-stage projection: the site replacement changes those together. Four probes are explanatory controls, not candidate tuning, and were never saved to production signal plans. The longer pair also lengthens WB service; it is not an exact independent-ring reproduction.

Confidence: high in legal coverage / zero allocation and the De Anza internal-wait trap; moderate in site localization of EB; low in attributing EB specifically to mismatched cycles versus ring projection. VTA's contradictory 180-s input versus 203/170-s ring sums, clearance convention and lagging EB-left behavior remain unresolved. A failure of this projection does not show that the real street fails.

Final suite: **62 tests passed**, including real sparse crossing checks for formerly missing L/T/R and all source U-turns. `tests_full.log`, build/check/timing/comparison/probe logs, original comparison CSVs, final CSVs and run hashes are saved. Raw diagnostic XML remains locally under ignored `reports/runs/fit`; the compact jam snapshot is committed. All traffic comparisons use training seeds 0–2; no final seed, signal optimization, frozen plan or presentation generation was used.

Still blocks a fair new performance test: 50.78% count agreement is below target; unmeasured intermediate turns, mixed-year/missing Mary movements, insertion queues, inferred lane/waiting geometry and unresolved ring/controller conventions. Obtain compatible counts, verify geometry and controller semantics before a new preregistered performance comparison. Textbook, frozen v1/v2/v3, results.csv, eval*.json, PREREGISTRATION and deck/page/video remain unchanged.

## Fit-fix review (seed 0 only; no new holdout evaluation)

The fitter is now SciPy NNLS, not routeSampler. Full-PM requests rise by 580: 490 are two replays of 245 U-turn routes; 90 are the net increase in non-U routes under the changed allocation (45 per fit hour). No duplicate replay was found. The original 328 count rows are unchanged. Measured fit-hour U demand is 272, scheduled 245; measured L/T/R totals are 9710, scheduled 8340 before / 8860 after. Scheduled measured L/T/R GEH<5 improves 70/96 to 82/96; this is fit-period scheduled agreement, not physical calibration. Site/quarter residuals are in `review_scheduled_fit.csv`.

Review found a real round-trip bug: `changeRight="authority"` disappeared from lanes `393485268#0_3` and `593271035_3`. Both restrictions are restored, and `build-net` now preserves lane-change restrictions across netconvert. All De Anza geometric foe masks and all 88 signal link mappings are unchanged from the parent. The four left links move waiting to the stop line; continuation bits and some response priorities change. This avoids the demonstrated internal trap but does not verify real-street storage or conflict handling, and it can favor plans differently.

Before the review repair, old demand on the changed network gives 1455 unfinished versus the archived 752 on the original network; current demand gives 1592. Thus the rise is not simply new real demand: most is caused by the network model change. Repeating the old-demand control after restoring both restrictions still gives 1455 unfinished (1337 waiting, 118 on-road), isolating the stop-line/internal waiting change as the dominant seed-0 cause, not the lane-permission bug. End-state textbook waiting: 1437 outside entry edge 754815172 (southbound North De Anza), 11 outside 593271049#0 (westbound Stevens Creek approach), plus 144 on-road; 57 are on 25085669#0 and 52 on its upstream 754815172. No seed-0 teleport occurred. Counts and locations are in `review_waits.json`; these are simulated capacity/queue effects, not evidence of real-street queues.

Frozen v3 ran once unchanged on the reviewed 8c14bd2 network: all-requested delay 863.87 s, unfinished 1188, teleports 66, EB/WB 384.24/276.59 s. Textbook seed 0: 770.38 s, 1592, 0, 367.68/138.62 s respectively. Delay uses the 900-s unfinished/teleport charge; EB/WB use completed nonteleported traversals. This establishes runtime compatibility, not superiority. `review_seed0.json` records these runs before the two lane restrictions were restored; no second v3 run was made.

The former 62 tests combine genuine sparse physical crossings, provenance/printed-total checks, and implementation checks. The contPos assertion and toy NNLS positive-allocation test do not establish realistic conflicts, field U-turn greens, demand accuracy or congestion fidelity. The new restriction regression protects the two lost permissions. U-turn greens remain model assumptions: SG0 is not a real controller authorization; whole-approach split service is only a stronger CMP inference.

Review validation: **63 tests PASS** (`review_tests_full.log`); an isolated execution of the actual `build-net` repair block through netconvert preserves every original external edge/lane attribute and installs all four stop-line overrides (`review_rebuild_check.log`). Full network regeneration was not run. No counts, textbook/frozen plans, results/evaluation/preregistration or presentation files were changed. New tuning remains blocked by inconsistent counts, incomplete topology, field-unverified waiting/U-turn service and unresolved controller semantics.
