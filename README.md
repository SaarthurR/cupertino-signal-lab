# Signal Learner

**Software that learns how traffic moves on a road, then suggests better traffic-light timing to a city engineer.**
Built in simulation by Saarth, Advaita and Prithvi for the Monta Vista AI Club hackathon (Nov 16–23, 2026).

> Traffic counts and timing in `data/processed/vta_*` are from the Santa Clara Valley Transportation
> Authority (VTA), *2024 CMP Monitoring and Conformance Report*, shared with us by VTA. Credit VTA if you reuse them.

## The project in 30 seconds

| | |
|---|---|
| **Problem** | Stevens Creek backs up toward Glenbrook. The city told us (Nov 1, 2026) its lights run fixed time-of-day plans. Traffic changes; the plans stay the same until an engineer retimes them. |
| **User** | A Cupertino traffic engineer deciding when and how to retime a road. |
| **What we built** | Signal Learner uses simulated sensor readings to model traffic, try 150 timings and give an engineer one recommendation to review. It never touches a real light. |
| **Result** | On Wolfe Road, the simulated delay score fell 26%. It was lower in all 20 held-out runs. On De Anza Boulevard, the learner recommended keeping the modeled old timing. |
| **Honest limit** | Everything is simulated. A real engineer, real timing files and real streets come next. |
| **Next step** | Review a recommendation with a Cupertino traffic engineer using the city’s actual timing and counts. |

## Game plan: read this, do these in order

### Step 1 · Everyone learns the whole project (30 minutes)
Every one of us must be able to explain the whole project, not only our own part.
1. Read **[docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md)** top to bottom. It explains traffic lights from zero, what our software does, what the numbers mean, and the judge answers.
2. Run `python3 -m tools.demo` and open the links it prints in Chrome:
   - **Slides:** slides 1–6 are the talk, 150 seconds including the live demo. Slides 7–17 are backup, only for judge questions. Press **N** for speaker notes. Read every note.
   - **Engineer console:** the demo shows the same simulated evening on Wolfe Road under two plans, modeled old timing above and our plan below. The console plays the saved run if SUMO or its generated inputs are missing.
   - **Video:** one Wolfe Rd rush hour, old timing vs our plan, side by side.
