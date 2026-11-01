# Signal Learner: what we built, in plain English

All results are from a computer simulation. No real light, camera or street was involved.

## The problem

Traffic changes, but a light's timing plan stays the same until someone retimes it. Smart systems exist,
but few lights have them, because they cost money and take time to set up.

## What we built

Software that learns a new road by watching it, then suggests a better timing plan.

1. **Map:** it draws the road from a public map.
2. **Watch:** it reads the road sensors while the old timing runs. We tested with 3 simulated evening rush hours.
3. **Learn:** it learns the traffic pattern and builds a practice copy of the road.
4. **Practice:** it tries 150 timing plans on the copy.
5. **Recommend:** it makes a one-page card for an engineer, who approves or rejects it.
6. **Check:** it watches the sensors and goes back to the old timing if traffic gets clearly worse.

It only makes recommendations. It never controls a light.

## Did it work?

We wrote the test rules first. Then we ran the test once, on two roads the software had not seen.
We made up the traffic on these roads. The "old timing" is a stand-in we built, not Cupertino's timing.

| Road | Old timing | Signal Learner | What happened |
|---|---|---|---|
| Wolfe Rd | 870 s | 643 s | 26% lower delay score. Unfinished trips fell from 968 to 217. |
| De Anza Blvd | 270 s | 270 s | It said "no change". A later check showed the plan it rejected was 6.4% worse. |

The delay score is not stopwatch time. It adds 900 seconds for each trip that never finishes.

A retiming with perfect traffic counts scored 846 s on Wolfe Rd. The learner beat it there.

## What did not go well

- On Wolfe Rd, one group of drivers got worse, by about 203 s.
- The practice copy had real errors. On De Anza it was badly wrong because of one shared lane.
- The undo check passed on Wolfe Rd but failed on De Anza. It undid a harmless change on 4 of 10 runs.
- Two roads is a small test.

## How it could connect to Cupertino

1. **Read:** take the city's data exports or controller logs.
2. **Recommend:** an engineer enters an approved change by hand. No connection to the lights is needed.
3. **Automatic:** only with city approval, much later.

We do not know yet what system runs these lights today. We asked the city.

## What we do in hackathon week

Fix the shared-lane error, watch for longer, test on new roads, and use real city data if it arrives.

## Files

- Slides: `dashboard/signal-learner/index.html` (press N for speaker notes)
- PDF: `dashboard/signal-learner/signal-learner.pdf`
- Video: `dashboard/signal-learner/wolfe_side_by_side.mp4`
