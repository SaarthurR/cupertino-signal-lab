# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep raw source files out of the repository.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it runs a fixed simulation only when requested in the console and does not rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

Open the printed Engineer console URL in a second tab. The Simulate screen compares modeled old timing with the proposed plan on the same held-out Wolfe Road run (seed 200). It starts SUMO when the generated inputs and simulator are available. Otherwise it plays the saved run and shows **Recording**.

For the live simulation on a fresh clone, first run `PYTHONPATH=src:. python -m tools.learner build-world --road wolfe` with the SUMO-enabled environment; this generates the ignored routes and old timing from the tracked road inputs.

Use Left and Right to change slides and N to show speaker notes. Slide 4 has the backup video. Click its thumbnail to play it and press Esc to close it. Slide 7 links to every backup topic. Save the PDF and the standalone MP4 from the launcher as offline copies. The PDF has a still from the Wolfe Road run.

## Present and rehearse

Slides 1–6 are the 150-second talk. Slides 7–17 are for questions. The [PDF](../dashboard/signal-learner/signal-learner.pdf) follows the same order. Open the notes, put the lines in your own words and do a timed pass on the presentation laptop. The [README](../README.md) has the speaking roles and the shorter route.

## Demo script: 85 seconds

Before the talk, open Corridors (`/console/#/corridors`) in the second tab. If Wolfe shows Approved or Deployed, use **Reset demo** at the bottom of Deploy & monitor. Budget 45 seconds for the simulation at 240× and speak while it runs. If it needs more time, skip the deploy click and return to slide 4.

| s | Screen | Click | Say |
|---:|---|---|---|
| 4 | Slide 3 | Switch to the console tab | "Here's what a city engineer would see." |
| 6 | Corridors | Wolfe Road row | “Here’s the recommendation waiting for review on Wolfe Road.” |
| 7 | Wolfe Road | Vallco Pkwy | “We used simulated sensor counts to build a model and try a hundred and fifty timings.” |
| 5 | Vallco Pkwy | Point to the timings, then Review recommendation | “Here’s how both plans time one light.” |
| 5 | Review | Approve | “The engineer can see what changes across the whole road.” |
| 3 | Approved | Run side-by-side simulation, then 240× | “Let’s run them side by side.” |
| 45 | Simulate | Point to both panels and then to the end card | “The top is our modeled old timing. The bottom is our plan. Both get the same traffic on the same Wolfe Road map.” “Red dots are stopped cars. The middle shows the difference in how many cars are waiting to enter.” At the end card, point to this run’s score. “This is one evening. The full comparison is on the next slide.” |
| 8 | Deploy & monitor | Deploy & monitor, then Deploy to 5 controllers | “Here’s how the console previews applying or rolling back the plan.” |
| 2 | | Switch back to the slides, slide 4 | |

**If you see Recording**, say “This is the saved run of the same evening” and continue. **If the console or playback fails**, go directly to slide 4. Play about 20 seconds of the backup video while explaining the two timings, then close it and give the 20-run result. If time is tight, use the comparison and still on slide 4.

Wolfe’s archived card predicts 137.6 → 79.6 in the model used to select the plan. The independent test result on slide 4 is 870.49 → 643.11. The annotated De Anza card explains why the candidate failed the relocation limit and what its practice forecast refers to.

## Develop separately

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before a full development run in a disposable checkout:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate inputs and replace Homestead's development outputs. They try 150 plans; do not run them during the talk. Read `reports/learner/homestead/card.md` afterward. If a command fails, inspect the reported SUMO error before using any output.

Do not run, delete, reset or tune on `reports/learner_heldout/`. Keep historical evidence separate from all new checks. City timing, representative measured days, actual controller integration and field benefits remain unvalidated.
