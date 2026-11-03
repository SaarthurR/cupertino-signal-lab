# Signal Learner: team presentation plan

Working plan: build the story around the existing simulation results. Saarth's review asked Advaita to focus on project organization, slides and the judges' narrative rather than simulator changes. The team should agree on speaking roles and the remaining work together.

## Goal and project contract
Signal Learner observes simulated detectors, reconstructs traffic, searches bounded timings, recommends a change or no change, and monitors an approved simulated change. The existing `docs/LEARNER-SPEC.md` remains the research contract. No real signals are connected. Synthetic traffic, constructed old timing, copy predictions and held-out measurements must remain distinct.

## Focus and proposed roles
- Advaita: project map, five-part pitch, evidence explanations, and the existing setup/demo handoff. See `docs/PITCH.md` and `docs/DEMO.md`.
- Saarth: existing simulations and results; coordinate any new model work with him.
- Prithvi: proposed trade-off backup slide, judge-question rehearsal and submission checks. These leave a meaningful presentation contribution for him; confirm the split as a team.

Keep the original held-out artifacts and decisions unchanged. VTA allowed the hackathon presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. The repository and raw data remain private. This permission does not establish approval for other publication.

## Demo path
Clone and install with Python 3.12 and the existing requirements. Run the tests. Launch `python -m tools.demo` without SUMO or any third-party Python package: it serves a temporary, allowlisted copy of the existing presentation assets and the two synthetic-road cards, bound to localhost. Use the slides to explain the six steps, play Wolfe's recorded comparison, show the measured Wolfe improvement and De Anza rejection, inspect the cards, and state the limitations. Stop with Ctrl-C. No simulations or report writes occur when launching the demo.

For a development simulation, explicitly build Homestead's generated world before `tools.learner run`. Keep this expensive operation separate from presenting saved results. Never rerun the completed held-out test.

## Presentation checks
- The five-part story maps to the existing slides and explains the intended user, mechanism, results, limits and next validation step.
- Every linked artifact exists. Rounded headline scores agree with the saved results; forecasts, held-out measurements and post-hoc diagnostics are clearly distinguished.
- Prithvi has concrete proposed deliverables, and no role is presented as agreed without the team confirming it.
- Only presentation and planning documents change. Research code, slides, PDF and experiment artifacts remain unchanged. Submit the handoff through a pull request for Saarth to review.

## Completed setup checks
- **A1 — Fresh setup:** the README documents all required generation steps. On an isolated clean copy, install the pinned requirements, build Homestead's world, and run the learner through recommendation successfully. For bounded verification, use the existing `practice(..., trials=1)` argument in a test harness around the unchanged CLI; do not repeat the unchanged 150-trial experiment. Keep the normal documented 150-trial run available. No source checkout reports are overwritten.
- **A2 — Local demo:** `python -m tools.demo --help` and the real server work using the standard library. Deck, PDF, video and cards return successfully; non-allowlisted repo files are unavailable. Bind only to `127.0.0.1`; invalid ports and missing assets fail clearly. Check GET, HEAD, denied paths and shutdown.
- **A3 — Presentable workflow:** verify slide navigation, notes, video and both card links in Chrome at 1280px and 375px, with no application console errors. The runbook distinguishes forecast scores from held-out scores and explains the preserved De Anza card's outdated reason. Retain the existing visual design.
- **A4 — Regression and handoff:** all existing and new unit tests pass; review the diff for correctness and file/network exposure; confirm frozen-result checksums match; document evidence and remaining team work. Changes are reviewed through a pull request; approval to share code for review does not authorize a public deployment.

## Out of scope and failure handling
No new frontend, dependencies, neural network, optimizer tuning, real controller adapter or permission assumption. A missing generated route file must be repaired through the documented world-build step, not by editing saved results. Missing demo assets fail before the server starts. An occupied port produces a clear error; the default uses an available port. Mobile is a scaled presentation deck, not a redesigned mobile app.

## Verification — 2026-11-02
- **A1 passed:** isolated clean clone, Python 3.12, `uv pip install -r requirements.txt` and `uv pip install -e .`; all 43 installed pinned versions matched. `build-world --road homestead` succeeded. The real `tools.learner` CLI ran watch, learn, practice (one trial via its existing function argument) and recommend, with one simulation worker; a labeled “no change” card was produced. Full 150-trial optimization was not repeated.
- **A2 passed:** five demo tests cover real GET/HEAD delivery, text card rendering, directory/path denial, rejected POST, missing/unsafe assets, invalid ports, an occupied port and cancelled-transfer logging. Real standard-library launcher, `--help`, video/PDF/card URLs, a cancelled video transfer and Ctrl-C shutdown/temporary-copy cleanup were checked. Client disconnects log briefly; unrelated I/O errors still propagate.
- **A3 passed:** Chrome screenshots at 1280×720 and 375×812; slide keys, speaker notes, 88-second video playback, both card URLs and runbook checked. No application console errors recorded. Existing mobile scaling retained; no frontend or deck edits.
- **A4 passed:** `PYTHONPATH=src python -m unittest discover -s tests -v`: 108 tests passed in the isolated environment with pinned packages. `git diff --check` and Python compilation passed. Correctness/security diff review found no blocking issue: only allowlisted copies served, loopback bind, no report-write endpoint, input validation and actionable startup errors. All 84 protected files under learner reports, held-out reports, worlds and roads retained their original SHA-256 hashes in the source checkout. Saarth independently tested and merged the setup work in PR #1.
