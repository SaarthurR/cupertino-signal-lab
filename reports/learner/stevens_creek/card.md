# Signal Learner card: stevens_creek

**SIMULATED recommendation from a copy learned only from the detector feed. Not city timing; no live control.**

**Decision: change.** The copy predicts a clear gain.

Expected in the copy (10 simulated rush hours): delay per requested trip 454.6 s -> 326.5 s, change -128.0 s (range -169.9 to -79.0 s), one-sided p = 0.001.

Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.

| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |
|---|---|---|---|---|
| De Anza Blvd | 104 -> 177 | 66 -> 18 | N:LRT S:LRT: 21 -> 46; N:L S:L: 33 -> 60; E:LRT W:LRT: 13 -> 23; E:L W:L: 10 -> 21 | +27 s green for N:L S:L (learned peak 445 veh/15 min); +25 s green for N:LRT S:LRT (learned peak 445 veh/15 min); offset 66 -> 18 s to fit the 177 s cycle |
| Bandley Dr | 104 -> 177 | 14 -> 86 | E:RT W:LT: 60 -> 60; W:LT: 16 -> 60; E:R N:LR: 10 -> 38 | +44 s green for W:LT (learned peak 283 veh/15 min); +28 s green for E:R N:LR (learned peak 169 veh/15 min); offset 14 -> 86 s to fit the 177 s cycle |
| Saich Way | 104 -> 177 | 0 -> 66 | E:RT W:LT: 57 -> 60; W:LT: 11 -> 30; E:R N:LR: 13 -> 58 | +45 s green for E:R N:LR (learned peak 165 veh/15 min); +19 s green for W:LT (learned peak 281 veh/15 min); offset 0 -> 66 s to fit the 177 s cycle |
| Stelling Rd | 104 -> 177 | 26 -> 168 | E:LRT W:LRT: 27 -> 48; E:L W:L: 19 -> 29; N:LRT S:LRT: 17 -> 48; N:L S:L: 14 -> 22 | +32 s green for N:LRT S:LRT (learned peak 203 veh/15 min); +21 s green for E:LRT W:LRT (learned peak 441 veh/15 min); offset 26 -> 168 s to fit the 177 s cycle |
| Mary Ave | 104 -> 177 | 100 -> 86 | E:RT W:T: 60 -> 60; E:R N:LR: 15 -> 60 | +45 s green for E:R N:LR (learned peak 286 veh/15 min); offset 100 -> 86 s to fit the 177 s cycle |

Phase order, clearances and minimum greens are unchanged. Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check rule goes back to old timing if the feed shows traffic clearly worse.
