# Signal Learner card: wolfe

**SIMULATED recommendation from a copy learned only from the detector feed. Not city timing; no live control.**

**Decision: change.** The copy predicts a clear gain.

Expected in the copy (10 simulated rush hours): delay per requested trip 137.6 s -> 79.6 s, change -58.0 s (range -70.3 to -44.6 s), one-sided p = 0.001.

Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.

| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |
|---|---|---|---|---|
| Vallco Pkwy | 65 -> 88 | 30 -> 50 | N:LT S:RT: 22 -> 38; N:LT: 10 -> 11; E:LR S:R: 10 -> 14 | +16 s green for N:LT S:RT (learned peak 408 veh/15 min); +4 s green for E:LR S:R (learned peak 408 veh/15 min); offset 30 -> 50 s to fit the 88 s cycle |
| I-280 south ramps | 65 -> 88 | 0 -> 58 | N:T S:T: 31 -> 42; W:LR: 10 -> 17 | +10 s green for N:T S:T (learned peak 360 veh/15 min); +7 s green for W:LR (learned peak 157 veh/15 min); offset 0 -> 58 s to fit the 88 s cycle |
| I-280 north ramps | 65 -> 88 | 20 -> 4 | N:LT S:RT: 21 -> 35; N:LT: 10 -> 10; S:LR: 10 -> 16 | +14 s green for N:LT S:RT (learned peak 502 veh/15 min); +6 s green for S:LR (learned peak 502 veh/15 min); offset 20 -> 4 s to fit the 88 s cycle |
| Pruneridge Ave | 65 -> 88 | 36 -> 83 | N:LRT S:LRT: 10 -> 20; N:L S:L: 10 -> 19; N:R W:LRT: 10 -> 12; E:LRT S:R: 10 -> 12 | +10 s green for N:LRT S:LRT (learned peak 344 veh/15 min); +9 s green for N:L S:L (learned peak 344 veh/15 min); offset 36 -> 83 s to fit the 88 s cycle |
| Apple Park Way | 65 -> 88 | 42 -> 47 | N:LT S:RT: 17 -> 34; N:LT: 10 -> 13; E:LR S:R: 12 -> 11 | +17 s green for N:LT S:RT (learned peak 360 veh/15 min); +3 s green for N:LT (learned peak 360 veh/15 min); offset 42 -> 47 s to fit the 88 s cycle |

Phase order, clearances and minimum greens are unchanged. Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check rule goes back to old timing if the feed shows traffic clearly worse.
