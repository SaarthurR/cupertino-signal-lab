# Hackathon sprint: reproducible setup and team demo

Status: approved by the user's 2026-11-02 instruction to write the spec and complete their assigned part in the same turn.

## Goal and project contract
Signal Learner observes simulated detectors, reconstructs traffic, searches bounded timings, recommends a change or no change, and monitors an approved simulated change. The existing `docs/LEARNER-SPEC.md` remains the research contract. No real signals are connected. Synthetic traffic, constructed old timing, copy predictions and held-out measurements must remain distinct.

## Ownership and scope
- Advaita (this sprint): reproducible fresh-clone instructions, a one-command local presentation launcher, and a complete operator runbook using the existing deck, video and engineer cards.
- Saarth: shared-lane reconstruction and a copy-quality gate. Validate using observable counts, without substituting hidden truth for missing turn information.
- Third teammate: undo-rule variability and fresh-road evaluation. Preregister new roads, seeds and pass/fail rules before running; measure harmful-change detection and harmless-change false alarms.

The teammate work is a backlog, not an acceptance condition for Advaita's completed lane. Keep the original held-out artifacts and their decisions byte-for-byte unchanged. The existing data-use restriction applies to the entire demo: team-only until VTA approves public use, or the team prepares a separately reviewed public version.

## Demo path
Clone and install with Python 3.12 and the existing requirements. Run the tests. Launch `python -m tools.demo` without SUMO or any third-party Python package: it serves a temporary, allowlisted copy of the existing presentation assets and the two synthetic-road cards, bound to localhost. Use the slides to explain the six steps, play Wolfe's recorded comparison, show the measured Wolfe improvement and De Anza rejection, inspect the cards, and state the limitations. Stop with Ctrl-C. No simulations or report writes occur when launching the demo.

For a development simulation, explicitly build Homestead's generated world before `tools.learner run`. Keep this expensive operation separate from presenting saved results. Never rerun the completed held-out test.

## Acceptance checks
- **A1 — Fresh setup:** the README documents all required generation steps. On an isolated clean copy, install the pinned requirements, build Homestead's world, and run the learner through recommendation successfully. For bounded verification, use the existing `practice(..., trials=1)` argument in a test harness around the unchanged CLI; do not repeat the unchanged 150-trial experiment. Keep the normal documented 150-trial run available. No source checkout reports are overwritten.
- **A2 — Local demo:** `python -m tools.demo --help` and the real server work using the standard library. Deck, PDF, video and cards return successfully; non-allowlisted repo files are unavailable. Bind only to `127.0.0.1`; invalid ports and missing assets fail clearly. Check GET, HEAD, denied paths and shutdown.
- **A3 — Presentable workflow:** verify slide navigation, notes, video and both card links in Chrome at 1280px and 375px, with no application console errors. The runbook distinguishes forecast scores from held-out scores and explains the preserved De Anza card's outdated reason. Retain the existing visual design.
- **A4 — Regression and handoff:** all existing and new unit tests pass; review the diff for correctness and file/network exposure; confirm frozen-result checksums match; document evidence and remaining teammate work; make a focused local commit. No push, publication, outreach or deployment.

## Out of scope and failure handling
No new frontend, dependencies, neural network, optimizer tuning, real controller adapter or permission assumption. A missing generated route file must be repaired through the documented world-build step, not by editing saved results. Missing demo assets fail before the server starts. An occupied port produces a clear error; the default uses an available port. Mobile is a scaled presentation deck, not a redesigned mobile app.

## Verification — 2026-11-02
- **A1 passed:** isolated clean clone, Python 3.12, `uv pip install -r requirements.txt` and `uv pip install -e .`; all 43 installed pinned versions matched. `build-world --road homestead` succeeded. The real `tools.learner` CLI ran watch, learn, practice (one trial via its existing function argument) and recommend, with one simulation worker; a labeled “no change” card was produced. Full 150-trial optimization was not repeated.
- **A2 passed:** five demo tests cover real GET/HEAD delivery, text card rendering, directory/path denial, rejected POST, missing/unsafe assets, invalid ports, an occupied port and cancelled-transfer logging. Real standard-library launcher, `--help`, video/PDF/card URLs, a cancelled video transfer and Ctrl-C shutdown/temporary-copy cleanup were checked. Client disconnects log briefly; unrelated I/O errors still propagate.
- **A3 passed:** Chrome screenshots at 1280×720 and 375×812; slide keys, speaker notes, 88-second video playback, both card URLs and runbook checked. No application console errors recorded. Existing mobile scaling retained; no frontend or deck edits.
- **A4 passed:** `PYTHONPATH=src python -m unittest discover -s tests -v`: 108 tests passed in the isolated environment with pinned packages. `git diff --check` and Python compilation passed. Correctness/security diff review found no blocking issue: only allowlisted copies served, loopback bind, no report-write endpoint, input validation and actionable startup errors. All 84 protected files under learner reports, held-out reports, worlds and roads retained their original SHA-256 hashes in the source checkout. Commit is local only.
