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

## Game plan: do these in order

### Step 1 · Learn the project (20 minutes)
Read **[docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md)**. It explains traffic lights from zero, what our software does, what the numbers mean, and how to answer judges.

### Step 2 · Open the slides and the demo
```sh
python3 -m tools.demo
```
It prints links. Open them in Chrome:
- **Slides:** the main deck is short (about 2.5 minutes). The slides after "Backup" are only for judge questions. Press **N** for speaker notes.
- **Engineer console:** the live demo. A clickable version of the tool a city engineer would use.
- **PDF:** backup if the slides will not open. Files: [dashboard/signal-learner/](dashboard/signal-learner/).

### Step 3 · Practice the demo path (2 minutes)
In the engineer console: **Recommendation → Approve → timing sheet → Test it → Watch**.
"Test it" runs the real simulation live in about 20 seconds. It needs the full setup (below). Without it, the page shows the saved result instead, so the demo never breaks.

### Step 4 · Prepare
| To do | Who | By |
|---|---|---|
| Ask the club leads: where to submit, deadline and time zone, pitch length, Q&A length, rubric, Wi-Fi, AI-use disclosure, private-repo access for judges | Prithvi | Nov 4 |
| Agree on roles: who presents, who drives the demo, who keeps time and handles the backup | All 3 | Nov 5 |
| Each of us reads the speaker notes and says them in our own words | All 3 | Nov 8 |
| Set up the presentation laptop (below) and run the demo with Wi-Fi **off** | Saarth | Nov 10 |
| Record a 30-second screen recording of the demo path as a backup | Advaita | Nov 12 |
| Full rehearsal, timed, twice, on the real laptop | All 3 | Nov 14 |
| Freeze the version we present; no changes after this | Saarth | Nov 15 |
| Submit early, then check a judge can open every link | Prithvi | Nov 22 |

### Step 5 · On the day
Laptop charged, Chrome open on the slides and the console, Wi-Fi off, PDF and backup video on the desktop. Main deck, then the live demo, then questions.

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
