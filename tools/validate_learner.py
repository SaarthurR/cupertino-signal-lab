"""Reproduce the new synthetic validation in a separate, empty output directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics

import yaml

from learner import card, learn, practice, road
from signal_lab import baseline, pipeline as p
from world import roads, trial, worlds

NAME = 'synthetic_grid'
BASELINE = 8199
OBSERVATION = (8200, 8201, 8202)
PROFILES = (8210, 8211, 8212)
DRIVER_SEEDS = (8310, 8311, 8312)
TRIALS = 24


def prepare_road(folder):
    folder.mkdir(parents=True)
    net_path = folder/'net.xml'
    p.run([p.BIN/'netgenerate', '--grid', '--grid.x-number', 2, '--grid.y-number', 1,
           '--grid.attach-length', 160, '--grid.length', 300, '--tls.set', 'A0,B0',
           '--default.lanenumber', 2, '--no-turnarounds', '--tls.allred.time', 1, '-o', net_path])
    network = p.sumolib.net.readNet(str(net_path), withPrograms=True)
    tls = sorted(network.getTrafficLights(), key=lambda t: t.getID())
    ids = [t.getID() for t in tls]
    incoming = {lane.getEdge() for t in tls for lane, _, _ in t.getConnections()}
    main = {e.getID() for e in incoming if e.getFromNode().getCoord()[1] == e.getToNode().getCoord()[1]}
    cfg = dict(roads.COMMON, name=NAME, role='synthetic_validation', street='Two-signal SUMO grid',
               signals=[dict(name=t, sumo_tls_id=t) for t in ids], mainline_edges=sorted(main),
               side_edges=sorted({e.getID() for e in incoming}-main), net=str(net_path),
               detectors=str(folder/'detectors.xml'), timing_inputs=str(folder/'timing.csv'),
               old_timing=str(folder/'old.xml'))
    p.xml_write(p.loop_detectors(net_path, network, ids), cfg['detectors'])
    p.write_csv(cfg['timing_inputs'], p.timing_rows(network, ids, cfg['speed_mph']))
    (folder/'road.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False))
    return cfg


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def run(out):
    study = out/'study.json'
    write(study, dict(geometry='new two-signal synthetic SUMO grid', baseline=BASELINE,
                      observation=OBSERVATION, test_profiles=PROFILES, driver_seeds=DRIVER_SEEDS,
                      search_trials=TRIALS, fit_limits=learn.FIT_LIMITS, approach_limit=practice.APPROACH_LIMIT,
                      detection_min=trial.BAD_MIN, false_alarm_max=trial.NOOP_MAX))
    cfg = prepare_road(road.ROADS/NAME)
    routes = {seed: out/f'{seed}.rou.xml' for seed in (BASELINE, *OBSERVATION, *PROFILES)}
    for seed, path in routes.items():
        worlds.profile_routes(cfg, seed, path)
    hashes = {seed: learn.digest(path) for seed, path in routes.items()}
    if len(set(hashes.values())) != len(routes):
        raise ValueError('Demand profiles must be distinct')
    old = road.file(cfg, 'old_timing')
    baseline.actuated(road.file(cfg, 'net'), routes[BASELINE], road.window(cfg)[0],
                      [s['sumo_tls_id'] for s in cfg['signals']], cfg['mainline_edges'],
                      road.file(cfg, 'timing_inputs'), old)
    observed = road.many([(cfg, routes[seed], old, seed, True) for seed in OBSERVATION])
    for seed, (_, (feed, lanes)) in zip(OBSERVATION, observed):
        folder = road.OUT/NAME/'feed'/f'seed{seed}'
        folder.mkdir(parents=True)
        p.write_csv(folder/'feed.csv', feed)
        p.write_csv(folder/'lanes.csv', lanes)
    fit = learn.learn(NAME)
    search = practice.practice(NAME, trials=TRIALS)
    decision = card.recommend(NAME)
    selected = card.selected_plan(NAME, cfg)
    controls = {arm: out/f'{arm}.xml' for arm in ('bad', 'noop')}
    worlds.bad_plan(cfg, controls['bad'])
    worlds.noop_plan(cfg, controls['noop'])
    summary = dict(complete=False, decision=decision['decision'], reason=decision['why'], search_trials=search['trials'],
                   copy_fit={k: fit[k] for k in learn.FIT_LIMITS}, demand_sha256=hashes, profiles={})
    for profile in PROFILES:
        demand = routes[profile]
        before = [s for s, _ in road.many([(cfg, demand, old, seed) for seed in DRIVER_SEEDS])]
        after = before if selected is None else [s for s, _ in road.many(
            [(cfg, demand, selected, seed) for seed in DRIVER_SEEDS])]
        with ThreadPoolExecutor(max_workers=road.MAX_SIMS) as pool:
            jobs = [pool.submit(worlds.check_run, NAME, path, arm, seed, demand=demand)
                    for seed in DRIVER_SEEDS for arm, path in controls.items()]
            runs = [job.result() for job in jobs]
        summary['profiles'][profile] = dict(old_score=statistics.mean(s['all_requested_delay_s'] for s in before),
                                           selected_score=statistics.mean(s['all_requested_delay_s'] for s in after),
                                           candidate_passes_limits=None if selected is None else practice.feasible(after, before),
                                           approach_regressions=practice.regressions(after, before),
                                           **trial.alarm_summary(runs, DRIVER_SEEDS))
        write(out/f'profile-{profile}.json', dict(old=before, selected=after, rollback=runs))
        write(out/'summary.json', summary)
        print(f'Validated profile {profile}', flush=True)
    summary['complete'] = True
    write(out/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new directory for generated inputs and results')
    out = parser.parse_args().output.resolve()
    out.mkdir()
    original = road.ROADS, road.OUT
    road.ROADS, road.OUT = out/'roads', out/'learner'
    try:
        print(json.dumps(run(out), indent=2, allow_nan=False))
    finally:
        road.ROADS, road.OUT = original


if __name__ == '__main__':
    main()
