# Cupertino Signal Lab

An AI Club hackathon model of Stevens Creek Boulevard, De Anza Boulevard → Mary Avenue. Decision support only; demo timing assumptions are not Cupertino's current signal plans. The binding architecture is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Status: M0 scaffold and M1 network implemented; blocked at M2 by missing real VTA corridor count sheets.** VTA's linked sample omits sites 211 and 217. No measured counts have been fabricated. See [the data-source audit](reports/data-source-audit.md).

```sh
source .venv/bin/activate
# Fresh environments: uv venv --python 3.12; uv pip install -r requirements.txt
uv pip install -e .
python -m signal_lab --help
nice -n 15 python -m signal_lab bench
nice -n 15 python -m signal_lab build-net
nice -n 15 python -m unittest discover -s tests -v
```

`bench` currently measures a synthetic actuated grid, not the final corridor. Importing `sumo` sets `SUMO_HOME`. SUMO child tools run at nice 15, serially, with a two-hour timeout. Follow all limits in [reports/bench.md](reports/bench.md) before long runs.

The remaining demo verbs expose help and fail explicitly until the missing source data is obtained and M2–M7 are implemented. The full 4.2 chain does **not** pass. There are no evaluation results, GEH percentage, paired Wilcoxon p-value, dashboard, video, or time-space diagram yet. The statistical outcome is unknown.

To resume: obtain the eight 15-minute PM turning-count intervals (16:30–18:30) for VTA CMP 211 (De Anza/Stevens Creek) and 217 (Stelling/Stevens Creek), with source pages/dates; transcribe and visually cross-check a sheet, then continue M2 through M7 in order. Older or estimated counts require an explicit change of the measured-PM specification.

Road data: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright). Source audit: VTA. `smoke_test.py` is retained unchanged.
