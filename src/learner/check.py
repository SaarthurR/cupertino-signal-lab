"""Check after an approved change: go back to old timing when the feed shows traffic clearly worse."""
from collections import defaultdict
from datetime import datetime
import math
import statistics

from . import learn, road

# Simulation screening: thresholds inherited from dev roads, with watched-day count variability below.
# A window is flagged when queues grow (upstream occupancy rises)
# or, on roads already saturated where occupancy cannot rise, when the signals serve fewer vehicles.
WINDOWS = 3  # consecutive flagged five-minute windows before going back
MEAN_RISE = 5.  # points of mean approach occupancy above the watched level, same time of day
APPROACH_RISE = 25.  # points on each of at least APPROACHES approaches
APPROACHES = 2  # one side-street queue sitting on or off its loop is not enough
SD_FACTOR = 3.  # never flag occupancy less than this many watched day-to-day SDs
COUNT_DROP = .06  # served count over the last 15 minutes below the watched level


def _windows(rows):
    """Parse one day; one bad or repeated approach invalidates its entire window."""
    windows, errors = defaultdict(dict), {}
    for row in rows:
        try:
            stamp = datetime.fromisoformat(row['window_end'])
            t = road.clock(row['window_end'])
            if stamp.microsecond or not 0 < t <= 86400 or t % 300:
                raise ValueError('timestamp must end an aligned five-minute window in the watched day')
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            errors[None] = f'invalid timestamp: {exc}'
            continue
        try:
            key = row['site'], row['approach']
            if not all(isinstance(k, str) and k for k in key):
                raise ValueError('missing site or approach')
            if key in windows[t]:
                raise ValueError('duplicate site/approach')
            windows[t][key] = None
            occupancy, count = float(row['occupancy']), float(row['count'])
            if str(row['ok']) != '1':
                raise ValueError('detector marked invalid')
            if not math.isfinite(occupancy) or not 0 <= occupancy <= 100:
                raise ValueError('occupancy outside 0..100')
            if not math.isfinite(count) or count < 0:
                raise ValueError('count must be finite and nonnegative')
            windows[t][key] = occupancy, count
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            errors[t] = f'invalid feed at {t}: {exc}'
    for t, values in windows.items():
        if t not in errors and not math.isfinite(WINDOWS*sum(c for _, c in values.values())):
            errors[t] = 'count totals exceed numerical range'
    return windows, errors


def _baseline(name):
    days = [_windows(rows) for rows in learn.read(name, 'feed')]
    keys = {key for windows, _ in days for values in windows.values() for key in values}
    groups, totals = defaultdict(list), []
    for windows, errors in days:
        counts = {}
        for t, values in windows.items():
            if None in errors or t in errors or set(values) != keys:
                continue
            counts[t] = sum(c for _, c in values.values())
            for key, pair in values.items():
                groups[t, *key].append(pair)
        totals.append(counts)
    base = {k: (statistics.mean(o for o, _ in v), statistics.pstdev(o for o, _ in v),
                statistics.mean(c for _, c in v)) for k, v in groups.items()}
    return base, keys, totals


def expected(name):
    """Valid complete watched occupancy (mean, SD) and count (mean), per window and approach."""
    return _baseline(name)[0]


def decide(name, rows, change_s):
    """Simulated monitoring only; incomplete windows break consecutive evidence."""
    insufficient = lambda reason: dict(go_back=False, time_s=None, status='insufficient_data', reason=reason)
    if not isinstance(change_s, (int, float)) or not math.isfinite(change_s) or not 0 <= change_s < 86400:
        return insufficient('invalid change time')
    base, keys, days = _baseline(name)
    if not base:
        return insufficient('no complete valid watched windows')
    windows, errors = _windows(rows)
    if None in errors:
        return insufficient(errors[None])
    times = sorted(t for t in set(windows) | set(errors) if t > change_s)
    if not times:
        return insufficient('no feed windows after the change')
    streak, history, last, valid = 0, [], None, 0
    issue = 'fewer than three consecutive valid five-minute windows'
    for t in times:
        if last is not None and t-last != 300:
            streak, history, valid = 0, [], 0
            issue = 'missing five-minute feed window'
        last = t
        values = windows[t]
        reason = errors.get(t)
        if set(values)-keys:
            reason = 'unknown site/approach'
        elif set(values) != keys:
            reason = reason or 'missing site/approach'
        elif any((t, *k) not in base for k in keys):
            reason = 'no valid watched baseline for feed window'
        if reason:
            streak, history, valid = 0, [], 0
            issue = reason
            continue
        valid += 1
        rises = {k: occ-base[(t, *k)][0] for k, (occ, _) in values.items()}
        mean_sd = statistics.mean(base[(t, *k)][1] for k in rises)
        mean_rise = statistics.mean(rises.values())
        high = sorted((k for k, rise in rises.items() if rise > max(APPROACH_RISE, SD_FACTOR*base[(t, *k)][1])),
                      key=rises.get, reverse=True)
        history.append((t, sum(c for _, c in values.values()), sum(base[(t, *k)][2] for k in keys)))
        history = history[-WINDOWS:]
        drop, count_flag = 0., False
        if len(history) == WINDOWS:
            served, watched = sum(v[1] for v in history), sum(v[2] for v in history)
            # Use whole-day totals to retain covariance across approaches and adjacent windows.
            samples = [sum(day[v[0]] for v in history) for day in days if all(v[0] in day for v in history)]
            spread = statistics.pstdev(samples) if len(samples) >= 2 else 0.
            count_flag = watched-served > max(COUNT_DROP*watched, SD_FACTOR*spread)
            drop = 1-served/watched if watched > 0 else 0.
        flagged = mean_rise > max(MEAN_RISE, SD_FACTOR*mean_sd) or len(high) >= APPROACHES or count_flag
        streak = streak+1 if flagged else 0
        if streak == WINDOWS:
            return dict(go_back=True, time_s=t, status='go_back', reason=f'mean occupancy {mean_rise:+.1f} points; approaches up over '
                        f'{APPROACH_RISE:.0f} points: {", ".join(" ".join(k) for k in high) or "none"}; '
                        f'served count {-drop:+.0%} over 15 min; {WINDOWS} windows running')
    if valid < WINDOWS:
        return insufficient(issue)
    return dict(go_back=False, time_s=None, status='within_range', reason='feed within watched range')
