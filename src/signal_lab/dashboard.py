"""2024 judge pages and video from saved, frozen-plan results."""
import csv
import gzip
from html import escape
import json
import os
import re
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# Match the page's system sans so the figures and the HTML read as one piece.
plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans']
from matplotlib.animation import FFMpegWriter
from matplotlib.collections import LineCollection
import numpy as np
import sumolib

from . import pipeline as p
from .evaluate import boundaries, FINAL_SEEDS as SEEDS
from .optimize import bounds as knob_bounds

# One neutral grey for the textbook plan, one accent for ours, everywhere.
COLORS = ('#636f78', '#0b7d73')
INK = ('var(--plan)', 'var(--accent)')
LABELS = ('Textbook plan', 'Our plan (v4)')
CONTROLLERS = ('actuated', 'optuna_v4')
FCD_SEED = 53  # The recorded evening; one of the preregistered test rush hours.
VIDEO = (58500, 66600)  # 16:15 to 18:30, the whole evening the frames cover
STEP = 4  # simulated seconds per video frame; the saved frames are 2 s apart
FPS = 25  # STEP x FPS = 100x real time, so the evening runs in about 81 s


def read_csv(path):
    with open(path, newline='') as stream:
        return list(csv.DictReader(stream))


def cohort(rows, scenario='pm_peak', window='holdout', controllers=('actuated', 'optuna_v3')):
    selected = [[r for r in rows if r['controller'] == c and r['scenario'] == scenario
                 and r['window'] == window and r['seed_group'] == 'v3_final'] for c in controllers]
    for group in selected:
        if sorted(int(r['seed']) for r in group) != list(SEEDS):
            raise ValueError(f'Expected exactly the preregistered test seeds: {scenario}/{window}')
        group.sort(key=lambda r: int(r['seed']))
    return selected


def stats(groups, metric):
    values = [np.array([float(r[metric]) for r in group]) for group in groups]
    return np.array([v.mean() for v in values]), np.array([v.std(ddof=1) for v in values])


def fcd(path, offsets):
    """Keep compact arrays; release each parsed timestep rather than retaining XML."""
    frames, paths, times = [], {}, []
    tracks, seen = {}, set()
    with gzip.open(path, 'rb') as stream:
        parser = ET.iterparse(stream, events=('start', 'end'))
        _, root = next(parser)
        for event, element in parser:
            if event == 'end' and element.tag == 'timestep':
                time = int(float(element.get('time')))
                times.append(time)
                for v in element:
                    vid = v.get('id')
                    edge = v.get('lane').rsplit('_', 1)[0]
                    if vid not in seen and 61200 <= time:
                        tracks[vid] = []
                    if vid in tracks:
                        tracks[vid].append((time, float(v.get('x')), float(v.get('y')), edge))
                    seen.add(vid)
                if (time-VIDEO[0]) % STEP == 0:
                    cars = list(element)
                    frames.append((time, np.array([[float(v.get(k)) for k in ('x', 'y', 'speed')] for v in cars]).reshape(-1, 3)))
                    for v in cars:  # only corridor samples are ever drawn, and keeping all of them exhausts memory
                        edge = v.get('lane').rsplit('_', 1)[0]
                        if edge in offsets:
                            paths.setdefault(v.get('id'), []).append((time, offsets[edge]+float(v.get('pos'))))
                root.clear()
    if times != list(range(VIDEO[0], VIDEO[1], 2)):
        raise ValueError('FCD must cover 16:15 to 18:30 at two-second intervals')
    return frames, paths, tracks


def typical_driver(rows, controllers=CONTROLLERS):
    """Nearest median saving across all entries, including pre-insertion waits."""
    groups = [{r['id']: r for r in rows if r['controller'] == c
               and 61200 <= float(r['requested_s']) < 63000} for c in controllers]
    if groups[0].keys() != groups[1].keys():
        raise ValueError('Race trips must have the same requested vehicles in both runs')
    candidates = []
    for vid in sorted(groups[0]):
        pair = [g[vid] for g in groups]
        if pair[0]['requested_s'] != pair[1]['requested_s']:
            raise ValueError('Race requested departure differs between runs')
        request = float(pair[0]['requested_s'])
        if not all(request <= float(r['depart_s']) <= float(r['arrival_s']) < VIDEO[1]
                   and r.get('teleported', '0') == '0' for r in pair):
            continue
        durations = [float(r['arrival_s'])-request for r in pair]
        candidates.append(dict(id=vid, requested=request, entry=pair[0]['entry'], durations=durations,
                               waits=[float(r['depart_s'])-request for r in pair],
                               drives=[float(r['arrival_s'])-float(r['depart_s']) for r in pair],
                               departures=[float(r['depart_s']) for r in pair],
                               arrivals=[float(r['arrival_s']) for r in pair]))
    if not candidates:
        raise ValueError('No complete paired trips in the video window')
    median = float(np.median([c['durations'][0]-c['durations'][1] for c in candidates]))
    chosen = min(candidates, key=lambda c: (abs(c['durations'][0]-c['durations'][1]-median), c['id']))
    return dict(chosen, median_saving=median, count=len(candidates),
                excluded=len(groups[0])-len(candidates), requested_count=len(groups[0]))


def trip_text(seconds):
    seconds = round(seconds)
    return f'{seconds//60} min {seconds%60:02} s'


def timeline():
    """Per-second counters for both plans, straight from the evaluation's own timeline."""
    series = {c: {} for c in CONTROLLERS}
    for row in read_csv(p.ROOT/f'reports/timeline_seed{FCD_SEED}.csv'):
        series[row['controller']][int(row['time_s'])] = tuple(
            int(row[k]) for k in ('waiting_on_road', 'blocked_from_entering', 'trips_finished'))
    for counts in series.values():
        if sorted(counts) != list(range(VIDEO[0], VIDEO[1])):
            raise ValueError('Timeline must cover every second from 16:15 to 18:30')
    return [series[c] for c in CONTROLLERS]


def segments(samples):
    """Break paths across missing samples/other roads; never join a teleport gap."""
    # A large position jump cannot represent one frame of road travel.
    return [(((a-VIDEO[0])/60, y), ((b-VIDEO[0])/60, z)) for (a, y), (b, z) in zip(samples, samples[1:])
            if b-a == STEP and 0 <= z-y < 40*STEP]


def geometry(cfg):
    net = sumolib.net.readNet(str(p.ROOT/'sim/corridor.net.xml'), withInternal=True)
    roads = [edge.getShape() for edge in net.getEdges()]
    signals = []
    for signal in cfg['signals']:
        coords = [a.getShape()[-1] for a, _, _ in net.getTLS(signal['sumo_tls_id']).getConnections()]
        signals.append((signal['name'], np.mean(coords, axis=0)))
    first, last = boundaries(cfg)['eb']
    path, _ = net.getShortestPath(net.getEdge(first), net.getEdge(last), withInternal=True)
    if not path:
        raise ValueError('No eastbound corridor path')
    offsets, distance = {}, 0
    for edge in path:
        offsets[edge.getID()] = distance
        distance += edge.getLength()
    return roads, signals, offsets, distance


def clock_text(time, seconds=True):
    """12-hour clock, because every caption and the page talk about the evening that way."""
    hour, minute, second = int(time)//3600, int(time)%3600//60, int(time)%60
    stamp = f'{(hour-1)%12+1}:{minute:02}'
    return f'{stamp}:{second:02} PM' if seconds else f'{stamp} PM'


def caption_script(counters):
    """Silent-video claims from this seed's saved counters, crossings and paired trips."""
    textbook, ours = counters
    crossings = read_csv(p.ROOT/f'reports/corridor_trips_seed{FCD_SEED}.csv')
    travel = [[np.mean([float(r['travel_s']) for r in crossings
                        if r['controller'] == c and r['direction'] == direction
                        and 63000 <= float(r['requested_s']) < VIDEO[1]])
               for c in CONTROLLERS] for direction in ('eb', 'wb')]
    rows = read_csv(p.ROOT/f'reports/trips_seed{FCD_SEED}.csv')
    groups = [{r['id']: r for r in rows if r['controller'] == c} for c in CONTROLLERS]
    pairs = [(a, groups[1][vid]) for vid, a in groups[0].items()
             if all(float(r['arrival_s']) >= 0 and r['teleported'] == '0'
                    for r in (a, groups[1][vid]))]
    worse = sum(float(b['arrival_s']) > float(a['arrival_s']) for a, b in pairs)
    return [(58500, 58800,
             f'One simulated rush hour, seed {FCD_SEED}. Same requests and roads, two light plans.\nWatch the line outside and the gap in trips finished.'),
            (58800, 59400,
             'Red = cars stopped on the road. A busy road alone does not tell the story.\nWatch the line outside and trips finished.'),
            (60300, 61200,
             f'4:45 PM, this seed: {textbook[60300][1]:,} cars waiting outside textbook, {ours[60300][1]:,} with v4.'),
            (63000, 63900,
             f'5:30 PM, this seed: {textbook[63000][1]:,} cars waiting outside textbook, {ours[63000][1]:,} with v4.'),
            (64800, 65400,
             f'Seed {FCD_SEED}, crossings requested after 5:30 and finished by 6:30 PM:\n'
             f'Eastbound {travel[0][0]:.0f} to {travel[0][1]:.0f} s; westbound {travel[1][0]:.0f} to {travel[1][1]:.0f} s (worse).'),
            (65400, 66000,
             f'Seed {FCD_SEED}: {worse:,} of {len(pairs):,} paired trips took longer with v4.\n'
             'Trips requested 5:00 to 5:30 PM; clocks include waiting outside.'),
            (66000, VIDEO[1],
             "This is a simulation with limits. Textbook is not the city's plan.\nSome trips get worse; this model needs more calibration before any street trial.")]


