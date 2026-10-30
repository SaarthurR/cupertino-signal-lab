# Count sources — updated October 30, 2026

**De Anza and Stelling now use real October 9, 2024 IDAX turn counts supplied by VTA on October 29, 2026 (Kia Sharifi, P.E., via Larissa Sanderfer). Mary remains 2018; Bandley/Saich remain estimates.** These historical counts do not measure present traffic. The earlier web search found only the public VTA sample; the emailed full sheets supersede the 2018 Vallco fallback at the two CMP sites. Previous values remain in git history (before this update: `9290ecc`).

## Selected sources

| Intersection | Actual count date | Source, 1-based page | Use |
|---|---|---|---|
| De Anza / Stevens Creek (211) | 2024-10-09 | `data/raw/vta/2024-cmp/211_De_Stevens_PM.pdf`, p1 | Eight measured quarters, 16:30–18:30 |
| Stelling / Stevens Creek (217) | 2024-10-09 | `data/raw/vta/2024-cmp/217_Stelling_Stevens_PM.pdf`, p1 | Eight measured quarters, 16:30–18:30 |
| Mary / Campus Dr / Stevens Creek | 2018-04-25 | Westport p28 | Measured 17:15–18:15 hourly observations in tmc_hourly.csv; estimated quarters in tmc.csv |
| Bandley / Stevens Creek | None located | Both 2024 sheets above | Estimated from neighbours; no survey date |
| Saich / Stevens Creek | None located | Both 2024 sheets above | Estimated from neighbours; no survey date |

The emailed PDFs are gitignored in the shared raw directory. `tmc_sources.csv` records their local source locators (no public URL was supplied), SHA256, page, count date, year and method. Estimated-node year 2024 describes the anchor vintage, not a survey at that node. Mary's quarter source remains estimated; its original hourly source remains measured.

