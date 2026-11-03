# Signal Learner: repair and validation plan

Goal: a judge-ready, reproducible simulation study with conservative recommendations and an accurate presentation. Existing held-out results remain historical evidence; they are never retuned, overwritten or rerun.

## Work and checks
- **A1 — Correct software:** repair monitoring gaps, zero baselines and malformed feeds; distinguish selected-plan forecasts from rejected candidates; count unique vehicles separately from signal passages. Regression tests must reproduce each failure and its repair.
- **A2 — Trustworthy recommendations:** reject poor or missing copy-fit evidence; expose underidentified shared-lane turn bounds rather than guessing an exact split; validate inputs; protect individual origin groups and test scoring sensitivity. New policy thresholds are documented engineering screening rules, not field calibration. Exercise the real pipeline in an isolated copy. Keep the learner blind to hidden routes.
- **A3 — Honest evidence:** retain every original research artifact; run reproducible development and separately fixed-protocol synthetic validation checks where inputs permit. Report abstentions and failures. Comparison with actual city timing, representative measured days, local bottleneck diagnosis, engineer acceptance, real export/controller integration and safety validation remain open until supporting evidence exists. They cannot be resolved by changing wording or fabricating data.
- **A4 — Actual presentation:** revise the existing HTML deck and regenerate the PDF. Lead with Stevens Creek and engineer decision support; show the working historical results with clear labels; consolidate limitations near the end; correct turn-passage labels; explain current screening separately from the original experiment. Review every slide at 1280px and 375px, navigation, notes and video, with no application errors. Consolidate team planning here and the operating instructions in DEMO.md.

## Boundaries
Use existing dependencies and preserve the visual design. Do not connect to signals, claim field benefits, invent data or endorse safety. VTA approved the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*; the raw data and repo stay private. Changes go through review on GitHub; no automatic merge or public deployment.

## External evidence still required
The ledger below maps all 30 findings to a repair, a demonstrated scope limit, or a specific unmet evidence requirement. A code fix does not close a field-validation requirement. Prithvi can own the human rehearsal, organizer/submission check and arranging engineer feedback with the team; Saarth reviews the technical and factual changes. These are proposed roles, not claims that the work has happened.

## New synthetic validation protocol

Before any new learner run, `tools.validate_learner` records source and input hashes in `reports/repair_validation/protocol.json`. It uses two manually pinned, previously untested OSM road models: two Bubb Road signals (65566258, 65645389) and two South Stelling signal groups (13044640725/13044640726, 65566742). These do not share signals with the original study. Ten synthetic observation profiles use per-origin factors seeded 5000–5009 with driver seeds 1000–1009. Three fixed unseen profiles use factors seeded 6000–6002 and paired driver seeds 7000–7009. They are not measured traffic days.

This is a local pre-execution hash freeze, not public or independently registered preregistration. Scientific source and input hashes are checked again before results are finalized.

Each strategy has a budget of 150 trials: TPE versus seeded random search, both on the same observed copies with search seeds 0–2 and confirmation seeds 10–19. A failed quality screen spends zero trials and keeps old timing. Report every abstention and all profile results; never infer superiority from an unrun search. Evaluation includes unchanged timing and fresh textbook retiming using the true synthetic profile as a descriptive comparator. Penalties 0/900/1800, unfinished trips, teleports and every origin group are retained. Rollback controls require bad-plan detection >=80%, harmless-change detection <=20%, and improvement over holding the bad plan; also report harm versus doing nothing and time before rollback. These thresholds are fixed before outcomes. Interrupted/completed outputs refuse overwrite; failures remain evidence.

Development copy screens require >=3 complete observation replicates, >=85% of count comparisons with GEH<5, <=15% aggregate count error, <=10 occupancy-point mean error, and <=20% unresolved turn-share width on any approach/quarter. These are conservative engineering screening rules, not validated field acceptance standards. Copies at the mean and +/-one observed count SD are stress cases, not confidence bounds. Confirmation permits <=5% mean origin-group degradation in each copy, no extra unfinished trips, existing teleport/side constraints, and no aggregate regression with 0/1800 penalties. A validated copy is still not proof of unobserved arrival demand.

### Executed outcome

The fixed run completed; validation did **not** pass. [Evidence and results](reports/repair_validation/README.md): Bubb preparation failed on unsupported boundary routing. Stelling's count comparisons fit, but occupancy error (30.004 points) and unresolved turn width (1.0) failed screening; TPE and random each ran zero optimization trials and retained old timing. Across three fixed profiles, rollback triggered in 0/30 degraded-plan runs and 0/30 harmless controls. The degraded plan actually worsened the paired score in 18 runs; all 18 were missed. No detection latency can be assigned to a missed trigger. Each profile failed the combined rollback criteria. No optimizer superiority, new recommendation benefit or reliable rollback was demonstrated. Source/input hashes and all new run evidence are preserved; no threshold was retuned afterward.

## Thirty-finding repair ledger

“External” means evidence is missing; it is not a completed repair. “Scoped” means the unsupported claim was removed or narrowed; the underlying real-world capability remains unproven.