def render_media(roads, signals, offsets, distance):
    data = [fcd(p.ROOT/f'reports/fcd_{c}_pm_peak_seed{FCD_SEED}.xml.gz', offsets) for c in CONTROLLERS]
    race = typical_driver(read_csv(p.ROOT/f'reports/trips_seed{FCD_SEED}.csv'))
    print('Median driver:', race, flush=True)
    (p.ROOT/'reports/race.json').write_text(json.dumps(race, indent=2)+'\n')
    counters = timeline()
    span = (VIDEO[1]-VIDEO[0])/60
    ticks = list(range(15, int(span)+1, 30))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True, layout='constrained')
    # A quarter hour at the peak: the whole evening drawn at once is a solid block of ink.
    zoom = [(t-VIDEO[0])/60 for t in (63000, 63900)]
    zoom_ticks = list(range(int(zoom[0]), int(zoom[1])+1, 5))
    for ax, (_, paths, _), label, color in zip(axes, data, LABELS, COLORS):
        lines = [line for samples in paths.values() for line in segments(samples)]
        ax.add_collection(LineCollection(lines, colors=color, linewidths=.4, alpha=.5))
        ax.set(xlim=zoom, ylim=(0, distance), title=label,
               xticks=zoom_ticks, xticklabels=[clock_text(VIDEO[0]+t*60, False) for t in zoom_ticks])
        ax.grid(alpha=.15)
    axes[0].set_ylabel('Eastbound distance from corridor entry (m)')
    fig.suptitle(f'Stevens Creek • eastbound trajectories • one test rush hour (seed {FCD_SEED})')
    fig.savefig(p.ROOT/'reports/time_space.png', dpi=150)
    plt.close(fig)

    # Zoomed on one junction: the hero map already shows the whole corridor, so this picture
    # earns its place only by showing the turning paths inside an intersection.
    name, (cx, cy) = next(s for s in signals if s[0].startswith('De Anza'))
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.add_collection(LineCollection(roads, colors='#9fb0bd', linewidths=2.4))
    ax.plot(cx, cy, 'o', color=COLORS[1], ms=11, zorder=3)
    ax.text(.02, .05, f'{name} signal', transform=ax.transAxes, fontsize=14, color='#13242f')
    ax.set(xlim=(cx-115, cx+115), ylim=(cy-72, cy+72), aspect='equal')
    ax.axis('off')
    fig.savefig(p.ROOT/'reports/network.png', dpi=180, facecolor='white', bbox_inches='tight', pad_inches=.08)
    plt.close(fig)

    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor('#f7f8fa')
    axes = [fig.add_axes([.03+i*.495, .56, .455, .275]) for i in range(2)]
    dots, readouts, bars, queues, finished_counts, rings, timers, driver_labels = [], [], [], [], [], [], [], []
    plan_colors = ('#b23b31', COLORS[1])
    max_blocked = max(v[1] for c in counters for v in c.values())
    all_points = np.concatenate([np.array(r) for r in roads])
    xmin, ymin = all_points.min(axis=0); xmax, ymax = all_points.max(axis=0)
    fig.text(.03, .962, 'Cupertino Signal Lab', fontsize=32, fontweight='bold', va='center')
    clock = fig.text(.97, .958, '', fontsize=42, family='monospace', fontweight='bold', ha='right', va='center')
    speed = fig.text(.97, .920, '', fontsize=24, fontweight='bold', ha='right', va='center', color='#0b5f58')
    fig.text(.03, .920, f'2024 model, seed {FCD_SEED}: one evening, two traffic light plans',
             fontsize=19, color='#53687a', va='center')
    for ax, label, color in zip(axes, LABELS, plan_colors):
        ax.set_facecolor('#f7f8fa')
        ax.add_collection(LineCollection(roads, colors='#c3ccd4', linewidths=4))
        for i, (name, (x, y)) in enumerate(signals):
            ax.plot(x, y, 'o', color='#263d50', ms=8)
            ax.annotate(name.replace(' Blvd', '').replace(' Rd', ''), (x, y), xytext=(0, 45 if name.startswith('De Anza') else 26 if i%2 else -30), textcoords='offset points', ha='center', fontsize=17, zorder=10, bbox=dict(facecolor='#f7f8fa', edgecolor='none', pad=2))
        ax.set(xlim=(xmin-30, xmax+30), ylim=(ymin-30, ymax+30), aspect='auto')
        ax.axis('off')
        ax.set_title(label, fontsize=30, fontweight='bold', pad=16)
        dots.append(ax.scatter([], [], c=[], s=24, cmap='RdYlGn', vmin=0, vmax=16, zorder=3))
        rings.append(ax.plot([], [], 'o', ms=22, mfc='none', mec='#13242f', mew=3, zorder=12)[0])
        driver_labels.append(ax.annotate('Typical driver', (0, 0), xytext=(0, -48), textcoords='offset points', ha='center',
                                         arrowprops=dict(arrowstyle='-', color='#13242f'), fontsize=16, fontweight='bold', zorder=13,
                                         bbox=dict(facecolor='#f7f8fa', edgecolor='none', pad=2)))
        queues.append(fig.text(.03+len(readouts)*.495, .527, '', fontsize=21, fontweight='bold', color=color))
        bar_ax = fig.add_axes([.03+len(readouts)*.495, .493, .455, .016])
        bar_ax.set(xlim=(0, max_blocked), ylim=(0, 1)); bar_ax.axis('off')
        bar_ax.barh(.5, max_blocked, height=1, color='#dde4e9')
        bars.append(bar_ax.barh(.5, 0, height=1, color=color)[0])
        timers.append(fig.text(.03+len(readouts)*.495, .479, '', fontsize=21, fontweight='bold', va='top'))
        fig.text(.03+len(readouts)*.495, .443,
                 f'wait to get on {race["waits"][len(readouts)]:.0f} s + driving {race["drives"][len(readouts)]:.0f} s',
                 fontsize=16, color='#53687a', va='top')
        finished_counts.append(fig.text(.03+len(readouts)*.495, .392, '', fontsize=21, fontweight='bold', color=color))
        readouts.append(fig.text(.03+len(readouts)*.495, .363, '', fontsize=16, color='#53687a'))
    caption = fig.text(.5, .333, '', fontsize=21, ha='center', va='center', color='#0b5f58')

    textbook, ours = counters
    minutes = [(t-VIDEO[0])/60 for t, _ in data[0][0]]
    queues_over_time = [[c[t][1] for t, _ in data[0][0]] for c in counters]
    chart_ax = fig.add_axes([.06, .095, .37, .15])
    chart_ax.set_facecolor('#f7f8fa')
    chart_ax.set(xlim=(0, span), ylim=(0, max_blocked*1.16),
                 xticks=ticks, xticklabels=[clock_text(VIDEO[0]+t*60, False) for t in ticks])
    chart_ax.set_ylabel('Cars', fontsize=17)
    chart_ax.set_title('Cars waiting to get onto Stevens Creek',
                       loc='left', fontsize=18, fontweight='bold', pad=10)
    chart_ax.grid(axis='y', alpha=.18)
    chart_ax.tick_params(labelsize=16)
    for spine in ('top', 'right'):
        chart_ax.spines[spine].set_visible(False)
    growth = [chart_ax.plot([], [], color=color, lw=4)[0] for color in plan_colors]
    end_labels = [chart_ax.annotate('', (0, 0), xytext=(-8, dy), textcoords='offset points',
                                   ha='right', va='center', fontsize=13, fontweight='bold', color=color,
                                   bbox=dict(facecolor='#f7f8fa', edgecolor='none', pad=2))
                  for color, dy in zip(plan_colors, (28, 6))]
    gap_ax = fig.add_axes([.59, .095, .36, .15])
    gap_ax.set_facecolor('#f7f8fa')
    gap = [ours[t][2]-textbook[t][2] for t, _ in data[0][0]]
    gap_ax.set(xlim=(0, span), ylim=(min(0, min(gap))-30, max(gap)+80),
               xticks=ticks, xticklabels=[clock_text(VIDEO[0]+t*60, False) for t in ticks])
    gap_ax.set_title('More trips finished with v4', loc='left', fontsize=18, fontweight='bold', pad=10)
    gap_ax.axhline(0, color='#636f78', lw=1)
    gap_ax.grid(axis='y', alpha=.18)
    gap_ax.tick_params(labelsize=16)
    for spine in ('top', 'right'):
        gap_ax.spines[spine].set_visible(False)
    gap_line, = gap_ax.plot([], [], color=COLORS[1], lw=4)
    gap_label = gap_ax.text(.98, .87, '', transform=gap_ax.transAxes, ha='right', fontsize=17, color=COLORS[1])
    fig.text(.5, .048, 'Red = stopped, yellow = slow, green = moving   |   North up', ha='center', fontsize=16)
    fig.text(.5, .019, f'2024 model, seed {FCD_SEED}. North to south scale expanded. Exact trip clocks; positions every 2 s. Signal states not recorded.', ha='center', fontsize=13, color='#53687a')

    script = caption_script(counters)
    race_start = race['requested']
    race_end = max(race['arrivals'])
    script.insert(0, (race_start, race_end,
                   f'Median-saving trip: {trip_text(race["durations"][0])} vs {trip_text(race["durations"][1])}, including the wait outside.\nClock starts at the same request; selected nearest the median saving.'))
    script.insert(1, (race_end, race_end+600,
                   f'This driver saved {race["durations"][0]-race["durations"][1]:g} seconds from request to arrival.\n'
                   f'Nearest median saving among {race["count"]:,} complete paired trips; {race["excluded"]:,} excluded.'))
    (p.ROOT/f'reports/video_captions_seed{FCD_SEED}.json').write_text(json.dumps(script, indent=2)+'\n')
    writer = FFMpegWriter(fps=FPS, codec='libx264', extra_args=['-threads', '1', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    output = p.ROOT/'reports/side_by_side.mp4'
    with writer.saving(fig, str(output), dpi=100):
        card = fig.add_axes([0, 0, 1, 1], zorder=5, facecolor='#f7f8fa')
        card.set_xticks([]); card.set_yticks([])  # axis('off') would hide the opaque backdrop too
        for spine in card.spines.values():
            spine.set_visible(False)
        for y, line, size in ((.66, 'Cupertino Signal Lab', 70), (.54, 'Less waiting outside the same full road', 34),
                              (.44, f'Left: {LABELS[0]}.    Right: {LABELS[1]}.', 30),
                              (.34, f'At 5:30 PM: {counters[0][63000][1]:,} waiting outside vs {counters[1][63000][1]:,}', 34),
                              (.24, f'{clock_text(VIDEO[0], False)} to {clock_text(VIDEO[1], False)}; {STEP*FPS}x, race at 20x', 26)):
            card.text(.5, y, line, ha='center', fontsize=size, fontweight='bold' if size > 60 else 'normal',
                      color='#13242f' if size > 26 else '#53687a')
        for _ in range(5*FPS):  # a 5 s title card so the video explains itself without a narrator
            writer.grab_frame()
        card.remove()
        peak = next(i for i, (time, _) in enumerate(data[0][0]) if time == 63000)
        for shot, index in enumerate([peak, *range(len(data[0][0]))]):
            time, _ = data[0][0][index]
            if time-STEP < race_start <= time:
                # Hold the request moment so even a sub-frame insertion wait is visible.
                clock.set_text(clock_text(race_start))
                speed.set_text('SLOW MOTION 20x - following one driver')
                caption.set_text('Slowing to 20x. Same driver, same moment. Watch the timers.')
                for i, timer in enumerate(timers):
                    timer.set_text('A typical driver: 0 min 00 s')
                    waiting, blocked, finished = counters[i][int(race_start)]
                    queues[i].set_text(f'Line outside: {blocked:,} cars')
                    bars[i].set_width(blocked)
                    finished_counts[i].set_text(f'Trips finished: {finished:,}')
                    readouts[i].set_text(f'{waiting:,} stopped on road')
                    growth[i].set_data(minutes[:index]+[(race_start-VIDEO[0])/60],
                                       queues_over_time[i][:index]+[blocked])
                    end_labels[i].xy = ((race_start-VIDEO[0])/60, blocked)
                    end_labels[i].set_text(f'{LABELS[i]}: {blocked:,}')
                for _ in range(FPS):
                    writer.grab_frame()
            clock.set_text(clock_text(time))
            speed.set_text('SLOW MOTION 20x - following one driver' if race_start <= time <= race_end else '100x speed')
            caption.set_text(next((line for start, stop, line in script if start <= time < stop), ''))
            if shot == 0:
                caption.set_text(f'5:30 PM preview: {counters[0][time][1]:,} waiting outside vs {counters[1][time][1]:,}.\n'
                                 'Next: replay both plans from 4:15 PM on the same clock.')
            for i in range(2):
                other_time, cars = data[i][0][index]
                if other_time != time:
                    raise ValueError('FCD clocks differ')
                dots[i].set_offsets(cars[:, :2]); dots[i].set_array(cars[:, 2])
                waiting, blocked, finished = counters[i][time]
                queues[i].set_text(f'Line outside: {blocked:,} cars')
                bars[i].set_width(blocked)
                finished_counts[i].set_text(f'Trips finished: {finished:,}')
                readouts[i].set_text(f'{waiting:,} stopped on road')
                samples = data[i][2][race['id']]
                arrive = race['arrivals'][i]
                position = next((s for s in samples if s[0] == time), None)
                rings[i].set_data([position[1]] if position else [], [position[2]] if position else [])
                driver_labels[i].set_visible(position is not None)
                if position:
                    driver_labels[i].xy = (position[1], position[2])
                if time < race_start:
                    text = f'A typical driver: starts at {clock_text(race_start)}'
                elif time < arrive:
                    text = f'A typical driver: {trip_text(time-race_start)}'
                else:
                    text = f'Arrived: {trip_text(arrive-race_start)}'
                timers[i].set_text(text)
            gap_line.set_data(minutes[:index+1], gap[:index+1])
            gap_label.set_text(f'{gap[index]:+,} trips')
            for line, series, label, name in zip(growth, queues_over_time, end_labels, LABELS):
                line.set_data(minutes[:index+1], series[:index+1])
                label.xy = (minutes[index], series[index])
                label.set_text(f'{name}: {series[index]:,}')
                label.set_ha('left' if minutes[index] < 45 else 'right')
                label.set_position((8 if minutes[index] < 45 else -8, label.get_position()[1]))
                label.set_visible(index > 0)
            if time <= (race_start+min(race['arrivals']))/2 < time+STEP:
                fig.savefig(p.ROOT/'reports/side_by_side_poster.png', dpi=100)
            if time-STEP <= race_end < time:
                caption.set_text('Back to 100x speed.')
                for _ in range(FPS):
                    writer.grab_frame()
            for _ in range(3*FPS if shot == 0 else 5 if race_start <= time <= race_end else 1):
                writer.grab_frame()
    plt.close(fig)
    if output.stat().st_size >= 25_000_000:
        raise ValueError('Video exceeds 25 MB')


def map_svg(roads, signals):
    points = np.concatenate([np.array(r) for r in roads])
    low = points.min(axis=0); span = points.max(axis=0)-low
    def xy(x, y):
        return ((x-low[0])/span[0]*1000+45, 228-(y-low[1])/span[1]*160)
    paths = []
    for road in roads:
        coords = ' '.join(f'{a:.1f},{b:.1f}' for a, b in (xy(*point) for point in road))
        paths.append(f'<polyline points="{coords}" fill="none" stroke="var(--road)" stroke-width="3"/>')
    for i, (name, point) in enumerate(signals):
        x, y = xy(*point)
        paths.append(f'<circle cx="{x}" cy="{y}" r="7" fill="var(--accent)"/><text x="{x}" y="{y-24 if i%2 else y+32}" text-anchor="middle" fill="currentColor" font-size="18">{escape(name)}</text>')
    return '<svg viewBox="0 0 1100 292" role="img" aria-label="Five signals from Mary Avenue in the west to De Anza Boulevard in the east; north up">'+''.join(paths)+'<text x="45" y="30" fill="currentColor" font-size="15">N up</text></svg>'


def chart(groups, metrics, title, unit=' s'):
    """Inline SVG stays sharp and follows the page's light/dark palette."""
    values = [stats(groups, key) for key, _ in metrics]
    maximum = max(float(max(m+s)) for m, s in values)*1.18
    height = 90+len(metrics)*112
    parts = [f'<svg viewBox="0 0 760 {height}" role="img" aria-label="{escape(title)}: mean and plus or minus one seed standard deviation"><title>{escape(title)}</title>']
    for j, ((key, label), (means, sds)) in enumerate(zip(metrics, values)):
        y = 45+j*112
        parts.append(f'<text x="0" y="{y-15}" fill="currentColor" font-size="16">{escape(label)}</text>')
        for i, (mean, sd) in enumerate(zip(means, sds)):
            yy = y+i*30; x = 170+mean/maximum*440; lo=170+max(0,mean-sd)/maximum*440; hi=170+(mean+sd)/maximum*440
            parts.append(f'<text x="0" y="{yy+16}" fill="currentColor" font-size="13">{LABELS[i]}</text><rect x="170" y="{yy}" width="{x-170:.2f}" height="22" fill="{INK[i]}"/><path d="M {lo} {yy+11} H {hi} M {lo} {yy+5} V {yy+17} M {hi} {yy+5} V {yy+17}" stroke="currentColor" fill="none"/><text x="{hi+12}" y="{yy+16}" fill="currentColor" font-size="14">{mean:.1f} ± {sd:.1f}{unit}</text>')
    return ''.join(parts)+'</svg>'


def svg(body, width, height, label):
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">'
            f'{body}</svg>')


def text(x, y, body, size=15, anchor='start', fill='currentColor', weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}" '
            f'font-size="{size}" font-weight="{weight}">{escape(str(body))}</text>')


