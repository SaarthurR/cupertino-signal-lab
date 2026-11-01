"""Check after an approved change: go back to old timing when the feed shows traffic clearly worse."""
from collections import defaultdict
import statistics

from . import learn, road

# Frozen go-back rule, set on dev roads. A window is flagged when queues grow (upstream occupancy rises)
# or, on roads already saturated where occupancy cannot rise, when the signals serve fewer vehicles.
WINDOWS = 3  # consecutive flagged five-minute windows before going back
MEAN_RISE = 5.  # points of mean approach occupancy above the watched level, same time of day
APPROACH_RISE = 25.  # points on each of at least APPROACHES approaches
APPROACHES = 2  # one side-street queue sitting on or off its loop is not enough
SD_FACTOR = 3.  # never flag occupancy less than this many watched day-to-day SDs
COUNT_DROP = .06  # served count over the last 15 minutes below the watched level


def expected(name):
    """Watched old-timing occupancy (mean, SD) and count (mean) per window and approach, across days."""
    groups = defaultdict(list)
    for rows in learn.read(name, 'feed'):
        for r in rows:
            groups[road.clock(r['window_end']), r['site'], r['approach']].append((float(r['occupancy']), float(r['count'])))
    return {k: (statistics.mean(o for o, _ in v), statistics.pstdev(o for o, _ in v), statistics.mean(c for _, c in v))
            for k, v in groups.items()}


def decide(name, rows, change_s):
    """rows: feed rows after the change. Returns whether to go back, when, and why."""
    base = expected(name)
    windows = defaultdict(dict)
    for r in rows:
        t = road.clock(r['window_end'])
        if t > change_s and int(r['ok']):
            windows[t][r['site'], r['approach']] = float(r['occupancy']), float(r['count'])
    streak, served, watched = 0, [], []
    for t in sorted(windows):
        rises = {k: occ-base[(t, *k)][0] for k, (occ, _) in windows[t].items()}
        mean_sd = statistics.mean(base[(t, *k)][1] for k in rises)
        mean_rise = statistics.mean(rises.values())
        high = sorted((k for k, rise in rises.items() if rise > max(APPROACH_RISE, SD_FACTOR*base[(t, *k)][1])),
                      key=rises.get, reverse=True)
        served.append(sum(c for _, c in windows[t].values()))
        watched.append(sum(base[(t, *k)][2] for k in windows[t]))
        drop = 1-sum(served[-WINDOWS:])/sum(watched[-WINDOWS:]) if len(served) >= WINDOWS else 0.
        flagged = mean_rise > max(MEAN_RISE, SD_FACTOR*mean_sd) or len(high) >= APPROACHES or drop > COUNT_DROP
        streak = streak+1 if flagged else 0
        if streak == WINDOWS:
            return dict(go_back=True, time_s=t, reason=f'mean occupancy {mean_rise:+.1f} points; approaches up over '
                        f'{APPROACH_RISE:.0f} points: {", ".join(" ".join(k) for k in high) or "none"}; '
                        f'served count {-drop:+.0%} over 15 min; {WINDOWS} windows running')
    return dict(go_back=False, time_s=None, reason='feed within watched range')
