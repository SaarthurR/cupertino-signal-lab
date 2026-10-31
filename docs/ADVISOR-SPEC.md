# Signal Advisor spec

## The idea

Traffic changes during the day. City timing plans change only when someone retimes them. The advisor reads
traffic counts every 5 minutes, spots when traffic no longer matches the running plan, and recommends a
different plan with a reason. A traffic engineer approves or rejects the recommendation.

**The advisor never writes to a real signal.** Controllers keep their own safety rules. In simulation, an
approved switch is applied by the simulator so we can measure what it would have done.

## What it proves, and what it does not

May claim: in simulation, on labeled synthetic traffic changes, recommendations did or did not beat a fixed plan.

Must not claim: live cameras, live control, street safety, calibrated traffic, machine learning, emissions
savings, or a comparison with Cupertino's real timing. Until real data arrives, every screen says
"simulated counts".

## The feed: the one interface that matters

A CSV or stream of rows. The advisor reads only this, so real city data can replace the simulator later.

| Column | Meaning |
|---|---|
| `window_end` | End of the 5-minute window, ISO 8601 |
| `site` | Signal name from `config/`, such as `De Anza Blvd` |
| `approach` | Compass leg: N, S, E or W |
| `count` | Vehicles counted in the window |
| `occupancy` | Percent of the window the upstream loop was covered by a vehicle, averaged across lanes |
| `ok` | `1` good, `0` sensor missing or suspect |

Why occupancy: stop-line counts top out when a road is full. In the first test, a 40% south surge raised stop-line
counts by only 10%, and 5-minute counts swung from 125 to 259 by chance. Counts alone cannot see a queue.

## Pieces, one builder each

1. **Scenarios and feed.** Labeled traffic changes on the existing routes, plus the detector feed above.
2. **Advisor.** Plain Python rule, feed to recommendation with a logged reason. Hold steady on bad data.
3. **Closed-loop test.** Apply approved switches in SUMO with TraCI, written rules before the run, new seeds.
4. **Demo.** Page and deck showing counts, recommendations, approvals and results, wins and losses alike.

## Rules for piece 2 (fixed now so it stays simple)

- Plan library: frozen plans only. Textbook, v5 rush hour, v5 night, and at most one surge plan.
- Compare smoothed counts and occupancy (15-minute rolling) to the profile each plan was tuned for. Recommend the closest plan.
- Thresholds come from seeds 0-4 only. If a scenario cannot be told apart from `calm`, report it and do not force it.
- Needs 2 windows in a row before recommending. At least 15 minutes between switches.
- Over 25% of rows `ok=0` or a stale feed: recommend nothing, say why.
- Approval delay in simulation: 5 minutes. The switch itself must be simulated, including its disruption.

## Stop rule

If the advisor does not beat fixed v5 in the test, we report that. A true "no gain" with a working feed and
tested fallback is still a valid result. We do not re-tune on test seeds.
