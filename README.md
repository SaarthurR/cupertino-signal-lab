# Signal Learner

**Software that learns how traffic moves on a road, then suggests better traffic-light timing to a city engineer.**
Built in simulation by Saarth, Advaita and Prithvi for the Monta Vista AI Club hackathon (submissions due Mon Nov 30, 2026).

> Traffic counts and timing in `data/processed/vta_*` are from the Santa Clara Valley Transportation
> Authority (VTA), *2024 CMP Monitoring and Conformance Report*, shared with us by VTA, which approved their use in our
> hackathon presentation. Cite VTA, and ask VTA before reusing them.

## The project in 30 seconds

| | |
|---|---|
| **Problem** | Stevens Creek backs up toward Glenbrook at evening rush hour. The city told us (Nov 1, 2026): “Stevens Creek Blvd is running time of day plans.” The clock picks which plan runs. When traffic changes, the plans stay the same until an engineer retimes them. |
| **User** | A Cupertino traffic engineer deciding when and how to retime a road. |
| **What we built** | Signal Learner uses simulated sensor readings to model traffic, try 150 timings and give an engineer one recommendation to review. It never touches a real light. |
| **Result** | On Wolfe Road, a road the learner never saw, the simulated delay score fell **26.1%**, from 870.5 to 643.1 seconds per trip. It was lower in all 20 held-out test runs (seeds 200–219). On De Anza Boulevard, the learner recommended keeping the modeled old timing. |
| **Limits** | Everything is simulated. The test traffic was made up, the “old timing” is not Cupertino’s real timing, and Wolfe’s worst-origin delay score rose about 203 s. |
| **Next step** | Review a recommendation with a Cupertino traffic engineer using the city’s actual timing and counts. |

## Run the demo

```sh
python3 -m tools.demo
```

