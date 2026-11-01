"""POST-HOC analysis of the Signal Learner held-out test; reads results, never changes them.
Usage: python -m tools.learner_story <deanza-posthoc|split-check|noop-control|facts|video>

Writes only to reports/learner_story/. Simulation only: every run is SUMO on labeled demand.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
import statistics
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from learner import check, road
from signal_lab import pipeline as p
from signal_lab.demand import seconds
from world import trial, worlds as w

OUT = p.ROOT/'reports/learner_story'
HELDOUT = p.ROOT/'reports/learner_heldout'
TRUTH = p.ROOT/'reports/learner_truth'
POSTHOC = 'POST-HOC: run after the frozen held-out test; not part of the preregistration.'
POSTHOC_SEEDS = range(230, 250)
VIDEO_SEED = 200
# Copy routes that turn right from southbound De Anza onto Lazaneo Dr; the hidden world sends these straight on.
LAZANEO_RIGHT, LAZANEO_THROUGH = '393494136#0 -779523373#3 -779523374#3', '393494136#0 393494140#0 393494140#2'


def rel(path):
    return str(Path(path).relative_to(p.ROOT))


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')
    print(f'wrote {OUT/name}')


def rows_for(name, timings, seeds):
    cfg = road.load(name)
    jobs = [(arm, seed) for seed in seeds for arm in timings]
    results = road.many([(cfg, w.routes(name), timings[arm], seed) for arm, seed in jobs])
    return [dict(road=name, arm=arm, seed=seed, **{k: s[k] for k in trial.METRICS}) for (arm, seed), (s, _) in zip(jobs, results)]


def deanza_posthoc():
    """The plan the card rejected, run in the De Anza world against the old timing on new seeds."""
    cfg = road.load('deanza')
    rows = rows_for('deanza', {'old': road.file(cfg, 'old_timing'), 'learner': road.OUT/'deanza/plan.add.xml'}, POSTHOC_SEEDS)
    p.write_csv(OUT/'deanza_posthoc.csv', rows)
    old = statistics.mean(r['all_requested_delay_s'] for r in rows if r['arm'] == 'old')
    summary = trial.summary(rows, 'learner')
    write('deanza_posthoc.json', dict(
        label=POSTHOC, demand='simulated, synthetic demand', seeds=list(POSTHOC_SEEDS),
        plan=rel(road.OUT/'deanza/plan.add.xml'), old_delay_s=old, rejected_plan=summary,
        change_share=summary['all_requested_delay_s']['diff_mean']/old,
        seeds_worse=sum(a['all_requested_delay_s'] > b['all_requested_delay_s'] for a, b in zip(
            (r for r in rows if r['arm'] == 'learner'), (r for r in rows if r['arm'] == 'old')))))


def split_check():
    """Diagnosis: give the copy the world's through/right split at Lazaneo Dr and rerun it on old timing."""
    cfg = road.load('deanza')
    root = ET.parse(road.OUT/'deanza/copy.rou.xml').getroot()
    moved = 0
    for vehicle in root.iter('vehicle'):
        route = vehicle.find('route')
        if LAZANEO_RIGHT in route.get('edges'):
            # The world sends about 1 in 9 of these right; keep that share turning.
            if moved % 9 != 8:
                route.set('edges', route.get('edges').replace(LAZANEO_RIGHT, LAZANEO_THROUGH))
            moved += 1
    practice = json.loads((road.OUT/'deanza/practice.json').read_text())
    with tempfile.TemporaryDirectory() as temp:
        fixed = Path(temp)/'copy_fixed.rou.xml'
        p.xml_write(root, fixed)
        stats = [s for s, _ in road.many([(cfg, fixed, road.file(cfg, 'old_timing'), seed) for seed in practice['search_seeds']])]
    watched = json.loads((TRUTH/'deanza/watch_metrics.json').read_text())
    write('deanza_split_check.json', dict(
        label=POSTHOC+' Diagnosis only; uses hidden-world knowledge the learner never had.',
        demand='simulated, synthetic demand', seeds=practice['search_seeds'], right_turn_routes=moved,
        copy_delay_s=practice['old_search_delay_s'],
        fixed_copy_delay_s=statistics.mean(s['all_requested_delay_s'] for s in stats),
        fixed_copy_unfinished=statistics.mean(s['unfinished'] for s in stats),
        world_watch_delay_s=statistics.mean(s['all_requested_delay_s'] for s in watched)))


