"""Recommend: one short card an engineer can approve or reject. Simulated; never sent to a signal."""
import csv
import json
import statistics
import xml.etree.ElementTree as ET

from . import road

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


def recommend(name):
    cfg = road.load(name)
    network = road.net(cfg)
    out = road.OUT/name
    result = json.loads((out/'practice.json').read_text())
    peak = {}
    for r in csv.DictReader(open(out/'pattern.csv')):
        peak[r['site'], r['approach']] = max(peak.get((r['site'], r['approach']), 0), float(r['mean_count']))
    change = result['clear_gain']
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
    expected = dict(copy_seeds=result['confirm_seeds'], old_delay_s=round(statistics.mean(before), 1),
                    new_delay_s=round(statistics.mean(before)+statistics.mean(diffs), 1),
                    change_s=round(statistics.mean(diffs), 1), change_range_s=[round(diffs[0], 1), round(diffs[-1], 1)],
                    change_share=round(-result['confirm_gain'], 4), p_value=round(result['confirm_p'], 4))
    card = dict(road=name, label=LABEL, decision='change' if change else 'no change',
                why=('The copy predicts a clear gain.' if change else
                     'No change: the copy predicts no clear gain over the old timing.'),
                expected_in_copy=expected, limits='Phase order, clearances and minimum greens are unchanged. '
                'Changes are bounded max greens, cycle and offsets. An engineer approves or rejects; the check '
                'rule goes back to old timing if the feed shows traffic clearly worse.', signals=signals)
    (out/'card.json').write_text(json.dumps(card, indent=2)+'\n')
    lines = [f'# Signal Learner card: {name}', '', f'**{LABEL}**', '', f"**Decision: {card['decision']}.** {card['why']}", '',
             f"Expected in the copy ({len(diffs)} simulated rush hours): delay per requested trip "
             f"{expected['old_delay_s']} s -> {expected['new_delay_s']} s, change {expected['change_s']:+} s "
             f"(range {expected['change_range_s'][0]:+} to {expected['change_range_s'][1]:+} s), one-sided p = {expected['p_value']}.", '',
             'Phases list the legs they serve: N:LT is traffic from the north leg turning left or going through.', '',
             '| Signal | Cycle s | Offset s | Max greens s (old -> new) | Reason |', '|---|---|---|---|---|']
    for s in signals:
        greens = '; '.join(f"{' '.join(g0['serves'])}: {g0['max_green_s']:.0f} -> {g1['max_green_s']:.0f}"
                           for g0, g1 in zip(s['old']['greens'], s['new']['greens']))
        lines.append(f"| {s['signal']} | {s['old']['cycle_s']:.0f} -> {s['new']['cycle_s']:.0f} | "
                     f"{s['old']['offset_s']:.0f} -> {s['new']['offset_s']:.0f} | {greens} | {s['reason']} |")
    lines += ['', card['limits'], '']
    (out/'card.md').write_text('\n'.join(lines))
    print(f"recommend {name}: {card['decision']}")
    return card
