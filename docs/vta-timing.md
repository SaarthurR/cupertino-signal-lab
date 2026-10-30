# Vistro input comparison: existing_vta

**Timing inputs in VTA's 2024 CMP model, not a confirmed city controller sheet.**
The name `existing_vta` identifies a conservative SUMO projection of those inputs, not a reproduction of a field controller.

The two five-page image reports were emailed by VTA on October 29, 2026; generated with PTV Vistro 2024 (SP 0-6), TJKM, Base Scenario, HCM 7th Edition, 15-minute analysis. Every page was rendered with `uv run --no-project --with pymupdf==1.26.7` and read visually. Page 1 gives approach/column order, page 3 timing inputs, page 4 calculated cycles/lane-group outputs, page 5 movement outputs and ring sequence. CSV page numbers are one-based. Raw PDFs remain in the shared, ignored `data/raw` directory; they were not modified.

| Source file under data/raw/vta/2024-cmp | SHA-256 |
| --- | --- |
| 211_De_Stevens_PM_Vistro Analysis.pdf | 97af2fbf40403eadc643d8241a82692c4e226810266785ee2193336584e49982 |
| 217_Stelling_Stevens_PM_Vistro Analysis.pdf | 000ee662d1527f20f601b0a81edf723053d11b92d9e45f7be2c8a41c21485c66 |

`vta_timing_2024.csv` retains 14 nonzero signal groups exactly as printed. Movement directions describe travel (NB means originating on the south approach), unlike `demand.movement_map`'s originating-leg compass. Stelling SG3/4 occupy the through columns but their control type is **Split**: they serve the entire NB/SB approach respectively. SG2 is **EB**, SG6 **WB** at both sites. U-turn input slots have SG0; no independent U-turn timing is invented. The result CSV preserves all 16 movement columns per site, including U-turns, and uses page 5 movement delays rather than the sometimes different page 4 lane-group delays.

The demand model now maps all four U-turns separately at each source site: 116 De Anza + 156 Stelling measured fit-hour inputs (617 across both recorded hours), never folded into lefts. Stelling NB/SB split states now include their U-turn links. Mainline U-turns retain the existing left-stage service; SG0 is not treated as an independent source phase. Mary U-turns remain unmodeled and disclosed. See `reports/fit/README.md` for count allocation, network corrections and runtime evidence.

## Source sanity, without changing printed values

- De Anza: input cycle **180 s**, offset **120 s**, Lead Green - Beginning of First Green. Ring 1 is 1→2 | 3→4: **203 s**; ring 2 is 6→5 | 7→8: **170 s**. Page 4 independently reports a **203 s calculated cycle**. These cannot honestly pass an assertion that each ring sums to 180 s.
- Stelling: input and calculated cycle **140 s**, offset **57 s**, same reference. Ring 1 is 1→2 | 3→4 = **140 s**; ring 2 is 5→6 = **65 s**, inactive during the **75 s** split side-approach portion. Its active plus inactive time is 140 s.
- All 14 printed maximum greens equal their printed splits; adding amber/all-red exceeds the split. De Anza SG6 also has walk+pedestrian clearance **42 s**, above its printed **40 s** maximum green. The CSV does not silently subtract clearances or change cycles. `source_issues()` exposes these discrepancies; the fast tests pin them explicitly.

## Mapping and deliberate projection

Reuse textbook green-state templates and the baseline's built-in actuated forward-skip/recall-rest construction. Source ring-1 order starts at SG1's lead green, so phase 0 and SUMO offset share the printed reference. This is nominal alignment; gap-outs/skips and the ring approximation prevent a promise of actual lead onset at every background cycle. Protected left templates suppress generated permissive left service. At Stelling, the two side templates are replaced with unopposed NB-all and SB-all states derived from actual SUMO connections. No pedestrian simulation is added; U-turns use left-stage or whole-approach service.

| Site | New green phase | Textbook template phase | Source SG(s) and printed split(s), s | Applied split / green, s | Frozen v3 template nominal split / green, s |
| --- | ---: | ---: | --- | --- | --- |
| 211 | 0 | 7 | WB L 1=50; EB L 5=23 (lag) | 23 / 18 | 18.665 / 12.165 |
| 211 | 3 | 5 | EB T/R 2=46; WB T/R 6=40 | 40 / 34.4 | 23.537 / 16.537 |
| 211 | 6 | 2 | NB L 3=32; SB L 7=40 | 32 / 27 | 57.289 / 50.789 |
| 211 | 9 | 0 | NB T/R 8=67; SB T/R 4=75 | 67 / 61.2 | 37.621 / 30.721 |
| 217 | 0 | 2 | WB L 1=25; EB L 5=33 | 25 / 20.5 | 23.054 / 17.154 |
| 217 | 3 | 0 | EB T/R 2=40; WB T/R 6=32 | 32 / 27 | 49.122 / 43.322 |
| 217 | 6 | 5 | NB all 3=38 | 38 / 32.9 | 41.119 / 34.619 (NS through) |
| 217 | 9 | 7 | SB all 4=37 | 37 / 31.9 | 20.444 / 14.544 (NS left) |

