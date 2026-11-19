# Signal Learner spec

## The idea

Most signals run plans that stay the same until someone retimes them. Adaptive systems exist (SCOOT, SCATS,
InSync, Surtrac, SynchroGreen) but reach few signals. Setting one up takes sensors, money and weeks of work.

Signal Learner is the cheap first step. Point it at a new road and it:

1. **Onboards** the road from the public map, with the road's old timing left running.
2. **Watches** a few days of the detector feed (`docs/FEED.md`). It changes nothing.
3. **Learns** the traffic pattern and builds a simulated copy of the road from what it saw.
4. **Practices** in the copy: a search tries many timings over many simulated rush hours.
5. **Recommends** a bounded change, with its reason and expected effect. An engineer approves or rejects it.
6. **Checks** the detector feed during a simulated trial. The trial returns to old timing after 15 minutes and records any alarm separately.

**It never writes to a real signal.** In simulation, an approved change is applied by the simulator.

## Frozen hackathon test

Each road has a "world": a SUMO run with demand the learner cannot read. The learner gets only the road map,
the signal list, the old timing and the feed. A test fails if learner code reads world demand or routes.
A guard test must enforce this.

- **Dev roads:** Stevens Creek (world = the VTA 2024 demand), one new road. May be used freely.
- **Held-out roads:** two new Cupertino roads, chosen and written in the preregistration before any learner run
  on them. World demand on new roads is generated from a fixed seed and is labeled synthetic.
- **Old timing:** a textbook actuated plan built from stale demand that differs from the world. It stands in for
  an out-of-date plan. It is not Cupertino's timing.
- **Watch period:** 3 simulated PM rush hours with different seeds. Test seeds are never seen by the learner.

The archived Wolfe and De Anza results use one synthetic demand profile per road and multiple SUMO seeds per
profile. The [preregistration](PREREGISTRATION-LEARNER.md) describes those results. The follow-up below uses
separate inputs and leaves that record intact.

## Limits on a recommendation

Keep phase order, clearance and pedestrian-related intervals. Bound each change to green settings and offsets,
with the same minimums as the existing plans. The change must be readable by an engineer as one short card.

## May claim, must not claim

May claim: in simulation, on labeled roads, a plan learned only from the feed did or did not beat stale timing.
May say "learned the traffic pattern" and "model-based search" (Optuna's TPE). May explain why a neural net was
not the first choice: RL needs hundreds of simulated runs, and we found no live signal using it.

Must not claim: live cameras, live control, street safety, calibrated traffic, neural networks, emissions savings,
"works on any intersection" beyond the roads tested, or any comparison with Cupertino's real timing.
Every screen says "simulated". VTA numbers carry VTA credit.

## Connection plan (shown in the demo, not built)

1. Read: data exports or high-resolution controller logs (ATSPM is the open tool) into the feed format.
2. Recommend: an engineer enters an approved change by hand in the city's central system. No connection is needed.
3. Automatic (NTCIP 1202): only with city approval, much later.

Open with the city: which system runs these signals, whether adaptive timing is in use, who owns them.

## Stop rule

Results are reported as they come, wins and losses alike. No re-tuning on test seeds or held-out roads. If the
learner does not beat stale timing, the demo says so and shows the current advisor as the working fallback.

## Follow-up research

- **Check the copy before search.** Require at least 85% of the approach-by-quarter-hour counts to have GEH below 5,
  at most 15% aggregate absolute count error, and at most 10 points of mean absolute occupancy error. Failing any
  check leaves old timing in place and skips Optuna. The fit records the inputs and the copy it scored. If any of
  them change, run learning and practice again before issuing a recommendation.
- **Check every approach.** A candidate can raise an origin approach's delay score by at most 5% on each paired
  seed used for search and confirmation. The existing side-street and relocation checks also apply. The card shows
  old and candidate scores by origin and the largest paired increase.
- **Measure alarms independently.** An alarm needs three consecutive matched five-minute windows from a baseline
  with at least three observation runs. A missing or partial window breaks the streak. Check occupancy and served
  counts against the observed variation. A scheduled return is verified from every simulated signal's program
  trace. Compare the held degraded plan's score with the paired no-op control to identify harm. The alarm check
  requires detection of at least 80% of harmful runs and alarms on at most 20% of either harmless control group.

Run the separate experiment with the repository's pinned Python 3.12 environment and a new output directory:

```sh
PYTHONPATH=src python -m tools.validate_learner /tmp/signal-learner-grid
```

The runner builds a synthetic two-signal corridor. It uses one demand profile to create the initial timing,
three different profiles for observations, and three more for evaluation. It runs three matched simulator seeds
on each evaluation profile. The output directory contains the study settings, hashes for the distinct route files,
per-seed metrics and actual signal transitions. The runner refuses an existing output directory.

In the two-signal grid, 28.1% of counts met the GEH target, aggregate absolute count error was 47.6%, and mean
absolute occupancy error was 14.4 points. The learner kept the old timing and ran zero search trials.
All 18 bounded trials restored both signals at 900 seconds. The alarm detected 0 of 9 harmful cases within the
trial window and flagged 0 of 9 no-op controls. The alarm failed the detection check and remains advisory.

City timing and simultaneous field measurements of traffic, queues and travel times are needed for a city comparison.
