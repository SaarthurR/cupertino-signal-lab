# Signal Learner (Cupertino Signal Lab)

**Monta Vista AI Club hackathon project.** The hackathon runs for one week, starts about Nov 16, 2026, and ends Mon Nov 23, 2026.
The club leads said pre-built code is allowed.

If you are new, read this page, then run `python3 -m tools.demo` from the cloned repo.
Open the printed Slides URL. The launcher uses only Python's standard library and runs no simulations.
It also prints links to the PDF, video and the two synthetic-road engineer cards. Press N in the slides for speaker notes.
Start with the [revised slide deck](dashboard/signal-learner/index.html).
Operator walkthrough: [docs/DEMO.md](docs/DEMO.md). Presentation scope and team plan: [SPEC.md](SPEC.md).
Plain-English version: [docs/WHAT-WE-BUILT.md](docs/WHAT-WE-BUILT.md).

**This repo is private. Keep the code and data inside the team.** VTA said on Nov 2 that we may use its counts and
Vistro data in our hackathon presentation. Every slide or page that shows them must cite: *VTA, 2024 CMP Monitoring and Conformance Report*.

## The project in one minute

Traffic changes, but most traffic lights run timing plans that stay the same until someone retimes them.
Smart systems that change timing on the go exist, but few lights have them, because they cost money and take time to set up.

Signal Learner is an inspectable simulation workflow. On a configured road, it:

1. **Maps** the road from a public map.
2. **Watches** the road sensors while the old timing keeps running.
3. **Learns** the traffic pattern and builds a practice copy of the road.
4. **Practices** by trying 150 timing plans on the copy.
5. **Recommends** a change on a one-page card. An engineer approves or rejects it.
6. **Checks** the sensors afterward and goes back to the old timing if traffic gets clearly worse.

## What it is not

Everything so far runs in a computer simulation (SUMO, a free traffic simulator).

- It is not connected to any real light, camera, sensor or city system.
- It does not control lights. It only makes recommendations.
- It is not a neural network. It learns a traffic pattern from sensor data, then uses a model-based search (Optuna).
- It has not been compared with Cupertino's real timing.

## Rules for what we say

**We may say:** in simulation, on the labeled roads, a plan learned only from sensor data did or did not beat stale timing.

**We must not say:** live cameras, live control, street safety, calibrated traffic, neural networks, emissions savings,
"works on any intersection", or any comparison with Cupertino's real timing.

Every results screen says "simulated". Any VTA number credits VTA. Full rules: [docs/LEARNER-SPEC.md](docs/LEARNER-SPEC.md).

## Original study (Nov 1, 2026)

| Part | Status |
|---|---|
| Original learner software, all six steps | Built; original test results preserved |
| Independent code review before the test | Passed |
| One-time test on two unseen roads | Done |
| Slides (15), PDF, Wolfe Rd video | Revised for the judge presentation; results checked against saved artifacts |
| Real city data | Not received |

### Results

We wrote the test rules first and ran the test once. The software got sensor data only. The true traffic stayed hidden.

| Road | Role | Traffic | Old timing | Signal Learner | Fresh retiming with perfect counts |
|---|---|---|---|---|---|
| Wolfe Rd | Unseen test | Made up by us | 870 s | **643 s (-26%)** | 846 s |
| De Anza Blvd | Unseen test | Made up by us | 270 s | 270 s ("no change") | 481 s |
| Homestead Rd | Practice road | Made up by us | 130 s | 77 s | 113 s |
| Stevens Creek Blvd | Practice road | VTA 2024 counts | 682 s | 471 s | 661 s |

On Stevens Creek, our earlier plan "v5" scored 369 s. It had full access to the true traffic, so it still beats the learner there.

The numbers are a **delay score**, not stopwatch time: total completed-trip delay plus 900 seconds per unfinished trip and stuck-car removal, divided by all requested trips.

On De Anza, a later check on new runs (not part of the test) showed the plan the learner rejected was 6.4% worse. So "no change" was the right call.

### Weak points

Say these before someone else finds them.

- The traffic on the new roads is made up.
- "Old timing" is a stand-in we built from out-of-date traffic. It is not Cupertino's timing.
- It watched only 3 simulated evening rush hours.
- On Wolfe Rd, one group of drivers got about 203 s worse.
- The practice copy is not close to the true traffic. On Wolfe Rd it had 24% fewer signal-turn passages (a vehicle may cross several signals); this is not a unique-trip count. On De Anza it was badly wrong, because the software misread one lane shared by straight and right-turning cars.
- The undo check failed its test on De Anza. It undid a harmless change on 4 of 10 runs.
- Two unseen roads is a small test.

