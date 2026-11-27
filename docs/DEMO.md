# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep raw source files out of the repository.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it runs a fixed simulation only when requested in the console and does not rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

Open the printed Engineer console URL in a second tab. It opens on Wolfe Road, step 1 of 3 (The problem, The fix, The proof). Step 3 compares modeled old timing with the proposed plan on the same held-out Wolfe Road run (seed 200). It starts SUMO when the generated inputs and simulator are available. Otherwise it plays the saved run and shows **Recording**.

For the live simulation on a fresh clone, first run `export PYTHONPATH=src` and `python -m tools.learner build-world --road wolfe` with the SUMO-enabled environment. This generates the ignored routes and old timing from the tracked road inputs.

Use Left and Right to change slides and N to show speaker notes. In the repo slides, slide 4 is a preview of the engineer console. Right (or **Open the console**) opens the live console full screen in the same tab, on Wolfe Road step 1. **Back to slides**, top right, opens slide 5; browser Back returns to slide 4. A clicker's Page Down and Page Up do the same. The chip shows only when the console was opened from the slides. Opened as a file instead of through the launcher, slide 4 stays a still and Right goes to slide 5. The “End of talk” slide links to every backup topic. Save the PDF and the standalone MP4 from the launcher as offline copies. The PDF has a still from the Wolfe Road run.

## Present and rehearse

The main talk is the slide deck served by the launcher (`dashboard/signal-learner/`): slides 1–7 are the talk, with the demo on slide 4 and the Wolfe result on slide 5. B1–B9 are for questions, and the last slide is the 60-second version. Slide 4 is a console preview that opens the live console. The Google Slides copy is older; do not present from it. Put the notes in your own words and do a timed pass on the presentation laptop. The [README](../README.md) has the speaking roles.

## Demo script: 45 seconds

Before the talk, open the console once (`/console/`); it lands on Wolfe Road step 1. If the stepper ends in Approved or Deployed instead of “Approve or reject”, click **Reopen** on step 3, or use **Reset demo** under More, Deploy & monitor.

| s | Screen | Click | Say |
|---:|---|---|---|
| 5 | Slide 4, the preview | Point at the three callouts | “This is the engineer console. Cars waiting with each timing, the proof, and the engineer decides.” |
| 0 | Opens on 1 The problem | **Right**, or **Open the console** | |
| 5 | 1 The problem | Point to the big 870 s | “This is Wolfe Road in the evening rush. With the current timing, the average trip loses 870 seconds, and 968 cars never get through.” |
| 5 | 2 The fix | **See the fix** | “Our fix: every light gets a longer round, and the busy directions get more green. The dark blue is Wolfe Road’s green.” |
| 20 | 3 The proof | **See the proof**, then **Run the simulation** (starts at 240×) | “Same cars, same evening. Top is the current timing, bottom is ours. Watch the two big numbers on the left: cars still waiting to get on the road.” |
| 10 | 3 The proof, then slide 5 | Point to the green “fewer waiting” line, then **Back to slides** (top right) | “That’s one evening. Here’s the full test.” Slide 5 shows the result. |

At 45 seconds, click **Back to slides** even if the run is still playing. A full run takes about 35 seconds at 240×, so it may not reach its end card. Approving is optional: the −26% result and **Approve new timing** sit just below the maps, and approving does not restart the run. Do not open Deploy & monitor in the main talk. That screen previews a future workflow, and no real controller is touched. Show it only if a judge asks.

**If you see Recording**, start with “This is a saved run of the same evening” and continue. **If the console or playback fails**, click **Back to slides** (or browser Back), talk over the slide 4 preview, then go to the result slide. **If the whole talk breaks**, give the 60-second version on the judge deck’s last slide. It needs no app, terminal or video.

**Three Wolfe numbers, three meanings.** Don’t read the forecast out loud.

| Number | What it is |
|---|---|
| 137.6 → 79.6 s, −42% | Forecast in the practice copy, used to pick the plan. Shown only under Details for engineers on step 3. |
| 856.0 → 650.2 s, −24% | One evening, held-out seed 200. The demo run and the video. |
| 870.49 → 643.11 s, −26.1% | The independent test: mean of 20 held-out runs, seeds 200–219, lower in all 20. The headline. |

The annotated De Anza card explains why the candidate failed the relocation limit and what its practice forecast refers to. In the console, De Anza Boulevard runs the same three steps and ends in **Keep current timing**.

## Develop separately

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before a full development run in a disposable checkout:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate inputs and replace Homestead's development outputs. They try 150 plans; do not run them during the talk. Read `reports/learner/homestead/card.md` afterward. If a command fails, inspect the reported SUMO error before using any output.

Do not run, delete, reset or tune on `reports/learner_heldout/`. Keep historical evidence separate from all new checks. City timing, representative measured days, actual controller integration and field benefits remain unvalidated.
