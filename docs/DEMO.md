# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep the repository and raw data private.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it runs a fixed simulation only when requested in the console and does not rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

The printed Engineer console URL opens the clickable product: Corridors (city map, all corridors, inbox of recommendations), a page per corridor and per signal (KPIs, timing sheet, approaches, coordination diagram, time-space diagram), Review (per-signal diff, expected impact, Approve / Schedule / Reject with notes; De Anza: keep current), Simulate, and Deploy & monitor (rollout plan, watch-after-deploy, roll back, audit log). Click Corridors → Wolfe Road → Review recommendation → Approve → Run the simulation → Deploy & monitor. Panels that need `dashboard/console/data/<road>/metrics.json` are hidden when that file is missing; add `?fixture` to the URL to preview them with clearly labelled fake numbers. Simulate runs old timing and the plan side by side on held-out seed 200, live in SUMO when this Python has libsumo; otherwise it plays the committed recording (labelled "Recording"). Rebuild the recording with `python -m tools.live_sim` and the map JSON with `python -m tools.sim_geometry`. Screenshots: `docs/console-shots/v3/`.

For the live simulation on a fresh clone, first run `PYTHONPATH=src:. python -m tools.learner build-world --road wolfe` with the SUMO-enabled environment; this generates the ignored routes and old timing from the tracked road inputs.

Left/Right changes slides; N toggles speaker notes; Home/End jumps to the beginning/end. Slide 5 (a URL ending in `/#5`) has the saved video: click the thumbnail to play it over the slide, Esc to close. The fixed widescreen stage scales on phones; landscape is more readable. Use the video's native controls if it does not start. Download the printed PDF URL as an offline fallback; it contains a still image, not playable video.

## Present and rehearse

The speaking copy is in the actual [HTML slides](../dashboard/signal-learner/index.html), available with N. The [PDF](../dashboard/signal-learner/signal-learner.pdf) follows the same 17 slides. Slides 1–9 are the main talk, about 150 seconds: problem, what we built, the live console demo (slide 4), Wolfe and De Anza results, the city workflow, one limits slide and the engineer ask. Slides 10–17 are backup for questions. A student must personally rehearse and verify media on the presentation laptop. Team roles and pending work are in the [README](../README.md).

The server also prints engineer-card URLs. Wolfe's archived card predicts 137.6 → 79.6 in the practice copy; the historical hidden-world result is separately 870.49 → 643.11. De Anza keeps old timing. Its archived reason says “no clear gain,” but the candidate actually failed the teleport constraint; its forecast describes that rejected candidate. The demo adds a reading note while preserving the archived source. This presentation update does not change the learner or replace the original results.

The original copy-count labels were wrong: 29,633 and 38,959 are signal-turn passages summed over traversals, not unique vehicles or trips. The deck corrects this label; frozen research outputs remain unchanged. VTA-derived material on slide 14 carries the approved citation.

## Develop separately

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before a full development run in a disposable checkout:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate inputs and replace Homestead's development outputs. They try 150 plans; do not run them during the talk. Read `reports/learner/homestead/card.md` afterward. If a command fails, inspect the reported SUMO error before using any output.

Do not run, delete, reset or tune on `reports/learner_heldout/`. Keep historical evidence separate from all new checks. City timing, representative measured days, actual controller integration and field benefits remain unvalidated.
