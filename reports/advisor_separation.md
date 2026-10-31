# Advisor separation: simulated counts

All five scenarios ran with frozen v5 PM, seeds 1–4 (seed 0 also supplies replay fixtures and profile calibration).
Each signal is the trailing three-window mean: counts are vehicles per five minutes;
occupancy is percent. Differences below are scenario mean minus calm mean at 17:15.
Noise is the calm max-minus-min across four seeds at that same time.
Detectable means all four scenario values lie outside all four calm values, the absolute
mean difference exceeds the calm range, and this holds in the same direction for two
consecutive windows of the same channel. Minutes are from 17:00, including the hold.
This is a descriptive fit-seed separation test, not an out-of-sample accuracy claim.

| Scenario | First separation | During 17:00–17:30? |
|---|---:|---|
| south_surge | 60 min | no |
| east_surge | 10 min | yes |
| drop | 10 min | yes |
| sensor_failure | none | no |

East surge is the one surge selected for tuning. South surge is excluded from the
advisor: no repeatable separation during the change; late effects first appear at 18:00,
30 minutes after the requested surge ends. Drop is distinguishable but is not night demand.
Sensor failure has exactly calm traffic; only De Anza N quality flags differ (1/17 rows).
It is excluded as a traffic profile. The advisor masks suspect rows; it refuses a window
only when more than 25% are bad, or required coverage/freshness is absent.
No threshold or profile uses seeds above 4. All runs used caffeinate -i, nice -n 15,
and at most three concurrent SUMO runs.

## south_surge

| Approach | Count Δ / noise | Occupancy Δ pp / noise pp | First separation, min (channel) |
|---|---:|---:|---|
| Bandley Dr E | -1.00 / 3.00 | -0.01 / 0.37 | 70 (count) |
| Bandley Dr N | +0.00 / 0.00 | -0.13 / 0.42 | none |
| Bandley Dr W | -0.17 / 3.67 | -0.16 / 0.85 | none |
| De Anza Blvd E | +0.67 / 3.33 | -0.08 / 0.71 | none |
| De Anza Blvd N | -5.83 / 26.00 | -0.43 / 8.43 | none |
| De Anza Blvd S | +0.50 / 9.33 | -0.71 / 4.13 | none |
| De Anza Blvd W | -2.08 / 8.33 | -1.76 / 8.82 | none |
| Mary Ave E | -1.25 / 2.00 | -0.07 / 0.50 | 60 (count) |
| Mary Ave N | -0.25 / 1.67 | +0.01 / 0.02 | none |
| Mary Ave W | -0.42 / 1.67 | +0.06 / 0.18 | none |
| Saich Way E | -0.25 / 2.00 | +0.02 / 0.11 | 70 (count) |
| Saich Way N | +0.00 / 0.00 | +0.01 / 0.04 | none |
| Saich Way W | -0.17 / 1.33 | +0.03 / 0.28 | none |
| Stelling Rd E | +0.17 / 3.33 | -0.13 / 6.18 | 60 (occupancy) |
| Stelling Rd N | +1.17 / 12.00 | +1.60 / 8.74 | none |
| Stelling Rd S | +0.75 / 5.67 | +0.52 / 7.30 | none |
| Stelling Rd W | +1.00 / 12.00 | -0.27 / 3.46 | none |

## east_surge

| Approach | Count Δ / noise | Occupancy Δ pp / noise pp | First separation, min (channel) |
|---|---:|---:|---|
| Bandley Dr E | -1.08 / 3.00 | -0.08 / 0.37 | none |
| Bandley Dr N | +0.00 / 0.00 | -0.07 / 0.42 | none |
| Bandley Dr W | +16.92 / 3.67 | +0.99 / 0.85 | 15 (count) |
| De Anza Blvd E | -0.58 / 3.33 | +0.08 / 0.71 | none |
| De Anza Blvd N | -11.58 / 26.00 | +1.38 / 8.43 | none |
| De Anza Blvd S | -0.25 / 9.33 | +0.70 / 4.13 | none |
| De Anza Blvd W | +16.42 / 8.33 | +4.70 / 8.82 | 15 (count) |
| Mary Ave E | -0.42 / 2.00 | -0.15 / 0.50 | none |
| Mary Ave N | -0.25 / 1.67 | -0.00 / 0.02 | none |
| Mary Ave W | +37.75 / 1.67 | +3.47 / 0.18 | 10 (count) |
| Saich Way E | -0.75 / 2.00 | -0.02 / 0.11 | none |
| Saich Way N | +0.00 / 0.00 | -0.00 / 0.04 | none |
| Saich Way W | +17.25 / 1.33 | +1.02 / 0.28 | 10 (count) |
| Stelling Rd E | -1.08 / 3.33 | +0.27 / 6.18 | 30 (occupancy) |
| Stelling Rd N | -1.33 / 12.00 | +0.55 / 8.74 | none |
| Stelling Rd S | -0.75 / 5.67 | +1.62 / 7.30 | none |
| Stelling Rd W | +33.33 / 12.00 | +18.05 / 3.46 | 10 (count) |

