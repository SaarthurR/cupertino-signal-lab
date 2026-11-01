# Signal Learner card: deanza

**SIMULATED recommendation from a copy learned only from the detector feed. Not city timing; no live control.**

**Decision: no change.** No change: the copy predicts no clear gain over the old timing.

Expected in the copy (10 simulated rush hours): delay per requested trip 1740.0 s -> 1544.4 s, change -195.7 s (range -403.0 to +7.8 s), one-sided p = 0.002.

Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.

| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |
|---|---|---|---|---|
| Lazaneo Dr | 94 -> 94 | 5 -> 5 | N:LRT S:LRT: 33 -> 33; N:L S:L: 17 -> 17; E:LRT W:LRT: 10 -> 10; E:L W:L: 10 -> 10 | no material change |
| Mariani Ave | 94 -> 94 | 31 -> 31 | N:LRT S:LRT: 33 -> 33; N:L S:L: 15 -> 15; E:LRT W:LRT: 10 -> 10; E:L W:L: 10 -> 10 | no material change |
| I-280 south ramps | 94 -> 94 | 7 -> 7 | N:LT S:RT: 33 -> 33; N:LT: 13 -> 13; W:LRT: 17 -> 17 | no material change |
| I-280 north ramps | 94 -> 94 | 0 -> 0 | N:RT S:LT: 42 -> 42; S:LT: 10 -> 10; E:LRT: 11 -> 11 | no material change |

Phase order, clearances and minimum greens are unchanged. Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check rule goes back to old timing if the feed shows traffic clearly worse.
