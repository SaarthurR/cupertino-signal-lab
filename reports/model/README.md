# 2024 model capacity evidence

Training seeds 0–2 only; every SUMO process nice 15, at most two concurrent. No signal optimization or held-out performance evaluation. Original network/count baseline: cc7617a.

Retained model choice: De Anza E/W lefts wait at the stop line, N/S lefts retain SUMO internal waiting. Stelling N/S lefts wait at the stop line to prevent the newly exposed seed-2 internal trap. Waiting points are not surveyed geometry. U-turn green remains an assumption; source SG0 is not controller authorization.

The 100.84 m, four-lane SB entry feeds a 109.28 m six-lane approach: right lane 0, through 1–4, left/U lane 5. Entry lane 3 feeds both through lane 4 and left lane 5. The existing changeLeft restriction on approach lane 3 prevents moving into lane 4 after the entry fork. With a full left pocket, the shared feeder reduces through utilization. No permission or external geometry was changed.

One-second detectors and unchanged textbook TLS show a median 2 s within-green discharge headway (about 1800 veh/h/lane; a conditional model discharge estimate, not measured field saturation). Original through green is 613 s/h; chosen 680 s/h. Four lanes at 1800 × 680/3600 give about 1360 veh/h before startup/blocking losses, below the supplied peak reference ~1537 through plus ~672 left. Actual fit-hour SB T/L crossings are 917/203 before and 1120/364 after; fit counts are 1574/541. This frozen textbook model still lacks service capacity.

The cached OSM way 25085669 says six lanes, `reverse;left|left||||`, and lane-change restrictions; it supports two left lanes at the existing mapped lane-expansion location, not an invented longer pocket. A two-left/three-through connection trial was worse under unchanged timing (see probes); rejected. Real lane storage and controller semantics remain unverified.

## Score labels

Same 96 measured L/T/R rows per period: scheduled fit 82, physical fit 64 before → 61 after (seed 0); scheduled replay/check 49, physical check 43 → 48. These are different clock periods and must not be presented as 82 scheduled versus 43 physical on identical rows. Seeds 0/1/2 physical fit: 61/62/62; physical check: 48/45/45. Including U, seed-0 check is 75/128. No source number or movement changed.

Textbook unfinished 701/884/830 of 15734, teleports 0/0/0; every source movement crosses under both plans on all three seeds. Overall good-enough check FAIL: count gain is modest and two unfinished counts exceed a strict 800 (mean 805). This is a less jammed hackathon model, not validated calibration.

## Options tried

Each row is a training diagnostic; compare the complete row, not just one metric. Exact connection overrides/options and hashes are in probes.json. `ns_default_lc2013` is the historical probe name for `--lanechange.overtake-right true`, not a change of lane-change model.

| Trial | Seed | Unfinished | Teleports | Physical fit LTR/96 | Physical check LTR/96 |
|---|---:|---:|---:|---:|---:|
| current | 0 | 1592 | 0 | 64 | 43 |
| sb_default | 0 | 750 | 1 | 63 | 48 |
| sb_wait5 | 0 | 1430 | 0 | 62 | 39 |
| sb_wait10 | 0 | 2736 | 261 | 61 | 25 |
| eb_only | 0 | 876 | 1 | 67 | 46 |
| sb_default_keepclear | 0 | 750 | 1 | 63 | 48 |
| dual_left | 0 | 1659 | 0 | 63 | 37 |
| sb_default_vis5 | 0 | 850 | 65 | 44 | 37 |
| ns_default | 0 | 692 | 0 | 65 | 45 |
| all_keepclear_false | 0 | 1592 | 0 | 64 | 43 |
| dual_default | 0 | 1900 | 0 | 65 | 42 |
| dual_both_default | 0 | 1286 | 0 | 60 | 42 |
| ignore_blocker30 | 0 | 1118 | 4 | 69 | 46 |
| ns_default_lc2013 | 0 | 548 | 0 | 67 | 41 |
| ns_default_seed1 | 1 | 686 | 1 | 63 | 44 |
| ns_default_seed2 | 2 | 799 | 109 | 66 | 34 |
| ns_default_stelling_ew0_seed2 | 2 | 719 | 14 | 61 | 40 |
| ns_default_stelling_all0_seed2 | 2 | 758 | 4 | 61 | 44 |
| sb_default_stelling_all0_seed2 | 2 | 627 | 10 | 56 | 42 |
| ns_default_stelling_all0_overtake_seed0 | 0 | 853 | 3 | 58 | 39 |
| ns_default_stelling_ns0_seed2 | 2 | 830 | 0 | 62 | 45 |
| ns_default_stelling_ns0_seed0 | 0 | 701 | 0 | 61 | 48 |
| ns_default_stelling_ns0_passright_seed0 | 0 | 878 | 0 | 63 | 42 |
| ns_default_stelling_ns0_passright_seed2 | 2 | 718 | 1 | 65 | 44 |
| chosen_seed1 | 1 | 884 | 0 | 62 | 45 |

## Reproduction and evidence

Environment: `SUMO_HOME="$PWD/.venv/lib/python3.12/site-packages/sumo" PYTHONPATH=src`; use `.venv/bin/python`. Required commands were `nice -n 15 .venv/bin/python -m signal_lab build-demand`, `... -m signal_lab check-demand`, `... -m signal_lab.vta_timing`, `... -m signal_lab.vta_compare`, and `... -m unittest discover -s tests -v`. Their complete logs are in this directory; comparison per-run logs remain under reports/fit.

Probes use the cc7617a network (`git show cc7617a:sim/corridor.net.xml`) as netconvert input, the connections/options in probes.json, current unchanged routes and textbook timing, seed as listed, begin 58500/end 68400, 300 s teleport timeout. All original external lane-change restrictions are restored after netconvert. Turn detectors use demand.turn_detectors; requested cohort is 59400–66600 with 1800 s drain. Raw probe XML, connection files and the local harness remain under ignored reports/runs/model; compact numbers and selected physical rows are committed here.

Production was regenerated by executing the actual build_net repair block (not a full OSM rebuild); unchanged XML blocks were retained verbatim after checking parsed semantic equality. invariants.log verifies all external edge/lane attributes/params, all 88 TLS link mappings, source counts and protected files. sb_discharge.csv derives conditional within-green headways from one-second SB E1 detectors, at least 5 seconds into uninterrupted protected green; raw TLS/E1 XML remains locally in original_discharge and chosen_discharge.

Full suite: 63 tests PASS. Frozen textbook/v1/v2/v3, results.csv, eval*.json, PREREGISTRATION and presentation assets were not changed. Existing_vta remains an inferred projection with unresolved input contradictions; completed nonteleported EB/WB times are survivor-biased and all-requested delay charges 900 s per unfinished/teleport event. No performance conclusion or new optimization is authorized by these results.