def team_svg():
    """Cars bunched behind red lights, then the same cars spread out under one green wave."""
    parts = []
    for y, reds, caption in ((78, (1, 3, 4), 'Idea: repeated reds make cars bunch up.'),
                             (228, (), 'Idea: staggered greens let cars keep rolling.')):
        parts.append(f'<rect x="16" y="{y-6}" width="528" height="12" rx="6" fill="var(--road)"/>')
        for i in range(5):
            x = 64+i*108
            parts.append(f'<line x1="{x}" y1="{y-10}" x2="{x}" y2="{y-34}" stroke="var(--road)" stroke-width="4"/>'
                         f'<rect x="{x-9}" y="{y-62}" width="18" height="34" rx="9" fill="{"var(--stop)" if i in reds else "var(--accent)"}"/>')
            queue = range(1, 5) if i in reds else (2,)
            for j in queue:
                parts.append(f'<rect x="{x-14-j*22:.0f}" y="{y+14}" width="17" height="11" rx="3" fill="currentColor" opacity=".72"/>')
        parts.append(text(16, y+58, caption, 19))
    return svg(''.join(parts), 560, 312, 'Cars queued behind red lights, then flowing through five greens in a row')


def offset_svg(path):
    """The textbook plan's real shared cycle and staggered main greens."""
    logics = ET.parse(path).getroot().findall('tlLogic')
    cycle = float(next(v.get('value') for v in logics[0].findall('param') if v.get('key') == 'cycleTime'))
    plans = {logic.get('id'): (float(logic.get('offset')),
                               float(next(f.get('duration') for f in logic.findall('phase') if f.get('name') == 'mainline')))
             for logic in logics}
    order = list(reversed(p.config()['signals']))
    parts = [f'<line x1="150" y1="{36+i*52}" x2="740" y2="{36+i*52}" stroke="var(--line)" stroke-width="20"/>'
             for i in range(len(order))]
    for i, signal in enumerate(order):
        offset, green = plans[signal['sumo_tls_id']]
        y = 36+i*52
        parts.append(text(0, y+5, signal['name'], 15))
        for start in (offset-cycle, offset):
            x, width = 150+start/cycle*590, green/cycle*590
            left, right = max(150., x), min(740., x+width)
            if right > left:
                parts.append(f'<rect x="{left:.1f}" y="{y-10}" width="{right-left:.1f}" height="20" rx="4" fill="var(--plan)"/>')
    parts.append(text(150, 36+len(order)*52+12, '0 s', 13, fill='var(--muted)'))
    parts.append(text(740, 36+len(order)*52+12, f'{cycle:.0f} s', 13, anchor='end', fill='var(--muted)'))
    return cycle, svg(''.join(parts), 760, 36+len(order)*52+24,
                      'Main green time for each of the five lights across one shared cycle')


