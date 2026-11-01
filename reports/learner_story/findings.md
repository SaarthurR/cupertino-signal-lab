# Signal Learner held-out test: what the results mean (POST-HOC)

**POST-HOC.** Written after the frozen held-out test. Nothing here changes `reports/learner_heldout/`, the
preregistration or any decision. Simulated; Wolfe and De Anza demand is synthetic. Numbers: `facts.json`.

## 1. Why the De Anza card said "no change"

The copy did predict a gain: 11.2% (1,740 s to 1,544 s per requested trip), one-sided p = 0.002 on copy seeds
10–19. That passed the gain gate (at least 2%) and the p gate (p under .05).

It failed the feasibility gate. The frozen rule allows at most 2 more teleports than the old timing on each
copy seed. The best plan had more on 4 of 10 seeds: seed 13 (+5), 14 (+3), 15 (+16) and 16 (+31). The
side-street limit passed (0.94x old). Source: `reports/learner/deanza/practice.json`, `confirm_feasible: false`.

The card's sentence "the copy predicts no clear gain" was wrong. `src/learner/card.py` now names the failed gate
for future cards. The De Anza card and its decision are unchanged.

## 2. Was "no change" right? (new seeds 230–249)

The rejected plan was run in the De Anza world against the old timing, same scoring (`deanza_posthoc.json`).

| De Anza world, seeds 230–249 | Old timing | Rejected plan |
|---|---|---|
| Delay per requested trip | 274.5 s | 292.1 s (+17.6 s, +6.4%) |
| Seeds where the plan was worse | | 13 of 20 |
| One-sided p (plan better) | | 0.96 |
| Teleports per rush hour | 1.45 | 12.15 |
| Unfinished trips | 0 | 0 |
| Worst origin-approach delay | 520.4 s | 477.7 s (-42.8 s) |

Yes, saying no was right on the main measure. The plan would have made average delay worse and teleports rose
in the world too. It did help the worst origin approach.

## 3. Why the copy showed about 1,740 s when the world shows about 270 s

Southbound De Anza at Lazaneo Dr has one lane shared by through and right-turning cars. The learner only
trusts turn counts from lanes that serve one turn, so it dropped that approach's turn counts. Nothing then told
the route fitter how many cars go straight. It guessed badly. The copy sent 3,791 cars right onto one-lane
Lazaneo Dr. The world sends about 3,340 straight on and about 400 right.

That one lane cannot carry them. The queue backs up the whole road and the copy gridlocks: about 5,100 of
12,786 trips never finish, each charged 900 s.

Check (`deanza_split_check.json`, uses world knowledge, diagnosis only): moving 8 of every 9 of those cars back
to straight-through cut copy delay on old timing from 1,703 s to 121 s, with 0 unfinished (world: 252 s).

## 4. Why the go-back rule gave false alarms on De Anza

The no-op change was undone on 4 of 10 seeds (221, 224, 225, 226). Old timing with no change at all, read by
the same rule from 17:00, flags the same 4 seeds (`go_back_control.json`). So the change did not cause the
alarms. On those seeds the world has a jam of its own: 7–12 teleports, queues at Mariani Ave northbound after
about 6 PM. The 3 watched rush hours had 0–1 teleports, so the rule's "normal range" never saw a jam day.
Wolfe control: 0 of 10.

Smallest future fix, **UNTESTED**: watch 10 rush hours instead of 3 (`WATCH_SEEDS`) so jam days fall inside
the normal range. The served-count flag has a fixed 6% floor with no day-to-day spread, so it may need one too.
The frozen rule is not changed.
