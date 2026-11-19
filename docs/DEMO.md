# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep the repository and raw data private.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it runs a fixed simulation only when requested in the console and does not rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

The printed Engineer console URL opens the clickable product: Corridors (city map, all corridors, inbox of recommendations), a page per corridor and per signal (KPIs, timing sheet, approaches, coordination diagram, time-space diagram), Review (per-signal diff, expected impact, Approve / Schedule / Reject with notes; De Anza: keep current), Simulate, and Deploy & monitor (rollout plan, Saved simulation evidence, roll back, audit log). For the talk, follow the timed demo script below. Panels that need `dashboard/console/data/<road>/metrics.json` are hidden when that file is missing; add `?fixture` to the URL to preview them with clearly labelled fake numbers. Simulate runs old timing and the plan side by side on held-out seed 200, live in SUMO when this Python has libsumo; otherwise it plays the committed recording (labelled "Recording"). Rebuild the recording with `python -m tools.live_sim` and the map JSON with `python -m tools.sim_geometry`. Screenshots: `docs/console-shots/v3/`.

For the live simulation on a fresh clone, first run `PYTHONPATH=src:. python -m tools.learner build-world --road wolfe` with the SUMO-enabled environment; this generates the ignored routes and old timing from the tracked road inputs.

Left/Right changes slides; N toggles speaker notes; Home/End jumps to the beginning/end. Slide 4 (a URL ending in `/#4`) has the saved video: click the thumbnail to play it over the slide, Esc to close. Play it only if the live demo failed. The fixed widescreen stage scales on phones; landscape is more readable. Use the video's native controls if it does not start. Download the printed PDF URL as an offline fallback; it contains a still image, not playable video.

## Present and rehearse

The speaking copy is in the actual [HTML slides](../dashboard/signal-learner/index.html), available with N. The [PDF](../dashboard/signal-learner/signal-learner.pdf) follows the same 17 slides. Slides 1–6 are the main talk, 150 seconds with the demo: hook and problem, the live console demo (slide 3), the Wolfe result, the city workflow and the engineer ask. Slides 7–17 are backup for questions, including what we built, De Anza and limits. A student must personally rehearse and verify media on the presentation laptop. Team roles and seconds per part are in the [README](../README.md).

## Demo script: 85 seconds

Before the talk: console open in a second tab on Corridors (`/console/#/corridors`), fresh state (if Wolfe shows Approved or Deployed, click Reset demo at the bottom of Deploy & monitor). The simulation takes 34 s at 240× (measured, live SUMO, 1440×900); talk over it, never wait in silence. Numbers below are what the screen shows.

| s | Screen | Click | Say |
|---:|---|---|---|
| 4 | Slide 3 | Switch to the console tab | "Here's what a city engineer would see." |
| 7 | Corridors | Wolfe Road row | "Every corridor in one inbox, and one recommendation waiting: Wolfe Road, new evening timing, −26%." |
| 7 | Wolfe Road | Signal 1, Vallco Pkwy (›) | "Signal Learner read this road's sensors, built a practice copy and tried 150 timing plans on it." |
| 10 | Vallco Pkwy | Scroll to the diagram, then Review recommendation › | "Each light gets a new timing sheet. Each dot is a car: with the plan, 85% arrive on green, up from 78." |
| 7 | Review | Approve | "The card shows what changes at every light and the expected effect. The engineer decides." |
| 3 | Approved | Run side-by-side simulation, then 240× | "Approved. Now let's test it." |
| 35 | Simulate | (none until the end card) | Over the run: "This is the real Wolfe Road map. Top: today's timing. Bottom: our plan. Same cars, same evening." "Red dots are stopped cars. The red number in the middle is how many more cars are stuck waiting with today's timing." At the end card: "This evening: 856 down to 650. Across 20 test evenings it never saw: 26% lower." |
| 10 | Deploy & monitor | Deploy & monitor, then Deploy to 5 controllers | "Deploy is simulated; no real controller is touched. After a change it keeps watching, and its roll-back rule caught all 10 deliberately bad plans." |
| 2 | | Switch back to the slides, slide 4 | |

Total 85 s. If the source pill says **Recording**, keep going: it is the same evening with the same end numbers. If the live run fails, skip Simulate, go to Deploy & monitor, then play the slide 4 video during the result.

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
