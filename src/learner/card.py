"""Recommend: one short card an engineer can approve or reject. Simulated; never sent to a signal."""
import csv
import json
import statistics
import xml.etree.ElementTree as ET

from . import practice, road

LABEL = 'SIMULATED recommendation from a copy learned only from the detector feed. Not city timing; no live control.'
TURN = {'l': 'L', 's': 'T', 'r': 'R'}  # left, through, right


def settings(path, cfg, network):
    """Per signal: cycle, offset and each green phase's min/max with the movements it serves."""
    rels = road.relations(cfg, network)
    legs = road.approaches(cfg, network)
    out = {}
    for logic in ET.parse(path).getroot().findall('tlLogic'):
        links = {c[2]: c for c in network.getTLS(logic.get('id')).getConnections()}
        cycle = float(next(v.get('value') for v in logic.findall('param') if v.get('key') == 'cycleTime'))
        greens = []
        for index, phase in enumerate(logic.findall('phase')):
            if phase.get('minDur') is None:
                continue
            moves = {}
            for i, (lane, outgoing, _) in links.items():
                a, b = lane.getEdge().getID(), outgoing.getEdge().getID()
                if phase.get('state')[i] in 'Gg' and b in rels.get(a, {}):
                    moves.setdefault(legs[a][1], set()).add(TURN[rels[a][b]])
            # e.g. 'N:LT' = traffic from the north leg turning left and going through.
            served = [f"{leg}:{''.join(sorted(turns))}" for leg, turns in sorted(moves.items())]
            greens.append(dict(phase=index, serves=served, min_green_s=round(float(phase.get('minDur')), 1),
                               max_green_s=round(float(phase.get('maxDur')), 1)))
        out[logic.get('id')] = dict(cycle_s=round(cycle, 1), offset_s=round(float(logic.get('offset')), 1), greens=greens)
    return out


def why(result):
    """The card sentence: name the gate that blocked the change, not just 'no clear gain'."""
    gate = result.get('quality_gate', {})
    if gate and not gate.get('passed', False):
        return 'No change: copy quality screening failed: ' + '; '.join(gate.get('reasons', []) or ['missing quality evidence']) + '.'
    if result['clear_gain']:
        return 'The copy predicts a clear gain.'
    if result['best_trial'] == 0:
        return 'No change: the search found nothing better than the old timing in the copy.'
    old, new = result['confirm_old'], result['confirm_new']
    failed = []
    if result['confirm_gain'] < practice.MIN_GAIN:
        failed.append(f"gain under {practice.MIN_GAIN:.0%}")
    if result['confirm_p'] >= practice.ALPHA:
        failed.append(f"p not under {practice.ALPHA}")
    paired = len(new) == len(old) and all(n.get('seed') == o.get('seed') for n, o in zip(new, old))
    if not paired:
        failed.append('confirmation runs do not have the same paired copy seeds')
    over = [str(n['seed']) for n, o in zip(new, old) if n['teleports'] > o['teleports']+practice.TELEPORT_MARGIN]
    if over:
        failed.append(f"teleports more than old + {practice.TELEPORT_MARGIN} on copy seeds {', '.join(over)}")
    if practice.side(new) > practice.SIDE_LIMIT*practice.side(old)+1e-9:
        ratio = f"{practice.side(new)/practice.side(old):.2f}x old" if practice.side(old) else 'increased from zero'
        failed.append(f"side-street delay {ratio}, limit {practice.SIDE_LIMIT}x")
    records = [*old, *new]
    screened = 'confirm_feasible' in result
    if screened or any('unfinished' in s for s in records):
        if not all('unfinished' in s for s in records):
            failed.append('missing unfinished-trip evidence')
        else:
            unfinished = [str(n['seed']) for n, o in zip(new, old) if n['unfinished'] > o['unfinished']]
            if unfinished:
                failed.append(f"more unfinished trips on copy seeds {', '.join(unfinished)}")
    if screened or any('origin_delay_s' in s for s in records):
        groups = set().union(*(s.get('origin_delay_s', {}) for s in old))
        if not groups or any(set(s.get('origin_delay_s', {})) != groups for s in records):
            failed.append('missing or inconsistent origin-group delay evidence')
        else:
            over_origins = sorted(g for g in groups if sum(s['origin_delay_s'][g] for s in new)
                                  > practice.SIDE_LIMIT*sum(s['origin_delay_s'][g] for s in old)+1e-9)
            if over_origins:
                failed.append(f"origin-group delay over {practice.SIDE_LIMIT}x old: {', '.join(over_origins)}")
    for penalty in (0, 1800):
        key = f'all_requested_delay_{penalty}_s'
        if screened or any(key in s for s in records):
            if not all(key in s for s in records):
                failed.append(f'missing delay evidence at {penalty} s penalty')
            elif sum(s[key] for s in new) > sum(s[key] for s in old)+1e-9:
                failed.append(f'aggregate delay regresses at {penalty} s penalty')
    if result.get('confirm_feasible') is False and not failed:
        failed.append('confirmation feasibility failed: missing or inconsistent screening evidence')
    for stress in result.get('stress_copies', []):
        if stress.get('passed'):
            continue
        reasons = []
        if stress.get('gain', 0) < practice.MIN_GAIN:
            reasons.append(f"gain under {practice.MIN_GAIN:.0%}")
        if stress.get('p', 1) >= practice.ALPHA:
            reasons.append(f"p not under {practice.ALPHA}")
        if not stress.get('feasible', False):
            reasons.append('feasibility limits failed')
        failed.append(f"shared-lane copy {stress['copy']}: {', '.join(reasons) or 'screening failed'}")
    if not failed:
        failed.append('selection screening did not pass')
    return (f"No change: in the copy the best plan cut delay {result['confirm_gain']:.1%} (p = {result['confirm_p']:.3f}), "
            f"but it failed the limits: {'; '.join(failed)}.")


