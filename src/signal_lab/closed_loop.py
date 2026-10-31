"""Simulation-only advisor experiment. Never connects to a field controller."""
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import traci
import traci.constants as tc

from . import advisor as a, demand as d, evaluate as e, feed as f, pipeline as p

SCENARIOS = ('calm', 'east_surge', 'drop', 'all_drop')


def approval_due(pending, time, last_switch):
    return pending is not None and time >= pending[1]+300 and (
        last_switch is None or time-last_switch >= 900)


def switch(connection, plan, time):
    """Restart all programs; retain configured offsets, lose phase continuity."""
    changes = []
    for logic in ET.parse(p.ROOT/plan).getroot().findall('tlLogic'):
        tls = logic.get('id')
        before = dict(program=connection.trafficlight.getProgram(tls),
                      phase=connection.trafficlight.getPhase(tls),
                      remaining=connection.trafficlight.getNextSwitch(tls)-time)
        connection.trafficlight.setProgram(tls, logic.get('programID'))
        connection.trafficlight.setPhase(tls, 0)
        connection.trafficlight.setPhaseDuration(tls, float(logic.find('phase').get('duration')))
        assert connection.trafficlight.getProgram(tls) == logic.get('programID')
        assert connection.trafficlight.getPhase(tls) == 0
        changes.append(dict(signal=tls, before=before, phase=0,
                            remaining=connection.trafficlight.getNextSwitch(tls)-time,
                            offset=logic.get('offset')))
    assert len(changes) == 5
    return changes


def routes(scenario, path):
    if scenario == 'all_drop':
        # Reuse the exact lasting-demand transformation, with no optimizer run.
        from tools.drift_check import drift_routes
        drift_routes(scenario, path)
    else:
        f.scenario_routes(scenario, path)


