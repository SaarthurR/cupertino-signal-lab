# Signal Learner

**Software that learns how traffic moves on a road, then suggests better traffic-light timing to a city engineer.**
Built in simulation by Saarth, Advaita and Prithvi for the Monta Vista AI Club hackathon (Nov 16–23, 2026).

> This repo is private. VTA allowed its counts in our presentation only. Every slide that shows them cites
> *VTA, 2024 CMP Monitoring and Conformance Report*.

## The project in 30 seconds

| | |
|---|---|
| **Problem** | Stevens Creek backs up toward Glenbrook. The city told us (Nov 1, 2026) its lights run fixed time-of-day plans. Traffic changes; the plans stay the same until an engineer retimes them. |
| **User** | A Cupertino traffic engineer deciding when and how to retime a road. |
| **What we built** | Signal Learner watches a road's sensors, learns the traffic pattern, tries 150 timing plans on a practice copy, and hands the engineer one card to approve or reject. It never touches a real light. |
| **Result** | On a test road it had never seen (Wolfe Rd), the delay score dropped 26% and it won all 20 test runs. On a second unseen road (De Anza) it said "keep the old timing", which was the right call. |
| **Honest limit** | Everything is simulated. A real engineer, real timing files and real streets come next. |

## Game plan: read this, do these in order

### Step 1 · Everyone learns the whole project (30 minutes)
Every one of us must be able to explain the whole project, not only our own part.
1. Read **[docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md)** top to bottom. It explains traffic lights from zero, what our software does, what the numbers mean, and the judge answers.
2. Run `python3 -m tools.demo` and open the links it prints in Chrome:
   - **Slides:** slides 1–9 are the talk, about 2.5 minutes plus the demo. Slides 10–17 are backup, only for judge questions. Press **N** for speaker notes. Read every note.
   - **Engineer console:** the live demo, a clickable version of the tool a city engineer would use. Click every screen.
   - **Video:** one Wolfe Rd rush hour, old timing vs our plan, side by side.
3. Click this path in the console once: **Recommendation → Approve → timing sheet → Test it → Watch → How it connects.**
4. Test yourself: answer every question in [section 6 of the guide](docs/PRESENTER-GUIDE.md#6-judge-questions-and-short-answers) out loud without looking.

### Step 2 · Learn your own part

| | **Advaita: the story** | **Saarth: the simulation and the demo** | **Prithvi: the real-world side** |
|---|---|---|---|
| **Presents** | Slides 1–3: the hook, the problem and our user, what we built. Slide 9: the close and our ask. | Slide 4 and the live demo in the engineer console. Slides 5–6: the Wolfe Rd and De Anza results. | Slide 7: how it would connect to a real city. Slide 8: limits and next steps. |
| **Learns deeply** | Guide sections [1](docs/PRESENTER-GUIDE.md#1-the-problem) and [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does). The city email and the VTA data in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). | Guide sections [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does) and [4](docs/PRESENTER-GUIDE.md#4-the-results-and-what-the-numbers-mean). The results in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). How the code runs: `src/learner/`, `tools/learner.py`. | Guide sections [2](docs/PRESENTER-GUIDE.md#2-traffic-lights-in-2-minutes) and [5](docs/PRESENTER-GUIDE.md#5-how-it-would-connect-to-a-real-city). The sourced facts in [research-hardware](docs/research-hardware.md). The "How it connects" screen in the console. |
| **Answers judge questions on** | Why Cupertino needs this. Who the user is. What we do next. | What the AI is. Is the data real. Is the test fair. What −26% means. Could it make things worse. | What hardware is in a traffic light. How it connects. Is it safe. Don't smart systems already exist. |
| **Also owns** | The 30-second backup recording of the demo | The presentation laptop setup and the live demo working | Club rules, time-keeping in rehearsal, the submission |

If one of us is away on the day, the other two cover their part. That is why Step 1 is for everyone.

### Step 3 · Prepare
| To do | Who | By |
|---|---|---|
| Ask the club leads: where to submit, deadline and time zone, pitch length, Q&A length, rubric, Wi-Fi, AI-use disclosure, private-repo access for judges | Prithvi | Nov 4 |
| Finish Step 1 and Step 2 | All 3 | Nov 7 |
| Rewrite your slides' speaker notes in your own words | All 3 | Nov 8 |
| Set up the presentation laptop (below) and run the demo with Wi-Fi **off** | Saarth | Nov 10 |
| Record a 30-second screen recording of the demo path as a backup | Advaita | Nov 12 |
| Quiz each other on the judge questions, swapping parts | All 3 | Nov 13 |
| Full rehearsal, timed, twice, on the real laptop | All 3 | Nov 14 |
| Freeze the version we present; no changes after this | Saarth | Nov 15 |
| Submit early, then check a judge can open every link | Prithvi | Nov 22 |

### Step 4 · On the day
Laptop charged. Chrome open on the slides and the console. Wi-Fi off. PDF and backup video on the desktop.
Order: Advaita (slides 1–3) → Saarth (slide 4, live demo, slides 5–6) → Prithvi (slides 7–8) → Advaita (slide 9) → questions, using backup slides 10–17.

## Setup on a new laptop

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). About 7 minutes of downloads, 1.4 GB.
```sh
git clone https://github.com/SaarthurR/cupertino-signal-lab.git && cd cupertino-signal-lab
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt && uv pip install -e .
export PYTHONPATH=src
python -m tools.learner build-world --road wolfe   # once: makes the files the live test needs
python -m unittest discover -s tests              # about 1 minute, all should pass
python -m tools.demo
```
Slides and the console without the live test need only `python3 -m tools.demo`, no setup.

## Where things are

| Path | What |
|---|---|
| [docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md) | Learn the project and the judge answers |
| [dashboard/signal-learner/](dashboard/signal-learner/) | Slides, PDF, video |
| [dashboard/console/](dashboard/console/) | The engineer console (live demo) |
| [docs/DEMO.md](docs/DEMO.md) | How the demo launcher works |
| [docs/PROJECT-DETAILS.md](docs/PROJECT-DETAILS.md) | Every detail of the study, results and limits |
| [docs/research-hardware.md](docs/research-hardware.md) | Sourced facts on signal hardware and city systems |
| `src/learner/`, `tools/learner.py` | The learner code and its commands |
| `reports/learner_heldout/` | The final test results. Never edit or rerun. |

Work on a branch and open a pull request into `main`.
