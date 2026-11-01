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
6. **Checks** the result on the feed after approval, and goes back to the old timing if traffic gets worse.

**It never writes to a real signal.** In simulation, an approved change is applied by the simulator.

## The honest test: the hidden world

Each road has a "world": a SUMO run with demand the learner cannot read. The learner gets only the road map,
the signal list, the old timing and the feed. A test fails if learner code reads world demand or routes.
A guard test must enforce this.

- **Dev roads:** Stevens Creek (world = the VTA 2024 demand), one new road. May be used freely.
- **Held-out roads:** two new Cupertino roads, chosen and written in the preregistration before any learner run
  on them. World demand on new roads is generated from a fixed seed and is labeled synthetic.
- **Old timing:** a textbook actuated plan built from stale demand that differs from the world. It stands in for
  an out-of-date plan. It is not Cupertino's timing.
- **Watch period:** 3 simulated PM rush hours with different seeds. Test seeds are never seen by the learner.

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
