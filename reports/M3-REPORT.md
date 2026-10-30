# M3 independent holdout count check

**50.78% of 128 measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).

Observed = 2024-10-09 measured De Anza/Stelling 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.
Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.
textbook coordinated-actuated baseline (not Cupertino's current timing) used. PM teleports: 0; running after drain: 144; waiting to insert: 1448. Teleports and incomplete trips limit interpretation.
A miss can reflect the repeated fit hour, mixed-year Mary observations, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.

Detailed rows: demand_check.csv / demand_check.md. Raw detector/summary XML removed after extraction.
