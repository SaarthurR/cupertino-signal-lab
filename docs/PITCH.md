# Signal Learner: the story we tell

Our audience is a judge seeing this project for the first time. Start with the problem, show the system working, and explain the evidence and limits. Use the existing results; no new simulation is needed to prepare this presentation.

**One sentence:** Signal Learner uses simulated traffic observations to test timing changes and give a traffic engineer a recommendation they can accept or reject.

## Five-part presentation

| Beat | Existing slides | What we say |
|---|---|---|
| Problem | 1–2 | “Traffic changes. A timing plan needs retiming to keep up. We built a way to investigate changes before an engineer approves them.” |
| How it works | 5–8 | “We map the road, watch simulated detectors, learn a traffic pattern, try 150 plans in a practice copy, and produce a recommendation card. An engineer makes the decision. The monitoring rule can undo a change inside the simulation.” |
| Show it | 9 | “These are the same simulated cars under two timing plans. This is a recording of one run, not a live street feed. Red cars are stopped; green cars are moving.” |
| What we learned | 10–11 | “On Wolfe, the learner cut the delay score by 26% across 20 paired test runs. On De Anza, it recommended no change. A later diagnostic found the rejected plan would have been worse. Choosing not to change a plan is a useful outcome too.” |
| Limits and next step | 13–16 | “The new roads use synthetic traffic and our old timing is a stand-in. One group on Wolfe got worse, and the undo rule gave false alarms on De Anza. We have a working simulated workflow; the next step is validating what data a real engineer could provide and whether the recommendation card is useful.” |

Slides 3–4 explain signal timing and existing adaptive systems. Slide 12 compares all roads. Keep these ready for questions; use them in the main talk if the allotted format allows. Agree on speaking roles and length once the organizers' format is confirmed. Press N for the existing speaker notes.

## Keep the evidence straight

- **Measured in the hidden simulation:** Wolfe's score was about 870 → 643; De Anza stayed about 270. These are not measured commute times. Unfinished trips and teleports are penalized in the score.
- **Forecast in the practice copy:** Wolfe's card shows about 138 → 80. That is a prediction from a different model, not another version of the 870 → 643 result. De Anza's archived card describes the rejected candidate; see the [runbook](DEMO.md) for its outdated reason.
- **Fair test:** Homestead and Stevens Creek were development roads. Wolfe and De Anza were held out. Do not present development-road wins as independent validation, or the post-hoc De Anza diagnosis as part of the original test.
- **Honest scope:** no live sensors, no real light control, no proven street safety or emissions savings. An average improvement does not mean every driver benefited. The learner is model-based search, not a neural network.
- **VTA:** cite *VTA, 2024 CMP Monitoring and Conformance Report* when showing the approved hackathon material. Permission for that presentation does not make the private repository or raw files public.

## Where everything fits

| Need | Source |
|---|---|
| Present and rehearse | [Slides](../dashboard/signal-learner/index.html), [PDF](../dashboard/signal-learner/signal-learner.pdf), [video](../dashboard/signal-learner/wolfe_side_by_side.mp4), [operator runbook](DEMO.md) |
| Explain a recommendation | [Wolfe card](../reports/learner/wolfe/card.md), [De Anza card](../reports/learner/deanza/card.md) |
| Check reported results | [Frozen results](../reports/learner_heldout/results.json), [per-run scores](../reports/learner_heldout/results.csv) |
| Explain failures | [Post-hoc findings](../reports/learner_story/findings.md); these diagnose the completed test, not a new test |
| Explain the implementation | `src/learner/` observes, reconstructs, searches, recommends and monitors; `src/world/` supplies hidden traffic and evaluations; `src/signal_lab/` supplies shared simulation utilities. [Research rules](LEARNER-SPEC.md) and [test protocol](PREREGISTRATION-LEARNER.md) define the evidence boundary. |

## Proposed handoff to Prithvi

These are useful remaining contributions, not assignments made without the team agreeing:

1. **Make one backup slide about trade-offs.** Use the saved findings to show the worse-served origin on Wolfe and De Anza's 4/10 undo false alarms. Link every number to its source. Keep the original slides and frozen results intact until the team reviews the addition.
2. **Own the judge-question rehearsal.** Practice “Where is the AI?”, “Why not use an existing adaptive system?”, “Is this real traffic?”, and “Who could use it?” Record questions the current slides cannot answer; avoid making up cost or deployment claims.
3. **Check the submission package.** Confirm the judging rubric, talk length and submission requirements with the organizers; check the citation and offline video/PDF on the actual presentation laptop. Agree on speaking roles with Saarth and Advaita.

Advaita's contribution is the project map, presentation structure, explanation of results and working demo handoff. Saarth asked to keep this work outside the simulator; any further experiments or model changes should be coordinated with him.