Open the links it prints: the slides, the engineer console and the Wolfe Road video. No setup is needed. Without the [setup below](#setup-on-a-new-laptop), the console plays a saved recording of the simulation instead of running it live.

> **Not this project’s result:** `dashboard/deck.html`, `dashboard/index.html` and `README-sim-v5.md` are the older Stevens Creek study (Oct 2026, 40.7%). Signal Learner’s result is Wolfe Road’s 26.1%. Homestead’s 41% on the backup slides is a Signal Learner practice road, not the older study either.

## Game plan: read this, do these in order

### Step 1 · Everyone learns the whole project (30 minutes)
Every one of us must be able to explain the whole project, not only our own part.
1. Read **[docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md)** top to bottom. It explains traffic lights from zero, what our software does, what the numbers mean, and the judge answers.
2. Open the **judge deck** (Google Slides in Saarth’s Drive, not in this repo). It is the main talk: slides 1–7 are the talk (about 2.5 minutes), then an “End of talk” slide; B1–B9 after it are backup for questions only, and the last slide is the 60-second version. Read every speaker note.
3. Run `python3 -m tools.demo` and open the links in Chrome:
   - **Slides:** the repo and offline version of the talk (17 slides, same numbers). Press **N** for speaker notes.
   - **Engineer console:** the demo shows the same simulated evening on Wolfe Road under two plans, modeled old timing above and our plan below.
   - **Video:** one Wolfe Rd rush hour, old timing vs our plan, side by side.
4. Click the demo once, following the [45-second script](docs/DEMO.md#demo-script-45-seconds): **Wolfe Road Review → Approve → Run side-by-side simulation at 240× → result slide**. Then look at **Deploy & monitor** and **How it connects** for questions only. They are not part of the main talk.
5. Test yourself: answer every question in [section 6 of the guide](docs/PRESENTER-GUIDE.md#6-judge-questions-and-short-answers) out loud without looking.

### Step 2 · Learn your own part

| | **Advaita: the story** | **Saarth: the simulation and the demo** | **Prithvi: the real-world side** |
|---|---|---|---|
| **Presents** | Slides 1–3: the problem, the result up front and how it works (37 s). Slide 7: our ask (10 s). | Slides 4–5: the live demo and the Wolfe Rd result (63 s). | Slide 6: no-change and our limits (20 s). Slide 7: the engineer decides (8 s). Leads Q&A with the backup slides. |
| **Learns deeply** | Guide sections [1](docs/PRESENTER-GUIDE.md#1-the-problem) and [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does). The city email and the VTA data in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). | Guide sections [3](docs/PRESENTER-GUIDE.md#3-what-signal-learner-does) and [4](docs/PRESENTER-GUIDE.md#4-the-results-and-what-the-numbers-mean). The results in [PROJECT-DETAILS](docs/PROJECT-DETAILS.md). How the code runs: `src/learner/`, `tools/learner.py`. | Guide sections [2](docs/PRESENTER-GUIDE.md#2-traffic-lights-in-2-minutes) and [5](docs/PRESENTER-GUIDE.md#5-how-it-would-connect-to-a-real-city). The sourced facts in [research-hardware](docs/research-hardware.md). The "How it connects" screen in the console. |
| **Answers judge questions on** | Why Cupertino needs this. Who the user is. What we do next. | What the AI is. Is the data real. Is the test fair. What −26% means. Could it make things worse. | What hardware is in a traffic light. How it connects. Is it safe. Don't smart systems already exist. |
| **Also owns** | The backup screen recording of the demo | The presentation laptop setup and the live demo working | Club rules, time-keeping in rehearsal, the submission |

If one of us is away on the day, the other two cover their part. That is why Step 1 is for everyone.

### Step 3 · Prepare
| To do | Who | By |
|---|---|---|
| Read the organizers’ submission email when it arrives; ask the club leads about format, pitch length, Q&A, rubric, Wi-Fi and AI-use disclosure | Prithvi | When the email arrives |
| Finish Step 1 and Step 2 | All 3 | Nov 27 |
| Put your speaker notes in your own words; fill in “Who did what” (B9) with one thing each of us built | All 3 | Nov 28 |
| Set up the presentation laptop (below) and run the demo with Wi-Fi **off** | Saarth | Nov 28 |
| Record a backup screen recording of the 45-second demo | Advaita | Nov 28 |
| Timed rehearsal twice on the real laptop, plus one where the demo “breaks” and we switch to the 60-second version | All 3 | Nov 29 |
| Freeze the version we present; no changes after this | Saarth | Nov 29 |
| Submit, then check a judge can open every link | Prithvi | Mon Nov 30 |
| If we are finalists (picked Dec 5): rehearse again before the presentation (about Dec 11, date not final) | All 3 | Dec 10 |

### Step 4 · On the day
Laptop charged. Chrome open on the judge deck and the console (already on Wolfe Road Review). Wi-Fi off. PDF and backup video on the desktop.

| Slide | Who | Seconds |
|---|---|---:|
| 1 · Hook: Stevens Creek backs up toward Glenbrook | Advaita | 12 |
| 2 · The result up front: Wolfe Rd −26% | Advaita | 14 |
| 3 · Try timing changes on a computer first | Advaita | 15 |
| 4 · Practice and test are kept apart | Saarth | 23 |
| 5 · Live demo in the console ([script](docs/DEMO.md#demo-script-45-seconds)) | Saarth | 45 |
| 6 · Result: Wolfe Rd −26.1%, lower in 20 of 20 runs | Saarth | 19 |
| 7 · Sometimes the answer is no change, and our limits | Prithvi | 21 |
| 8 · The engineer stays in charge | Prithvi | 14 |
| 9 · Our ask | Advaita | 12 |
| Hand-offs | | 5 |
| **Total** | | **180** |

The seconds are word-count targets, so time a real rehearsal. If the demo breaks, go to slide 5. If the whole talk breaks, or the slot is shorter than 2.5 minutes, give the 60-second version (last slide).

## Setup on a new laptop

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). About 7 minutes of downloads, 1.4 GB. Do it before the day, never live.
```sh
git clone https://github.com/SaarthurR/cupertino-signal-lab.git && cd cupertino-signal-lab
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt && uv pip install -e .
export PYTHONPATH=src
python -m tools.learner build-world --road wolfe   # once: makes the files the live simulation needs
python -m unittest discover -s tests              # about 1 minute, all should pass
python -m tools.demo
```

## Where things are

| Path | What |
|---|---|
| [docs/PRESENTER-GUIDE.md](docs/PRESENTER-GUIDE.md) | Learn the project and the judge answers |
| [docs/DEMO.md](docs/DEMO.md) | The 45-second demo script and the demo launcher |
| [dashboard/signal-learner/](dashboard/signal-learner/) | Repo slides, PDF, video |
| [dashboard/console/](dashboard/console/) | The engineer console (live demo) |
| [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md) | Questions for the club leads, pre-submit checks, day-of list |
| `python3 -m tools.check_links` | Checks every link in the README and docs opens |
| [docs/PROJECT-DETAILS.md](docs/PROJECT-DETAILS.md) | Every detail of the study, results and limits |
| [docs/research-hardware.md](docs/research-hardware.md) | Sourced facts on signal hardware and city systems |
| `src/learner/`, `tools/learner.py` | The learner code and its commands |
| `reports/learner_heldout/` | The final test results. Never edit or rerun. |
| `dashboard/deck.html`, `dashboard/index.html`, [README-sim-v5.md](README-sim-v5.md) | The older Stevens Creek study (40.7%). History only. |

Work on a branch and open a pull request into `main`.
