# Cupertino Signal Lab

A reproducible AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. **Historical 2018 demand; not current Cupertino traffic.** Demo timing assumptions are not city signal plans.

**Status: M0–M2 implemented; M3 holdout check implemented and run with the provisional M1 generated actuated plan. Stopped before M4 for independent review, as requested.** The M4 textbook coordinated-actuated baseline is pending, so M3 must be rerun after it exists. Baseline, optimization, evaluation, dashboard and video are not built in this piece.

```sh
source .venv/bin/activate
# Fresh environments: uv venv --python 3.12; uv pip install -r requirements.txt
uv pip install -e .
nice -n 15 python -m signal_lab build-net
nice -n 15 python -m signal_lab build-demand
nice -n 15 python -m signal_lab check-demand
nice -n 15 python -m unittest discover -s tests -v
```

M2 produces both PM/night demand through SUMO routeSampler, fits only 16:30–17:30, and replays that fit hour for holdout. Night finishes with **zero teleports**. PM is congested under the provisional timing: **1040 teleports, 1249 vehicles running and 6609 waiting to insert after a 30-minute drain**.

M3: **14.58% of 96 measured holdout movement-intervals have GEH < 5**, below the 85% target. This is an unsuccessful count match, not a calibrated model. Counts are physical turn-lane detector entries; quarter-hour observations are converted to hourly flows for GEH. No delay improvement or paired Wilcoxon result is available before M4–M6.

Data: De Anza (Jan 10, 2018) and Stelling (Jan 17, 2018) have measured quarter-hour turns. Mary has newer Apr 25, 2018 hourly observations, preserved separately; its quarter-hour profile is estimated. Bandley and Saich are estimated. Thus **3 of 5 quarter-hour profiles are estimated**. Mary's current OSM topology lacks movements representing 775 vehicles/hour on the sheet; those observations are retained but cannot be simulated. All dates, methods and limits: [source audit](reports/data-source-audit.md), [provenance CSV](data/processed/tmc_sources.csv). The agent visually checked Stelling PDF p.554; independent human sign-off remains pending.

Outputs: [M2 report](reports/M2-REPORT.md), [M3 holdout report](reports/demand_check.md), [holdout rows](reports/demand_check.csv). Spec: [architecture](docs/ARCHITECTURE.md). No dashboard/video/result comparison exists yet. The full 4.2 command intentionally stops at `baseline`.

SUMO jobs run at nice 15, serially, with a two-hour timeout; the heat guard may pause them. Follow [laptop limits](reports/bench.md) before long jobs. No dependencies were added for this data piece. `smoke_test.py` remains unchanged.

Roads © [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). Counts: City of Cupertino / Vallco TIA (Traffic Data Service), Westport CEQAnet appendix (National Data & Surveying Services). VTA sample was audited but does not supply corridor counts.
