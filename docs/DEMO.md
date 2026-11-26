# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep raw source files out of the repository.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it runs a fixed simulation only when requested in the console and does not rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

Open the printed Engineer console URL in a second tab. The Simulate screen compares modeled old timing with the proposed plan on the same held-out Wolfe Road run (seed 200). It starts SUMO when the generated inputs and simulator are available. Otherwise it plays the saved run and shows **Recording**.

For the live simulation on a fresh clone, first run `export PYTHONPATH=src` and `python -m tools.learner build-world --road wolfe` with the SUMO-enabled environment. This generates the ignored routes and old timing from the tracked road inputs.

Use Left and Right to change slides and N to show speaker notes. In the repo slides, slide 4 has the backup video: click its thumbnail to play it and press Esc to close it. Slide 7 links to every backup topic. Save the PDF and the standalone MP4 from the launcher as offline copies. The PDF has a still from the Wolfe Road run.

## Present and rehearse

The main talk is the team’s Google Slides judge deck: slides 1–9 are the 180-second talk, with the demo on slide 5 and the Wolfe result on slide 6. B1–B14 are for questions, and the last slide is the 60-second version. The repo slides (`dashboard/signal-learner/`, served by the launcher) are the offline version with the same numbers: slides 1–6 are the talk, the demo is slide 3 and the result is slide 4. Put the notes in your own words and do a timed pass on the presentation laptop. The [README](../README.md) has the speaking roles.

## Demo script: 45 seconds

Before the talk, open the console at Wolfe Road Review (`/console/#/wolfe/review`) in the second tab. If Wolfe shows Approved or Deployed, use **Reset demo** at the bottom of Deploy & monitor, then go back to Review.

| s | Screen | Click | Say |
|---:|---|---|---|
| 5 | Review | Point to the green bars and the changed timings | “Here’s the recommendation the engineer sees. Every light gets a longer round, and the busiest directions get more green.” |
| 5 | Review | Approve, then Run side-by-side simulation, then 240× | “I’ll approve it in the demo and run both plans.” |
| 25 | Simulate | Point to both panels, then to the waiting count | “Both sides get the same simulated trips. The top is the old plan. The bottom is ours. Red dots are stopped cars. Watch how many cars are stuck waiting to get onto the road.” |
| 10 | Simulate | Switch back to the slides | “This is one evening. Next is the full test.” |

At 45 seconds, go to the result slide even if the run is still playing. A full run takes about 35 seconds at 240×, so it may not reach its end card. Do not open Deploy & monitor in the main talk. That screen previews a future workflow, and no real controller is touched. Show it only if a judge asks.

**If you see Recording**, start with “This is a saved run of the same evening” and continue. **If the console or playback fails**, talk over the demo slide’s screenshot, then go to the result slide. **If the whole talk breaks**, give the 60-second version on the judge deck’s last slide. It needs no app, terminal or video.

**Three Wolfe numbers, three meanings.** Don’t read the forecast out loud.

| Number | What it is |
|---|---|
| 137.6 → 79.6 s, −42% | Forecast in the practice copy, used to pick the plan. Shown on the Review card. |
| 856.0 → 650.2 s, −24% | One evening, held-out seed 200. The demo run and the video. |
| 870.49 → 643.11 s, −26.1% | The independent test: mean of 20 held-out runs, seeds 200–219, lower in all 20. The headline. |

The annotated De Anza card explains why the candidate failed the relocation limit and what its practice forecast refers to.

## Develop separately

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before a full development run in a disposable checkout:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate inputs and replace Homestead's development outputs. They try 150 plans; do not run them during the talk. Read `reports/learner/homestead/card.md` afterward. If a command fails, inspect the reported SUMO error before using any output.

Do not run, delete, reset or tune on `reports/learner_heldout/`. Keep historical evidence separate from all new checks. City timing, representative measured days, actual controller integration and field benefits remain unvalidated.
