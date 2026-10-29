"""Offline judge demo from frozen evaluation CSVs and illustrative seed-0 FCD."""
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
LABELS = ('Textbook plan', 'Our plan')
CONTROLLERS = ('actuated', 'optuna_v3')
FCD_SEED = 33  # The recorded evening; one of the preregistered test rush hours.
VIDEO = (58500, 66600)  # 16:15 to 18:30, the whole evening the frames cover
STEP = 4  # simulated seconds per video frame; the saved frames are 2 s apart
FPS = 25  # STEP x FPS = 100x real time, so the evening runs in about 81 s


def read_csv(path):
    with open(path, newline='') as stream:
        return list(csv.DictReader(stream))


def cohort(rows, scenario='pm_peak', window='holdout', controllers=CONTROLLERS):
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


def typical_driver(tracks, endpoints, mainline, requested):
    """Median-nearest request-to-arrival saving; entry/arrival use 2 s FCD samples."""
    candidates = []
    for vid in sorted(tracks[0].keys() & tracks[1].keys()):
        if vid not in requested or not 61200 <= requested[vid] < 63000:
            continue
        pair = [group[vid] for group in tracks]
        if not all(endpoints[0] in [s[3] for s in samples]
                   and endpoints[1] in [s[3] for s in samples]
                   and [s[3] for s in samples].index(endpoints[0]) < [s[3] for s in samples].index(endpoints[1])
                   and samples[-1][0] < VIDEO[1]-2
                   and all(s[3] in mainline or s[3].startswith(':') for s in samples)
                   and all(b[0]-a[0] == 2 and np.hypot(b[1]-a[1], b[2]-a[2]) < 80
                           for a, b in zip(samples, samples[1:])) for samples in pair):
            continue
        durations = [samples[-1][0]+2-requested[vid] for samples in pair]
        candidates.append((vid, durations, durations[0]-durations[1]))
    if not candidates:
        raise ValueError('No comparable complete westbound trips in both FCDs')
    median = float(np.median([c[2] for c in candidates]))
    chosen = min(candidates, key=lambda c: (abs(c[2]-median), c[0]))
    return dict(id=chosen[0], requested=requested[chosen[0]], durations=chosen[1],
                median_saving=median, count=len(candidates))


def trip_text(seconds):
    seconds = round(seconds)
    return f'{seconds//60} min {seconds%60:02} s'


def timeline():
    """Per-second counters for both plans, straight from the evaluation's own timeline."""
    series = {c: {} for c in CONTROLLERS}
    for row in read_csv(p.ROOT/'reports/timeline_seed33.csv'):
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
    """On-screen lines for the silent video; each one is dropped unless the timeline backs it up."""
    textbook, ours = counters
    def shut(t): return textbook[t][1], ours[t][1]
    def ahead(t): return ours[t][2]-textbook[t][2]
    script = [(VIDEO[0], VIDEO[0]+600,
               'Both roads are full at rush hour. The difference: how many cars get through,\nand how long the line outside is.')]
    # First sustained backlog outside the textbook corridor while ours still lets everyone in.
    begins = next((t for t in range(*VIDEO) if all(textbook[s][1] >= 25 for s in range(t, t+300))), None)
    if begins and shut(begins)[0] > shut(begins)[1]:
        script.append((begins, begins+720, f'{clock_text(begins, False)} — the queue outside the textbook plan '
                                           f'starts growing: {shut(begins)[0]} cars shut out, {shut(begins)[1]} on ours.'))
    for t, window in ((60300, 900), (63000, 900)):  # 4:45 and 5:30, while the rush is building
        if shut(t)[0] > shut(t)[1]:
            script.append((t, t+window, f'{clock_text(t, False)} — {shut(t)[0]:,} cars shut out of the corridor '
                                        f'on the left, {shut(t)[1]:,} on ours.'))
    if ahead(64800) > 0:
        script.append((64800, 65700, f'{clock_text(64800, False)} — our plan has finished {ahead(64800):,} more trips.'))
    if ahead(66000) > 0 and shut(66000)[0] > shut(66000)[1]:
        script.append((66000, VIDEO[1], f'{clock_text(66000, False)} — {ahead(66000):,} more trips finished, '
                                       f'{shut(66000)[0]-shut(66000)[1]:,} fewer cars shut out.'))
    return script


