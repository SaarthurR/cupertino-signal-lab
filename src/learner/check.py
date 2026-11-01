"""Check after an approved change: go back to old timing when the feed shows traffic clearly worse."""
from collections import defaultdict
import statistics

from . import learn, road

# Frozen go-back rule. Upstream occupancy rises as queues grow, while counts saturate.
WINDOWS = 3  # consecutive five-minute windows
MEAN_RISE = 5.  # points of mean approach occupancy above the watched level, same time of day
APPROACH_RISE = 25.  # points on each of at least APPROACHES approaches
APPROACHES = 2  # one side-street queue sitting on or off its loop is not enough
SD_FACTOR = 3.  # never flag less than this many watched day-to-day SDs


def expected(name):
    """Watched old-timing occupancy per window and approach: mean and spread across days."""
    groups = defaultdict(list)
    for rows in learn.read(name, 'feed'):
        for r in rows:
            groups[road.clock(r['window_end']), r['site'], r['approach']].append(float(r['occupancy']))
    return {k: (statistics.mean(v), statistics.pstdev(v)) for k, v in groups.items()}


def decide(name, rows, change_s):
    """rows: feed rows after the change. Returns whether to go back, when, and why."""
    base = expected(name)
    windows = defaultdict(dict)
    for r in rows:
        t = road.clock(r['window_end'])
        if t > change_s and int(r['ok']):
            windows[t][r['site'], r['approach']] = float(r['occupancy'])
    streak = 0
    for t in sorted(windows):
        rises = {k: occ-base[(t, *k)][0] for k, occ in windows[t].items()}
        mean_sd = statistics.mean(base[(t, *k)][1] for k in rises)
        mean_rise = statistics.mean(rises.values())
        high = sorted((k for k, rise in rises.items() if rise > max(APPROACH_RISE, SD_FACTOR*base[(t, *k)][1])),
                      key=rises.get, reverse=True)
        flagged = mean_rise > max(MEAN_RISE, SD_FACTOR*mean_sd) or len(high) >= APPROACHES
        streak = streak+1 if flagged else 0
        if streak == WINDOWS:
            return dict(go_back=True, time_s=t, reason=f'mean occupancy +{mean_rise:.1f} points; approaches up over '
                        f'{APPROACH_RISE:.0f} points: {", ".join(" ".join(k) for k in high) or "none"}; {WINDOWS} windows running')
    return dict(go_back=False, time_s=None, reason='feed within watched range')
