# Signal Learner: team demo runbook

The slides and PDF include VTA-derived results. On Nov 2, VTA allowed their use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. The repo itself stays private; keep the raw data inside the team.

## Start without installing simulation packages

From the repository root, run `python3 -m tools.demo`. Python 3.12 is the project's supported version. Open the printed Slides URL. All files are served from a temporary copy on `127.0.0.1`; no experiment runs or report writes occur. No network connection is needed after cloning. If a fixed port is needed, use `python3 -m tools.demo --port 8769`. Ctrl-C stops the server and removes its temporary copy.

Use Left/Right to change slides, N for speaker notes, Home/End for the beginning/end. Direct URLs ending in `/#9`, for example, open slide 9. On phones the existing widescreen deck scales down; use landscape for readability. This is a presentation, not a mobile application. The printed PDF URL is the fallback if browser media fails; download it before disconnecting. The PDF does not play the video.

## Walkthrough

Use the [five-part pitch and project map](PITCH.md) to organize the talk. This runbook supplies the operating details and evidence boundaries.

1. **Problem and mechanism — slides 1–8.** Traffic patterns change. We observe simulated detector data, reconstruct demand, search 150 bounded plans, and give an engineer a recommendation. It is Optuna's model-based search, not a neural network. Maps are based on OpenStreetMap; no real sensors or lights are connected.
2. **Watch — slide 9.** Play the saved Wolfe comparison. It is one recorded simulated rush hour at 100x speed, not a live experiment or the average across all tests. Red dots are stopped vehicles; green dots move. Vehicles unable to enter the network are not drawn.
3. **Evidence — slides 10–11.** Across 20 paired held-out runs, Wolfe's delay score fell from about 870 to 643 (26%). De Anza kept old timing. The score charges 900 seconds per unfinished trip and per teleport; these are not measured commute times. Old timing is our constructed stand-in, not Cupertino's plan. The new roads use synthetic traffic.
4. **Inspect the decision — open the printed engineer-card URLs.** Wolfe's card shows the proposed cycle, offsets and green changes. Its copy forecast (138 to 80) is different from the held-out world result (870 to 643). De Anza's archived card has an outdated reason: it says “no clear gain,” but the copy predicted an 11.2% gain and the plan failed the teleport feasibility limit. Its displayed forecast belongs to the rejected candidate; the actual recommendation keeps old settings. Preserve the card as evidence. A later diagnostic on new seeds found the rejected plan was 6.4% worse in the hidden world; that is post-hoc evidence, not part of the original test.
5. **Limits and next work — slides 13–16.** Wolfe improved overall but one origin group's delay worsened by about 203 seconds. The copy underestimated Wolfe's trips and misread a shared lane on De Anza. The undo rule falsely triggered on 4 of 10 harmless-change De Anza runs. Two held-out roads is a small test. Close with the planned shared-lane fix, better normal-traffic coverage, and preregistered fresh-road testing.

Slide 12 is the cross-road table containing VTA-derived numbers. It carries the required citation: VTA, 2024 CMP Monitoring and Conformance Report.

## Development, separate from presenting

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before the first full development run:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate world inputs and replace Homestead's development feed, copy, search and card outputs. Use your own checkout or a disposable copy when preserving a teammate's development results. The full run tries 150 plans; do not run it during the presentation. Start with `reports/learner/homestead/card.md` afterward. A failure stops the command; read the reported SUMO error rather than continuing with stale output.

Do not run, delete or reset `reports/learner_heldout/`. Do not tune on Wolfe/De Anza or test seeds. All such results are already final.

## Proposed team split

| Owner | Work |
|---|---|
| Advaita | Project structure, slide narrative, explanation of existing results, setup and demo handoff |
| Saarth | Simulation and existing results; coordinate any further model work with him |
| Prithvi | Suggested: trade-off backup slide, judge-question rehearsal and submission checks; see PITCH.md |

Agree on roles and judging requirements as a team before treating this split as final. The README's event dates and pre-built-code allowance are team notes, not independently confirmed organizer rules. City data has not arrived and cannot be claimed. VTA permission covers the hackathon presentation, with the citation above.