def render_media(roads, signals, offsets, distance):
    cfg = p.config()
    westbound = boundaries(cfg)['wb']
    data = [fcd(p.ROOT/f'reports/fcd_{c}_pm_peak_seed{FCD_SEED}.xml.gz', offsets) for c in CONTROLLERS]
    requested = {v.get("id"): float(v.get("depart"))
                 for v in ET.parse(p.ROOT/"sim/routes_pm_peak.rou.xml").getroot().findall("vehicle")}
    race = typical_driver([d[2] for d in data], westbound, cfg['mainline_edges'], requested)
    print('Typical driver:', race, 'observed departures:', [d[2][race['id']][0][0] for d in data], flush=True)
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
    dots, readouts, bars, queues, rings, timers, driver_labels = [], [], [], [], [], [], []
    plan_colors = ('#b23b31', COLORS[1])
    max_blocked = max(v[1] for c in counters for v in c.values())
    all_points = np.concatenate([np.array(r) for r in roads])
    xmin, ymin = all_points.min(axis=0); xmax, ymax = all_points.max(axis=0)
    fig.text(.03, .962, 'Cupertino Signal Lab', fontsize=32, fontweight='bold', va='center')
    clock = fig.text(.97, .958, '', fontsize=42, family='monospace', fontweight='bold', ha='right', va='center')
    fig.text(.03, .920, 'One evening on Stevens Creek Boulevard, two traffic light plans',
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
        timers.append(fig.text(.03+len(readouts)*.495, .459, '', fontsize=21, fontweight='bold'))
        readouts.append(fig.text(.03+(len(readouts))*.495, .425, '', fontsize=17, color='#53687a'))
    caption = fig.text(.5, .367, '', fontsize=23, ha='center', va='center', color='#0b5f58')

    textbook, ours = counters
    minutes = [(t-VIDEO[0])/60 for t, _ in data[0][0]]
    queues_over_time = [[c[t][1] for t, _ in data[0][0]] for c in counters]
    chart_ax = fig.add_axes([.105, .095, .72, .19])
    chart_ax.set_facecolor('#f7f8fa')
    chart_ax.set(xlim=(0, span), ylim=(0, max_blocked*1.16),
                 xticks=ticks, xticklabels=[clock_text(VIDEO[0]+t*60, False) for t in ticks])
    chart_ax.set_ylabel('Cars', fontsize=17)
    chart_ax.set_title('Cars stuck waiting to get onto Stevens Creek',
                       loc='left', fontsize=21, fontweight='bold', pad=10)
    chart_ax.grid(axis='y', alpha=.18)
    chart_ax.tick_params(labelsize=16)
    for spine in ('top', 'right'):
        chart_ax.spines[spine].set_visible(False)
    growth = [chart_ax.plot([], [], color=color, lw=4)[0] for color in plan_colors]
    end_labels = [chart_ax.annotate('', (0, 0), xytext=(8, dy), textcoords='offset points',
                                   ha='left', va='center', fontsize=17, fontweight='bold', color=color,
                                   bbox=dict(facecolor='#f7f8fa', edgecolor='none', pad=2))
                  for color, dy in zip(plan_colors, (28, 6))]
    fig.text(.5, .048, f'Red = stopped, yellow = slow, green = moving   |   North up   |   {STEP*FPS}x; driver race slowed to 20x', ha='center', fontsize=16)
    fig.text(.5, .019, 'One of the 20 test rush hours. North to south scale expanded. Trip timers sampled every 2 s. Signal states not recorded. 2018 demand assumptions.', ha='center', fontsize=13, color='#53687a')

    script = caption_script(counters)
    race_start = race['requested']
    race_end = max(d[2][race['id']][-1][0]+2 for d in data)
    script.append((race_start, race_end,
                   f'Typical westbound trip: {trip_text(race["durations"][0])} vs {trip_text(race["durations"][1])}, including the wait outside.\nClock starts at the same request; selected nearest the median saving.'))
    script.append((race_end, race_end+600,
                   f'This driver saved {race["durations"][0]-race["durations"][1]:g} seconds from request to arrival.\n'
                   f'Median saving: {race["median_saving"]:g} seconds across {race["count"]} comparable westbound trips.'))
    writer = FFMpegWriter(fps=FPS, codec='libx264', extra_args=['-threads', '1', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    output = p.ROOT/'reports/side_by_side.mp4'
    with writer.saving(fig, str(output), dpi=100):
        card = fig.add_axes([0, 0, 1, 1], zorder=5, facecolor='#f7f8fa')
        card.set_xticks([]); card.set_yticks([])  # axis('off') would hide the opaque backdrop too
        for spine in card.spines.values():
            spine.set_visible(False)
        for y, line, size in ((.66, 'Cupertino Signal Lab', 70), (.54, 'A shorter line outside the same full road', 34),
                              (.44, f'Left: {LABELS[0]}.    Right: {LABELS[1]}.', 30),
                              (.34, f'{clock_text(VIDEO[0], False)} to {clock_text(VIDEO[1], False)}, sped up {STEP*FPS} times', 26)):
            card.text(.5, y, line, ha='center', fontsize=size, fontweight='bold' if size > 60 else 'normal',
                      color='#13242f' if size > 26 else '#53687a')
        for _ in range(3*FPS):  # a 3 s title card so the video explains itself without a narrator
            writer.grab_frame()
        card.remove()
        for index, (time, _) in enumerate(data[0][0]):
            if time-STEP < race_start <= time:
                # Hold the request moment so even a sub-frame insertion wait is visible.
                clock.set_text(clock_text(race_start))
                caption.set_text('Request snapshot (held for readability): both drivers asked to drive.\n'
                                 'The total clock includes waiting to get on, then driving.')
                for i, timer in enumerate(timers):
                    timer.set_text('Typical driver • waiting to get on • 0 min 00 s')
                    waiting, blocked, finished = counters[i][int(race_start)]
                    queues[i].set_text(f'Line outside: {blocked:,} cars')
                    bars[i].set_width(blocked)
                    readouts[i].set_text(f'{waiting:,} stopped on road   |   {finished:,} trips finished')
                    growth[i].set_data(minutes[:index]+[(race_start-VIDEO[0])/60],
                                       queues_over_time[i][:index]+[blocked])
                    end_labels[i].xy = ((race_start-VIDEO[0])/60, blocked)
                    end_labels[i].set_text(f'{LABELS[i]}: {blocked:,}')
                for _ in range(FPS):
                    writer.grab_frame()
                fig.savefig(p.ROOT/'reports/side_by_side_poster.png', dpi=100)
            clock.set_text(clock_text(time))
            caption.set_text(next((line for start, stop, line in script if start <= time < stop), ''))
            for i in range(2):
                other_time, cars = data[i][0][index]
                if other_time != time:
                    raise ValueError('FCD clocks differ')
                dots[i].set_offsets(cars[:, :2]); dots[i].set_array(cars[:, 2])
                waiting, blocked, finished = counters[i][time]
                queues[i].set_text(f'Line outside: {blocked:,} cars')
                bars[i].set_width(blocked)
                readouts[i].set_text(f'{waiting:,} stopped on road   |   {finished:,} trips finished')
                samples = data[i][2][race['id']]
                depart, arrive = samples[0][0], samples[-1][0]+2
                position = next((s for s in samples if s[0] == time), None)
                rings[i].set_data([position[1]] if position else [], [position[2]] if position else [])
                driver_labels[i].set_visible(position is not None)
                if position:
                    driver_labels[i].xy = (position[1], position[2])
                if time < race_start:
                    text = f'Typical driver • requests {clock_text(race_start)}'
                elif time < depart:
                    text = f'Typical driver • waiting to get on • {trip_text(time-race_start)}'
                elif time < arrive:
                    text = f'Typical driver • driving • {trip_text(time-race_start)} total'
                else:
                    text = f'Typical driver • arrived in {trip_text(arrive-race_start)} total'
                timers[i].set_text(text)
            for line, series, label, name in zip(growth, queues_over_time, end_labels, LABELS):
                line.set_data(minutes[:index+1], series[:index+1])
                label.xy = (minutes[index], series[index])
                label.set_text(f'{name}: {series[index]:,}')
                label.set_visible(index > 0)
            for _ in range(5 if race_start <= time <= race_end else 1):
                writer.grab_frame()
    plt.close(fig)
    if output.stat().st_size >= 50_000_000:
        raise ValueError('Video exceeds 50 MB')


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
    for y, reds, caption in ((78, (1, 3, 4), 'Lights on their own: cars pile up behind every red.'),
                             (228, (), 'Lights as a team: one green wave and the cars keep rolling.')):
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


def knobs(trials):
    """What the tuner may change: counted from the search's own record, ranged from its search space."""
    families = {}
    for column in trials[0]:
        if column.startswith('params_'):
            key = column[len('params_'):]
            families.setdefault(key.split('_')[0], []).append(key)
    rows = [(len(families[family]), name, detail(*knob_bounds(families[family][0])))
            for family, name, detail in KNOBS]
    if sum(count for count, _, _ in rows) != sum(map(len, families.values())):
        raise ValueError('Knob families do not cover the recorded search space')
    return rows


def tuner_loop_svg(f):
    """One turn of the tuning loop, and what 300 turns bought: try 0 against the plan we kept."""
    box, pitch = 345, 385
    parts = ['<defs><marker id="loop" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
             '<polygon points="0 0, 9 3.5, 0 7" fill="var(--road)"/></marker></defs>']
    for i, (title, first, second) in enumerate((('Pick a plan', '32 numbers', '5 lights'),
                                                ('Run it', '5 practice', 'rush hours'),
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
    low = min(min(v) for v in values)*.985
    high = max(max(v) for v in values)*1.004
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
    return svg(''.join(parts), 700, 70+len(values[0])*22,
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


PIPELINE_GROUPS = (('Build the street', 3), ('Find a better plan', 4))


def pipeline_steps(f):
    return [('The street', 'map to simulator'), ('The data', f'{f["measured"][0]["year"]} city counts'),
            ('The cars', f'{f["trips"]:,} trips'), ('Textbook plan', 'the one to beat'),
            ('Tuning', f'{len(f["curve"])} tries, one kept'), ('The rules', 'written in advance'),
            ('Fair test', f'{f["n_test"]} unseen hours')]


def prereg():
    """Date, side-street cap and stuck-car allowance come from the committed file, not from memory."""
    words = (p.ROOT/'docs/PREREGISTRATION.md').read_text()
    return (re.search(r'\d{4}-\d{2}-\d{2}', words).group(),
            int(re.search(r'at most (\d+)% above', words).group(1)),
            int(re.search(r'baseline \+ (\d+) teleports', words).group(1)))


def rules_svg(f):
    """The promises we wrote down and saved before the final test, in plain words."""
    rules = (('The one score that decides it',
              'Time lost per car, counting every car, even the ones that never got moving.'),
             ('A promise to the side streets',
              f'Side street drivers may not end up more than {f["cap"]}% worse off than today.'),
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
    """The honest limits, worded as the work that follows. Every one names a real shortcoming."""
    steps = [f'Only {f["close"]} of {len(f["checks"])} counted movements matched closely (GEH under 5); better counts come first.',
             f'Get real counts for {" and ".join(escape(n) for n in f["guessed"])}. Nobody ever counted those two '
             'side streets, so we estimated them.',
             'Take it outside the simulator: current counts from VTA, pedestrians and bikes in the model, and a '
             'supervised pilot before any real light changes.']
    for seed, before, after in f['cap_fail_seeds']:
        steps.insert(0, f'Work out what happened in rush hour {seed-min(SEEDS)+1}. In that one hour our plan left '
                        f'{after} cars so stuck the simulator had to lift them out, where the textbook plan left '
                        f'{before}, breaking the rule we set ourselves before the test.')
    return steps


def build_deck(rows, roads, signals):
    """Eleven slides for the live pitch, on the page's own look and the page's own numbers."""
    f = facts(rows)
    slides = [
        ('<h1>Cupertino Signal Lab</h1><p class="lead">Five traffic lights on Stevens Creek, retimed by a computer '
         'and tested on rush hours it had never seen.</p><p class="hint">Arrow keys to move. Press N for notes.</p>',
         'Hi, we are Cupertino Signal Lab. We took five real traffic lights near school and asked a computer to retime them.'),
        (f'<h2>Rush hour barely moves.</h2><div class="fill" style="--fw:1664px">{map_svg(roads, signals)}</div>'
         '<p class="under">Mary Avenue to De Anza Boulevard. Five signals in about two kilometres.</p>',
         'This is the stretch we studied. Five lights in a row, and at five thirty the eastbound line barely moves.'),
        (f'<h2>What if the five lights worked as a team?</h2><div class="fill" style="--fw:940px">{team_svg()}</div>',
         'Right now each light decides on its own. If they turn green in order, a car can roll the whole way without stopping.'),
        (f'<h2>How we built it</h2><div class="steps">'
         + ''.join(f'<div><small>Step {i+1}</small><strong>{title}</strong><span>{sub}</span></div>'
                   for i, (title, sub) in enumerate(pipeline_steps(f))) + '</div>',
         'We rebuilt the real street in a traffic simulator, filled it with cars from the city counts, built the plan an engineer would use, then let a computer search for a better one.'),
        (f'<h2>We checked our traffic against the real counts.</h2><div class="two" style="--cols:900px 1fr"><div class="fill">'
         f'{grid_svg(f["close"], len(f["checks"]))}</div><div>'
         f'<p>One square per real counted movement. We matched {f["close"]} of {len(f["checks"])}. '
         '</p>'
         f'<p>The counts are from {f["measured"][0]["year"]}, and {len(f["guessed"])} of the five intersections '
         'were never counted at all.</p></div></div>',
         'Before any result, the thing we would want a judge to push on. Our traffic has the right shape but it is not exact, and we say so on the page.'),
        (f'<h2>The tuner learns from its own tries.</h2>'
         f'<div class="fill" style="--fw:1664px">{tuner_loop_svg(f)}</div>'
         f'<p class="under">Nobody picked the winner by hand. Try 0 was the textbook plan.</p>',
         f'This is the loop. The computer sets the five lights, runs {f["search_seeds"]} whole practice rush hours '
         f'in the simulator, and gets back one score: the seconds an average car loses. Then the tuner looks at '
         f'every try so far, builds a picture of which settings scored well, and aims the next try at the promising '
         f'part, {len(f["curve"])} times. Where is the AI? It is not a neural network. It is machine learning '
         f'search, called Bayesian optimization: it learns from its own tries instead of guessing at random. '
         f'The textbook plan was try 0 at {f["try0"]:,.0f} seconds a car, and the plan we kept scored '
         f'{f["kept_score"]:,.0f}.'),
        (f'<h2>What it can change, and how we score it.</h2>'
         f'<div class="fill" style="--fw:1664px">{plan_space_svg(f)}</div>',
         f'The tuner only ever touches these {sum(c for c, _, _ in f["knobs"])} numbers: one cycle length shared by '
         f'all five lights, when each light starts its green, how long each phase of green runs, the shortest green '
         f'the main road may get, and how much quiet traffic ends a green early. It is scored on one number, the '
         f'seconds an average car loses, counting every car that asked to drive, including the ones that never got '
         f'in. And it may not win by hurting anybody: no direction more than {f["cap"]}% slower than today, and no '
         f'more cars left stuck. That threw out {f["thrown_out"]} of the {len(f["curve"])} tries.'),
        (f'<h2>{len(f["curve"])} plans tried, then a test it could not study for.</h2>'
         f'<div class="two" style="--cols:1020px 600px"><div class="fill">{curve_svg(f["curve"])}</div>'
         f'<div class="fill">{seeds_svg(((f["search_seeds"], "var(--road)", f"{f['search_seeds']} rush hours to practise on"), (f["pick_seeds"], "var(--road)", f"{f['pick_seeds']} more to pick the finalist"), (f["n_test"], "var(--accent)", f"{f['n_test']} brand new ones for the fair test")))}</div></div>'
         f'<p class="under">Before running that last test we wrote down what would count as a win, on {f["prereg_date"]}, and saved it.</p>',
         f'A tuning tool tried {len(f["curve"])} timing plans on {f["search_seeds"]} practice rush hours. The ten best were then run again on {f["pick_seeds"]} fresh ones, and the winner of that run off is the plan we kept, which is why it is not the very lowest point on this curve. Then, before the final test, we wrote down what would count as a win, so we could not pick a flattering number afterwards.'),
        ('<h2>The same evening, run twice.</h2><div class="fill video">'
         '<video controls playsinline preload="metadata" poster="../reports/side_by_side_poster.png">'
         '<source src="../reports/side_by_side.mp4" type="video/mp4"></video></div>'
         '<p class="under">Left: the textbook plan. Right: our plan. Same cars, same clock.</p>',
         'Here they are side by side, the whole evening sped up. Same cars, same clock. Watch the chart at the bottom: cars waiting outside, textbook in red and ours in teal. The typical-driver clock starts when the car asks to drive, including the wait to get on.'),
        (f'<h2>Every direction came out ahead.</h2><div class="scores">'
         f'<div class="score"><strong>{f["delay_cut"]:.0f}%</strong><span>less time lost per car</span></div>'
         f'<div class="score"><strong>{f["faster"]:.0f}%</strong><span>faster eastbound</span></div>'
         f'<div class="score"><strong>{f["wb_cut"]:.0f}%</strong><span>faster westbound</span></div>'
         f'<div class="score"><strong>{f["side_cut"]:.0f}%</strong><span>less time lost on the side streets</span></div>'
         f'<div class="score pair"><strong>{f["teleports"][0]} &rarr; {f["teleports"][1]}</strong><span>cars left badly stuck</span></div></div>'
         f'<p class="under">Across {f["n_test"]} rush hours the tuner had never seen, scored against rules we wrote down before the test.</p>',
         f'Our plan cut the time an average car loses by about {f["delay_cut"]:.0f} percent across {f["n_test"]} rush hours it had never seen, and it was better in {f["verdict"]}. Both directions of Stevens Creek got faster, and so did the side streets, which was the thing we were most worried about breaking.'),
        (f'<h2>What we would do next</h2><ul class="notes">'
         + ''.join(f'<li>{step}</li>' for step in next_steps(f))
         + '</ul><p class="under">Nothing here was tested on a real street. Road data from OpenStreetMap, counts from '
         'City of Cupertino traffic reports, simulated in SUMO. Thank you.</p>',
         f'Four honest limits, as next steps. One of the {f["n_test"]} test hours broke our own stuck-car rule and we '
         'still owe an explanation for it, two of the five side streets were never counted, and none of this has been '
         'tested on a real street. Thanks for listening.'),
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
.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:28px}}
.steps>div{{padding:28px;border:1.5px solid var(--line);border-radius:12px;background:var(--paper)}}
.steps small{{display:block;font-size:26px;color:var(--accent);font-weight:700}}
.steps strong{{display:block;font-size:36px;margin:12px 0}}
.steps span{{font-size:28px;color:var(--muted)}}
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
    """Every derived number the page and the deck quote, read once from the project's own files."""
    groups = cohort(rows)
    with open(p.ROOT/'sim/routes_pm_peak.rou.xml') as stream:
        trips = sum(1 for line in stream if '<vehicle ' in line)
    trials = read_csv(p.ROOT/'reports/optimize_v3_trials.csv')
    scores = {int(t['number']): float(t['value']) for t in trials}  # trial number, not row order
    search = json.loads((p.ROOT/'reports/optimize_v3.json').read_text())
    checks = read_csv(p.ROOT/'reports/demand_check.csv')
    sources = read_csv(p.ROOT/'data/processed/tmc_sources.csv')
    measured = [r for r in sources if r['source'] == 'measured']
    counts = {}  # 15-minute totals at the first measured intersection
    for row in read_csv(p.ROOT/'data/processed/tmc.csv'):
        if row['intersection'] == measured[0]['intersection']:
            counts[row['interval_start']] = counts.get(row['interval_start'], 0)+int(row['vehicles'])
    base_cycle, base_svg = offset_svg(p.ROOT/'sim/tls_actuated_pm_peak.add.xml')
    wins = sum(float(b[PRIMARY]) < float(a[PRIMARY]) for a, b in zip(*groups))
    delay, side, eb, wb, stuck = (stats(groups, k)[0] for k in
                                  (PRIMARY, 'side_all_requested_delay_s', 'mainline_travel_eb_s',
                                   'mainline_travel_wb_s', 'unfinished'))
    # The unfinished charge is a scoring convention; recover it from the two charge levels.
    row = groups[0][0]
    charge = ((float(row[PRIMARY])-float(row['all_requested_delay_0_s']))*float(row['requested'])
              / (float(row['unfinished'])+float(row['teleports'])))
    prereg_date, cap, slack = prereg()
    tests = read_csv(p.ROOT/'reports/wilcoxon.csv')
    def pvalue(metric, window='holdout', controller=CONTROLLERS[1]):
        matches = [r for r in tests if r['scenario'] == 'pm_peak' and r['window'] == window
                   and r['seed_group'] == 'v3_final' and r['metric'] == metric
                   and r['controller'] == controller]
        if len(matches) != 1 or int(matches[0]['n']) != len(groups[0]):
            raise ValueError(f'Missing paired test: {metric}')
        return float(matches[0]['p_value'])
    return {
        'groups': groups, 'cfg': p.config(), 'trips': trips, 'curve': best_so_far(trials),
        'thrown_out': sum(float(r['value']) >= 1e9 for r in trials if r['state'] == 'COMPLETE'),
        'search_seeds': len(search['seeds']), 'pick_seeds': len(search['selection_seeds']),
        'knobs': knobs(trials), 'try0': scores[0], 'kept': int(search['best']['trial']),
        'kept_score': scores[int(search['best']['trial'])],
        'search_minutes': search['wall_s']/60,
        'miss_charge': charge, 'prereg_date': prereg_date, 'cap': cap, 'slack': slack, 'pvalue': pvalue,
        'checks': checks, 'close': sum(float(r['geh']) < 5 for r in checks),
        'target': round(len(checks)*.85), 'measured': measured,
        'hourly': [r['intersection'] for r in sources if r['source'] != 'measured' and r['count_date']],
        'guessed': [r['intersection'] for r in sources if not r['count_date']],
        'counts': counts, 'base_cycle': base_cycle, 'base_svg': base_svg, 'n_test': len(groups[0]),
        'verdict': f'all {wins}' if wins == len(groups[0]) else f'{wins} of the {len(groups[0])}',
        'delay_cut': (1-delay[1]/delay[0])*100, 'side_cut': (1-side[1]/side[0])*100,
        'faster': (1-eb[1]/eb[0])*100, 'wb_cut': (1-wb[1]/wb[0])*100,
        'unstuck': stuck[0]-stuck[1], 'odds': round(1/pvalue(PRIMARY), -2),
        'cap_fail_seeds': [(int(b['seed']), int(a['teleports']), int(b['teleports']))
                           for a, b in zip(*groups) if int(b['teleports']) > int(a['teleports'])+slack],
        'cap_fails': sum(int(b['teleports']) > int(a['teleports'])+slack for a, b in zip(*groups)),
        'teleports': [sum(int(r['teleports']) for r in group) for group in groups],
    }


def build_page(rows, roads, signals):
    f = facts(rows)
    groups = f['groups']
    def means(key): return stats(groups, key)[0]
    def pair(key): return ' → '.join(f'{v:,.1f}' for v in means(key))
    def pv(key): return f'{f["pvalue"](key):.6f}'
    v2 = cohort(rows, controllers=('actuated', 'optuna'))
    delay, side = means(PRIMARY), means('side_all_requested_delay_s')
    verdict_line = (f'Across {f["n_test"]} brand new rush hours our plan cut the time an average car loses by '
                    f'{f["delay_cut"]:.1f}%, and it beat the textbook plan in {f["verdict"]}.')
    headline = (f'On the {f["n_test"]} preregistered test seeds, the optimized plan cuts rush-hour holdout '
                f'all-requested delay from {delay[0]:,.2f} to {delay[1]:,.2f} s per requested vehicle '
                f'({f["delay_cut"]:.1f}%, one-sided paired Wilcoxon p={pv(PRIMARY)}), improves the side-origin '
                f'constraint to ratio {side[1]/side[0]:.3f} and cuts both directions of corridor travel, but the '
                f'training teleport cap fails on {f["cap_fails"]} of {f["n_test"]} seeds, so no overall feasible '
                'winner is established under the preregistered rule.')
    tables=[]
    for scenario in ('pm_peak','night'):
        timing=read_csv(p.ROOT/f'reports/timing_v3_{scenario}.csv')
        names={s['sumo_tls_id']:s['name'] for s in p.config()['signals']}
        body = ''
        seen = set()
        for r in timing:
            signal = r['sumo_tls_id']
            first = signal not in seen
            seen.add(signal)
            values = (names[signal] if first else '', f"{float(r['cycle_s']):.1f}" if first else '',
                      f"{float(r['offset_s']):.1f}" if first else '', r['phase'],
                      f"{float(r['min_green_s']):.1f}", f"{float(r['max_green_s']):.1f}",
                      f"{float(r['passage_s']):.1f}")
            body += '<tr>'+''.join(f'<td>{escape(v)}</td>' for v in values)+'</tr>'
        tables.append(f'<details{" open" if scenario == "pm_peak" else ""}><summary>{"Rush-hour" if scenario=="pm_peak" else "Night"} optimized timing · phase rows</summary><div class="scroll"><table><thead><tr><th>Signal</th><th>Cycle (s)</th><th>Offset (s)</th><th>Phase</th><th>Min green (s)</th><th>Max green (s)</th><th>Passage (s)</th></tr></thead><tbody>{body}</tbody></table></div></details>')
    trips, curve = f['trips'], f['curve']
    miss_charge, checks, close = f['miss_charge'], f['checks'], f['close']
    measured, hourly, guessed, counts = f['measured'], f['hourly'], f['guessed'], f['counts']
    base_cycle, base_svg, verdict = f['base_cycle'], f['base_svg'], f['verdict']
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
.wide>svg,.wide>img{{min-width:560px}}
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
@media(max-width:720px){{main{{padding:0 18px 52px}}.step{{padding:52px 0}}.scores{{grid-template-columns:1fr;gap:26px}}.card{{padding:16px}}}}
</style><main>
<p class="masthead">Cupertino Signal Lab<span>AI Club hackathon project</span></p>
<header><h1>Rush hour on Stevens Creek.</h1><p class="lead">Five traffic lights in a row, and a line of cars that barely moves.</p>
<figure><div class="card tight wide" tabindex="0">{map_svg(roads, signals)}</div><figcaption>The stretch we studied, drawn from the real street map. Eastbound runs from Mary Avenue to De Anza Boulevard. North is up, and the north to south distance is stretched so the names fit.</figcaption></figure></header>

<section class="step"><h2>What if the five lights worked as a team?</h2>
<p>Today each light decides on its own. If they turn green in order, a car can roll from one end to the other without stopping. That is the whole idea we tested.</p>
<figure><div class="card">{team_svg()}</div></figure></section>

<section class="step"><h2>How we built it</h2>
<p>Three steps to build a street we could experiment on, then four to find a better plan and check it honestly.</p>
<figure><div class="card wide flow" tabindex="0">{pipeline_svg(pipeline_steps(f), PIPELINE_GROUPS)}</div></figure></section>

<section class="step"><div class="split"><div><span class="n">1</span><h2>We rebuilt the real street inside a traffic simulator.</h2>
<p>Every road and every turning path comes from the public street map. All five lights line up with the real ones.</p></div>
<figure><div class="card tight wide" tabindex="0"><img src="../reports/network.png" alt="Close view of one intersection showing every road and turning path the simulated cars can use" loading="lazy"></div><figcaption>Inside one of the five intersections. Every short curve is a turn a simulated car can take.</figcaption></figure></div></section>

<section class="step"><span class="n">2</span><h2>The car counts come from City of Cupertino traffic reports.</h2>
<p>People stood at the intersections and wrote down every turn, every 15 minutes. The newest public counts we could find are from {measured[0]['year']}, so that is the traffic we model. It is not today's traffic.</p>
<figure><div class="card wide" tabindex="0">{bars_svg(sorted(counts.items()), 'cars through ' + measured[0]['intersection'] + ' per 15 minutes')}</div><figcaption>Counted at {escape(measured[0]['intersection'])} and Stevens Creek on {measured[0]['count_date']}. The rush builds toward 17:15 and stays heavy for an hour.</figcaption></figure>
<ul class="chips"><li>Counted every 15 minutes: {', '.join(escape(r['intersection']) for r in measured)}</li><li>Counted by the hour: {', '.join(escape(n) for n in hourly)}</li><li>No counts, estimated: {', '.join(escape(n) for n in guessed)}</li></ul></section>

<section class="step"><div class="split"><div><span class="n">3</span><h2>Those counts become {trips:,} car trips.</h2>
<p>Every counted turn becomes cars with a real route through the corridor, released across the two hour rush. Then we checked our traffic against the real counts.</p></div>
<figure><div class="card">{grid_svg(close, len(checks))}</div><figcaption>One square per counted movement; filled squares matched closely.</figcaption></figure></div></section>

<section class="step"><span class="n">4</span><h2>First we built the plan an engineer would use.</h2>
<p>A standard textbook formula gives all five lights one shared {base_cycle:.0f} second cycle and starts each main green at a different moment. That plan is what we have to beat. It is not Cupertino's current timing.</p>
<figure><div class="card wide" tabindex="0">{base_svg}</div><figcaption>Each bar is the main road's green time at that light through one cycle. Going east, each green starts later than the one before, and the last one wraps into the next cycle.</figcaption></figure></section>

<section class="step"><span class="n">5</span><h2>The computer tried {len(curve)} timing plans and kept the best.</h2>
<p>One try goes like this: pick a timing plan, run {f['search_seeds']} practice rush hours with it in the simulator, score the result, then let the tuner choose what to try next. It is not a brain and it is not guessing at random. It builds a picture of which settings scored well so far and aims the next try at the promising part, which is a kind of machine learning called Bayesian optimization. Try 0 was the textbook plan and scored {f['try0']:,.0f} seconds lost per car; {len(curve)} tries later we kept try {f['kept']}, at {f['kept_score']:,.0f}. Our first search sped up eastbound but left westbound drivers worse off, so we gave the tuner stricter rules and searched again.</p>
<figure><div class="card wide" tabindex="0">{curve_svg(curve)}</div><figcaption>The best score so far across {len(curve)} tries. Lower is better: the score adds up the time every car loses. Most of the gain arrives early, then the tool fine tunes. The lowest point here is not the plan we kept: the ten best were run again on {f['pick_seeds']} fresh rush hours, and try {f['kept']} won that run off.</figcaption></figure>
<p>It may change {sum(c for c, _, _ in f['knobs'])} numbers, and nothing else:</p>
<ul class="chips">{''.join(f'<li>{count} &middot; {escape(name.lower())}, {escape(detail)}</li>' for count, name, detail in f['knobs'])}</ul>
<p>The score is one number: the seconds an average car loses, counting every car that asked to drive. That is what stops a plan winning by holding cars out of the corridor, because every trip that never finished was charged {miss_charge/60:.0f} minutes. On top of that, no direction of Stevens Creek and no side street may come out more than {f['cap']}% slower than the textbook plan, and no plan may leave more than {f['slack']} extra cars stuck. Breaking any of those threw a try out on the spot, which is what happened to {f['thrown_out']} of the {len(curve)} tries.</p></section>

<section class="step"><span class="n">6</span><h2>We wrote the rules down before the test.</h2>
<p>It is easy to run a test, look at twenty numbers and announce whichever one looks best. So on {f['prereg_date']} we wrote down what would count as a win, saved it in the project's history, and only then ran the final test. Everything below is scored against this, including the one rule we broke.</p>
<figure><div class="card tight wide" tabindex="0">{rules_svg(f)}</div></figure></section>

<section class="step"><div class="split"><div><span class="n">7</span><h2>Then we tested both plans on {f['n_test']} rush hours the tuner never saw.</h2>
<p>The computer searched on {f['search_seeds']} practice rush hours and used {f['pick_seeds']} more to choose between its best plans. The final {f['n_test']} were kept out of all of that: same road, same demand, new randomness. Our plan could not win by memorising its practice runs.</p></div>
<figure><div class="card">{seeds_svg(((f['search_seeds'], 'var(--road)', f'{f["search_seeds"]} rush hours to practise on'), (f['pick_seeds'], 'var(--road)', f'{f["pick_seeds"]} more to pick the finalist'), (f['n_test'], 'var(--accent)', f'{f["n_test"]} brand new ones for the fair test')))}</div></figure></div></section>

<section class="step"><h2>Watch the same evening twice.</h2>
<figure><div class="card tight"><video controls playsinline preload="metadata" poster="../reports/side_by_side_poster.png" aria-label="Side by side traffic simulation of the textbook plan and our plan"><source src="../reports/side_by_side.mp4" type="video/mp4">Open <a href="../reports/side_by_side.mp4">the video</a>.</video></div></figure>
<ul class="notes"><li>Left is the textbook plan. Right is our plan. Same cars, same clock.</li><li>Red dots are cars that have stopped. Green dots are moving.</li><li>The chart at the bottom shows cars waiting outside: textbook in red, ours in teal. The race clock includes the wait to get on.</li></ul>
<small>{clock_text(VIDEO[0], False)} to {clock_text(VIDEO[1], False)} at {STEP*FPS}x speed, from one of the {f['n_test']} test rush hours. One run shows what the plans look like; it does not prove anything on its own, and the numbers below come from all {f['n_test']}. The north to south scale is stretched and signal states were not recorded.</small></section>

<section class="step"><h2>The result</h2>
<p>{verdict_line}</p>
<div class="scores"><div class="score"><strong>{f['delay_cut']:.1f}%</strong><span>less time lost per car, counting every car</span></div><div class="score"><strong>{f['faster']:.1f}%</strong><span>faster eastbound through the corridor</span></div><div class="score"><strong>{f['wb_cut']:.1f}%</strong><span>faster westbound through the corridor</span></div><div class="score"><strong>{f['side_cut']:.1f}%</strong><span>less time lost by side street cars</span></div><div class="score pair"><strong>{f['teleports'][0]} → {f['teleports'][1]}</strong><span>cars that got so stuck the simulator had to lift them out</span></div></div>
<p>The first number is the one we promised to judge on. If our plan were really no better, a gap this one sided would turn up in about one test out of {f['odds']:,.0f}. The side streets improved too, which was the thing we were most afraid of breaking.</p>
<figure><div class="card wide" tabindex="0">{paired_svg(groups, PRIMARY, 'Time lost per car, counting every car (seconds)')}</div><figcaption>Each line is one of the {f['n_test']} test rush hours, with both plans run on the same randomness. Our plan loses less time in {verdict}.</figcaption></figure></section>

<section class="step"><h2>What we would do next</h2>
<ul class="notes">{limits}</ul></section>

<details><summary>For the curious: full numbers, tests and method</summary>
<p>{headline}</p>
<p class="muted">The three counters in the video come from the simulator's own per-second summary for seed {FCD_SEED} (<a href="../reports/timeline_seed33.csv">CSV</a>): waiting on the road counts halting vehicles, under 0.1 m/s; shut out of the corridor counts vehicles whose scheduled departure has passed with no insertion yet; trips finished counts arrivals so far. The chart compares the number waiting outside under each plan, textbook in red and ours in teal, on the same scale as the outside-line bars. The ring follows one westbound driver selected at the median saving among paired through trips requested between 5:00 and 5:30 PM. Timers start at scheduled departure in the demand file and include waiting to get on, then driving, until arrival estimated from two-second samples.</p>
<p class="muted">Preregistered on {f['prereg_date']} in <a href="../docs/PREREGISTRATION.md">docs/PREREGISTRATION.md</a>, before the optimizer or the test ran: the primary endpoint, the {f['cap']}% side-origin cap, the baseline + {f['slack']} teleport rule, the untouched seeds {min(SEEDS)} to {max(SEEDS)}, and a promise to report whichever way it went. The confirmatory comparison is the single test above; everything else here is descriptive and unadjusted.</p>
<p class="counts">Requested: <strong>{pair('requested')}</strong><br>Completed: <strong>{pair('completed')}</strong><br>Unfinished: <strong>{pair('unfinished')}</strong> (still running or never inserted).</p>
<div class="card wide" tabindex="0">{chart(groups,[('all_requested_delay_0_s','All-requested delay, no unfinished or teleport charge'),(PRIMARY,f'All-requested delay, {miss_charge:.0f} s charge (preregistered primary)'),('all_requested_delay_1800_s','All-requested delay, 1800 s charge')],'Preregistered primary and its sensitivity')}<small>Lower is better. Zero-charge p={pv('all_requested_delay_0_s')}; primary p={pv(PRIMARY)}; 1800 s p={pv('all_requested_delay_1800_s')}. Score = [completed time loss + completed insertion delay + charge x (unfinished + teleport events)] / requested vehicles. The charge is a scoring convention, not measured delay; the direction holds at all three levels.</small></div>
<div class="card wide" tabindex="0">{chart(groups,[('side_all_requested_delay_s','Side-origin all-requested delay')],'Side-origin constraint')}{chart(groups,[('unfinished','Unfinished vehicles')],'Unfinished vehicles',unit='')}{chart(groups,[('teleports','Teleport events')],'Teleport events',unit='')}<small>Side-origin p={pv('side_all_requested_delay_s')} at paired-mean ratio {side[1]/side[0]:.3f}, inside the {f['cap']}% cap. Unfinished p={pv('unfinished')}. Teleports p={pv('teleports')} tested for improvement: they fall overall, {f['teleports'][0]} to {f['teleports'][1]} events over {f['n_test']} seeds, but still exceed baseline + {f['slack']} on {f['cap_fails']} of {f['n_test']} seeds ({', '.join(f'seed {s}: {a} to {b}' for s, a, b in f['cap_fail_seeds'])}). That is the preregistered feasibility rule failing on the final test, so no feasible winner is declared.</small></div>
<div class="card wide" tabindex="0">{chart(groups,[('mainline_travel_eb_s','Eastbound corridor travel'),('mainline_travel_wb_s','Westbound corridor travel')],'Corridor travel')}<small>EB p={pv('mainline_travel_eb_s')}; WB p={pv('mainline_travel_wb_s')}; both directions improve, EB {f['faster']:.1f}% and WB {f['wb_cut']:.1f}%, and both are descriptive secondary endpoints rather than the confirmatory test. Directional travel excludes pre-insertion delay and teleported vehicles.</small></div>
<div class="card wide" tabindex="0">{chart(groups,[('mean_time_loss_s','Completed-only time loss'),('side_time_loss_s','Completed-only side-origin time loss'),('mean_depart_delay_s','Completed-only insertion delay')],'Completed-only outcomes')}<small>Completed-only loss p={pv('mean_time_loss_s')} for improvement: that original outcome worsens, because the optimized plan completes trips the textbook plan never starts. Side-origin completed-only loss has p={pv('side_time_loss_s')} for improvement. These omit unfinished demand and carry survivor bias, which is why the preregistered primary counts every requested vehicle.</small></div>
<small>Bars show mean plus or minus one sample standard deviation across seeds {min(SEEDS)} to {max(SEEDS)}, not confidence intervals and not real-world uncertainty. P-values are paired one-sided Wilcoxon tests, optimized below textbook. Full PM and holdout windows overlap and are not independent replications. Fitted-hour demand is replayed, so these seeds test randomness and later operating conditions, not unseen measured demand.</small>
<p class="muted">Earlier try, kept for the record: the previous plan was frozen before this search and tested on the same {f['n_test']} seeds. It scored the primary endpoint lower still, {stats(v2, PRIMARY)[0][1]:,.2f} s, which is {(1-stats(v2, PRIMARY)[0][1]/delay[0])*100:.1f}% below textbook (p={f['pvalue'](PRIMARY, controller='optuna'):.6f}), but it left {sum(int(r['teleports']) for r in v2[1])} stuck cars against the textbook plan's {f['teleports'][0]} and broke the baseline + {f['slack']} teleport rule on {sum(int(b['teleports']) > int(a['teleports'])+f['slack'] for a, b in zip(*v2))} of {f['n_test']} seeds, and on its own earlier test cohort it had left westbound travel worse than textbook. The plan on this page is the third search, which added per-direction travel caps and a per-signal minimum mainline green.</p>
<p class="muted">Night is estimated demand and shows no supported gain: all-requested delay {' to '.join(f'{v:.2f}' for v in stats(cohort(rows,'night','full'),PRIMARY)[0])} s.</p>
<figure><img src="../reports/time_space.png" alt="Eastbound car trajectories for the textbook and optimized plans" loading="lazy"><figcaption>One path per car while it is on the eastbound corridor, across the busiest quarter hour. Rising lines mean movement, flat lines mean waiting. Same single test rush hour (seed {FCD_SEED}) as the video, not aggregate evidence.</figcaption></figure>
<p class="muted">Data and limits in full: public counts are from {measured[0]['year']}. {' and '.join(escape(r['intersection']) for r in measured)} have measured quarter-hour counts; {', '.join(escape(n) for n in guessed)} and {', '.join(escape(n) for n in hourly)} profiles are estimated, with {', '.join(escape(n) for n in hourly)} built from hourly observations. This is not a picture of current traffic. Mary's mapped layout omits movements totaling 775 vehicles per hour.</p>
<p class="muted">Teleports have not gone away: holdout totals {f['teleports'][0]} to {f['teleports'][1]} across {f['n_test']} seeds; full PM totals {sum(int(r['teleports']) for r in cohort(rows,window='full')[0])} to {sum(int(r['teleports']) for r in cohort(rows,window='full')[1])}. SUMO can relocate stuck cars after 300 s, which distorts congestion. Completing more trips does not prove more cars entered the road. The simulated counts matched the measured ones on {close} of {len(checks)} movement intervals, below the {round(len(checks)*.85)} an engineer would expect.</p>
<p class="muted">No field testing was done. An engineer would need current counts, the actual timing sheets and a supervised pilot before considering any real change. The timing below is a demo proposal; phase order and clearance rules are preserved and nothing is sent to city lights.</p>
{''.join(tables)}
<p class="muted"><a href="../reports/results.csv">All results (CSV)</a> · <a href="../reports/wilcoxon.csv">Paired tests (CSV)</a> · <a href="../data/processed/tmc_sources.csv">Count sources (CSV)</a></p>
</details>
<footer><strong>Cupertino Signal Lab</strong>, a student hackathon project. Road data from OpenStreetMap contributors (ODbL). Counts from City of Cupertino Vallco and Westport traffic reports. Simulation in SUMO, tuning with Optuna, built with Python, Matplotlib and ffmpeg.</footer>
</main></html>'''

def dashboard():
    os.nice(15)
    cfg = p.config()
    roads, signals, offsets, distance = geometry(cfg)
    rows = read_csv(p.ROOT/'reports/results.csv')
    page = build_page(rows, roads, signals)
    deck = build_deck(rows, roads, signals)
    render_media(roads, signals, offsets, distance)
    (p.ROOT/'dashboard').mkdir(exist_ok=True)
    (p.ROOT/'dashboard/index.html').write_text(page)
    (p.ROOT/'dashboard/deck.html').write_text(deck)
    print('Built dashboard/index.html, dashboard/deck.html, side_by_side.mp4, side_by_side_poster.png, time_space.png')