def bars_svg(pairs, unit):
    top = max(v for _, v in pairs)*1.08
    width = 700/len(pairs)
    parts = [text(0, 16, unit, 15, fill='var(--muted)')]
    for i, (name, value) in enumerate(pairs):
        x, height = 30+i*width, value/top*170
        parts.append(f'<rect x="{x+7:.1f}" y="{230-height:.1f}" width="{width-14:.1f}" height="{height:.1f}" rx="4" fill="var(--plan)"/>')
        parts.append(text(x+width/2, 252, name, 14, 'middle', 'var(--muted)'))
        parts.append(text(x+width/2, 224-height, f'{value:,.0f}', 14, 'middle'))
    parts.append('<line x1="24" y1="230" x2="736" y2="230" stroke="var(--line)" stroke-width="2"/>')
    return svg(''.join(parts), 760, 268, unit)


def grid_svg(hit, total):
    """One square per measured count; filled means the simulation landed close to it."""
    columns, cell = 8, 24
    parts = []
    for i in range(total):
        x, y = 2+i % columns*cell, 2+i//columns*cell
        if i < hit:
            style = 'fill="var(--accent)" stroke="var(--accent)"'
        else:
            style = 'fill="none" stroke="var(--line)"'
        parts.append(f'<rect x="{x}" y="{y}" width="19" height="19" rx="4" stroke-width="2" {style}/>')
    edge = 2+columns*cell
    for centre, colour, line in ((hit//2, 'var(--accent)', f'{hit} we matched'),
                                 ((hit+total)//2, 'var(--accent)', f'{total} counted movements')):
        y = 2+centre//columns*cell+11
        parts.append(f'<line x1="{edge}" y1="{y}" x2="{edge+20}" y2="{y}" stroke="{colour}" stroke-width="2"/>'
                     + text(edge+28, y+5, line, 14, fill=colour, weight=600))
    return svg(''.join(parts), 460, -(-total//columns)*cell+6, f'{hit} of {total} measured counts matched closely')


def best_so_far(trials):
    best, curve = float('inf'), []
    for trial in trials:
        if trial['state'] != 'COMPLETE':
            continue
        best = min(best, float(trial['value']))
        curve.append(best)
    if len(curve) < 2:
        raise ValueError('Need at least two completed trials for the search curve')
    return curve


def curve_svg(curve):
    """Best score so far, trial by trial: the tuner's learning curve."""
    low, high = min(curve), max(curve)
    def point(i, value):
        return 110+i/(len(curve)-1)*600, 30+(high-value)/(high-low)*190
    line = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (point(i, v) for i, v in enumerate(curve)))
    parts = [f'<polyline points="{line}" fill="none" stroke="var(--accent)" stroke-width="3.5" stroke-linejoin="round"/>',
             f'<line x1="104" y1="220" x2="716" y2="220" stroke="var(--line)" stroke-width="2"/>',
             text(0, 36, f'{high:,.0f}', 14, fill='var(--muted)'), text(0, 224, f'{low:,.0f}', 14, fill='var(--muted)'),
             text(0, 16, 'score (lower is better)', 14, fill='var(--muted)'),
             text(110, 248, 'first try', 14, fill='var(--muted)'),
             text(710, 248, f'try {len(curve)}', 14, 'end', fill='var(--muted)')]
    x, y = point(len(curve)-1, low)
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="var(--accent)"/>'
                 + text(x-14, y-16, 'best on practice', 14, 'end', 'var(--accent)', 600))
    return svg(''.join(parts), 760, 260, 'Best score so far falls as the tuner tries more timing plans')


KNOBS = (  # family prefix in the trial record, plain name, what its search range means
    ('cycle', 'Cycle length', lambda lo, hi: f'one round of greens, shared by all five, {lo:g} to {hi:g} s'),
    ('offset', 'Start times', lambda lo, hi: 'where in that cycle each light turns green: the wave'),
    ('share', 'Green split dials', lambda lo, hi: f'stretch or shrink one phase’s green, x{lo:g} to x{hi:g}'),
    ('min', 'Shortest main green', lambda lo, hi: f'{lo:g} to {hi:g} s, and never longer than that phase’s green'),
    ('passage', 'Gap times', lambda lo, hi: f'how much quiet ends a green early, {lo:g} to {hi:g} s'),
)

LOOP = (('Pick a plan', '32 numbers that set', 'all five lights'),
        ('Run it', '5 practice rush hours,', 'a whole evening each'),
        ('Score it', 'seconds an average car', 'loses, lower is better'),
        ('Narrow it down', 'the tuner learns which', 'settings scored well'))


def knobs(trials, version=3):
    """What the tuner may change: counted from the search's own record, ranged from its search space."""
    families = {}
    for column in trials[0]:
        if column.startswith('params_'):
            key = column[len('params_'):]
            families.setdefault(key.split('_')[0], []).append(key)
    rows = [(len(families[family]), name, detail(*knob_bounds(families[family][0], version)))
            for family, name, detail in KNOBS]
    if sum(count for count, _, _ in rows) != sum(map(len, families.values())):
        raise ValueError('Knob families do not cover the recorded search space')
    return rows


def tuner_loop_svg(f):
    """One turn of the tuning loop, and what 300 turns bought: try 0 against the plan we kept."""
    box, pitch = 345, 385
    parts = ['<defs><marker id="loop" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
             '<polygon points="0 0, 9 3.5, 0 7" fill="var(--road)"/></marker></defs>']
    for i, (title, first, second) in enumerate((('Pick a plan', f'{sum(c for c, _, _ in f["knobs"])} numbers', f'{f["n_signals"]} lights'),
                                                ('Run it', f'{f["search_seeds"]} practice', 'rush hours'),
                                                ('Score it', 'Seconds lost', 'per car'),
                                                ('Learn', 'Use scores', 'to try again'))):
        x = i*pitch
        if i:
            parts.append(f'<line x1="{x-pitch+box+8}" y1="108" x2="{x-10}" y2="108" '
                         'stroke="var(--road)" stroke-width="3" marker-end="url(#loop)"/>')
        parts.append(f'<rect x="{x}" y="20" width="{box}" height="220" rx="16" fill="var(--paper)" '
                     'stroke="var(--line)" stroke-width="2"/>'
                     + text(x+30, 62, i+1, 24, fill='var(--accent)', weight=700)
                     + text(x+30, 106, title, 44, weight=600)
                     + text(x+30, 164, first, 44, fill='var(--muted)')
                     + text(x+30, 212, second, 44, fill='var(--muted)'))
    parts.append(f'<path d="M {3*pitch+box/2} 240 V 260 Q {3*pitch+box/2} 270 {3*pitch+box/2-10} 270 '
                 f'H {box/2+10} Q {box/2} 270 {box/2} 260 V 252" fill="none" stroke="var(--road)" '
                 'stroke-width="3" marker-end="url(#loop)"/>'
                 + text(750, 310, f'next try, {len(f["curve"])} tries in all', 24, 'middle', 'var(--muted)'))
    parts.append(text(0, 344, f'Score on the {f["search_seeds"]} practice rush hours, seconds lost per car',
                      24, fill='var(--muted)'))
    for i, (value, label, ink) in enumerate(((f['try0'], 'Try 0, the textbook plan', INK[0]),
                                             (f['kept_score'], f'Try {f["kept"]}, the plan we kept', INK[1]))):
        y = 366+i*78
        width = value/f['try0']*790
        parts.append(text(0, y+40, label, 28)
                     + f'<rect x="510" y="{y}" width="{width:.1f}" height="56" rx="6" fill="{ink}"/>'
                     + text(530+width, y+42, f'{value:,.0f} s', 34, fill=ink, weight=700))
    parts.append(text(0, 536, f'{f["search_minutes"]:.0f} minutes on a laptop.', 22, fill='var(--muted)'))
    return svg(''.join(parts), 1500, 550,
               f'The tuning loop: pick a plan, run it, score it, narrow the search, then try again. '
               f'Try 0, the textbook plan, scored {f["try0"]:,.0f} seconds lost per car; '
               f'try {f["kept"]}, the plan we kept, scored {f["kept_score"]:,.0f}.')


def plan_space_svg(f):
    """Everything the tuner is allowed to touch, and the single score plus the rules it is held to."""
    parts = [text(0, 34, 'What it can change', 30, weight=700)]
    for i, (count, name, detail) in enumerate(f['knobs']):
        y = 116+i*96
        parts.append(text(80, y, count, 50, 'end', 'var(--accent)', 700)
                     + text(116, y-8, name, 28, weight=600)
                     + text(116, y+26, detail, 21, fill='var(--muted)'))
    total = sum(count for count, _, _ in f['knobs'])
    parts.append(text(0, 584, f'{total} numbers in all, and nothing else.', 22, fill='var(--muted)'))
    ox = 790
    parts.append(text(ox, 34, 'How it is scored', 30, weight=700)
                 + f'<rect x="{ox}" y="62" width="710" height="150" rx="16" fill="var(--soft)"/>'
                 + text(ox+30, 112, 'Seconds an average car loses,', 29, weight=600)
                 + text(ox+30, 150, 'counting every car that asked to drive.', 29, weight=600)
                 + text(ox+30, 186, f'A car that never finishes is charged {f["miss_charge"]/60:.0f} minutes.',
                        21, fill='var(--muted)'))
    rules = ((f'No direction more than {f["cap"]}% slower',
              'eastbound, westbound and the side streets, against textbook'),
             ('No more cars left stuck',
              f'at most {f["slack"]} more than textbook, in every practice hour'),
             (f'{f["thrown_out"]} of the {len(f["curve"])} tries broke a rule',
              'and were thrown out on the spot'),
             (f'Then {f["pick_seeds"]} more rush hours picked the finalist',
              f'and {f["n_test"]} it had never seen tested it'))
    for i, (head, body) in enumerate(rules):
        y = 282+i*82
        parts.append(f'<circle cx="{ox+23}" cy="{y-9}" r="21" fill="var(--soft)"/>'
                     f'<path d="M {ox+12.5} {y-9.8} l 7.3 7.3 L {ox+33.5} {y-20.3}" fill="none" '
                     'stroke="var(--accent)" stroke-width="4" stroke-linejoin="round"/>'
                     + text(ox+68, y, head, 26, weight=600)
                     + text(ox+68, y+32, body, 21, fill='var(--muted)'))
    return svg(''.join(parts), 1500, 610,
               f'The {total} numbers the tuner may change, the one score it is judged on, '
               'and the rules a plan may not break')


def seeds_svg(bands):
    """Every rush hour the project ever ran, split by what it was allowed to decide."""
    cell, parts = 26, []
    for i, (count, fill, label) in enumerate(bands):
        y = 34+i*84
        parts.append(text(0, y-10, label, 16))
        parts.extend(f'<rect x="{j*cell}" y="{y}" width="20" height="20" rx="6" fill="{fill}"/>' for j in range(count))
    width = max(count for count, _, _ in bands)*cell
    return svg(''.join(parts), width, 34+len(bands)*84-30,
               ' and '.join(label for _, _, label in bands))


def paired_svg(groups, key, label):
    """One row per test rush hour: both plans, same randomness. Labelled on the data, not in a key."""
    values = [[float(r[key]) for r in group] for group in groups]
    low = min(min(v) for v in values)//100*100
    high = (max(max(v) for v in values)//100+1)*100
    def place(j, i):
        return 150+(values[j][i]-low)/(high-low)*500
    parts = [text(0, 20, label, 15, fill='var(--muted)')]
    for i in range(len(values[0])):
        y = 70+i*22
        a, b = place(0, i), place(1, i)
        parts.append(f'<line x1="{a:.1f}" y1="{y}" x2="{b:.1f}" y2="{y}" stroke="var(--line)" stroke-width="3"/>'
                     f'<circle cx="{a:.1f}" cy="{y}" r="6" fill="{INK[0]}"/><circle cx="{b:.1f}" cy="{y}" r="6" fill="{INK[1]}"/>')
        parts.append(text(0, y+5, f'rush hour {i+1}', 13, fill='var(--muted)'))
    # Name the plans over the row where they sit furthest apart, each label turned inward
    # into the gap: side by side they collide, and turned outward they leave the chart.
    widest = max(range(len(values[0])), key=lambda i: abs(values[0][i]-values[1][i]))
    for j, name in enumerate(LABELS):
        x = place(j, widest)
        inward = x < place(1-j, widest)
        parts.append(text(x+(12 if inward else -12), 54, name, 14, 'start' if inward else 'end', INK[j], 600))
    axis_y = 70+len(values[0])*22
    for value in (low, (low+high)/2, high):
        x = 150+(value-low)/(high-low)*500
        parts.append(text(x, axis_y+12, f'{value:.0f} s', 13, 'middle', 'var(--muted)'))
    return svg(''.join(parts), 700, 100+len(values[0])*22,
               f'{label} for both plans in each of the {len(values[0])} test rush hours')


def pipeline_svg(steps, groups):
    """The whole project as one left-to-right flow, so a judge sees the shape before the detail."""
    box, pitch, lefts, x = 150, 186, [], 20
    for _, size in groups:
        lefts += [x+j*pitch for j in range(size)]
        x += size*pitch+34  # a wider gap where the project changes from building to searching
    def left(i): return lefts[i]
    parts = ['<defs><marker id="flow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
             '<polygon points="0 0, 9 3.5, 0 7" fill="var(--road)"/></marker></defs>']
    at = 0
    for name, size in groups:
        start, end = left(at), left(at+size-1)+box
        at += size
        parts.append(text(start, 26, name, 13, fill='var(--muted)', weight=700)
                     + f'<line x1="{start}" y1="38" x2="{end}" y2="38" stroke="var(--line)" stroke-width="2"/>')
    for i, (title, sub) in enumerate(steps):
        x = left(i)
        if i:
            parts.append(f'<line x1="{left(i-1)+box+7}" y1="110" x2="{x-9}" y2="110" '
                         'stroke="var(--road)" stroke-width="2" marker-end="url(#flow)"/>')
        parts.append(f'<rect x="{x}" y="58" width="{box}" height="104" rx="12" fill="var(--paper)" '
                     'stroke="var(--line)" stroke-width="1.5"/>'
                     + text(x+16, 84, f'Step {i+1}', 12.5, fill='var(--accent)', weight=700)
                     + text(x+16, 112, title, 17, weight=600)
                     + text(x+16, 136, sub, 13.5, fill='var(--muted)'))
    return svg(''.join(parts), left(len(steps)-1)+box+20, 182,
               f'The {len(steps)} steps of the project, in order')


def system_svg(f):
    """One shared overview for the pitch and the page, in the existing theme."""
    boxes = [
        ('Real counts', ['VTA field counts:', 'cars per turn,', 'every 15 min']),
        ('Virtual street', ['Real map in SUMO,', 'a traffic simulator', '(like a video game)']),
        ('Virtual cars', [f'{f["trips"]:,} cars made', 'to match the counts']),
        ('Tuner', ['Tries a light timing,', 'watches the simulator,', 'scores and learns;', f'{len(f["curve"])} tries in all']),
        ('Fair test', ['Best vs textbook plan', f'on {f["n_test"]} new simulated', 'rush hours']),
    ]
    parts = ['<defs><marker id="system-arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
             '<polygon points="0 0, 9 3.5, 0 7" fill="var(--accent)"/></marker></defs>']
    for i, (name, lines) in enumerate(boxes):
        x = 2+i*338
        if i:
            parts.append(f'<path d="M{x-36} 150 H{x-8}" stroke="var(--accent)" stroke-width="3" marker-end="url(#system-arrow)"/>')
        parts.append(f'<rect x="{x}" y="32" width="300" height="236" rx="12" fill="var(--paper)" stroke="var(--line)" stroke-width="2"/>'
                     + text(x+20, 88, name, 36, weight=600))
        for j, line in enumerate(lines):
            parts.append(text(x+20, 142+j*36, line, 28, fill='var(--muted)'))
    parts.append('<path d="M1166 268 V344 H490 V280" fill="none" stroke="var(--accent)" stroke-width="3" marker-end="url(#system-arrow)"/>'
                 + text(828, 394, 'try → score → learn', 32, 'middle', 'var(--accent)', 600))
    return svg(''.join(parts), 1656, 424,
               'Real counts to virtual street to virtual cars to tuner to fair test. The tuner loops back to the simulator: try, score, learn.')


def rules_svg(f):
    """The promises we wrote down and saved before the final test, in plain words."""
    rules = (('The one score that decides it',
              'Time lost per car, counting every car, even the ones that never got moving.'),
             ('A promise to the side streets',
              f'Side-street score at most {f["cap"]}% above the textbook plan.'),
             ('A rule about cars getting stuck',
              f'A plan may not leave more cars stuck than the textbook plan does, give or take {f["slack"]}.'),
             (f'{f["n_test"]} brand new rush hours',
              'Chosen in advance, never used for tuning, and run once.'))
    height = 86+len(rules)*72
    parts = [f'<rect x="1.5" y="1.5" width="697" height="{height-3}" rx="14" fill="none" stroke="var(--line)" stroke-width="3"/>',
             text(32, 50, 'Written down and saved before we ran the test', 18, weight=700),
             text(668, 50, f['prereg_date'], 14, 'end', 'var(--muted)')]
    for i, (head, body) in enumerate(rules):
        y = 110+i*72
        parts.append(f'<circle cx="46" cy="{y-5}" r="13" fill="var(--soft)"/>'
                     f'<path d="M 39.5 {y-5.5} l 4.5 4.5 L 52.5 {y-12}" fill="none" stroke="var(--accent)" '
                     'stroke-width="2.6" stroke-linejoin="round"/>'
                     + text(74, y, head, 16.5, weight=600) + text(74, y+24, body, 14.5, fill='var(--muted)'))
    return svg(''.join(parts), 700, height, 'The four rules we committed to before the final test')


def next_steps(f):
    """One closing section, shared by the page and the deck."""
    return [
        f'Calibrate the model: {f["close"]} of {len(f["checks"])} counted turn slots match closely, up from {f["old_close"]} of {len(f["checks"])}. It is not fully calibrated.',
        "Test against a stronger baseline. Textbook is a weak baseline, not the city's real plan.",
        f'Use a separate night plan: side-street delay rises {f["night_side"][0]:.1f} to {f["night_side"][1]:.1f} s, failing our {f["cap"]}% rule. Rush-hour v4 with a separate night plan is untested.',
        f'Protect each trip group. One-seed check: South Stelling mean delay rises {f["south_harm"]:+.0f} s. Some trip groups get much worse.',
        f'Resolve the timing report: De Anza rings total {f["rings"][0]:g}/{f["rings"][1]:g} s against a {f["vta_cycles"]["De Anza Blvd"]:g} s cycle.',
        'Check U-turn greens and waiting spots on the street. Both are model assumptions.',
        f'Get counts for {" and ".join(f["guessed"])}. Both are estimates. Mary uses {f["mary_year"]} data.',
        'Test outside the simulator. This is a simulation, not a field result. Demand replays the fitted hour, with new randomness.',
    ]


def build_deck(rows, roads, signals):
    """The saved 2024 result, using the existing slide layouts and visual system."""
    f = facts(rows)
    def pair(values, digits=0):
        return ' → '.join(f'{v:,.{digits}f}' for v in values)
    limits = next_steps(f)
    slides = [
        (f'<h1>{f["delay_cut"]:.1f}% less rush-hour delay</h1>'
         f'<p class="lead">Against the textbook plan on {f["n_test"]} unseen simulated rush hours.</p>'
         f'<p>Cupertino Signal Lab · VTA {f["year"]} counts<br>Paired test p ≈ {f["primary_p"]:.0e}</p>',
         'We retimed five Stevens Creek lights in SUMO. The score counts every car that asked to drive, including waiting to enter and unfinished trips. This is a fixed-demand simulation result versus textbook.'),
        (f'<h2>More cars finish the rush hour</h2><div class="scores">'
         f'<div class="score pair"><strong>{pair(f["unfinished"])}</strong><span>unfinished cars</span></div>'
         f'<div class="score pair"><strong>{pair(f["teleports"])}</strong><span>stuck-car events</span></div></div>'
         f'<p class="under">Totals across {f["n_test"]} paired runs. Textbook → v4.</p>'
         f'<p>Average delay per requested car: {pair(f["delay"])} s.</p>',
         f'Unfinished includes cars still driving and cars waiting to enter after the drain. Each unfinished trip or teleport receives a {f["miss_charge"]:g} second scoring charge. It is a convention, not observed delay.'),
        (f'<h2>Eastbound and side streets gain</h2><div class="scores">'
         f'<div class="score pair"><strong>{pair(f["eb"])}</strong><span>eastbound travel, s</span></div>'
         f'<div class="score pair"><strong>{pair(f["side"])}</strong><span>side-street delay, s</span></div>'
         f'<div class="score pair cost"><strong>{pair(f["wb"])}</strong><span>westbound travel, s</span></div></div>'
         '<p class="under">Textbook → v4. Westbound is slightly slower.</p>',
         'These are means across the final test. Directional travel covers completed, nonteleported corridor crossings and excludes waiting to enter. Side-street delay counts every requested side-origin trip. Aggregate gains can hide harm to particular trip groups.'),
        (f'<h2>{f["n_signals"]} lights on Stevens Creek</h2><div class="fill" style="--fw:1664px">{map_svg(roads, signals)}</div>'
         '<p class="under">Mary Avenue to De Anza Boulevard.</p>',
         'The real map comes from OpenStreetMap. SUMO moves each car through these mapped roads and modeled lights.'),
        ('<h2>One rush hour, two plans</h2><video controls preload="metadata" poster="../reports/side_by_side_poster.png" src="../reports/side_by_side.mp4"></video>'
         '<p class="under">2024 model, final-test seed 53. Textbook versus frozen v4.</p>',
         'Same requests and clock. The race includes waiting outside; the captions show the gains and the trips that get worse. This is one simulated seed.'),
        (f'<h2>We asked VTA for real data</h2><div class="two" style="--cols:1000px 592px"><div class="fill">'
         f'{bars_svg(sorted(f["counts"].items()), "De Anza: counted cars per 15 minutes")}</div><div>'
         f'<p>IDAX counts<br>{f["count_date"]}</p><p>VTA also sent its model timing for De Anza and Stelling.</p>'
         '<p>Thank you to VTA:<br>Kia Sharifi, P.E.<br>Larissa Sanderfer</p></div></div>',
         'We asked VTA and received its 2024 counts and Vistro model reports. These are historical field counts and model timing inputs, not a confirmed current city controller sheet.'),
        (f'<h2>Better data exposed our model’s gaps</h2>'
         f'<p class="lead">The old model sent no cars on {f["missing_turns"]} counted turns.</p>'
         '<p>We fixed the allocation and added U-turns. We kept the observed counts.</p>'
         '<p class="under">New evidence helped us find and repair a real model problem.</p>',
         'The missing allocations were De Anza eastbound left and Stelling westbound left and right. They already had legal connections. We repaired the demand allocation, modeled U-turns separately, and corrected modeled waiting positions. These changes do not establish full calibration.'),
        (f'<h2>How it works</h2><div class="fill">{system_svg(f)}</div>'
         '<p class="under">Output: a candidate timing plan for an engineer to review.</p>',
         'The simulator is like a video game of Stevens Creek. The tuner changes the lights, watches the score, and learns which settings to try next.'),
        (f'<h2>The tuner learns from its own tries</h2><div class="fill" style="--fw:1664px">{tuner_loop_svg(f)}</div>'
         '<p class="under">Try 0 was textbook. Fresh runs picked the finalist.</p>',
         f'Bayesian optimization learns from its own trials. It is not a neural network. Each trial runs {f["search_seeds"]} practice rush hours. Try 0 scored {f["try0"]:,.0f} seconds per car, and selected try {f["kept"]} scored {f["kept_score"]:,.0f} on practice.'),
        (f'<h2>What it can change, and how we score it</h2><div class="fill" style="--fw:1664px">{plan_space_svg(f)}</div>',
         f'The tuner changes {sum(c for c, _, _ in f["knobs"])} settings. The score counts every requested car. Mean side-street, eastbound and westbound results must stay within {f["cap"]}% of textbook. Every seed must have at most {f["slack"]} extra stuck-car events. Rush hour passes these aggregate rules, night does not.'),
        (f'<h2>{len(f["curve"])} trials, then an unseen test</h2><div class="two" style="--cols:992px 600px">'
         f'<div class="fill">{curve_svg(f["curve"])}</div><div class="fill">{seeds_svg(((f["search_seeds"], "var(--road)", "Practice: " + f["train_range"]), (f["pick_seeds"], "var(--road)", "Selection: " + f["pick_range"]), (f["n_test"], "var(--accent)", "Final test: " + f["test_range"])))}</div></div>'
         f'<p class="under">Rules committed first, {f["prereg_date"]}. Selected try {f["kept"]}.</p>',
         'We wrote the rules before the optimizer ran, froze the selected plan, then ran the final test. The final seeds were held out of tuning and selection. These are repeats of historical demand with new randomness, not separately measured evenings.'),
        (f'<h2>v4 improves on v3 too</h2><div class="scores">'
         f'<div class="score"><strong>{f["delay"][0]:.0f} s</strong><span>textbook delay</span></div>'
         f'<div class="score"><strong>{f["v3_delay"]:.0f} s</strong><span>frozen v3 delay</span></div>'
         f'<div class="score"><strong>{f["delay"][1]:.0f} s</strong><span>v4 delay</span></div></div>'
         f'<p>Cycle: v4 {f["cycle"]:.0f} s, textbook {f["base_cycle"]:.1f} s.</p>'
         '<p class="under">Same final rush-hour test. Mean delay per requested car.</p>',
         'Frozen v3 also beats textbook on the new data. v4 has the lowest delay of these three. The confirmatory paired test is v4 versus textbook, not v4 versus v3.'),
        (f'<h2>VTA’s timing inputs in our model</h2><div class="scores">'
         f'<div class="score"><strong>{f["vta_cycles"]["De Anza Blvd"]:g} s</strong><span>De Anza input cycle</span></div>'
         f'<div class="score"><strong>{f["vta_cycles"]["Stelling Rd"]:g} s</strong><span>Stelling input cycle</span></div></div>'
         '<p>Our close copy jams in the model.</p>'
         '<p class="under">A projection, not a claim about the street. We do not claim to beat VTA or the city.</p>',
         'VTA supplied Vistro inputs. Our SUMO copy cannot reproduce independent rings, overlaps and every controller detail. Its congestion is a projection failure to investigate, not evidence that the street fails.'),
        ('<h2>What we would do next</h2><ul class="notes">'
         + ''.join(f'<li>{step}</li>' for step in limits[:4]) + '</ul>',
         'The aggregate rush-hour win is only the start. ' + ' '.join(limits[:4])),
        ('<h2>What we would do next</h2><ul class="notes">'
         + ''.join(f'<li>{step}</li>' for step in limits[4:])
         + '</ul><p class="under">Roads: OpenStreetMap. Counts and timing inputs: VTA. Thank you.</p>',
         'Before any street trial, resolve these model and source limits. ' + ' '.join(limits[4:])),
    ]
    body = ''.join(f'<section class="slide"><div class="inner">{html}</div>'
                   f'<p class="note">{escape(note)}</p></section>' for html, note in slides)
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cupertino Signal Lab, pitch deck</title>
<style>
:root{{color-scheme:light dark;--bg:#f5f7f8;--paper:#fff;--ink:#13242f;--muted:#53687a;--line:#dde4e9;--accent:#0b7d73;--soft:#eef7f5;--warn:#a6560d;--plan:#636f78;--stop:#b23b31;--road:#a9b8c4}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1a23;--paper:#17242e;--ink:#e8eff3;--muted:#a7bac6;--line:#2e414e;--accent:#5ecabd;--soft:#16302d;--warn:#e9a75d;--plan:#9aa9b4;--stop:#e2796c;--road:#61788a}}}}
*{{box-sizing:border-box;margin:0}}
html,body{{width:100%;height:100%;overflow:hidden;background:var(--bg)}}
body{{color:var(--ink);font:28px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.viewport{{position:fixed;inset:0;overflow:hidden}}
.stage{{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden;transform-origin:0 0;background:var(--bg)}}
.slide{{position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;visibility:hidden;opacity:0;pointer-events:none;padding:96px 128px 112px;background:var(--bg)}}
.slide.active{{visibility:visible;opacity:1;pointer-events:auto;z-index:1}}
.inner{{display:flex;flex-direction:column;justify-content:center;height:100%;gap:40px}}
h1{{font-size:132px;line-height:1;letter-spacing:-.045em;max-width:16ch}}
h2{{font-size:76px;line-height:1.06;letter-spacing:-.035em;max-width:20ch}}
p{{font-size:32px;line-height:1.45;max-width:46ch;color:var(--muted)}}
.lead{{font-size:44px;line-height:1.3;color:var(--muted);max-width:28ch}}
.hint{{font-size:24px;color:var(--muted)}}
.under{{font-size:27px}}
.fill{{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}}
.fill>svg{{width:100%;max-width:var(--fw,1664px);height:auto;max-height:100%}}
.two{{flex:1;display:grid;grid-template-columns:var(--cols,1fr 1fr);gap:72px;align-items:center;align-content:center;min-height:0}}
.two p{{font-size:30px;margin-bottom:22px}}
.video{{height:100%}}
video{{max-height:640px;border-radius:18px;background:#0b1218}}

.scores{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:40px}}
.score strong{{display:block;font-size:96px;line-height:1;letter-spacing:-.04em;color:var(--accent);font-variant-numeric:tabular-nums}}
.score.pair strong{{font-size:60px}}  /* "185 to 17" needs twice the room of a percentage */
.score.cost strong{{color:var(--warn)}}
.score span{{display:block;margin-top:16px;font-size:28px;color:var(--muted);max-width:14ch}}
.notes{{list-style:none;padding:0;max-width:64ch}}
.notes li{{padding:18px 0;border-top:1px solid var(--line);font-size:28px;line-height:1.35}}
/* A footer bar, not floating text: a four-line note would otherwise sit on top of the slide. */
.note{{position:absolute;left:0;right:0;bottom:0;padding:18px 128px 26px;font-size:22px;line-height:1.4;color:var(--muted);max-width:none;display:none;background:var(--bg);border-top:1px solid var(--line)}}
body.notes-on .note{{display:block}}
body.notes-on .slide{{padding-bottom:208px}}  /* the longest note is four lines; never cover the slide */
.count{{position:fixed;right:22px;bottom:16px;z-index:9;font-size:14px;color:var(--muted);font-variant-numeric:tabular-nums}}
@media(prefers-reduced-motion:no-preference){{.slide{{transition:opacity .22s ease-out}}}}
</style>
<div class="viewport"><div class="stage" id="stage">{body}</div></div>
<p class="count" id="count"></p>
<script>
// Fixed 1920x1080 stage, scaled as one piece so slides never reflow.
const stage = document.getElementById('stage'), slides = [...document.querySelectorAll('.slide')],
      count = document.getElementById('count');
let at = 0;
const fit = () => {{
  const k = Math.min(innerWidth/1920, innerHeight/1080);
  stage.style.transform = `translate(${{(innerWidth-1920*k)/2}}px, ${{(innerHeight-1080*k)/2}}px) scale(${{k}})`;
}};
const show = i => {{
  at = Math.max(0, Math.min(i, slides.length-1));
  slides.forEach((s, j) => s.classList.toggle('active', j === at));
  count.textContent = `${{at+1}} / ${{slides.length}}`;
}};
addEventListener('resize', fit);
addEventListener('keydown', e => {{
  if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(e.key)) {{ show(at+1); e.preventDefault(); }}
  else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)) {{ show(at-1); e.preventDefault(); }}
  else if (e.key === 'Home') show(0);
  else if (e.key === 'End') show(slides.length-1);
  else if (e.key === 'n' || e.key === 'N') document.body.classList.toggle('notes-on');
}});
fit(); show(0);
</script>
</html>'''


PRIMARY = 'all_requested_delay_s'  # The preregistered score: delay per requested car.


def facts(rows):
    """All quoted numbers come from saved project artifacts, never a new simulation."""
    evaluation = json.loads((p.ROOT/'reports/eval_v4.json').read_text())
    search = json.loads((p.ROOT/'reports/optimize_v4.json').read_text())
    seeds = evaluation['seeds']
    def groups_for(controller='optuna_v4', scenario='pm_peak', window='holdout'):
        groups = [[r for r in rows if r['controller'] == c and r['scenario'] == scenario
                   and r['window'] == window and r['seed_group'] == 'v4_final']
                  for c in ('actuated', controller)]
        for group in groups:
            group.sort(key=lambda r: int(r['seed']))
            if [int(r['seed']) for r in group] != seeds:
                raise ValueError(f'Expected exactly v4 final seeds: {controller}/{scenario}/{window}')
        if any(a['requested'] != b['requested'] for a, b in zip(*groups)):
            raise ValueError('Paired plans must have identical requested demand')
        return groups
    groups = groups_for()
    trials = read_csv(p.ROOT/'reports/optimize_v4_trials.csv')
    scores = {int(t['number']): float(t['value']) for t in trials if t['state'] == 'COMPLETE'}
    sources = read_csv(p.ROOT/'data/processed/tmc_sources.csv')
    measured = [r for r in sources if r['source'] == 'measured']
    counts = {}
    for row in read_csv(p.ROOT/'data/processed/tmc.csv'):
        if row['intersection'] == measured[0]['intersection']:
            counts[row['interval_start']] = counts.get(row['interval_start'], 0)+int(row['vehicles'])
    checks = [r for r in read_csv(p.ROOT/'reports/model/physical_training.csv')
              if r['seed'] == '0' and r['source'] == 'measured' and r['movement'] != 'U'
              and r['interval_start'] >= '17:30']
    missing = [r for r in read_csv(p.ROOT/'reports/fit/movement_summary.csv')
               if r['source'] == 'measured' and r['period'] == 'fit' and r['movement'] != 'U'
               and float(r['observed']) > 0 and float(r['before_scheduled']) == 0]
    protocol = (p.ROOT/'docs/PREREGISTRATION.md').read_text().split('## Optimization v4 preregistration')[1]
    timing_doc = (p.ROOT/'docs/vta-timing.md').read_text()
    readme = (p.ROOT/'README.md').read_text()
    south = re.search(r'South Stelling-origin.*?mean delay rose \*\*([\d.]+) → ([\d.]+) s', readme)
    vta_cycles = {r['intersection']: float(r['cycle_s']) for r in read_csv(p.ROOT/'data/processed/vta_timing_2024.csv')}
    base_cycle, base_svg = offset_svg(p.ROOT/'sim/tls_actuated_pm_peak.add.xml')
    def means(metric): return stats(groups, metric)[0]
    delay = means(PRIMARY)
    test = next(t for t in evaluation['tests'] if t['controller'] == 'optuna_v4'
                and t['scenario'] == 'pm_peak' and t['window'] == 'holdout' and t['metric'] == PRIMARY)
    row = groups[0][0]
    charge = ((float(row[PRIMARY])-float(row['all_requested_delay_0_s']))*float(row['requested'])
              / (float(row['unfinished'])+float(row['teleports'])))
    def seed_range(values): return f'{min(values)} to {max(values)}'
    return {
        'groups': groups, 'trips': int(row['requested']), 'curve': best_so_far(trials),
        'thrown_out': sum(float(r['value']) >= 1e9 for r in trials if r['state'] == 'COMPLETE'),
        'search_seeds': len(search['seeds']), 'pick_seeds': len(search['selection_seeds']),
        'train_range': seed_range(search['seeds']), 'pick_range': seed_range(search['selection_seeds']),
        'test_range': seed_range(seeds), 'knobs': knobs(trials, version=4),
        'try0': scores[0], 'kept': int(search['best']['trial']),
        'kept_score': scores[int(search['best']['trial'])], 'search_minutes': search['wall_s']/60,
        'miss_charge': charge, 'prereg_date': re.search(r'\d{4}-\d{2}-\d{2}', protocol).group(),
        'cap': int(re.search(r'<=([\d]+)%', protocol).group(1))-100,
        'slack': int(re.search(r'textbook\+(\d+)', protocol).group(1)),
        'checks': checks, 'close': sum(float(r['geh']) < 5 for r in checks),
        'old_close': int(re.search(r'old-model (\d+)/', protocol).group(1)),
        'missing_turns': len(missing), 'year': measured[0]['year'],
        'count_date': measured[0]['count_date'], 'counts': counts,
        'mary_year': next(r['year'] for r in sources if r['intersection'].startswith('Mary')),
        'guessed': [r['intersection'] for r in sources if not r['count_date']],
        'base_cycle': base_cycle, 'base_svg': base_svg, 'cycle': search['best']['params']['cycle_s'],
        'n_signals': len(p.config()['signals']), 'n_test': len(seeds), 'delay': delay, 'delay_cut': (1-delay[1]/delay[0])*100,
        'eb': means('mainline_travel_eb_s'), 'wb': means('mainline_travel_wb_s'),
        'side': means('side_all_requested_delay_s'), 'primary_p': float(test['p_value']),
        'v3_delay': stats(groups_for('optuna_v3'), PRIMARY)[0][1],
        'unfinished': [sum(int(r['unfinished']) for r in group) for group in groups],
        'teleports': [sum(int(r['teleports']) for r in group) for group in groups],
        'night_side': stats(groups_for(scenario='night', window='full'), 'side_all_requested_delay_s')[0],
        'south_harm': float(south[2])-float(south[1]), 'vta_cycles': vta_cycles,
        'rings': [float(v) for v in re.findall(r'ring [12].*?\*\*(\d+) s\*\*', timing_doc, re.I)[:2]],
    }


def build_page(rows, roads, signals):
    f = facts(rows)
    def pair(values, digits=0): return ' → '.join(f'{v:,.{digits}f}' for v in values)
    limits = ''.join(f'<li>{step}</li>' for step in next_steps(f))
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cupertino Signal Lab</title>
<style>
:root{{color-scheme:light dark;--bg:#f5f7f8;--paper:#fff;--ink:#13242f;--muted:#53687a;--line:#dde4e9;--accent:#0b7d73;--soft:#eef7f5;--warn:#a6560d;--plan:#636f78;--stop:#b23b31;--road:#a9b8c4;--r:14px}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1a23;--paper:#17242e;--ink:#e8eff3;--muted:#a7bac6;--line:#2e414e;--accent:#5ecabd;--soft:#16302d;--warn:#e9a75d;--plan:#9aa9b4;--stop:#e2796c;--road:#61788a}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
main{{max-width:1040px;margin:auto;padding:0 28px 72px}}
h1{{font-size:clamp(38px,6.4vw,64px);line-height:1.03;letter-spacing:-.045em;margin:16px 0 20px;max-width:15ch}}
h2{{font-size:clamp(25px,3.5vw,35px);line-height:1.14;letter-spacing:-.03em;margin:0 0 12px;max-width:21ch}}
p{{margin:12px 0;max-width:60ch}}
.lead{{font-size:clamp(19px,2.3vw,22px);color:var(--muted);max-width:42ch}}
.muted{{color:var(--muted)}}
small{{display:block;font-size:13.5px;line-height:1.55;color:var(--muted);max-width:74ch;margin-top:14px}}
.masthead{{display:flex;justify-content:space-between;gap:20px;padding:22px 0;border-bottom:1px solid var(--line);font-size:14.5px;font-weight:600;letter-spacing:.01em}}
.masthead span{{color:var(--muted);font-weight:400}}
header{{padding:52px 0 0}}
.step{{padding:78px 0;border-top:1px solid var(--line)}}
.n{{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:999px;background:var(--soft);color:var(--accent);font:700 16px/1 inherit;margin-bottom:16px}}
figure{{margin:28px 0 0}}
figcaption{{font-size:14.5px;line-height:1.55;color:var(--muted);margin-top:14px;max-width:70ch}}
.card{{background:var(--paper);border:1px solid var(--line);border-radius:var(--r);padding:26px}}
.card.tight{{padding:12px}}
svg,img,video{{display:block;width:100%;height:auto}}
img{{border-radius:calc(var(--r) - 4px);background:#fff}}
video{{border-radius:var(--r);background:#0b1218}}
.wide{{overflow-x:auto}}
.wide:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}
.wide>svg{{min-width:560px}}
.wide.flow>svg{{min-width:880px}}
.split{{display:grid;grid-template-columns:5fr 6fr;gap:48px;align-items:center}}
.split>*{{min-width:0}}  /* grid items default to min-content, which a wide figure blows past */
.split figure{{margin:0}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 0;padding:0;list-style:none}}
.chips li{{background:var(--soft);color:var(--accent);border-radius:999px;padding:8px 16px;font-size:15px;font-weight:600}}
.scores{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:26px;margin:14px 0 8px}}
.score strong{{display:block;font-size:clamp(38px,5vw,52px);line-height:1;letter-spacing:-.04em;color:var(--accent);font-variant-numeric:tabular-nums}}
.score.pair strong{{font-size:clamp(32px,3.2vw,36px)}}  /* "185 to 17" needs twice the room of a percentage */
.score.cost strong{{color:var(--warn)}}
.score span{{display:block;margin-top:12px;font-size:16.5px;max-width:22ch}}
.label{{margin:34px 0 0;font-size:13.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}
.notes{{margin:18px 0 0;padding:0;list-style:none;max-width:62ch}}
.notes li{{padding:14px 0;border-top:1px solid var(--line)}}
.counts{{font-variant-numeric:tabular-nums}}
details{{border-top:1px solid var(--line)}}
summary{{cursor:pointer;padding:22px 0;font-weight:600;font-size:19px}}
summary:focus-visible,a:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}
details details summary{{font-size:16px;padding:14px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}}
th,td{{text-align:left;padding:9px;border-bottom:1px solid var(--line);white-space:nowrap}}
.scroll{{overflow-x:auto}}
a{{color:var(--accent)}}
::selection{{background:var(--soft);color:var(--ink)}}
.wide,.scroll{{scrollbar-color:var(--road) transparent;scrollbar-width:thin}}
video{{accent-color:var(--accent)}}
footer{{padding:34px 0;font-size:14px;color:var(--muted);border-top:1px solid var(--line)}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@media(prefers-reduced-motion:no-preference){{@supports(animation-timeline:view()){{.step{{animation:fade linear both;animation-timeline:view();animation-range:entry 4% entry 30%}}}}}}
@media(max-width:860px){{.split{{grid-template-columns:1fr;gap:26px}}.split figure{{margin-top:12px}}}}
@media(max-width:720px){{.card:has(>svg){{overflow-x:auto}}.card>svg{{min-width:560px}}.card:has(>svg)::after{{content:"Swipe diagram sideways to read";display:block;font-size:13px;color:var(--muted);margin-top:10px}}main{{padding:0 18px 52px}}.step{{padding:52px 0}}.scores{{grid-template-columns:1fr;gap:26px}}.card{{padding:16px}}}}
</style><main>
<p class="masthead">Cupertino Signal Lab<span>AI Club hackathon project</span></p>
<header><h1>{f['delay_cut']:.1f}% less rush-hour delay</h1>
<p class="lead">{f['n_signals']} Stevens Creek lights, retimed in a simulator. Against textbook on {f['n_test']} unseen simulated rush hours using VTA {f['year']} counts.</p>
<p>Mean delay per requested car: {pair(f['delay'])} s. Paired test p ≈ {f['primary_p']:.0e}.</p>
<div class="scores"><div class="score pair"><strong>{pair(f['unfinished'])}</strong><span>unfinished cars</span></div><div class="score pair"><strong>{pair(f['teleports'])}</strong><span>stuck-car events</span></div></div>
<small>Textbook → v4. Counts total all {f['n_test']} runs. Unseen means new random seeds, with historical demand replayed.</small>
<figure><div class="card tight wide" tabindex="0">{map_svg(roads, signals)}</div><figcaption>Mary Avenue to De Anza Boulevard. Road geometry from OpenStreetMap. North is up, with the north to south scale stretched so names fit.</figcaption></figure></header>

<section class="step"><h2>Eastbound and side streets gain</h2>
<div class="scores"><div class="score pair"><strong>{pair(f['eb'])} s</strong><span>eastbound travel</span></div><div class="score pair"><strong>{pair(f['side'])} s</strong><span>side-street delay</span></div><div class="score pair cost"><strong>{pair(f['wb'])} s</strong><span>westbound travel, slightly worse</span></div></div>
<p>Means across the final rush-hour test, textbook → v4. Directional travel counts completed nonteleported corridor crossings and excludes waiting to enter. Side-street delay counts all requested side-origin trips.</p>
<figure><div class="card wide" tabindex="0">{paired_svg(f['groups'], PRIMARY, 'Delay per requested car (seconds)')}</div><figcaption>Each line pairs both plans on the same random seed.</figcaption></figure></section>

<section class="step"><h2>One rush hour, two plans</h2>
<video controls preload="metadata" poster="../reports/side_by_side_poster.png" src="../reports/side_by_side.mp4"></video>
<p>2024 model, final-test seed 53. Textbook versus frozen v4. The race includes waiting outside; captions show gains and costs in this one simulated seed.</p></section>

<section class="step"><h2>We asked VTA for real data</h2>
<p>VTA sent IDAX counts from {f['count_date']} and its model timing for De Anza and Stelling. Thank you to VTA, Kia Sharifi, P.E., and Larissa Sanderfer.</p>
<figure><div class="card wide" tabindex="0">{bars_svg(sorted(f['counts'].items()), 'De Anza: counted cars per 15 minutes')}</div><figcaption><a href="../data/processed/tmc_sources.csv">Count sources and dates</a> and <a href="../data/processed/vta_counts_2024.csv">transcribed VTA counts</a>.</figcaption></figure>
<p>The new data exposed {f['missing_turns']} counted turns where the old model sent no cars. We fixed the allocation and added U-turns. Better evidence helped us find and repair a real model problem.</p></section>

<section class="step"><h2>How it works</h2><figure><div class="card wide flow" tabindex="0">{system_svg(f)}</div></figure>
<p>Output: a candidate timing plan for an engineer to review.</p>
<figure><div class="card">{team_svg()}</div><figcaption>Green start times let the lights work as a team.</figcaption></figure></section>

<section class="step"><h2>The tuner learns from its own tries</h2>
<p>Pick a timing plan, run {f['search_seeds']} practice rush hours, score it, then use those results to choose the next try. This is Bayesian optimization: learning which settings worked so far.</p>
<figure><div class="card wide" tabindex="0">{tuner_loop_svg(f)}</div></figure>
<figure><div class="card wide" tabindex="0">{plan_space_svg(f)}</div></figure>
<p>The score counts every car that asked to drive, including waiting to enter. Each unfinished trip or stuck-car event adds a {f['miss_charge']:.0f} s charge. That charge is a scoring rule, not measured delay.</p></section>

<section class="step"><h2>Rules committed before the search</h2>
<p>We committed the rules on {f['prereg_date']}. The tuner tried {len(f['curve'])} plans on seeds {f['train_range']}, picked the finalist on {f['pick_range']}, then tested on {f['test_range']}. Settings froze before the final test.</p>
<figure><div class="card wide" tabindex="0">{curve_svg(f['curve'])}</div><figcaption>Best practice score so far. Fresh selection runs chose try {f['kept']}, which need not be the lowest point on this curve.</figcaption></figure>
<figure><div class="card tight wide" tabindex="0">{rules_svg(f)}</div></figure>
<p>v3 beats textbook too: {f['v3_delay']:.0f} s versus {f['delay'][0]:.0f} s per requested car. v4 lowers that to {f['delay'][1]:.0f} s. Its cycle is {f['cycle']:.0f} s, against {f['base_cycle']:.1f} s for textbook.</p></section>

<section class="step"><h2>VTA’s timing inputs in our model</h2>
<p>De Anza: {f['vta_cycles']['De Anza Blvd']:g} s. Stelling: {f['vta_cycles']['Stelling Rd']:g} s. These are VTA model inputs, not confirmed current city controller settings.</p>
<p>Our close copy jams in the model. This is a projection, not a claim about the street. We do not claim to beat VTA or the city.</p>
<p><a href="../docs/vta-timing.md">Source timing and projection choices</a></p></section>

<section class="step"><h2>What we would do next</h2><ul class="notes">{limits}</ul></section>

<details><summary>Saved results and test method</summary>
<p>One-sided paired Wilcoxon p={f['primary_p']:.9f} for v4 versus textbook, rush-hour holdout delay per requested car. This is the single confirmatory test. Other endpoints and comparisons are descriptive. Full PM overlaps the holdout.</p>
<p>The score adds completed time loss and insertion delay, plus {f['miss_charge']:.0f} s per unfinished trip and teleport event, then divides by all requested cars. Each holdout run requests {f['trips']:,} trips. The night demand is estimated.</p>
<p><a href="../reports/results_2024.csv">2024 results CSV</a> · <a href="../reports/eval_v4.json">Frozen evaluation</a> · <a href="../reports/optimize_v4.json">Search and selection</a> · <a href="../docs/PREREGISTRATION.md">Committed rules</a> · <a href="../reports/timing_v4_pm_peak.csv">Rush-hour timing</a></p>
</details>
<footer>Cupertino Signal Lab, a student hackathon project. Road data © OpenStreetMap contributors (ODbL). VTA supplied IDAX counts and Vistro timing inputs. Simulated in SUMO, tuned with Optuna. Mary retains older source data as disclosed above.</footer>
</main></html>'''

def dashboard(skip_video=False):
    os.nice(15)
    cfg = p.config()
    roads, signals, offsets, distance = geometry(cfg)
    rows = read_csv(p.ROOT/'reports/results_2024.csv')
    page = build_page(rows, roads, signals)
    deck = build_deck(rows, roads, signals)
    if not skip_video:
        render_media(roads, signals, offsets, distance)
    (p.ROOT/'dashboard').mkdir(exist_ok=True)
    (p.ROOT/'dashboard/index.html').write_text(page)
    (p.ROOT/'dashboard/deck.html').write_text(deck)
    print('Built dashboard/index.html and dashboard/deck.html' + ('' if skip_video else ' and media'))
