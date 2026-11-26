# Submission and club checklist (Prithvi's part)

Prithvi owns the club rules, time-keeping in rehearsal and the submission (see [README Step 3](../README.md#step-3--prepare)).
This page turns that into things to ask, check and tick. Fill in the blanks as answers arrive. Do not guess any of them.

## 1. Questions for the club leads

Copy this into a message:

> Hi! Quick questions for the Monta Vista AI Club hackathon (submissions due Mon Nov 30, 2026) from the Signal Learner team:
> 1. Where do we submit (form, email, or a repo link), and who receives it?
> 2. What is the exact deadline, including the time zone?
> 3. How long is the pitch, and how long is Q&A?
> 4. Is there a rubric or judging criteria we can see?
> 5. Will the room have Wi-Fi? Our demo runs fully offline on a laptop, so we only need a screen or HDMI.
> 6. Do you need a statement about how we used AI tools, and what format?
> 7. Can the judges open a private GitHub repo? If not, the repo needs to be public.
> 8. Our traffic counts come from VTA. Do you need anything from us about data credit or permission? (We credit "VTA, 2024 CMP Monitoring and Conformance Report".)

| # | Question | Answer | Asked | Answered |
|---|---|---|---|---|
| 1 | Where to submit | | | |
| 2 | Deadline and time zone | | | |
| 3 | Pitch length and Q&A length | | | |
| 4 | Rubric | | | |
| 5 | Wi-Fi in the room | | | |
| 6 | AI-use disclosure | | | |
| 7 | Judge access to the repo | | | |
| 8 | Data credit | | | |

If the pitch is shorter than our 3-minute talk, use the 60-second version (last slide of the judge deck).

## 2. Before submitting

- [ ] `python3 -m tools.check_links` says `all links open`. Add `--web` once with internet to check outside links too.
- [ ] `python -m unittest discover -s tests` says `OK`.
- [ ] `python3 -m tools.demo` starts, and the slides, console, video and PDF links all open.
- [ ] Repo visibility matches what the club said in question 7.
- [ ] The VTA credit is in the README and on the slides.
- [ ] Nothing in `reports/learner_heldout/` has changed (never edit or rerun it).
- [ ] The version being submitted is the one tagged or frozen by Saarth.
- [ ] Open every link in the submission from a signed-out browser window, as a judge would.

## 3. On the day

- [ ] Laptop charged, Chrome open on the slides and the console, Wi-Fi off.
- [ ] PDF and the backup video on the desktop.
- [ ] A timer ready. Say the time at 60 and 120 seconds in rehearsal.
- [ ] Speaker order and seconds: the speaker notes in the judge deck (each slide's notes start with who speaks and for how long).

## 4. Prithvi's own part

- Slides 7–8 in the judge deck: limits, and how it would fit the city. Read [Presenter Guide sections 2 and 5](PRESENTER-GUIDE.md#2-traffic-lights-in-2-minutes) and [research-hardware](research-hardware.md).
- Leads Q&A. Be able to answer the hardware, safety and "don't smart systems already exist?" questions in [Presenter Guide section 6](PRESENTER-GUIDE.md#6-judge-questions-and-short-answers) without looking.
