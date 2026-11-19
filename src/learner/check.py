"""Experimental detector-feed alarm for simulated trials."""
from collections import defaultdict
import math
import statistics

from . import learn, road

# Compare upstream occupancy and how many vehicles get through against the watched range.
WINDOWS = 3  # consecutive flagged five-minute windows for an alarm
WINDOW_S = 300
TRIAL_S = 900  # fixed simulation expiry, independent of the alarm
MEAN_RISE = 5.  # points of mean approach occupancy above the watched level, same time of day
APPROACH_RISE = 25.  # points on each of at least APPROACHES approaches
APPROACHES = 2  # one side-street queue sitting on or off its loop is not enough
SD_FACTOR = 3.  # never flag occupancy less than this many watched day-to-day SDs
COUNT_DROP = .06  # five-minute served count below the watched level


def expected(name):
    """Watched old-timing occupancy (mean, SD) and count (mean) per window and approach, across days."""
    days = [samples(rows) for rows in learn.read(name, 'feed')]
    base, counts = {}, {}
    if len(days) < 3:
        return base, counts
    for t, first in days[0].items():
        matched = [day.get(t, {}) for day in days]
        if any(v.keys() != first.keys() or None in v.values() for v in matched):
            continue
        occupancy = {key: [v[key][0] for v in matched] for key in first}
        base[t] = {key: (statistics.mean(v), statistics.pstdev(v)) for key, v in occupancy.items()}
        totals = [sum(c for _, c in v.values()) for v in matched]
        counts[t] = statistics.mean(totals), statistics.pstdev(totals)
    return base, counts


def samples(rows):
    windows = defaultdict(dict)
    for r in rows:
        t, key = road.clock(r['window_end']), (r['site'], r['approach'])
        occupancy, count = float(r['occupancy']), float(r['count'])
        valid = (key not in windows[t] and int(r['ok']) == 1 and math.isfinite(count) and count >= 0
                 and 0 <= occupancy <= 100)
        windows[t][key] = (occupancy, count) if valid else None
    return windows


def decide(name, rows, change_s):
    """rows: feed rows after the change. Returns whether to go back, when, and why."""
    base, counts = expected(name)
    windows = samples(rows)
    streak, contiguous, best_coverage = 0, 0, 0
    previous = change_s
    for t in sorted(t for t in windows if t > change_s and (t-change_s) % WINDOW_S == 0):
        if t != previous+WINDOW_S:
            streak, contiguous = 0, 0
        previous = t
        values, reference = windows[t], base.get(t, {})
        if not reference or values.keys() != reference.keys() or None in values.values() or t not in counts:
            streak, contiguous = 0, 0
            continue
        contiguous += 1
        best_coverage = max(best_coverage, contiguous)
        rises = {k: occ-reference[k][0] for k, (occ, _) in values.items()}
        mean_sd = statistics.mean(reference[k][1] for k in rises)
        mean_rise = statistics.mean(rises.values())
        high = sorted((k for k, rise in rises.items() if rise > max(APPROACH_RISE, SD_FACTOR*reference[k][1])),
                      key=rises.get, reverse=True)
        mean_count, sd_count = counts[t]
        loss = mean_count-sum(c for _, c in values.values())
        flagged = (mean_rise > max(MEAN_RISE, SD_FACTOR*mean_sd) or len(high) >= APPROACHES
                   or loss > max(COUNT_DROP*mean_count, SD_FACTOR*sd_count))
        streak = streak+1 if flagged else 0
        if streak == WINDOWS:
            return dict(go_back=True, time_s=t, reason=f'mean occupancy {mean_rise:+.1f} points; approaches up over '
                        f'{APPROACH_RISE:.0f} points: {", ".join(" ".join(k) for k in high) or "none"}; '
                        f'{loss:+.0f} fewer vehicles served in the last window; {WINDOWS} windows running')
    reason = 'No sustained alarm' if best_coverage >= WINDOWS else 'Insufficient matched feed for an alarm'
    return dict(go_back=False, time_s=None, reason=reason)