def noop_control():
    """Diagnosis: old timing with no change at all, read by the frozen go-back rule from 17:00."""
    out = {}
    for name in trial.HELDOUT_ROADS:
        cfg = road.load(name)
        results = road.many([(cfg, w.routes(name), road.file(cfg, 'old_timing'), s, True) for s in trial.TEST_GOBACK_SEEDS])
        noop = {r['seed']: r for r in json.loads((HELDOUT/'go_back.json').read_text())
                if r['road'] == name and r['program'] == 'noop'}
        runs = [dict(seed=seed, teleports=s['teleports'], noop_went_back=noop[seed]['go_back'],
                     **check.decide(name, rows, seconds('17:00')))
                for seed, (s, (rows, _)) in zip(trial.TEST_GOBACK_SEEDS, results)]
        out[name] = dict(go_back_rate=statistics.mean(r['go_back'] for r in runs), runs=runs)
    write('go_back_control.json', dict(label=POSTHOC+' Diagnosis only; the frozen rule is unchanged.',
                                       demand='simulated, synthetic demand', **out))


def mean_arm(name, arm):
    with open(HELDOUT/'results.csv') as stream:
        return statistics.mean(float(r['all_requested_delay_s']) for r in csv.DictReader(stream)
                               if r['road'] == name and r['arm'] == arm)