def run(scenario, seed, arm, folder, calibration=None, stop=None):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    cfg = p.config()
    begin, end = map(d.seconds, (cfg['scenarios']['pm_peak']['begin'], cfg['scenarios']['pm_peak']['end']))
    finish = stop or end+1800
    route = folder/'demand.xml'
    routes(scenario, route)
    detectors, ids, unmapped = f.feed_detectors(folder)
    assert not unmapped
    library = calibration or json.loads(a.CALIBRATION.read_text())
    # Unique program IDs prevent the PM and night v5 programs overwriting each other.
    programs = ET.Element('additional')
    for name, spec in library['plans'].items():
        for logic in ET.parse(p.ROOT/spec['path']).getroot().findall('tlLogic'):
            logic.set('programID', name)
            programs.append(logic)
    p.xml_write(programs, folder/'programs.xml')
    args = e.command('pm_peak', 'optuna_v5', seed, cfg)
    args[args.index('-r')+1] = route
    # Load v5 PM last so it is the initial active program without a TraCI reset.
    active = ET.parse(p.ROOT/library['plans']['v5_pm']['path']).getroot()
    for logic in active.findall('tlLogic'):
        logic.set('programID', 'v5_pm')
    p.xml_write(active, folder/'initial.xml')
    args[args.index('-a')+1] = f'{detectors},{folder}/programs.xml,{folder}/initial.xml'
    # The PM copy in programs would duplicate initial.xml.
    for logic in list(programs):
        if logic.get('programID') == 'v5_pm':
            programs.remove(logic)
    p.xml_write(programs, folder/'programs.xml')
    args += ['-e', finish, '--summary-output', folder/'summary.xml',
             '--tripinfo-output', folder/'trips.xml', '--tripinfo-output.write-unfinished', 'true',
             '--vehroute-output', folder/'routes.xml', '--vehroute-output.exit-times', 'true',
             '--vehroute-output.write-unfinished', 'true', '--error-log', folder/'warnings.txt']
    traci.start(list(map(str, args)), label=str(folder), stdout=open(folder/'sumo.log', 'w'), doSwitch=False)
    connection = traci.getConnection(str(folder))
    counts, previous = Counter(), {}
    # shortcut: per-step occupancy approximates the detector file, which SUMO buffers and cannot be read live.
    occupied, steps = Counter(), 0
    history, rows = [], []
    state, pending, last_switch = a.State(), None, None
    switches = recommendations = 0
    try:
        for detector in ids:
            connection.inductionloop.subscribe(detector, [
                tc.LAST_STEP_VEHICLE_ID_LIST if detector.startswith('stop_') else tc.LAST_STEP_OCCUPANCY])
        with (folder/'events.jsonl').open('w') as events:
            while connection.simulation.getTime() < finish:
                connection.simulationStep()
                time = int(connection.simulation.getTime())
                steps += 1
                for detector, values in connection.inductionloop.getAllSubscriptionResults().items():
                    if detector.startswith('upstream_'):
                        occupied[detector] += values[tc.LAST_STEP_OCCUPANCY]
                        continue
                    current = set(values[tc.LAST_STEP_VEHICLE_ID_LIST])
                    counts[ids[detector]] += len(current-previous.get(detector, set()))
                    previous[detector] = current
                if approval_due(pending, time, last_switch):
                    target = pending[0]
                    # Library paths have shared original IDs; use the loaded unique IDs.
                    root = ET.parse(p.ROOT/library['plans'][target]['path']).getroot()
                    for logic in root.findall('tlLogic'):
                        logic.set('programID', target)
                    transition = folder/'transition.xml'
                    p.xml_write(root, transition)
                    changes = switch(connection, transition, time)
                    events.write(json.dumps(dict(event='switch', time_s=time, plan=target,
                                                 recommended_s=pending[1], signals=changes))+'\n')
                    switches += 1
                    last_switch, pending = time, None
                    state = replace(state, plan=target, candidate=None, streak=0,
                                    last_change=f.CLOCK+timedelta(seconds=time))
                if time % 300 == 0:
                    occupancy = defaultdict(list)
                    for detector, key in ids.items():
                        if detector.startswith('upstream_'):
                            occupancy[key].append(occupied[detector]/steps)
                    batch = [dict(window_end=(f.CLOCK+timedelta(seconds=time)).isoformat(),
                                  site=site, approach=approach, count=counts[site, approach],
                                  occupancy=sum(occupancy[site, approach])/len(occupancy[site, approach]), ok=1)
                             for site, approach in sorted(set(ids.values()))]
                    counts.clear()
                    occupied.clear()
                    steps = 0
                    if begin < time <= end:
                        rows.extend(batch)
                        history = [r for r in history if r.window_end > f.CLOCK+timedelta(seconds=time-900)]
                        history.extend(a.Row(**{**r, 'window_end': f.CLOCK+timedelta(seconds=time)}) for r in batch)
                        if arm == 'advisor':
                            decision, proposed = a.recommend(history, state, f.CLOCK+timedelta(seconds=time), library)
                            events.write(json.dumps(dict(event='recommendation', time_s=time, **decision))+'\n')
                            if pending is None and decision['plan']:
                                pending = decision['plan'], time
                                recommendations += 1
                            # Recommendations are not actual switches; retain actual plan/hold clock.
                            state = replace(proposed, plan=state.plan, last_change=state.last_change)
    finally:
        connection.close()
    p.write_csv(folder/'feed.csv', rows)
    if stop:
        return rows
    requested, origins = {}, {}
    for v in ET.parse(route).getroot().findall('vehicle'):
        edges = v.find('route').get('edges').split()
        origin = next(edge for edge in edges if edge in cfg['mainline_edges'] or edge in cfg['side_edges'])
        requested[v.get('id')] = float(v.get('depart')), origin in cfg['side_edges']
        origins[v.get('id')] = float(v.get('depart')), origin
    teleports = re.findall(r"Teleporting vehicle '([^']+)'", (folder/'warnings.txt').read_text())
    assert len(teleports) == d.summary_stats(folder/'summary.xml')['teleports']
    trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')}
    travels = e.corridor_times(folder/'routes.xml', e.boundaries(cfg), set(cfg['mainline_edges']), set(teleports))
    groups = e.origin_delays(origins, trips, teleports, begin, end)
    return dict(scenario=scenario, seed=seed, controller=arm,
                **e.metrics(requested, trips, travels, teleports, begin, end),
                worst_origin_delay_s=max(groups.values()), origin_delay_s=groups,
                switches=switches, recommendations=recommendations,
                false_switches=switches if scenario == 'calm' else 0)