## drop

| Approach | Count Δ / noise | Occupancy Δ pp / noise pp | First separation, min (channel) |
|---|---:|---:|---|
| Bandley Dr E | -14.08 / 3.00 | -0.53 / 0.37 | 15 (count) |
| Bandley Dr N | -1.33 / 0.00 | -0.33 / 0.42 | 15 (count) |
| Bandley Dr W | -19.75 / 3.67 | -1.02 / 0.85 | 10 (count) |
| De Anza Blvd E | -10.42 / 3.33 | -0.47 / 0.71 | 15 (count) |
| De Anza Blvd N | +6.50 / 26.00 | -6.03 / 8.43 | none |
| De Anza Blvd S | -20.00 / 9.33 | -4.06 / 4.13 | 15 (count) |
| De Anza Blvd W | -17.50 / 8.33 | -5.91 / 8.82 | 15 (count) |
| Mary Ave E | -20.08 / 2.00 | -0.86 / 0.50 | 15 (count) |
| Mary Ave N | -6.00 / 1.67 | -0.20 / 0.02 | 10 (count) |
| Mary Ave W | -37.92 / 1.67 | -1.85 / 0.18 | 10 (count) |
| Saich Way E | -12.00 / 2.00 | -0.59 / 0.11 | 15 (count) |
| Saich Way N | -1.33 / 0.00 | -0.16 / 0.04 | 10 (count) |
| Saich Way W | -18.50 / 1.33 | -0.69 / 0.28 | 10 (count) |
| Stelling Rd E | -9.08 / 3.33 | -11.89 / 6.18 | 20 (count) |
| Stelling Rd N | -10.83 / 12.00 | -16.36 / 8.74 | 10 (occupancy) |
| Stelling Rd S | -12.25 / 5.67 | -27.49 / 7.30 | 10 (count) |
| Stelling Rd W | -37.83 / 12.00 | -11.66 / 3.46 | 10 (count) |

## sensor_failure

| Approach | Count Δ / noise | Occupancy Δ pp / noise pp | First separation, min (channel) |
|---|---:|---:|---|
| Bandley Dr E | +0.00 / 3.00 | +0.00 / 0.37 | none |
| Bandley Dr N | +0.00 / 0.00 | +0.00 / 0.42 | none |
| Bandley Dr W | +0.00 / 3.67 | +0.00 / 0.85 | none |
| De Anza Blvd E | +0.00 / 3.33 | +0.00 / 0.71 | none |
| De Anza Blvd N | +0.00 / 26.00 | +0.00 / 8.43 | none |
| De Anza Blvd S | +0.00 / 9.33 | +0.00 / 4.13 | none |
| De Anza Blvd W | +0.00 / 8.33 | +0.00 / 8.82 | none |
| Mary Ave E | +0.00 / 2.00 | +0.00 / 0.50 | none |
| Mary Ave N | +0.00 / 1.67 | +0.00 / 0.02 | none |
| Mary Ave W | +0.00 / 1.67 | +0.00 / 0.18 | none |
| Saich Way E | +0.00 / 2.00 | +0.00 / 0.11 | none |
| Saich Way N | +0.00 / 0.00 | +0.00 / 0.04 | none |
| Saich Way W | +0.00 / 1.33 | +0.00 / 0.28 | none |
| Stelling Rd E | +0.00 / 3.33 | +0.00 / 6.18 | none |
| Stelling Rd N | +0.00 / 12.00 | +0.00 / 8.74 | none |
| Stelling Rd S | +0.00 / 5.67 | +0.00 / 7.30 | none |
| Stelling Rd W | +0.00 / 12.00 | +0.00 / 3.46 | none |
