"""CSV-only advice. No simulator imports, learning, approval or signal control."""
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

FIELDS = ('window_end', 'site', 'approach', 'count', 'occupancy', 'ok')
WINDOW = timedelta(minutes=5)
HOLD = timedelta(minutes=15)
CALIBRATION = Path(__file__).with_name('advisor_profiles.json')


@dataclass(frozen=True)
class Row:
    window_end: datetime
    site: str
    approach: str
    count: int
    occupancy: float
    ok: int


@dataclass(frozen=True)
class State:
    # Last recommendation only; this does not imply engineer approval or a signal switch.
    plan: str = 'v5_pm'
    candidate: str | None = None
    streak: int = 0
    last_window: datetime | None = None
    last_change: datetime | None = None


def read_feed(path):
    rows, seen = [], set()
    with open(path, newline='') as stream:
        reader = csv.DictReader(stream)
        if (reader.fieldnames is None or len(reader.fieldnames) != len(FIELDS)
                or set(reader.fieldnames) != set(FIELDS)):
            raise ValueError('Feed columns must be '+','.join(FIELDS))
        for line, raw in enumerate(reader, 2):
            try:
                row = Row(datetime.fromisoformat(raw['window_end']), raw['site'], raw['approach'],
                          int(raw['count']), float(raw['occupancy']), int(raw['ok']))
                if (None in raw or row.window_end.tzinfo is None or not row.site.strip()
                        or row.approach not in ('N', 'S', 'E', 'W') or row.count < 0
                        or not math.isfinite(row.occupancy) or not 0 <= row.occupancy <= 100
                        or row.ok not in (0, 1)):
                    raise ValueError('Invalid timestamp, site, approach, count, occupancy or ok')
                key = row.window_end, row.site, row.approach
                if key in seen:
                    raise ValueError('Duplicate approach/window')
                seen.add(key)
                rows.append(row)
            except (TypeError, ValueError) as error:
                raise ValueError(f'Feed line {line}: {error}') from error
    if not rows:
        raise ValueError('Feed is empty')
    return sorted(rows, key=lambda r: (r.window_end, r.site, r.approach))


def smooth(rows):
    """Mean count per five minutes and occupancy; never use suspect measurements."""
    groups = defaultdict(list)
    for row in rows:
        if row.ok:
            groups[row.site, row.approach].append(row)
    return {key: (sum(r.count for r in rs)/3, sum(r.occupancy for r in rs)/3)
            for key, rs in groups.items() if len(rs) == 3}


def distances(signal, calibration):
    return {name: sum(((signal[tuple(f['approach'])][j]-f['profiles'][name][j])/f['scale'][j])**2
                     for f in calibration['features'] if tuple(f['approach']) in signal
                     for j in range(2) if f['scale'][j] > 0)
            for name in calibration['profiles']}


def recommend(rows, state, now, calibration):
    """One trailing 15-minute snapshot -> decision and new immutable advisory state.

    Caller supplies an aware clock. Offline replay uses each recorded window end.
    A real consumer must supply its real clock and track approvals independently.
    """
    latest = max((r.window_end for r in rows), default=None)
    decision = dict(window_end=latest.isoformat() if latest else None, plan=None, reason='')
    reset = replace(state, candidate=None, streak=0)
    def refuse(reason, **fields):
        return {**decision, 'reason': reason, **fields}, reset
    if now.tzinfo is None:
        raise ValueError('Advisor clock must include a timezone')
    if latest is None or not timedelta(0) <= now-latest <= WINDOW:
        return refuse('Feed stale or future-dated; no recommendation')
    if latest == state.last_window:
        return {**decision, 'reason': 'Window already evaluated'}, state
    if state.last_window is not None and latest < state.last_window:
        return refuse('Window out of order')
    expected = {tuple(f['approach']) for f in calibration['features']}
    times = {latest-i*WINDOW for i in range(3)}
    recent = [r for r in rows if r.window_end in times]
    keys = [(r.window_end, r.site, r.approach) for r in recent]
    if len(set(keys)) != len(keys) or any((r.site, r.approach) not in expected for r in recent):
        return refuse('Duplicate or unrecognized approach; no recommendation')
    reset = replace(reset, last_window=latest)
    by_time = Counter(r.window_end for r in recent)
    if set(by_time) != times:
        return refuse('Need three consecutive five-minute windows')
    good = Counter(r.window_end for r in recent if r.ok)
    bad_fraction = max(1-good[t]/len(expected) for t in times)
    decision['bad_fraction'] = bad_fraction
    if bad_fraction > .25:
        return refuse(f'Bad or missing rows {bad_fraction:.1%} exceed 25%; no recommendation',
                      bad_fraction=bad_fraction)
    signal = smooth(recent)
    if not signal:
        return refuse('No complete good approach history')
    scores = distances(signal, calibration)
    source = calibration['plans'][state.plan]['profile']
    target = min(scores, key=lambda name: (scores[name], name != source))
    margin = scores[source]-scores[target]
    threshold = calibration['margins'][source][target]
    decision.update(profile=target, distance=scores[target], margin=margin, threshold=threshold)
    evidence = sorted((f for f in calibration['features'] if tuple(f['approach']) in signal),
                      key=lambda f: sum(((signal[tuple(f['approach'])][j]-f['profiles'][source][j])/f['scale'][j])**2
                                        for j in range(2) if f['scale'][j] > 0), reverse=True)[:2]
    numbers = '; '.join(f"{f['approach'][0]} {f['approach'][1]}: "
                        f"count {signal[tuple(f['approach'])][0]:.1f} vs {f['profiles'][source][0]:.1f}, "
                        f"occupancy {signal[tuple(f['approach'])][1]:.2f}% vs {f['profiles'][source][1]:.2f}%"
                        for f in evidence)
    decision['reason'] = f'Closest profile {target}; {numbers}'
    if target == source or margin <= threshold:
        decision['reason'] += f'; hold (margin {margin:.3f} <= required {threshold:.3f})'
        return decision, reset
    plan = next((name for name, spec in calibration['plans'].items()
                 if spec['profile'] == target and name != 'textbook'), None)
    if plan is None:
        decision['reason'] += '; no validated plan for this profile'
        return decision, reset
    consecutive = state.last_window == latest-WINDOW and state.candidate == plan
    updated = replace(reset, candidate=plan, streak=state.streak+1 if consecutive else 1)
    if updated.streak < 2:
        decision['reason'] += '; waiting for second consecutive window'
    elif state.last_change is not None and latest-state.last_change < HOLD:
        decision['reason'] += '; waiting for 15-minute hold'
    else:
        decision['plan'] = plan
        decision['reason'] += f'; margin {margin:.3f} > {threshold:.3f}; held {updated.streak} windows'
        updated = replace(updated, plan=plan, candidate=None, streak=0, last_change=latest)
    return decision, updated


def replay(rows, calibration):
    state = State()
    windows = defaultdict(list)
    for row in rows:
        windows[row.window_end].append(row)
    history = []
    for time, batch in sorted(windows.items()):
        history = [r for r in history if r.window_end > time-3*WINDOW]+batch
        decision, state = recommend(history, state, time, calibration)
        yield decision


def advise(feed):
    path = Path(feed)
    rows = read_feed(path)
    calibration = json.loads(CALIBRATION.read_text())
    output = path.with_suffix('.advisor.jsonl')
    with output.open('w') as stream:
        for decision in replay(rows, calibration):
            stream.write(json.dumps(decision, allow_nan=False)+'\n')
            if decision['plan']:
                print(json.dumps(decision, allow_nan=False))
    print(f'Advisor replay log: {output}')
