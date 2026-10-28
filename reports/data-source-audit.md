# Historical count sources — Round 2, October 28, 2026

**All usable observations found are from 2018. None are current traffic measurements.** A bounded parallel search covered the requested City development/agenda and agency leads. A later report year was never treated as the date of traffic collection. It found a newer **April 25, 2018 Mary Avenue hourly sheet**, but no newer usable quarter-hour sheet for De Anza or Stelling. This does not establish that unpublished counts do not exist.

## Selected sources

| Intersection | Actual count date | PDF pages (1-based) | Use |
|---|---|---|---|
| De Anza / Stevens Creek | 2018-01-10 | Vallco 602–603 | Eight measured 15-minute bins, 16:30–18:30 |
| Stelling / Stevens Creek | 2018-01-17 | Vallco 554–555 | Eight measured 15-minute bins, 16:30–18:30 |
| Mary / Campus Dr / Stevens Creek | 2018-04-25 | Westport 28 | Measured hourly totals, 17:15–18:15, preserved in tmc_hourly.csv; estimated quarter-hour disaggregation in tmc.csv |
| Bandley / Stevens Creek | None located | Vallco anchor pages above | Estimated; no claimed survey date |
| Saich / Stevens Creek | None located | Vallco anchor pages above | Estimated; no claimed survey date |