def recommend(name):
    cfg = road.load(name)
    network = road.net(cfg)
    out = road.OUT/name
    result = json.loads((out/'practice.json').read_text())
    peak = {}
    with open(out/'pattern.csv') as stream:
        for r in csv.DictReader(stream):
            peak[r['site'], r['approach']] = max(peak.get((r['site'], r['approach']), 0), float(r['mean_count']))
    change = result['clear_gain'] and result.get('quality_gate', {}).get('passed', True)
    old = settings(road.file(cfg, 'old_timing'), cfg, network)
    new = settings(out/'plan.add.xml', cfg, network) if change else old
    signals = []
    for signal in cfg['signals']:
        a, b = old[signal['sumo_tls_id']], new[signal['sumo_tls_id']]
        changes = sorted(((g1['max_green_s']-g0['max_green_s'], g0['serves']) for g0, g1 in zip(a['greens'], b['greens'])),
                         key=lambda c: -abs(c[0]))
        reasons = [f"{delta:+.0f} s green for {' '.join(serves)} (learned peak "
                   f"{max(peak.get((signal['name'], s[0]), 0) for s in serves):.0f} veh/15 min)"
                   for delta, serves in changes[:2] if abs(delta) >= 2]
        if change and abs(b['offset_s']-a['offset_s']) >= 2:
            reasons.append(f"offset {a['offset_s']:.0f} -> {b['offset_s']:.0f} s to fit the {b['cycle_s']:.0f} s cycle")
        signals.append(dict(signal=signal['name'], sumo_tls_id=signal['sumo_tls_id'], old=a, new=b,
                            reason='; '.join(reasons) or 'no material change'))
    before = [s['all_requested_delay_s'] for s in result['confirm_old']]
    diffs = sorted(result['confirm_diffs_s'])
    if before and diffs:
        expected = dict(available=True, copy_seeds=result['confirm_seeds'], old_delay_s=round(statistics.mean(before), 1),
                        new_delay_s=round(statistics.mean(before)+statistics.mean(diffs), 1),
                        change_s=round(statistics.mean(diffs), 1), change_range_s=[round(diffs[0], 1), round(diffs[-1], 1)],
                        change_share=round(-result['confirm_gain'], 4), p_value=round(result['confirm_p'], 4))
    else:
        expected = dict(available=False, reason='No copy forecast: confirmation simulations were not run.',
                        copy_seeds=result.get('confirm_seeds', []), old_delay_s=None, new_delay_s=None,
                        change_s=None, change_range_s=None, change_share=None, p_value=None)
    rejected = expected if expected['available'] and not change and result['best_trial'] != 0 else None
    if expected['available'] and not change:
        expected = dict(expected, new_delay_s=expected['old_delay_s'], change_s=0.,
                        change_range_s=[0., 0.], change_share=0., p_value=None)
    card = dict(road=name, label=LABEL, decision='change' if change else 'no change', why=why(result),
                expected_in_copy=expected, rejected_candidate_in_copy=rejected, limits='Phase order, clearances and minimum greens are unchanged. '
                'Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check '
                'rule goes back to old timing if the feed shows traffic clearly worse.', signals=signals)
    (out/'card.json').write_text(json.dumps(card, indent=2)+'\n')
    forecast = expected.get('reason')
    if expected['available']:
        forecast = (f"Selected plan in the copy ({len(diffs)} simulated rush hours): delay per requested trip "
                    f"{expected['old_delay_s']} s -> {expected['new_delay_s']} s, change {expected['change_s']:+} s "
                    f"(range {expected['change_range_s'][0]:+} to {expected['change_range_s'][1]:+} s)"
                    + (f", one-sided p = {expected['p_value']}." if change else '. No timing change is selected.'))
    lines = [f'# Signal Learner card: {name}', '', f'**{LABEL}**', '', f"**Decision: {card['decision']}.** {card['why']}", '',
             forecast, '',
             'Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.', '',
             '| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |', '|---|---|---|---|---|']
    if rejected is not None:
        lines[8:8] = [f"Rejected candidate in the copy: {rejected['old_delay_s']} s -> {rejected['new_delay_s']} s, "
                      f"change {rejected['change_s']:+} s (range {rejected['change_range_s'][0]:+} to "
                      f"{rejected['change_range_s'][1]:+} s), one-sided p = {rejected['p_value']}. "
                      'This candidate is not selected.', '']
    for s in signals:
        greens = '; '.join(f"{' '.join(g0['serves'])}: {g0['max_green_s']:.0f} -> {g1['max_green_s']:.0f}"
                           for g0, g1 in zip(s['old']['greens'], s['new']['greens']))
        lines.append(f"| {s['signal']} | {s['old']['cycle_s']:.0f} -> {s['new']['cycle_s']:.0f} | "
                     f"{s['old']['offset_s']:.0f} -> {s['new']['offset_s']:.0f} | {greens} | {s['reason']} |")
    lines += ['', card['limits'], '']
    (out/'card.md').write_text('\n'.join(lines))
    print(f"recommend {name}: {card['decision']}")
    return card