def facts():
    """Every number the demo may quote, with unit, label and the file it comes from."""
    out = []

    def add(road_name, name, value, unit, label, source, note=None):
        out.append(dict(road=road_name, name=name, value=float(f'{value:.6g}') if isinstance(value, float) else value,
                        unit=unit, label=label, source=rel(source), **({'note': note} if note else {})))

    results = json.loads((HELDOUT/'results.json').read_text())
    for name in ('wolfe', 'deanza', 'stevens_creek', 'homestead'):
        heldout = name in results['roads']
        label = 'simulated, VTA 2024 counts' if name == 'stevens_creek' else 'simulated, synthetic demand'
        if heldout:
            r, src = results['roads'][name], HELDOUT/'results.json'
            old, arms, goback = mean_arm(name, 'old'), {a: r[a] for a in ('learner', 'fresh')}, r['go_back']
            add(name, 'old_delay', old, 's per requested trip', label, HELDOUT/'results.csv')
            add(name, 'decision', r['decision'], 'card', label, src)
            add(name, 'holm_p', r['holm_p'], 'p', label, src)
            seeds = (list(trial.TEST_SEEDS), list(trial.TEST_GOBACK_SEEDS))
        else:
            src = TRUTH/name/'dev_check.json'
            r = json.loads(src.read_text())
            old, arms, goback = r['old']['all_requested_delay_s']['mean'], r['arms'], r['go_back']
            add(name, 'old_delay', old, 's per requested trip', label, src)
            add(name, 'decision', json.loads((road.OUT/name/'card.json').read_text())['decision'], 'card', label,
                road.OUT/name/'card.json')
            seeds = (r['seeds'], sorted({x['seed'] for x in goback['runs']}))
        for arm in ('learner', 'fresh'):
            m = arms[arm]
            add(name, f'{arm}_delay', m['all_requested_delay_s']['mean'], 's per requested trip', label, src)
            add(name, f'{arm}_change', m['all_requested_delay_s']['diff_mean']/old, 'share of old delay', label, src)
            add(name, f'{arm}_p_one_sided', m['all_requested_delay_s']['p_less'], 'p', label, src)
            add(name, f'{arm}_unfinished', m['unfinished']['mean'], 'trips per rush hour', label, src)
            add(name, f'{arm}_worst_origin_delay', m['worst_origin_delay_s']['mean'], 's per requested trip', label, src)
            add(name, f'{arm}_worst_origin_change', m['worst_origin_delay_s']['diff_mean'], 's vs old', label, src)
        add(name, 'old_unfinished', arms['learner']['unfinished']['mean']-arms['learner']['unfinished']['diff_mean'],
            'trips per rush hour', label, src)
        add(name, 'old_worst_origin_delay', arms['learner']['worst_origin_delay_s']['mean']
            - arms['learner']['worst_origin_delay_s']['diff_mean'], 's per requested trip', label, src)
        add(name, 'go_back_bad_plan_undone', goback['bad_go_back_rate'], 'share of seeds', label, src)
        add(name, 'go_back_noop_undone', goback['noop_go_back_rate'], 'share of seeds', label, src)
        add(name, 'go_back_passed', goback['passed'], 'pass mark: bad >= 0.8, no-op <= 0.2', label, src)
        add(name, 'test_seeds', seeds[0], 'seeds', label, src)
        add(name, 'go_back_seeds', seeds[1], 'seeds', label, src)
        fit = r['copy_vs_truth']
        add(name, 'copy_turn_geh_under_5', fit['geh_under_5_share'], 'share of 15-min turn counts', label, src)
        add(name, 'copy_turn_abs_error', fit['abs_error_share'], 'share of true turn trips', label, src)
        add(name, 'copy_trips_vs_truth', fit['copy_trips']/fit['truth_trips']-1, 'share', label, src,
            f"{fit['copy_trips']} copy vs {fit['truth_trips']} true turn trips")
        practice = road.OUT/name/'practice.json'
        pr = json.loads(practice.read_text())
        add(name, 'copy_old_delay', statistics.mean(s['all_requested_delay_s'] for s in pr['confirm_old']),
            's per requested trip, in the copy', 'simulated, copy learned from feed', practice)
        add(name, 'predicted_change', -pr['confirm_gain'], 'share of copy old delay', 'simulated, copy learned from feed',
            practice, 'copy seeds 10-19')
        if pr['clear_gain']:
            add(name, 'actual_change', arms['learner']['all_requested_delay_s']['diff_mean']/old, 'share of old delay',
                label, src)
        add(name, 'copy_seeds', dict(search=pr['search_seeds'], confirm=pr['confirm_seeds']), 'seeds',
            'simulated, copy learned from feed', practice)
        timing = road.OUT/name/'timing.json'
        if timing.exists():
            for step, seconds in json.loads(timing.read_text()).items():
                add(name, f'run_time_{step}', seconds, 'wall-clock s, up to 3 simulations at once', 'measured compute time', timing)
        else:
            add(name, 'run_time_practice', pr['wall_s'], 'wall-clock s, up to 3 simulations at once', 'measured compute time',
                practice, 'watch and learn times were not recorded for this road')
    for name, path in (('deanza', OUT/'deanza_posthoc.json'), ('deanza', OUT/'deanza_split_check.json')):
        if path.exists():
            add(name, path.stem, json.loads(path.read_text()), 'see file', 'simulated, synthetic demand, POST-HOC', path)
    write('facts.json', dict(label='Numbers for the demo. Every number is from simulation; none is from a real signal.',
                             roles={n: road.load(n)['role'] for n in sorted({f['road'] for f in out})},
                             watch_seeds=list(w.WATCH_SEEDS), facts=out))