The movement-to-group correspondence is high confidence from pages 1/3/5 and checked against network connections. **Temporal fidelity is limited:** paired stages use the shorter source split, the larger amber and all-red, and green = applied split − those clearances. The applied schedule has 18 s (De Anza) / 8 s (Stelling) background slack. Independent ring overlaps, unequal splits and De Anza's EB-left lag are not reproduced. Stelling's NB/SB templates differ from v3, so those two rows are structural comparisons, not matching movements. Maximum-recall groups select the rest stage (De Anza NS through, Stelling EW through); source minimum/pedestrian recalls are all No. Existing global gap logic uses the shortest reported extension per site (2.5 / 2 s), not phase-specific source extensions. Walk/clearance are transcribed but not simulated; this plan is unsuitable for pedestrian or controller-safety validation.

Bandley, Saich and Mary retain **all textbook timing attributes**, except the new plan's program ID. Their 117.9 s cycle is retained because the source sites do not share a cycle; no 180 s corridor assumption is introduced. Textbook and all frozen v1/v2/v3 files are untouched.

## Assumed versus reported inputs

Textbook common cycle is **117.9 s**; frozen v3 is **137.1122804334809 s**. The 180 s De Anza input lies outside the optimizer's 80–150 s search range; Stelling's 140 s lies inside. The assumption that these sites share one cycle is wrong **for these Vistro inputs**. Stelling's split approaches also contradict the generated simultaneous NS-through/NS-left arrangement. These findings say nothing definitive about present city-controller settings.

Printed offsets differ by **63 s** (De Anza minus Stelling); because 180 ≠ 140, this is not a fixed progression offset on one common cycle. Textbook phase-0 offsets are 8.8 / 29.91 s and v3 phase-0 offsets 11.855278790176616 / 131.61834948789732 s; they reference different first stages, so subtracting them from source lead-green offsets would be misleading. No optimization or frozen plan was changed to accommodate the reports.

## Original deferred runtime checklist (superseded by reports/fit)

The checklist below records the earlier stop. Current home-run outputs and diagnostic limitations are in `reports/fit/README.md`, `reports/vta_*` and `reports/fit/tests_full.log`. The original timing work ran five fast tests; the merged-branch review passed 31 focused counts/timing/dashboard/demand checks with external process launches blocked, plus diff checks. No simulation or routeSampler was started during the review. An earlier 101-second empty static offset probe established SUMO's offset convention; it was not a comparison run.

When Saarth is home, from this merged worktree (battery at least 25%, one simulation at a time):

```sh
cd /Users/saarthranka/Documents/school/ai-club-hackathon-vta2024
export SUMO_HOME="$(.venv/bin/python -c 'import sumo; print(sumo.__path__[0])')"
pmset -g batt
PYTHONPATH=src nice -n 15 .venv/bin/python -m unittest discover -s tests -p test_vta_counts.py -v
PYTHONPATH=src nice -n 15 .venv/bin/python -m unittest discover -s tests -p test_vta_timing.py -v
PYTHONPATH=src nice -n 15 .venv/bin/python -m signal_lab build-demand
PYTHONPATH=src nice -n 15 .venv/bin/python -m signal_lab check-demand
PYTHONPATH=src nice -n 15 .venv/bin/python -m signal_lab.vta_timing
PYTHONPATH=src nice -n 15 .venv/bin/python -m signal_lab.vta_compare
PYTHONPATH=src nice -n 15 .venv/bin/python -m unittest discover -s tests -v
```

The comparison command **starts SUMO** (the full test suite also starts SUMO): serial full PM only, seeds 0–2, this worktree's PM routes, 900 s warmup and 1800 s drain. It refuses battery below 25% or an already-running SUMO process; the shared launcher applies nice 15. It writes `reports/vta_timing_comparison.csv`, `reports/vta_movement_comparison.csv`, `reports/vta_timing_run.json`, and per-run logs under `reports/fit`. No optimization or holdout evaluation is called. Review source contradictions/phase states before treating any result as meaningful. Both CSVs and the JSON identify mixed demand: 2024 De Anza/Stelling L/T/R/U, Bandley/Saich estimates based on those counts, and 2018 Mary estimates. JSON hashes include routes, counts and source metadata. Do not regenerate dashboard, deck or video: their generators combine live demand inputs with frozen 2018 evaluation evidence and require a separate migration.

All-requested delay reuses the preregistered 900 s unfinished/teleport charge; the output also retains 0/1800 s sensitivities, side all-requested delay, completed EB/WB travel sample sizes, unfinished and teleport counts. Movement comparison uses completed local approach+departure crossing time minus external-edge freeflow, excluding teleported vehicles. It includes internal-junction traversal in the excess and is **not HCM control delay**; neither it nor completed-trip samples count blocked/unfinished crossings as observed delay. Vistro is a separate 15-minute 2024 model versus full-PM mixed-year demand SUMO; numerical agreement would not establish validation. Report all results as a three-training-seed look, without significance or field-benefit claims.
