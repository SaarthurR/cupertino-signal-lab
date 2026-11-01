# Signal Learner card: homestead

**SIMULATED recommendation from a copy learned only from the detector feed. Not city timing; no live control.**

**Decision: change.** The copy predicts a clear gain.

Expected in the copy (10 simulated rush hours): delay per requested trip 80.1 s -> 69.2 s, change -11.0 s (range -16.0 to -7.9 s), one-sided p = 0.001.

Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.

| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |
|---|---|---|---|---|
| Wright Ave | 72 -> 138 | 45 -> 39 | E:LRT W:LRT: 21 -> 46; E:L W:L: 10 -> 28; N:LRT S:LRT: 10 -> 24; N:L S:L: 10 -> 19 | +25 s green for E:LRT W:LRT (learned peak 267 veh/15 min); +18 s green for E:L W:L (learned peak 267 veh/15 min); offset 45 -> 39 s to fit the 138 s cycle |
| Mary Ave | 72 -> 138 | 0 -> 126 | E:RT W:LT: 24 -> 56; W:LT: 10 -> 12; E:R N:LR: 10 -> 27 | +32 s green for E:RT W:LT (learned peak 297 veh/15 min); +17 s green for E:R N:LR (learned peak 273 veh/15 min); offset 0 -> 126 s to fit the 138 s cycle |
| Kennewick Dr | 72 -> 138 | 25 -> 112 | E:RT W:LT: 17 -> 42; W:LT: 10 -> 14; E:R N:LR: 17 -> 38 | +25 s green for E:RT W:LT (learned peak 323 veh/15 min); +22 s green for E:R N:LR (learned peak 257 veh/15 min); offset 25 -> 112 s to fit the 138 s cycle |
| Hollenbeck Ave | 72 -> 138 | 52 -> 77 | E:LRT W:LRT: 16 -> 45; E:L W:L: 10 -> 19; N:LT S:LRT: 10 -> 28; N:L S:L: 10 -> 15 | +29 s green for E:LRT W:LRT (learned peak 268 veh/15 min); +18 s green for N:LT S:LRT (learned peak 158 veh/15 min); offset 52 -> 77 s to fit the 138 s cycle |
| Forge Way | 72 -> 138 | 8 -> 113 | E:LT W:RT: 26 -> 60; E:LT: 10 -> 17; S:LR W:R: 11 -> 24 | +34 s green for E:LT W:RT (learned peak 290 veh/15 min); +13 s green for S:LR W:R (learned peak 290 veh/15 min); offset 8 -> 113 s to fit the 138 s cycle |

Phase order, clearances and minimum greens are unchanged. Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check rule goes back to old timing if the feed shows traffic clearly worse.
