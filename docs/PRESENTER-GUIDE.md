# Presenter guide: understand Signal Learner in 20 minutes

Read this once, top to bottom. Then you can explain the project and answer judges without notes.

## 1. The problem

- Stevens Creek Blvd backs up toward Glenbrook in the evening. That is what started this.
- Cupertino's traffic manager told us by email (Nov 1, 2026): "Stevens Creek Blvd is running **time of day plans**." That means the clock picks which plan runs: one for the morning rush, one for the evening, and so on. Sensors can still change how a plan runs; the city's answer tells us when plans switch, not that the lights ignore cars.
- Traffic changes over the years: new buildings, new jobs, new routes. The plan stays the same until an engineer retimes it, and retiming takes work. The city's project to retime Stevens Creek and De Anza (RFP PW-2026-853) was under evaluation when we checked.
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

1. **Watch:** reads the simulated road sensors for 3 evening rush hours. Changes nothing.
2. **Learn:** works out the traffic pattern (how many cars, from where, every 15 minutes) and builds a **practice copy** of the road.
3. **Practice:** tries 150 timing plans on the practice copy.
4. **Recommend:** gives the engineer one card: old timing, new timing, the reason and the expected effect. The engineer approves or rejects.
5. **Check:** after a change, it watches the simulated sensors and tells the engineer to go back if traffic looks clearly worse. It passed on Wolfe but raised false alarms on De Anza, so it is not dependable yet.

It never controls a real light. The engineer decides and enters any change.

**Where is the AI?** Two parts. It *learns* the traffic pattern from sensor counts. Then a search method called **Optuna** picks which timing to try next, based on how earlier tries scored. It is not a chatbot and not a neural network. That is on purpose: every try is saved, so an engineer can check it.

## 4. The results, and what the numbers mean

**Delay score:** add up how long every car was delayed. Every car that never finished its trip counts as 900 seconds (15 minutes). Divide by all cars. Lower is better. It is a score, not a stopwatch time for one driver.

**Three Wolfe numbers:** forecast −42% (the practice copy's guess, used to pick the plan) · one evening −24% (seed 200, the demo) · 20-run test −26.1% (the headline). Lead with −26%.

| Road | What happened |
|---|---|
| **Wolfe Rd** (unseen test road) | Delay score 870 → 643 seconds, **−26%**. Better on all 20 test rush hours. Cars that never got through: 968 → 217 per rush hour. A textbook retiming only got −3%. |
| **De Anza Blvd** (unseen test road) | It said **keep the old timing**. We checked the plan it turned down: it was 6.4% worse. A later check (not part of the main test) supports the no-change call. |
| Homestead, Stevens Creek (practice roads) | −41% and −31% (10 runs each). We tuned our rules on these, so they do not count as a fair test. Homestead's 41% is not the older Stevens Creek study's 40.7%. |

**Why it was a fair test:** Wolfe and De Anza were kept hidden until the end. The software only saw sensor counts, never the true traffic. The test rules were written down and saved in git before the test ran. One try each, no do-overs.

The Stevens Creek practice road uses VTA 2024 counts at two of its five intersections, De Anza and Stelling (cite: *VTA, 2024 CMP Monitoring and Conformance Report*); the rest are older or estimated. The two test roads use made-up traffic, because the real counts only cover two intersections.

## 5. How it would connect to a real city

Our software sits **beside** the city's system and only reads from it.

1. **Read:** sensor counts, controller logs and the current timing sheets, through a records request to the city.
2. **Recommend:** the engineer compares our card with their own plan and enters any change in their own system. Google's Project Green Light works this way today: it sends recommendations to city engineers, who apply them.
3. **Much later, only with city approval and a safety review:** a direct connection to the central system, using the standard called **NTCIP 1202**.

The conflict monitor in every cabinet can put a light into flash if it sees conflicting greens. It does not check whether a timing plan is good; that is the engineer's job.

## 6. Judge questions and short answers

| Question | Answer |
|---|---|
| Why does Cupertino need this? | The city confirmed Stevens Creek runs time-of-day plans, and its project to retime Stevens Creek and De Anza was under evaluation when we checked (Nov 3). Retiming is slow work; we make the first draft fast and checkable. |
| Who uses it? | A city traffic engineer. They get one card and decide. |
| Don't smart traffic systems already exist? | Yes: SCOOT, SCATS, InSync, Surtrac, SynchroGreen, Google Green Light. Many change timing on the go and need a connection to the lights. Ours only reads data and suggests, like Green Light, and every step can be checked. We have not compared ourselves with them yet. |
| What is the AI? | Pattern learning from sensor counts, plus Optuna, a search that learns which timings to try next. |
| Is the data real? | The Stevens Creek practice road uses VTA 2024 counts at two of its five intersections (De Anza and Stelling); the rest are older or estimated. The two test roads use made-up traffic. All results are simulated. |
| Does −26% mean my commute is 26% shorter? | No. It is a delay score in simulation, with a big penalty for cars that never get through. |
| Did you test on the same roads you trained on? | No. The two test roads were hidden until the end, with rules written first. |
| Is the "old timing" the city's real timing? | No. We do not have the city's timing files yet. That is our first ask. |
| Could it make things worse for someone? | Yes. Wolfe’s worst-origin delay score rose about 203 s. The average improvement does not establish fairness. That is why an engineer decides, and why we'd check each approach first. |
| How does it connect to real lights? What hardware is there? | See section 5. It reads data; the engineer enters changes. No real connection is built yet. |

## 7. Say this, not that

| Don't say | Say |
|---|---|
| "It cuts commutes by 26%." | "In simulation, the delay score dropped 26%." |
| "It controls the lights." | "It recommends; the engineer decides." |
| "It's safe." | "The engineer approves every change. The conflict monitor only catches conflicting greens; it doesn't make a plan safe." |
| "That was the right call on De Anza." | "A later check supports keeping the old timing." |
| "It's connected to the city." | "Here is how it would connect, step by step." |

## 8. On stage: the demo and the fallback

- **The demo is 45 seconds** (judge deck slide 4; full script in [DEMO.md](DEMO.md#demo-script-45-seconds)). Start with the console already on Wolfe Road step 1, The problem. Point at 870 s, click See the fix and point at the longer rounds, then See the proof and Run the simulation (it starts at 240×) for about 25 seconds, say "This is one evening; next is the full test," and go to the result slide at 45 seconds even if the run is still playing.
- **Never open Deploy & monitor in the main talk.** It previews a future workflow; no real controller is touched. Show it only if a judge asks.
- **If the screen says Recording**, say "This is a saved run of the same evening."
- **If the demo breaks**, talk over the slide's screenshot and go to the result slide. **If the whole talk breaks**, give the 60-second version on the judge deck's last slide: what it does, the Wolfe −26% result, the limits and our ask. No app, terminal or video needed.
