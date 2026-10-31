# Simulated counts: scenarios and feed (piece 1)

Run `PYTHONPATH=src nice -n 15 .venv/bin/python -m signal_lab feed --scenario calm --seed 0`.
Replace `calm` with `south_surge`, `east_surge`, `drop`, or `sensor_failure`.
Each run uses the frozen v5 PM plan. It writes `reports/feed/<scenario>_seed<seed>/feed.csv`,
derived routes, raw detector/trip/summary XML, a SUMO log, and `metadata.json`. This directory is ignored.
No source routes, plans, historical results, or detector definitions are changed. No optimizer runs.

The single traffic-change start is `CHANGE_START` in `src/signal_lab/feed.py`: 17:00.
Changes last 30 minutes, within PM 16:30–18:30. Warmup and drain retain existing settings.
`calm` copies PM demand byte for byte. `south_surge` adds 40% to vehicles requested on entry
754815172 (southbound N De Anza). `east_surge` adds 30% on entry 526011476 (eastbound Stevens Creek).
`drop` removes 30% per entry. Counts round to the nearest whole vehicle per affected entry.
Evenly spaced selections deterministically clone or remove vehicles from the change window.
Clones keep the original routes, departure times, and vehicle attributes. No random demand fitting occurs.
Saturation can prevent extra requests from inserting; metadata reports the change-window requested cohort's
insertions during the change and by the end of the drain, including added vehicles separately.
These are network insertions, distinct from counts at a downstream signal.

Feed columns are `window_end,site,approach,count,occupancy,ok`. Windows are 300 seconds, PM only.
ISO timestamps use a fixed **synthetic** date, 2026-10-31, and offset -07:00.
N/S/E/W mean originating compass legs; N is southbound, W is eastbound.
Site names come from config. Mapping uses network TLS connections and incoming-edge coordinates through
`demand.movement_map`, never a hand-entered detector table. Metadata lists unmapped original detectors.

Each run makes a private copy of the 67 `stop_*` and 67 `upstream_*` E1 loops at 300-second frequency.
`occupancy` is the arithmetic mean of upstream lane occupancy percentages for each approach.
Upstream crossings are excluded from `count` to prevent double counting. Counts sum `nVehEntered`
(front crossings, including zero counts) across stop-line lanes for each site/approach.
These measure arrivals at loops one metre before the signal; they are not completed trips.
Missing detector intervals fail extraction instead of becoming good zero counts.
`sensor_failure` uses identical calm traffic and marks only De Anza's N approach `ok=0`
for the four windows from 17:00–17:20. Counts are retained but flagged suspect.

The short real SUMO unit test checks three stop-line detections against three independently
recorded vehicle-route traversals across the same signal. Full seed-0 calm/south runs quantify
insertion capacity, rather than assuming the requested surge reaches the road.