def fcd_frames(path):
    """(time, [[x, y, speed], ...]) per saved FCD step."""
    import numpy as np
    frames = []
    with gzip.open(path, 'rb') as stream:
        parser = ET.iterparse(stream, events=('start', 'end'))
        _, root = next(parser)
        for event, element in parser:
            if event == 'end' and element.tag == 'timestep':
                frames.append((int(float(element.get('time'))), np.array(
                    [[float(v.get(k)) for k in ('x', 'y', 'speed')] for v in element]).reshape(-1, 3)))
                root.clear()
    return frames


def video():
    """Wolfe Rd, old vs learner, one held-out test seed; the dashboard's FCD-to-MP4 path, run headless."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    from matplotlib.collections import LineCollection
    import numpy as np
    from signal_lab.dashboard import clock_text, COLORS, FPS, STEP, VIDEO

    name = 'wolfe'
    cfg = road.load(name)
    timings = {'Old timing': road.file(cfg, 'old_timing'), 'Signal Learner plan': road.OUT/name/'plan.add.xml'}
    with tempfile.TemporaryDirectory() as temp:
        def run(item):
            label, timing = item
            out = Path(temp)/f'{label[:3]}.xml.gz'
            # Same net, routes, timing and seed as the scored test run; stopping at 18:30 leaves earlier steps unchanged.
            p.run([p.BIN/'sumo', '-n', road.file(cfg, 'net'), '-r', w.routes(name), '-a', timing, '-b', VIDEO[0],
                   '-e', VIDEO[1], '--seed', VIDEO_SEED, '--time-to-teleport', cfg['time_to_teleport'],
                   '--no-step-log', '--fcd-output', out, '--device.fcd.period', STEP])
            return fcd_frames(out)
        with ThreadPoolExecutor(max_workers=2) as pool:
            data = list(pool.map(run, timings.items()))
    common = sorted({t for t, _ in data[0]} & {t for t, _ in data[1]})
    data = [{t: cars for t, cars in frames} for frames in data]
    with open(HELDOUT/'results.csv') as stream:
        seed = {r['arm']: r for r in csv.DictReader(stream) if r['road'] == name and int(r['seed']) == VIDEO_SEED}

    network = road.net(cfg)
    roads = [edge.getShape() for edge in network.getEdges()]
    points = np.concatenate([np.array(r) for r in roads])
    (xmin, ymin), (xmax, ymax) = points.min(axis=0), points.max(axis=0)
    signals = [(s['name'], np.mean([a.getShape()[-1] for a, _, _ in network.getTLS(s['sumo_tls_id']).getConnections()], axis=0))
               for s in cfg['signals']]
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor('#f7f8fa')
    fig.text(.03, .955, 'Wolfe Rd, Cupertino: old timing vs Signal Learner plan', fontsize=26, fontweight='bold', va='center')
    fig.text(.03, .91, f'SIMULATED, SYNTHETIC DEMAND. Held-out test seed {VIDEO_SEED}, same cars in both. '
             "Old timing is a stale textbook plan, not Cupertino's timing.", fontsize=13, color='#53687a', va='center')
    clock = fig.text(.97, .955, '', fontsize=30, family='monospace', fontweight='bold', ha='right', va='center')
    fig.text(.97, .91, f'{STEP*FPS}x speed', fontsize=15, ha='right', va='center', color='#0b5f58')
    dots, counts = [], []
    for i, label in enumerate(timings):
        ax = fig.add_axes([.03+i*.49, .1, .45, .72])
        ax.set_facecolor('#f7f8fa')
        ax.add_collection(LineCollection(roads, colors='#c3ccd4', linewidths=3))
        for name_, (x, y) in signals:
            ax.plot(x, y, 'o', color='#263d50', ms=6)
            ax.annotate(name_, (x, y), xytext=(10, 0), textcoords='offset points', va='center', fontsize=10, color='#263d50')
        ax.set(xlim=(xmin-30, xmax+30), ylim=(ymin-30, ymax+30), aspect='equal')
        ax.axis('off')
        ax.set_title(label, fontsize=22, fontweight='bold', color=COLORS[i])
        dots.append(ax.scatter([], [], c=[], s=8, cmap='RdYlGn', vmin=0, vmax=16, zorder=3))
        counts.append(fig.text(.03+i*.49, .07, '', fontsize=15, fontweight='bold', color=COLORS[i]))
    fig.text(.5, .025, 'Red = stopped, green = moving | Cars waiting to enter are not drawn | North up | '
             'Simulated, synthetic demand | Not a real signal',
             ha='center', fontsize=12, color='#53687a')
    card = fig.add_axes([0, 0, 1, 1], zorder=5, facecolor='#f7f8fa')
    card.set_xticks([]); card.set_yticks([])  # axis('off') would hide the opaque backdrop too
    for spine in card.spines.values():
        spine.set_visible(False)

    def show_card(lines):
        card.clear(); card.set_facecolor('#f7f8fa'); card.set_xticks([]); card.set_yticks([])
        for y, (text, size) in zip(np.linspace(.7, .25, len(lines)), lines):
            card.text(.5, y, text, ha='center', fontsize=size, color='#13242f' if size > 22 else '#53687a',
                      fontweight='bold' if size > 30 else 'normal')
        card.set_visible(True)

    output = OUT/'wolfe_side_by_side.mp4'
    OUT.mkdir(parents=True, exist_ok=True)
    writer = FFMpegWriter(fps=FPS, codec='libx264', extra_args=['-threads', '1', '-preset', 'fast', '-crf', '23',
                                                                  '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    old, new = seed['old'], seed['learner']
    test = json.loads((HELDOUT/'results.json').read_text())['roads'][name]['learner']
    with writer.saving(fig, str(output), dpi=100):
        show_card([('Wolfe Rd: old timing vs Signal Learner plan', 40), ('Simulated, synthetic demand', 26),
                   (f'Held-out test seed {VIDEO_SEED}, 4:15 to 6:30 PM, {STEP*FPS}x speed', 22),
                   ("Old timing is a stale textbook plan, not Cupertino's timing.", 20)])
        for _ in range(3*FPS):
            writer.grab_frame()
        card.set_visible(False)
        for index, time in enumerate(common):
            clock.set_text(clock_text(time))
            for i, frame in enumerate(data):
                cars = frame[time]
                dots[i].set_offsets(cars[:, :2]); dots[i].set_array(cars[:, 2])
                counts[i].set_text(f'{len(cars):,} cars on the road, {int((cars[:, 2] < .5).sum()):,} stopped')
            if time == 63000:
                fig.savefig(OUT/'wolfe_side_by_side_poster.png', dpi=100)
            writer.grab_frame()
        show_card([(f'Seed {VIDEO_SEED}, delay per requested trip', 30),
                   (f"Old {float(old['all_requested_delay_s']):.0f} s, learner {float(new['all_requested_delay_s']):.0f} s", 34),
                   (f"Unfinished trips: {old['unfinished']} vs {new['unfinished']}", 26),
                   (f"All 20 test seeds: {mean_arm(name, 'old'):.1f} s vs {test['all_requested_delay_s']['mean']:.1f} s; "
                    f"worst origin approach {test['worst_origin_delay_s']['diff_mean']:.0f} s worse", 22),
                   ('Simulated, synthetic demand. 900 s charged per unfinished trip.', 20)])
        for _ in range(4*FPS):
            writer.grab_frame()
    plt.close(fig)
    size = output.stat().st_size
    if size >= 40_000_000:
        raise ValueError(f'Video is {size/1e6:.1f} MB, over 40 MB')
    print(f'wrote {rel(output)}: {len(common)} frames, {size/1e6:.1f} MB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('deanza-posthoc', 'split-check', 'noop-control', 'facts', 'video'))
    step = parser.parse_args().step
    {'deanza-posthoc': deanza_posthoc, 'split-check': split_check, 'noop-control': noop_control,
     'facts': facts, 'video': video}[step]()


if __name__ == '__main__':
    main()