[Vallco DEIR Appendix H / May 2018 TIA, raw-count Appendix B](https://www.cupertino.gov/files/assets/city/v/1/departments/documents/community-development/planning/major-projects/the-rise/vallco-historical-project-information/vallco-specific-plan/ceqa/appendix-h-transportation.pdf).

[Westport Appendix H, official CEQAnet attachment](https://files.ceqanet.lci.ca.gov/253213-3/attachment/3CrHQTT3Zg88EHdiWjlstzTVL-KKLpZvvZFxozGEyHL8gYDB-jXqEsYbOb71LBc1SMI-lwBxTq6TV4Si0). Mary sheet: National Data & Surveying Services ID 18-08195-001. Source is the field sheet, not adjacent Synchro forecast pages 26–27. Its 2018-11-27 memo date and adjacent 2019 SR-85 memo are not Mary's count date.

Downloaded source copies (gitignored): `data/raw/city/vallco-appendix-h.pdf`, `data/raw/city/westport-appendix-h.pdf`.
SHA256 respectively: `8938c669cf41f5d97f677f88516385409adc96a9c7c7e1b03784ede3295b3c3e`, `3c4798f23eaa0be7aa130c693ff88352c06ca8014163882c1c368df919d0e59c`.

`tmc_sources.csv` records the source URL, 1-based PDF pages, actual count date or blank when no survey exists, historical basis year, and estimation method for every signal. Its `source` describes the quarter-hour data in `tmc.csv`. Mary's real hourly observation remains `source=measured` in `tmc_hourly.csv`; its manufactured quarters remain `source=estimated`. `year=2018` on estimated nodes describes the input vintage, not a measurement there.

## Transcription and visual cross-check

The agent rendered and visually checked the entire Stelling sheet, PDF p.554 (January 17, 2018), against the eight transcribed rows. **This is an agent visual check, not an independent human sign-off.** Raw PDF text was also extracted with native PDFKit; no OCR-imputed counts were used. The format's approach/intersection totals include pedestrians, so those totals must not be used directly as vehicle counts.

| Interval | Vehicles (12 R/T/L cells) | Pedestrians (4 crossing legs) | PDF intersection total |
|---|---:|---:|---:|
| 16:30 | 1027 | 50 | 1077 |
| 16:45 | 1011 | 45 | 1056 |
| 17:00 | 1067 | 51 | 1118 |
| 17:15 | 1200 | 54 | 1254 |
| 17:30 | 1261 | 60 | 1321 |
| 17:45 | 1175 | 36 | 1211 |
| 18:00 | 1216 | 78 | 1294 |
| 18:15 | 1297 | 75 | 1372 |

Also checked the sheet's 17:30–18:30 peak-hour movement sums by approach: north leg 962, east leg 1357, south leg 893, west leg 1737; total **4949 vehicles**. North leg 16:30 R/T/L = **29/86/62**; east leg = **17/132/68**. Tests lock these independent printed totals and selected cells.

Conventions: N/S/E/W mean **originating intersection leg**, so N is southbound and E is westbound. `vehicles` is lights+buses+trucks, excluding pedestrians. Interval-specific heavy totals are unavailable on these aggregate sheets, so `heavy` is blank (unknown), not zero. Crossing-leg `peds` are stored once on the T row, not copied onto all three turns; pedestrians are not simulated in this piece. The SUMO model represents all vehicle totals with passenger vehicles.

Mary's page was also visually checked: R/T/L/U by leg are N=138/78/123/0; E=165/892/125/13; S=75/20/126/0; W=113/1680/177/48. Sum **3773**, matching the printed TEV; **61** are U-turns. The number 362 at the top is outbound flow, not the sum of the southbound approach. Only five movements exist in the current OSM Mary network (N R/L, E R/T, W T). **775 measured vehicles/hour, including 61 U-turns, cannot be represented** and remain in the hourly source file. Reconstructing Campus Drive and missing turns requires a later network review; it was not silently invented in this data piece. Rounding the five retained hourly counts to quarters adds another 2 vehicles/hour of rounding difference.

## Estimation and fit/holdout separation

- Bandley and Saich: mainline through volume linearly interpolated by longitude between measured De Anza and Stelling through volumes for the same quarter; each other legal movement = 5 vehicles/15 minutes. All such rows are estimated. These are transparent assumptions, not an OD survey.
- Mary: retained hourly movement / 4, rounded to integer vehicles; uniform extension across 16:30–18:30. Both temporal disaggregation and extension are estimates. No hourly value is called a measured quarter.
- PM demand construction reads **only 16:30–17:30** rows, samples routes once (seed 0), then repeats those departures/routes one hour later. The first quarter is copied 900 seconds earlier for warmup. No 17:30–18:30 observed counts are used to generate routes. An adversarial test changes every holdout value by 100,000 and verifies byte-identical generated PM/night routes.
- Night: 10% of fit-hour mainline-origin movement totals; 2 vehicles/hour for each side-origin turn; integer sampling. Source estimated throughout.
- GEH uses only measured De Anza/Stelling **17:30–18:30** rows, converted from quarter-hour counts to hourly rates. Estimated nodes and Mary's disaggregated quarters are excluded.

## Rejected newer leads

| Lead | Finding |
|---|---|
| [VTA 2024 CMP sample](https://www.vta.org/sites/default/files/2025-08/2024%20CMP%20Monitoring%20Appendices_Sample.pdf), [official document listing](https://www.vta.org/projects/documents?project=1116) | 11-page “Sample Only”; raw sheets are Campbell/Bascom and Hamilton/Winchester, not sites 211/217. The [127-page main report](https://www.vta.org/sites/default/files/2026-02/2024_VTA_CMP_Monitoring_Report.pdf) has LOS letters, not these raw turns. Two likely full-appendix URLs returned 404. |
| The Rise / later Vallco modifications | Located traffic TIA has January 2018 observations; later plans/modifications do not establish newer traffic collection. |
| Westport Appendix H, pp.49–54 | Actual May 22, 2019 quarter-hour counts, but at SR-85 ramps / De Anza College driveway, a different intersection. Excluded. |
| [Westport 2020 memo](https://cupertino.legistar.com/View.ashx?GUID=5C387078-F558-45BD-BCF3-0F44802DEDAF&ID=9668484&M=F), [2021 memo](https://cupertino.legistar.com/View.ashx?GUID=AEFCB492-9E5F-494D-8379-739DE2F77D43&ID=9776661&M=F) | Trip-generation comparisons, not new count sheets. |
| [Marina Plaza December 2022 addendum](https://files.ceqanet.lci.ca.gov/196280-3/attachment/wYmj4b6i6oUJIsJdMMAccS-C5Qa0myMJ7ZW01U0oZGpdu0UZ_-mcnFglNj7fOXdUeivZ9RG5ciZmmfQp0) | No turning-movement count sheets located. |
| [Stevens Creek Corridor Vision Study, December 2024](https://www.cupertino.gov/files/assets/city/v/1/departments/documents/public-works/transportation/transportation-amp-mobility/stevens-creek-vision-study/stevens-creek-blvd-vision-study-report.pdf) | Corridor planning, collisions, parking/transit context; no qualifying intersection turn sheets. |
| [Cupertino 2026 retiming RFP PW-2026-853](https://apps.cupertino.org/details/853) | Scope requires future counts at these signals. Procurement scope is not count results. |
| VTA BRT / agency / County / Caltrans searches | No qualifying raw sheets at the five target nodes located; Caltrans state-highway counts are not city-intersection TMCs. |
| [De Anza College 2008 traffic appendix](https://facilities.fhda.edu/_downloads/DA%20-%20EIR%20Addendum%20With%20Traffic%202008.pdf) | Mary p.59 and Bandley p.61 sheets dated May 15, 2007; older than selected basis. |

## Network and measurement limits

Using `--osm.turn-lanes` had suppressed all four Stelling right turns because incomplete OSM lane tags were interpreted as movement exclusions. Removing that option lets SUMO infer connections geometrically while retaining lane counts and the five TLS ids. All 24 measured movement types now map to legal connections. This is inferred connectivity, not field validation, and changes turn-lane allocation at other nodes too; inspect before treating it as engineering geometry.

M3 uses SUMO induction loops at the **start of each internal turning lane**, summing `nVehEntered` by movement/quarter. These count physical entries; a teleported jump is not inferred from a planned route. A small real SUMO run verifies three vehicles produce three detector entries. See [SUMO E1 documentation](https://sumo.dlr.de/docs/Simulation/Output/Induction_Loops_Detectors_%28E1%29.html). Summary `teleports` is cumulative; a focused regression verifies it is read once from the final step.

The existing M1 actuated program is provisional: the user stopped this piece before M4, so no textbook baseline, tuning, or performance comparison is claimed. Holdout results must be regenerated after the independently reviewed M4 plan exists. The poor PM count match and gridlock are disclosed in demand_check.md; the model cannot be called calibrated or successfully count-matched.