3. Click the demo path in the console once, following the timed script in [docs/DEMO.md](docs/DEMO.md#demo-script-85-seconds): **Corridors → Wolfe Road → Vallco Pkwy → Review → Approve → Run the simulation at 240× → Deploy & monitor**. Then open **How it connects** (left menu).
4. Test yourself: answer every question in [section 6 of the guide](docs/PRESENTER-GUIDE.md#6-judge-questions-and-short-answers) out loud without looking.

### Step 2 · Learn your own part

| | **Advaita: the story** | **Saarth: the simulation and the demo** | **Prithvi: the real-world side** |
|---|---|---|---|
| **Presents** | Slides 1–2: the hook, the problem and our user (23 s). Slide 6: the close and our ask (10 s). | Slide 3 and the live demo in the engineer console (85 s). Slide 4: the Wolfe Rd result (12 s). | Slide 5: how it would connect to a real city (15 s). Leads Q&A with the backup slides. |
| **Learns deeply** | Guide sections [1](docs/PRESENTER-GUIDE.md#1-the-problem) and [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does). The city email and the VTA data in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). | Guide sections [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does) and [4](docs/PRESENTER-GUIDE.md#4-the-results-and-what-the-numbers-mean). The results in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). How the code runs: `src/learner/`, `tools/learner.py`. | Guide sections [2](docs/PRESENTER-GUIDE.md#2-traffic-lights-in-2-minutes) and [5](docs/PRESENTER-GUIDE.md#5-how-it-would-connect-to-a-real-city). The sourced facts in [research-hardware](docs/research-hardware.md). The "How it connects" screen in the console. |
| **Answers judge questions on** | Why Cupertino needs this. Who the user is. What we do next. | What the AI is. Is the data real. Is the test fair. What −26% means. Could it make things worse. | What hardware is in a traffic light. How it connects. Is it safe. Don't smart systems already exist. |
| **Also owns** | The backup screen recording of the demo | The presentation laptop setup and the live demo working | Club rules, time-keeping in rehearsal, the submission |

If one of us is away on the day, the other two cover their part. That is why Step 1 is for everyone.

### Step 3 · Prepare
| To do | Who | By |
|---|---|---|
| Ask the club leads about submission, deadline and time zone, pitch length, Q&A, rubric, Wi-Fi and AI-use disclosure | Prithvi | Nov 4 |
| Finish Step 1 and Step 2 | All 3 | Nov 7 |
| Rewrite your slides' speaker notes in your own words | All 3 | Nov 8 |
| Set up the presentation laptop (below) and run the demo with Wi-Fi **off** | Saarth | Nov 10 |
| Record a screen recording of the 85-second demo path as a backup | Advaita | Nov 12 |
| Quiz each other on the judge questions, swapping parts | All 3 | Nov 13 |
| Full rehearsal, timed, twice, on the real laptop | All 3 | Nov 14 |
| Freeze the version we present; no changes after this | Saarth | Nov 15 |
| Submit early, then check a judge can open every link | Prithvi | Nov 22 |

### Step 4 · On the day
Laptop charged. Chrome open on the slides and the console. Wi-Fi off. PDF and backup video on the desktop.
Order: Advaita (slides 1–2) → Saarth (slide 3, live demo, slide 4) → Prithvi (slide 5) → Advaita (slide 6) → questions, using backup slides 7–17.

| Part | Who | Seconds |
|---|---|---:|
| 1 · Hook: Stevens Creek backs up to Glenbrook | Advaita | 8 |
| 2 · Problem and who it's for | Advaita | 15 |
| 3 · Live demo in the console ([script](docs/DEMO.md#demo-script-85-seconds)) | Saarth | 85 |
| 4 · Result: Wolfe Rd −26%, simulation | Saarth | 12 |
| 5 · How it connects to the city | Prithvi | 15 |
| 6 · Our ask | Advaita | 10 |
| Hand-offs | | 5 |
| **Total** | | **150** |

For a 2-minute slot, cap the demo at 67 seconds. From Wolfe Road go straight to Review, then show the simulation at 240×. End on the comparison card and return to slide 5. The card already shows the Wolfe result.

## Setup on a new laptop

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). About 7 minutes of downloads, 1.4 GB.
```sh
git clone https://github.com/SaarthurR/cupertino-signal-lab.git && cd cupertino-signal-lab
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt && uv pip install -e .
export PYTHONPATH=src
python -m tools.learner build-world --road wolfe   # once: makes the files the live simulation needs
python -m unittest discover -s tests              # about 1 minute, all should pass
python -m tools.demo
```
Slides and the console need only `python3 -m tools.demo`, no setup. Without the setup, the Simulate screen plays a saved recording of the same evening instead of running it live.

## Where things are

| Path | What |
|---|---|
| [docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md) | Learn the project and the judge answers |
| [dashboard/signal-learner/](dashboard/signal-learner/) | Slides, PDF, video |
| [dashboard/console/](dashboard/console/) | The engineer console (live demo) |
| [docs/DEMO.md](docs/DEMO.md) | How the demo launcher works |
| [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md) | Questions for the club leads, pre-submit checks, day-of list |
| `python3 -m tools.check_links` | Checks every link in the README and docs opens |
| [docs/PROJECT-DETAILS.md](docs/PROJECT-DETAILS.md) | Every detail of the study, results and limits |
| [docs/research-hardware.md](docs/research-hardware.md) | Sourced facts on signal hardware and city systems |
| `src/learner/`, `tools/learner.py` | The learner code and its commands |
| `reports/learner_heldout/` | The final test results. Never edit or rerun. |

Work on a branch and open a pull request into `main`.
