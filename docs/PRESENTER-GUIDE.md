# Presenter guide: understand Signal Learner in 20 minutes

Read this once, top to bottom. Then you can explain the project and answer judges without notes.

## 1. The problem

- Stevens Creek Blvd backs up toward Glenbrook in the evening. That is what started this.
- Cupertino's traffic manager told us by email (Nov 1, 2026): Stevens Creek runs **time-of-day plans**. That means a fixed timing for mornings, a fixed timing for evenings, and so on.
- Traffic changes as routes and travel patterns change. Engineers have to review the timing plans and decide when to update them.
- **Our user:** a city traffic engineer who has to decide *when* a road needs new timing and *what* the new timing should be.

## 2. Traffic lights in 2 minutes

| Word | Plain meaning |
|---|---|
| **Controller** | A small computer in a metal box (the cabinet) at the corner. It runs the timing plan. |
| **Sensors** | Wire loops in the road, cameras or radar. They tell the controller a car is waiting. |
| **Cycle** | One full round of greens for every direction. Example: 65 seconds. |
| **Green time** | How long one direction gets to go. |
| **Offset** | When a light turns green compared with its neighbour, so cars can hit green after green. |
| **Conflict monitor** | A separate safety box. If two crossing directions ever got green, it switches the light to flashing. |
| **Central system** | The city's computer that connects to the controllers. Cupertino chose Cubic Trafficware for this (announced 2019). |

## 3. What Signal Learner does

1. **Watch:** reads the road sensors for 3 evening rush hours. Changes nothing.
2. **Learn:** works out the traffic pattern (how many cars, from where, every 15 minutes) and builds a **practice copy** of the road.
3. **Practice:** tries 150 timing plans on the practice copy.
4. **Recommend:** gives the engineer one card: old timing, new timing, the reason and the expected effect. The engineer approves or rejects.
5. **Check:** in simulation, a rule watches for sustained changes in sensor occupancy and how many vehicles get through. It can flag a rollback. It flagged 4 of 10 unchanged De Anza runs.

It never controls a real light. The engineer decides and enters any change.

**Where is the AI?** We fit a traffic model to the sensor counts. Then **Optuna** uses the scores from earlier trials to choose timing settings to try next. The trial history shows what the search tried.

## 4. The results, and what the numbers mean

**Delay score** is the total delay on completed trips plus a 900-second penalty per unfinished trip and per vehicle relocation by SUMO, divided by all requested trips. Completed-trip delay includes waiting to enter. Lower is better.

| Road | What happened |
|---|---|
| **Wolfe Rd** (unseen test road) | Delay score 870 → 643 seconds, **−26%**. Better on all 20 test rush hours. Cars that never got through: 968 → 217 per rush hour. A textbook retiming only got −3%. |
| **De Anza Blvd** (held-out road) | It said **keep the old timing** after the candidate exceeded the limit for vehicle relocations. A later check on 20 new runs found a 6.4% higher average delay score for the rejected plan. |
| Homestead, Stevens Creek (practice roads) | −41% and −31%. We tuned our rules on these, so they do not count as a fair test. |

**Why it was a fair test:** Wolfe and De Anza were kept hidden until the end. The software only saw sensor counts, never the true traffic. The test rules were written down and saved in git before the test ran. One try each, no do-overs.

The Stevens Creek model uses counts from two intersections. *VTA, 2024 CMP Monitoring and Conformance Report*. Wolfe and De Anza use synthetic traffic.

## 5. How it would connect to a real city

The proposed design would read city data and give the engineer a recommendation to review.

1. **Read:** sensor counts, controller logs and the current timing sheets, through a records request to the city.
2. **Recommend:** the engineer compares our card with their own plan and enters any change in their own system. Google's Project Green Light works this way today: it sends recommendations to city engineers, who apply them.
3. **Much later, only with city approval and a safety review:** a direct connection to the central system, using the standard called **NTCIP 1202**.

The conflict monitor in every cabinet stays in charge of safety no matter what software suggests.

## 6. Judge questions and short answers

| Question | Answer |
|---|---|
| Why does Cupertino need this? | When traffic changes on Stevens Creek, the engineer has to decide whether to update its scheduled plans. Signal Learner gives them a timing proposal they can inspect. |
| Who uses it? | A city traffic engineer. They get one card and decide. |
| Don't smart traffic systems already exist? | Yes: SCOOT, SCATS, InSync, Surtrac, SynchroGreen, Google Green Light. Many change timing on the go and need a connection to the lights. Ours only reads data and suggests, like Green Light, and every step can be checked. We have not compared ourselves with them yet. |
| What is the AI? | Pattern learning from sensor counts, plus Optuna, a search that learns which timings to try next. |
| Is the data real? | The Stevens Creek model uses counts at two intersections from *VTA, 2024 CMP Monitoring and Conformance Report*. The two test roads use synthetic traffic. All results are simulated. |
| Does −26% mean my commute is 26% shorter? | No. It is a delay score in simulation, with a big penalty for cars that never get through. |
| Did you test on the same roads you trained on? | No. The two test roads were hidden until the end, with rules written first. |
| Is the "old timing" the city's real timing? | No. We do not have the city's timing files yet. That is our first ask. |
| Could it make things worse for someone? | Yes. Wolfe’s average score improved, while the worst-approach score rose by about 203 seconds. We’d review individual approaches with the engineer. |
| How does it connect to real lights? What hardware is there? | See section 5. It reads data; the engineer enters changes; the safety box stays in charge. No real connection is built yet. |

## 7. Say this, not that

| Don't say | Say |
|---|---|
| "It cuts commutes by 26%." | "In simulation, the delay score dropped 26%." |
| "It controls the lights." | "It recommends; the engineer decides." |
| "It's safe." | "The safety box in the cabinet stays in charge, and an engineer approves every change." |
| "It's connected to the city." | "Here is how it would connect, step by step." |