## What the city said

- **Oct 31:** we emailed Cupertino Traffic & Engineering asking for data. No reply yet.
- **Nov 1:** David Stillman, Transportation Manager, answered our question: "Stevens Creek Blvd is running time of day plans."
- **VTA** sent the 2024 counts and timing reports on Oct 29. On Nov 2, Kia Sharifi (VTA) answered our Oct 30 questions:
  we may use the data in the presentation with the citation *VTA, 2024 CMP Monitoring and Conformance Report*. VTA only counted sites 211 (De Anza) and
  217 (Stelling), not the signals between them. The current timing sheets come from the City of Cupertino through its
  public records portal, https://cityofcupertinoca.nextrequest.com/ (VTA's Vistro timing may not match the street today).

Saarth holds these email threads. Send any new question through Saarth, so the city and VTA do not get mixed messages.

## How we got here

1. **Stevens Creek simulation (Oct 21-30).** We tuned one set of timing plans once. It scored 40.7% better than a textbook plan, but only in simulation, and not against city timing. It felt like a one-time result anyone could produce. Saved at tag `sim-v5-final`; details in [README-sim-v5.md](README-sim-v5.md).
2. **Signal Advisor (Oct 31).** Software that picks from a few fixed plans. It works in simulation, but it cannot learn a new road. **An independent review failed it:** it was fit on more data than its written rules allow. Do not present its results unless it is refit and retested on new seeds. Code: `src/signal_lab/advisor.py`, `closed_loop.py`.
3. **Signal Learner (Nov 1).** The current project.

`dashboard/deck.html` and `dashboard/index.html` are the **old** project. Use `dashboard/signal-learner/`.

## Further validation

| Job | Notes |
|---|---|
| Resolve shared-lane ambiguity | Improve reconstruction and validate a copy-quality gate separately |
| Validate rollback | Test harmful-change detection and harmless-change false alarms separately |
| Test on fresh roads | Fix roads, seeds and rules before running; report every outcome |
| Use real city data | Only if the city sends it |
| Practice the presentation | Speaker notes are in the slides |

**Submission check:** confirm the organizers' judging criteria. VTA approved presentation use with the exact credit above; keep the repository and raw data private.

The presentation scope and proposed team handoff are in [SPEC.md](SPEC.md). Experimental learner changes are reviewed separately; this presentation update does not change the simulator or revalidate the historical results.

## Test rules that protect the results

- Never change, delete or rerun `reports/learner_heldout/`. That test is final. The command refuses to rerun.
- Do not tune on test seeds or on Wolfe Rd or De Anza Blvd. New ideas need new roads and new seeds.
- Report results as they come, wins and losses alike.
- Do not remove `reports/results_advisor_v2.csv` or its test marker.

## Run it

Python 3.12 and [uv](https://docs.astral.sh/uv/). SUMO installs with the requirements.

```sh
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
export PYTHONPATH=src

python -m unittest discover -s tests            # about 1 minute
python -m tools.learner build-world --road homestead  # required: generated world routes are excluded from Git
python -m tools.learner run --road homestead    # all steps on one practice road, about 15 minutes
```

Results go to `reports/learner/<road>/`. Start with `card.md`, the engineer's card.
The two Homestead commands replace its development outputs; use your own checkout or a disposable copy
to preserve a teammate's results. They are separate from `python -m tools.demo`, which only presents saved files.
Keep the completed held-out test unchanged; it is not a setup step.

## Where things are

| Path | What it holds |
|---|---|
| `dashboard/signal-learner/` | Slides, PDF, video |
| `docs/WHAT-WE-BUILT.md` | Plain-English summary |
| `docs/LEARNER-SPEC.md` | The idea and the claim rules |
| `docs/PREREGISTRATION-LEARNER.md` | The test rules, written before the test |
| `src/learner/`, `src/world/`, `tools/learner.py` | The learner, the hidden-traffic worlds, the commands |
| `reports/learner/` | Each road's feed, pattern, plan and card |
| `reports/learner_heldout/` | The final test results |
| `reports/learner_story/` | Why the results came out as they did, labeled post-hoc |
| `src/signal_lab/` | Older simulator code the learner reuses |

**Branches:** work on a branch and open a pull request into `main`. Old work: tags `sim-v5-final`, `calib-probe` and branch `old-2018-model`.