| # | Finding | Repair or evidence still required |
|---|---|---|
| 1 | Is timing the real bottleneck? | External: measure queue extent/duration, arrivals, throughput and downstream blocking alongside the current plan. |
| 2 | Stevens Creek story versus Wolfe result | Scoped: deck distinguishes local motivation, development roads and the independent synthetic Wolfe result. No Glenbrook benefit claimed. |
| 3 | Actual city timing comparator | External: obtain and validate the current controller plan; constructed timing is labeled throughout. |
| 4 | Existing competitors | Scoped: no novelty, lower-cost or better-performance claim; transparent workflow is demonstrated, advantage needs comparison. |
| 5 | Real input availability | External: complete the detector/log inventory below; input completeness and health are enforced in development. |
| 6 | Engineer usefulness/cost | External: a real engineer reviews the card and records effort, corrections and accept/reject reasons. |
| 7 | Only two independent roads | New checks exposed Bubb's unsupported geometry; Stelling prepared but abstained. No new recommendation benefit or citywide generalization was demonstrated. |
| 8 | Seeds mistaken for traffic days | Fixed: profile and driver seeds are separate; new observation demand varies; deck never claims measured days. |
| 9 | Field calibration | External: validate contemporary queues and route travel times on independent measurements, not counts alone. |
| 10 | Weak comparators | Equal-budget TPE/random comparison is wired but both spent zero trials after screening; no optimizer advantage was tested. Fresh textbook retiming is descriptive. Actual engineer/city comparisons remain external. |
| 11 | Arbitrary unfinished penalty | Fixed screening: retain 0/900/1800 outcomes, block additional unfinished trips and sensitivity regressions; the primary remains a labeled score. |
| 12 | p-values versus model uncertainty | Scoped: statistical outcomes only apply to specified simulated inputs; stress cases are not field confidence bounds. |
| 13 | Shared-lane turn ambiguity | Fixed screening: report per-turn lower/upper bounds and refuse excessive ambiguity. Exact splits still require additional observations. |
| 14 | Throughput versus demand | Scoped/external: stop-line counts are labeled; unserved demand requires upstream/queue evidence unavailable here. |
| 15 | Poor copy allowed into search | Fixed: fit/coverage/hash gates block search and suppress forecasts when evidence is missing or stale. |
| 16 | Good count fit hides wrong traffic | Fixed screening plus explicit limitation: turn bounds, occupancy checks and stress cases; field demand identification remains unproven. |
| 17 | One overconfident copy | Fixed bounded check: mean/low/high count-spread copies must all pass; not claimed to span all possible traffic. |
| 18 | Trips versus passages | Fixed: future metrics count unique cohort vehicles separately; deck and generated facts label historic passage totals correctly. |
| 19 | Harm hidden by averages | Fixed screening: every origin group is checked, and per-origin results are retained; no promise that every driver benefits. |
| 20 | Undo false alarms | Input defects fixed; new synthetic controls exposed missed harmful changes. No thresholds were tuned after these outcomes. The rule remains experimental; reliability is unresolved. |
| 21 | Late rollback and residual harm | New protocol retains paired harm and trigger timing; missed triggers are disclosed rather than assigned a fake latency. Rollback is not a safety mechanism. |
| 22 | Gaps treated as consecutive | Fixed with regression tests: invalid/missing windows reset streak and rolling history. |
| 23 | Zero-count crash | Fixed with regression tests and explicit insufficient-data states. |
| 24 | Rejected forecast shown as selected | Fixed in card JSON, Markdown and facts export, including no-search unavailable forecasts. Historical cards remain archived evidence. |
| 25 | No real operating adapter | External: obtain a real export sample and mapping before implementing or claiming compatibility. No real control endpoint exists. |
| 26 | Arbitrary-road claim | Scoped: onboarding requires pinned/map-checked signals; new geometry tests do not establish arbitrary-road support. |
| 27 | Safety and other modes | External: engineering review of real clearances, pedestrian/bicycle/transit behavior and controller semantics; no safety claim. |
| 28 | Tests mistaken for validity | Fixed reporting: regression, synthetic validation and field readiness are reported separately. |
| 29 | Recorded demo over-read | Fixed: one recording, non-inserted vehicles, forecast/test/post-hoc differences are explained in slides and notes. |
| 30 | Deck and rehearsal | HTML/PDF revised and independently reviewed. Student rehearsal and actual presentation-laptop check remain human tasks. |

## Field and user-validation worksheet

Before a field-performance claim, record the source/date/owner for: current geometry and controller plans; lane/detector mapping; timestamp/timezone and five-minute lane counts; upstream occupancy and detector health; missing/duplicate interval policy; representative demand, queue and route travel-time measurements from the same period; pedestrian/bicycle/transit requirements; and data-use permission. The field-export adapter is not built because no verified export sample is available.

Ask a real traffic engineer: which card entries are usable, which need correction, what input is missing, what would prevent approval, and how long review takes. Record their actual answers and any conflicts with current operations. No interview, endorsement, savings or adoption commitment has been obtained in this repair work. Prithvi can coordinate that review with the team, verify organizer requirements, and lead the human rehearsal without being assigned unapproved simulator changes.
