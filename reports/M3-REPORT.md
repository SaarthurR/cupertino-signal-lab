# M3 independent holdout count check

**14.58% of 96 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = historical measured 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
M1 generated actuated plan used; M4 baseline pending. PM teleports: 1040; running after drain: 1249; waiting to insert: 6609. Teleports and incomplete trips limit interpretation.
A miss can reflect day-to-day differences (the two sites were counted on different dates), the repeated fit hour, assumed side-street demand, OSM geometry/connectivity, or queues in the provisional timing; this run does not isolate those causes.

Detailed rows: demand_check.csv / demand_check.md. Raw detector/summary XML removed after extraction.
