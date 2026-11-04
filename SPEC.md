> **Superseded Nov 3, 2026:** the current team plan, roles and to-dos are in the [README](README.md). This file is kept as history.

# Hackathon presentation: scope and team plan

Status: approved by Advaita's instruction to correct PR #2 to Saarth's requested scope on 2026-11-02.

## Goal
Present Signal Learner as a working simulation project motivated by rush-hour backups on Stevens Creek toward Glenbrook. Explain the original results clearly and finish with a short limitations section and a traffic-engineer ask. Keep the existing visual design.

## Scope and ownership
- Advaita: the HTML deck, matching PDF, natural speaker notes, README, demo runbook and local presentation launcher.
- Saarth: review the project story and facts; decide separately whether experimental learner/simulator changes should be accepted.
- Prithvi: proposed presentation rehearsal, organizer/submission check and help coordinating engineer feedback, subject to the team agreeing.

Experimental learner code, monitoring changes, new simulations and their reports belong in a separate draft PR. They are not required to merge the presentation. The research contract in `docs/LEARNER-SPEC.md` and all original experiment artifacts remain unchanged.

## Demo path
Run `python3 -m tools.demo`. Present 15 slides: Stevens Creek motivation, the working workflow, the saved Wolfe video, original results, one short limitations section, the proposed city workflow and the engineer ask. Use N for notes. Keep the PDF as the offline fallback. The launcher serves allowlisted presentation assets on localhost and does not run experiments or rewrite research reports.

## Acceptance checks
- **A1 — Scope:** the complete PR diff contains only the deck/PDF, README, this team plan, demo runbook, `tools/demo.py` and directly related presentation/demo tests. No simulator/learner source, research-contract edits, experimental tests or fresh-validation reports. Confirm with a file-list assertion against main.
- **A2 — Story and evidence:** remove the fresh-validation slide; keep 15 slides with one short limitations section at slide 13. Slide 11 explains in a plain sentence that its rejected-plan comparison was checked afterward. Preserve accurate original scores, signal-turn passage labels, synthetic-data labels and the VTA credit. Check every slide and its notes.
- **A3 — Working presentation:** click through all slides in Advaita's existing signed-in Chrome Profile 1 at 1280px and 375px. Check notes, keyboard navigation, video playback, card links and application errors. Regenerate the PDF and verify 15 pages and matching content. Run the full presentation-branch test suite and protected-artifact checks.
- **A4 — Review handoff:** keep the replacement presentation PR description to 3–5 plain lines and request Saarth's review. Preserve experimental work in a separate draft PR for later review. Replace the mixed PR #2 with clean branches from main and link it to both replacements. Do not merge or deploy. A student still needs to read the talk aloud and rehearse on the actual presentation laptop; assistant/browser checks are not human rehearsal.

## Boundaries
No new simulator behavior, dependencies, optimizer tuning, real signal connection or field-benefit claim. VTA approved the hackathon presentation with the exact credit *VTA, 2024 CMP Monitoring and Conformance Report*. Keep the repository and raw data private. Preserve original held-out artifacts byte-for-byte and never rerun them.

## Verification — 2026-11-02
- **A1 passed:** an exact file-list assertion found only the eight allowed presentation files; simulator/learner source and the research contract match main.
- **A2 passed:** all 15 slides and speaking notes reviewed; the later De Anza comparison is explained in one plain sentence; the removed fresh-validation slide is absent. The PDF has 15 pages at 1440 × 810 points, with matching text and inspected page renders.
- **A3 passed:** the presentation branch's full 111-test suite passed. Every slide was exercised at 1280px and 375px in the existing Desktop Chrome Profile 1; no horizontal overflow or application errors were recorded. Keyboard navigation, notes and advancing video playback were checked. Real demo HTTP/card delivery is covered by the demo tests. All 104 protected original artifacts retained their hashes.
- **A4 prepared:** the presentation and experimental research use separate branches from main. The research branch passed 148 tests, while its failed scientific validation remains unresolved. Student spoken rehearsal and the actual presentation-laptop check remain pending.
