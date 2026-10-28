# Count source audit — 2026-10-28

## Required 2024 VTA source is missing the corridor count sheets

The architecture identifies VTA CMP sites 211 (De Anza / Stevens Creek) and 217 (Stevens Creek / Stelling). The supplied download is real, but it is an **11-page sample**, not the complete detailed appendix.

| Official source | Verified contents / response |
| --- | --- |
| [VTA CMP program](https://www.vta.org/programs/congestion-management-agency) | Links main report and sample appendices |
| [VTA project documents](https://www.vta.org/projects/documents?project=1116) | Attachment explicitly titled “2024 CMP Monitoring Appendices Sample Only” |
| [Supplied sample PDF](https://www.vta.org/sites/default/files/2025-08/2024%20CMP%20Monitoring%20Appendices_Sample.pdf) | Downloaded successfully, 11 pages. Sites 211/217 appear in summary/LOS listings, **not** raw turn tables |
| [Main report](https://www.vta.org/sites/default/files/2026-02/2024_VTA_CMP_Monitoring_Report.pdf) | HTTP 200 PDF, 127 pages; Appendix G listed in TOC but absent from file. PDF p.36 / printed p.29 lists LOS E and D− for sites 211 and 217, not turn volumes |
| [VTA title search](https://www.vta.org/search?search=2024%20CMP%20Monitoring%20Appendices) | Returns only the Sample Only document |

Sample raw count sheets: PDF pp.8–9 E Campbell Avenue / S Bascom Avenue (September 24, 2024); pp.10–11 Hamilton Avenue / Winchester Boulevard (October 23, 2024). Neither is on this corridor. A summary LOS letter cannot be converted into 15-minute movement counts.

Downloaded sample: `data/raw/vta/2024_CMP_Monitoring_Appendices_Sample.pdf` (gitignored).
SHA256: `5c7713e8430a4e5adc26d7237a654e70f182bb8171d38650d485829210ee5565`.

Two likely full-appendix filenames under VTA's 2025-08 directory were tested: `2024%20CMP%20Monitoring%20Appendices.pdf` and `2024_CMP_Monitoring_Appendices.pdf`. Both returned HTTP 404 HTML, not PDFs. Public searches for the exact appendix title, Appendix G, and each site's 2024 count sheet did not locate a full copy. This is evidence that the specified sources do not provide the sheets; it is not proof that no copy exists anywhere.

## Real historical alternative found; requires a source/date change

[Cupertino Vallco DEIR Appendix H (May 2018 TIA)](https://www.cupertino.gov/files/assets/city/v/1/departments/documents/community-development/planning/major-projects/the-rise/vallco-historical-project-information/vallco-specific-plan/ceqa/appendix-h-transportation.pdf): PDF pp.554–555 contain Stevens Creek / Stelling 15-minute PM rows, count date January 17, 2018; pp.602–603 contain De Anza / Stevens Creek rows, January 10, 2018. These are real counts at the right intersections, **not VTA 2024 counts**.

[Apple Campus 2 DEIR Appendix B](https://s3.amazonaws.com/Apple-Campus2-DEIR/Appendix-B-Transportation-Impact-Analysis.pdf): PDF p.165 has Stelling PM counts dated May 10, 2011; p.205 has De Anza PM counts dated May 3, 2011. Also historical.

No historical rows have been relabeled as current or as VTA measurements. No synthetic values have been labeled measured. No `tmc.csv` has been manufactured. The requested visual cross-check of a corridor VTA sheet remains impossible until a sheet is supplied. Using the historical alternative requires explicit approval of the changed source/date; a source-choice question has been presented.