Mary source: [Westport Appendix H, official CEQAnet attachment](https://files.ceqanet.lci.ca.gov/253213-3/attachment/3CrHQTT3Zg88EHdiWjlstzTVL-KKLpZvvZFxozGEyHL8gYDB-jXqEsYbOb71LBc1SMI-lwBxTq6TV4Si0), NDS ID 18-08195-001, p28; local `data/raw/city/westport-appendix-h.pdf`, SHA256 `3c4798f23eaa0be7aa130c693ff88352c06ca8014163882c1c368df919d0e59c`. The November 2018 memo date is not the survey date. Prior De Anza/Stelling source: [Vallco Appendix H](https://www.cupertino.gov/files/assets/city/v/1/departments/documents/community-development/planning/major-projects/the-rise/vallco-historical-project-information/vallco-specific-plan/ceqa/appendix-h-transportation.pdf), pp602–603 / 554–555, January 10 / 17, 2018.

## Transcription and visual cross-check

Both scrambled-text PDFs were rendered with PyMuPDF and page 1 read by eye. `vta_counts_2024.csv` transcribes all numeric count-table cells: eight UT/LT/TH/RT quarters, 15-minute/rolling totals, Count Total, peak All/HV/HV%, heavy totals, bicycles and pedestrian crossings, including printed totals and peak rows. `period` distinguishes intervals from summary rows; `category` distinguishes counts; percent values use percentage points. `approach` is the originating compass leg (N = southbound, E = westbound); pedestrian approach means the crossing leg. `ALL` marks printed aggregate cells. Bicycles and pedestrians are excluded from vehicle totals; heavy vehicles are already included. No OCR-imputed count is used.

`tests/test_vta_counts.py` sums every quarter across movements, every column across quarters, and every peak-hour column; checks all printed rolling hours; and matches each peak movement against separately recorded Vistro Analysis p2 Base Volume Input (`period=vistro_peak`). All checks pass. **This is an agent visual check, not independent human sign-off.**

| Site | Sheet peak hour | All vehicles (incl UT) | UT | Modelled L/T/R | Heavy | Bikes | Ped crossings |
|---|---|---:|---:|---:|---:|---:|---:|
| De Anza 211 | 17:15–18:15 | 6271 | 151 | 6120 | 55 | 7 | 125 |
| Stelling 217 | 17:00–18:00 | 4393 | 171 | 4222 | 45 | 10 | 179 |

The production schema is unchanged. De Anza/Stelling U-turn rows are now included separately with measured source labels; Mary U-turns remain unmodeled. No U-turn is folded into left/through counts. Quarter-hour heavy counts are available by approach, but not by movement, so `heavy` stays blank in tmc.csv (unknown, not zero). Crossing-leg pedestrians are stored once on the T row. The model uses homogeneous passenger vehicles and does not simulate bicycles or pedestrians.

Mary's hourly R/T/L/U by leg remain N=138/78/123/0, E=165/892/125/13, S=75/20/126/0, W=113/1680/177/48; sum 3773, including 61 U-turns. Only N R/L, E R/T, W T exist in the current OSM model: **775 observed vehicles/hour cannot be represented**. Rounding retained movements to quarters adds 2 vehicles/hour. No network changes were made.

For a common **17:15–18:15** clock window, the 2024 Stelling westbound exit toward Mary is E-through 689 + N-right 157 + S-left 197 = **1043 veh/h**; Mary's 2018 east-leg L/T/R arrivals total **1182**, a **139 veh/h (13.3%)** excess at Mary. Mary's full-sheet eastbound exit is W-through 1680 + N-left 123 + S-right 75 = **1878**, versus Stelling's west-leg L/T/R arrivals **1526**: **352 veh/h (23.1%)** excess at Mary. With only modelled Mary movements the eastbound exit is 1803, still **277 veh/h (18.2%)** higher. These are mixed-year boundary mismatches, not proof of a conservation error: local access, the count years and missing topology differ. Through-only discrepancies are Mary E-through 892 vs Stelling 689 (+203), and Mary W-through 1680 vs Stelling 937 (+743). Mary is left labelled and unchanged.

## Estimation and fit/holdout separation

- Bandley and Saich: mainline through volume linearly interpolated by longitude between the replaced 2024 measured De Anza and Stelling through volumes for the same quarter; each other legal movement = 5 vehicles/15 minutes (20 vehicles/hour per movement, 40 vehicles/hour from each side street). These side turns are arbitrary low-demand placeholders, not observed turns or an OD survey. All such rows are estimated. Newer segment ADT suggests side demand may be understated but cannot establish PM turns. Obtain current directional turning-movement counts before claiming calibration or field applicability.
- Mary: retained hourly movement / 4, rounded to integer vehicles; uniform extension across 16:30–18:30. Both temporal disaggregation and extension are estimates. No hourly value is called a measured quarter.
- PM demand construction reads **only 16:30–17:30** rows, samples routes once (seed 0), then repeats those departures/routes one hour later. The first quarter is copied 900 seconds earlier for warmup. No 17:30–18:30 observed counts are used to generate routes. An adversarial test changes every holdout value by 100,000 and verifies byte-identical generated PM/night routes.
- Night: 10% of fit-hour mainline-origin movement totals; 2 vehicles/hour for each side-origin turn; integer sampling. Source estimated throughout.
- GEH uses only measured De Anza/Stelling **17:30–18:30** rows, converted from quarter-hour counts to hourly rates. Estimated nodes and Mary's disaggregated quarters are excluded.

## Newer City segment ADT (not turning counts)

The [City traffic-data page](https://www.cupertino.gov/Your-City/Departments/Public-Works/Transportation-Mobility/Traffic-and-Collision-Data) links the [Traffic Flow Map](https://experience.arcgis.com/experience/aedd536ab2e14a348650ceed761db18b). Its [official TrafficCount2025 layer](https://services2.arcgis.com/WsCmJmL1F5wsSOiu/arcgis/rest/services/TrafficCount2025/FeatureServer/0), checked October 28, 2026, includes newer average daily traffic (ADT) segment counts:

| Segment adjacent to Stevens Creek | ADT vehicles/day | Layer date field |
|---|---:|---|
| Mary, Meteor–Stevens Creek | 2,605 | 2023 |
| Saich, Alves–Stevens Creek | 2,576 | 2023 |
| Bandley, Alves–Stevens Creek | 4,520 | 2024–2026 bucket, no single year specified |
| De Anza, Lazaneo–Stevens Creek (north) | 31,080 | 2023 |
| De Anza, Stevens Creek–Bollinger (south) | 30,140 / 32,720 / 34,500 | 2023; duplicate records with identical segment labels |

Do not sum or arbitrarily select the duplicate De Anza south records. Stelling-adjacent records remain in the 2015–2017 bucket; no newer populated count field was found there. ADT has neither PM direction nor turn shares: it cannot replace TMCs or validate the low Bandley/Saich side-turn placeholders. Those ADT records do not change turning counts. The separate emailed 2024 TMCs above are the basis of this update.

## Earlier web-search leads (before the emailed sheets)

| Lead | Finding |
|---|---|
| [VTA 2024 CMP sample](https://www.vta.org/sites/default/files/2025-08/2024%20CMP%20Monitoring%20Appendices_Sample.pdf), [official document listing](https://www.vta.org/projects/documents?project=1116) | Public 11-page “Sample Only” (superseded by the emailed corridor sheets above); raw sheets are Campbell/Bascom and Hamilton/Winchester, not sites 211/217. The [127-page main report](https://www.vta.org/sites/default/files/2026-02/2024_VTA_CMP_Monitoring_Report.pdf) has LOS letters, not these raw turns. Two likely full-appendix URLs returned 404. |
| The Rise / later Vallco modifications | Located traffic TIA has January 2018 observations; later plans/modifications do not establish newer traffic collection. |
| Westport Appendix H, pp.49–54 | Actual May 22, 2019 quarter-hour counts, but at SR-85 ramps / De Anza College driveway, a different intersection. Excluded. |
| [Westport 2020 memo](https://cupertino.legistar.com/View.ashx?GUID=5C387078-F558-45BD-BCF3-0F44802DEDAF&ID=9668484&M=F), [2021 memo](https://cupertino.legistar.com/View.ashx?GUID=AEFCB492-9E5F-494D-8379-739DE2F77D43&ID=9776661&M=F) | Trip-generation comparisons, not new count sheets. |
| [Marina Plaza December 2022 addendum](https://files.ceqanet.lci.ca.gov/196280-3/attachment/wYmj4b6i6oUJIsJdMMAccS-C5Qa0myMJ7ZW01U0oZGpdu0UZ_-mcnFglNj7fOXdUeivZ9RG5ciZmmfQp0) | No turning-movement count sheets located. |
| [Stevens Creek Corridor Vision Study, December 2024](https://www.cupertino.gov/files/assets/city/v/1/departments/documents/public-works/transportation/transportation-amp-mobility/stevens-creek-vision-study/stevens-creek-blvd-vision-study-report.pdf) | Corridor planning, collisions, parking/transit context; no qualifying intersection turn sheets. |
| [Cupertino 2026 retiming RFP PW-2026-853](https://apps.cupertino.org/details/853) | Scope requires future counts at these signals. Procurement scope is not count results. |
| VTA BRT / agency / County / Caltrans searches | No qualifying raw sheets at the five target nodes located; Caltrans state-highway counts are not city-intersection TMCs. |
| [De Anza College 2008 traffic appendix](https://facilities.fhda.edu/_downloads/DA%20-%20EIR%20Addendum%20With%20Traffic%202008.pdf) | Mary p.59 and Bandley p.61 sheets dated May 15, 2007; older than selected basis. |

## Network and measurement limits

Using `--osm.turn-lanes` had suppressed all four Stelling right turns because incomplete OSM lane tags were interpreted as movement exclusions. Removing that option lets SUMO infer connections geometrically while retaining lane counts and the five TLS ids. All 24 L/T/R movement types, plus eight separately modeled source-site U-turns, map to legal connections. This is inferred connectivity, not field validation, and changes turn-lane allocation at other nodes too; inspect before treating it as engineering geometry.

M3 uses SUMO induction loops at the **start of each internal turning lane**, summing `nVehEntered` by movement/quarter. These count physical entries; a teleported jump is not inferred from a planned route. A small real SUMO run verifies three vehicles produce three detector entries. See [SUMO E1 documentation](https://sumo.dlr.de/docs/Simulation/Output/Induction_Loops_Detectors_%28E1%29.html). Summary `teleports` is cumulative; a focused regression verifies it is read once from the final step.

The October 30 data rebuild used the retained textbook coordinated-actuated baseline without rewriting timing. Completed before the away-from-home stop: GEH < 5 fell from **41/96 (42.71%)** on the earlier inputs to **37/96 (38.54%)**; target 85% remains unmet. PM seed 0: **0 teleports, 105 running + 647 waiting to insert = 752 unfinished** after the 30-minute drain; **118.421 s** completed-trip time loss, 13,683 completed non-warmup departures. Build-demand also completed night with 415 inserted, zero running/waiting/teleports. No subsequent SUMO run is authorized while away.

At the earlier away-stop, the full test suite had not run; current home-run checks are recorded below and in `reports/fit/tests_full.log`. Existing M4/optimization/evaluation reports, results.csv, dashboard, deck, video and their archived race evidence remain **2018-demand results** and require a separate later rerun. This update does not establish calibration, delay gains or current-city benefit.

## Home fit correction

See `reports/fit/README.md` and `reports/fit/movement_diagnosis.csv` for current results. All original count values and source labels are preserved; 64 measured U-turn quarters were added from the retained transcription. The symmetric count fit replaces hard count ceilings because mixed-year and estimated corridor observations are inconsistent. GEH now reports all 128 measured quarters, with the shared 96 L/T/R quarters stated separately.

Restoring De Anza EB left exposed a junction gridlock hidden by the previous zero allocation. `sim/vta_stopline.con.xml` moves the four De Anza left waiting points to the stop line; netconvert retains external geometry, TLS link indices and all plan files. This inferred internal waiting model is not field-verified geometry. `build-net` reapplies it after OSM conversion. The count-check residuals still combine departure-to-crossing lag, queues and insertion limits; they do not individually identify each effect.
