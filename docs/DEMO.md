# Signal Learner: demo runbook

VTA approved use in the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. Keep the repository and raw data private.

## Start the presentation

From the repository root, run `python3 -m tools.demo` with the supported Python 3.12 environment. Open the printed Slides URL. The command serves a temporary copy on `127.0.0.1`; it does not run experiments or rewrite reports. Use `python3 -m tools.demo --port 8769` for a fixed port. Ctrl-C stops the server and removes the temporary copy. No network connection is needed after cloning.

Left/Right changes slides; N toggles speaker notes; Home/End jumps to the beginning/end. A URL ending in `/#9` opens the saved video. The fixed widescreen stage scales on phones; landscape is more readable. Play the video with its native controls if autoplay is blocked. Download the printed PDF URL as an offline fallback; it contains a still image, not playable video.

## Present and rehearse

The speaking copy is in the actual [HTML slides](../dashboard/signal-learner/index.html), available with N. The [PDF](../dashboard/signal-learner/signal-learner.pdf) follows the same 15 slides. Slides 1–2 introduce Stevens Creek; 3–8 explain the working system; 9 plays one saved synthetic Wolfe run; 10–12 show the original evidence; 13 gives one short limitations section; 14 proposes the city workflow; 15 closes with the engineer ask. A student must personally rehearse and verify media on the presentation laptop. Team roles and pending work belong in [SPEC.md](../SPEC.md).

The server also prints engineer-card URLs. Wolfe's archived card predicts 137.6 → 79.6 in the practice copy; the historical hidden-world result is separately 870.49 → 643.11. De Anza keeps old timing. Its archived reason says “no clear gain,” but the candidate actually failed the teleport constraint; its forecast describes that rejected candidate. The demo adds a reading note while preserving the archived source. This presentation update does not change the learner or replace the original results.

The original copy-count labels were wrong: 29,633 and 38,959 are signal-turn passages summed over traversals, not unique vehicles or trips. The deck corrects this label; frozen research outputs remain unchanged. VTA-derived material on slide 12 carries the approved citation.

## Develop separately

Follow the README's Python 3.12 setup and tests. Homestead's generated demand is excluded from Git. Before a full development run in a disposable checkout:

```sh
python -m tools.learner build-world --road homestead
python -m tools.learner run --road homestead
```

These commands generate inputs and replace Homestead's development outputs. They try 150 plans; do not run them during the talk. Read `reports/learner/homestead/card.md` afterward. If a command fails, inspect the reported SUMO error before using any output.

Do not run, delete, reset or tune on `reports/learner_heldout/`. Keep historical evidence separate from all new checks. City timing, representative measured days, actual controller integration and field benefits remain unvalidated.
