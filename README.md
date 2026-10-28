# Cupertino Signal Lab

A reproducible AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. **Historical 2018 demand; not current Cupertino traffic.** Demo timing assumptions are not city signal plans.

**Status: M0–M4 implemented. M3 rerun with the textbook coordinated-actuated baseline (not Cupertino's current timing). Stopped before M5 for independent review.** Optimization, evaluation, dashboard and video remain pending.

```sh
source .venv/bin/activate
# Fresh environments: uv venv --python 3.12; uv pip install -r requirements.txt
uv pip install -e .
nice -n 15 python -m signal_lab build-net
nice -n 15 python -m signal_lab build-demand
nice -n 15 python -m signal_lab baseline
nice -n 15 python -m signal_lab check-demand
nice -n 15 python -m signal_lab bench
nice -n 15 python -m unittest discover -s tests -v
```

M2 produces both PM/night demand through SUMO routeSampler, fits only 16:30–17:30, and replays that fit hour for holdout. Routes and data are unchanged by M4. The baseline uses Webster seeds, coordinator offsets, engineering clearance inputs, force-offs and detector-based phase skips; night rests in mainline green without a conflicting call.

M4 seed 0: night inserts **439**, with **zero teleports** and **8.341 s** mean time loss. PM inserts **17,312**, with **32 teleports**, **117 running** and **571 waiting to insert** after the drain; completed-trip mean time loss is **176.832 s**. Means exclude warmup departures; unfinished trips are absent. These timing assumptions are not a successful PM calibration.

M3: **39.58% of 96 measured holdout movement-intervals have GEH < 5**, below the 85% target (corrected-route provisional M1 timing: 48.96%). Counts are physical turn-lane detector entries; quarter-hour observations are converted to hourly flows for GEH. No delay improvement or paired Wilcoxon result is claimed. [Baseline details](reports/M4-REPORT.md) and [real corridor benchmark](reports/bench.md): **2.291 s per simulation hour**, approximately **21 minutes serial for 200 trials** including warmup/drain, excluding optimizer overhead and rescoring.

Data: De Anza (Jan 10, 2018) and Stelling (Jan 17, 2018) have measured quarter-hour turns. Mary has newer Apr 25, 2018 hourly observations, preserved separately; its quarter-hour profile is estimated. Bandley and Saich are estimated. Thus **3 of 5 quarter-hour profiles are estimated**. Mary's current OSM topology lacks movements representing 775 vehicles/hour on the sheet; those observations are retained but cannot be simulated. All dates, methods and limits: [source audit](reports/data-source-audit.md), [provenance CSV](data/processed/tmc_sources.csv). The agent visually checked Stelling PDF p.554; independent human sign-off remains pending.

Outputs: [M4 baseline report](reports/M4-REPORT.md), [M2 report](reports/M2-REPORT.md), [M3 holdout report](reports/demand_check.md), [holdout rows](reports/demand_check.csv). Spec: [architecture](docs/ARCHITECTURE.md). No dashboard/video/result comparison exists yet. The full 4.2 command intentionally stops at `optimize`.

SUMO jobs run at nice 15, serially, with a two-hour timeout; the heat guard may pause them. Follow [laptop limits](reports/bench.md) before long jobs. No dependencies were added for M4. `smoke_test.py` remains unchanged.

Roads © [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). Counts: City of Cupertino / Vallco TIA (Traffic Data Service), Westport CEQAnet appendix (National Data & Surveying Services). VTA sample was audited but does not supply corridor counts.
