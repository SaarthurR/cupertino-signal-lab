# Team tasks: Nov 27–29, 2026

**Read this first.** It is written for you and for any AI agent you use. Give your agent this whole file.

## Where we are

The research, the data and the result are **done and locked**. Do not rerun or change them.
What is left is how we **show** it: the slide deck and the engineer console. Both are AI-made first drafts.
Your job is to make them a real, good presentation that a judge understands in one viewing.

## Who does what

| Person | Owns | Done means |
|---|---|---|
| **Advaita** | **The slide deck**: `dashboard/signal-learner/index.html` (talk slides 1–7, the backup slides B1–B9, the 60-second slide). | Every slide reads clearly in 5 seconds. The 7 talk slides flow as one story. It looks like a real product launch, not a school template. |
| **Prithvi** | **The engineer console** (the live demo): `dashboard/console/` (`index.html`, `console.js`, `console.css`, `sim.js`, `charts.js`). | Someone who never saw it understands each screen of the Wolfe Road path (1 The problem → 2 The fix → 3 The proof → Approve) in 5 seconds. The 45-second demo works with no confusion. |
| **Saarth** | Reviews and merges your PRs. Presents the demo. Freezes the final version on Nov 29. | |

When you finish your part, review the other person's part once, as a judge would.

## Step 0: get the latest code (do this first)

1. One of you approves **PR #13** on GitHub. The repo needs one approval before Saarth can merge it. Saarth merges it.
2. Then: `git checkout main && git pull`
3. Make your own branch: `git checkout -b deck/<your-name>` or `console/<your-name>`.

## Step 1: understand the project (30 minutes)

1. Read [PRESENTER-GUIDE.md](PRESENTER-GUIDE.md) top to bottom.
2. Run the demo: `python3 -m tools.demo`. Open the links it prints in Chrome.
   - `/` is the slide deck. Arrow keys move. **N** shows speaker notes.
   - On slide 4, press **Right**. The live console opens. **Back to slides** returns to slide 5.
3. Click the demo once, following [DEMO.md](DEMO.md#demo-script-45-seconds).

## Step 2: improve your part

Work on your own branch. Look at your part on a laptop screen (1440×900) and a projector-size screen (1920×1080).
For each slide or screen, ask:
- What is the **one** thing a judge should take from this? Is it the biggest thing on the screen?
- Can I remove a word, a box or a number and lose nothing? Then remove it.
- Is every number labelled in plain words: what it measures, and where it comes from?
- Does it flow from the screen before it?

### Rules (for you and your agent)

- **No new numbers or claims.** Every number must already be in the data or in the table below. You may cut words; you may not add facts.
- **Do not change** anything in `reports/`, `src/`, `roads/` or `data/`. Those are the research. They are locked.
- Use these exact words for the one weak result: "worst-origin delay score" or "worst-off starting point" got slower. **Never** say "one group got worse".
- No filler lines like "tested on a computer first". No emojis.
- Keep it working offline. No fonts or scripts from the internet. A new image file must also be added to `ASSETS` in `tools/demo.py`, or it will not load.
- Keep the deck → console → deck flow working (slide 4 → Right → console → **Back to slides** → slide 5).

### The locked numbers

| Number | What it means (say it this way) |
|---|---|
| **−26%** (870.5 → 643.1 s) | The result. Average delay per trip on Wolfe Road, over 20 test evenings the tool never practiced on. Lower on **all 20**. This is the number we quote. |
| −42% (137.6 → 79.6 s) | The tool's own guess before testing, on its practice copy. Only used to pick the plan. Not the result. |
| −24% (856.0 → 650.2 s) | The one evening shown in the demo. |
| about +203 s (2,565.8 → 2,768.6 s) | Wolfe's worst-origin delay score got slower. Our main limit. |
| De Anza: no change (269.9 s) | The best new plan failed a jam check, so the tool kept the old timing. A later check found that plan was 6.4% worse, on 13 of 20 evenings. |
| 968 → 217 | Cars that never got through, per evening, on Wolfe. Each counts as 15 minutes of delay. |
| 150 | Timing plans the tool tried on the practice copy. |
| Real streets | Not tested. Everything is a simulation. It never touches a real light. |

## Step 3: check, then open a PR

1. `python3 -m tools.check_links` → must say `all links open`.
2. `python -m unittest discover -s tests` → must say `OK`. (Run it with `PYTHONPATH=src`.)
3. Click through the full talk and the demo once more.
4. Push your branch and open a PR to `main`. Add before and after screenshots of what you changed.

## Dates

| What | Who | By |
|---|---|---|
| Approve PR #13 | Advaita or Prithvi | Nov 27 |
| Deck PR | Advaita | Nov 28 |
| Console PR | Prithvi | Nov 28 |
| Fill in "Who did what" (backup slide B9): one thing each of us built | All 3 | Nov 28 |
| Timed rehearsal twice, plus one where the demo "breaks" | All 3 | Nov 29 |
| Freeze: no changes after this | Saarth | Nov 29 |
| Submit | Prithvi | Mon Nov 30 |

Speaking parts, rehearsal and the submission steps are in the [README game plan](../README.md#game-plan-read-this-do-these-in-order) and [SUBMISSION-CHECKLIST.md](SUBMISSION-CHECKLIST.md).
