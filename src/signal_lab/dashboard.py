"""Offline judge demo from frozen evaluation CSVs and illustrative seed-0 FCD."""
import ast
import csv
import gzip
from html import escape
import os
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from matplotlib.collections import LineCollection
import numpy as np
import sumolib
from scipy.stats import wilcoxon

from . import pipeline as p
from .evaluate import boundaries, command, CONTROLLERS

COLORS = ('#52657b', '#087f78')
LABELS = ('Textbook plan', 'Optimized plan')


def read_csv(path):
    with open(path, newline='') as stream:
        return list(csv.DictReader(stream))


def cohort(rows, scenario='pm_peak', window='holdout'):
    selected = [[r for r in rows if r['controller'] == c and r['scenario'] == scenario
                 and r['window'] == window and r['seed_group'] == 'out_of_sample'] for c in CONTROLLERS]
    for group in selected:
        if sorted(int(r['seed']) for r in group) != list(range(3, 13)):
            raise ValueError(f'Expected exactly seeds 3–12: {scenario}/{window}')
        group.sort(key=lambda r: int(r['seed']))
    return selected


def stats(groups, metric):
    values = [np.array([float(r[metric]) for r in group]) for group in groups]
    return np.array([v.mean() for v in values]), np.array([v.std(ddof=1) for v in values])


def fcd(path):
    """Keep compact arrays; release each parsed timestep rather than retaining XML."""
    frames, tracks = [], {}
    with gzip.open(path, 'rb') as stream:
        parser = ET.iterparse(stream, events=('start', 'end'))
        _, root = next(parser)
        for event, element in parser:
            if event == 'end' and element.tag == 'timestep':
                time = float(element.get('time'))
                cars = list(element)
                frames.append((time, np.array([[float(v.get(k)) for k in ('x', 'y', 'speed')] for v in cars]).reshape(-1, 3)))
                for v in cars:
                    tracks.setdefault(v.get('id'), []).append((time, v.get('lane').rsplit('_', 1)[0], float(v.get('pos'))))
                root.clear()
    times = [t for t, _ in frames]
    if len(times) != 900 or times != list(range(63000, 63900)):
        raise ValueError('FCD must cover 17:30–17:45 at one-second intervals')
    return frames, tracks


def traffic_counts(time, cars, departures, inserted, arrivals):
    """Due but never inserted is distinct from stopped on-road traffic."""
    return (int(np.count_nonzero(cars[:, 2] < .1)),
            sum(depart <= time and inserted.get(vid, float('inf')) > time
                for vid, depart in departures.items()),
            sum(arrival <= time for arrival in arrivals))


def counter_history(data):
    departures = {v.get('id'): float(v.get('depart')) for v in
                  ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot().findall('vehicle')}
    histories = []
    for controller, (frames, tracks) in zip(CONTROLLERS, data):
        # The saved FCD starts at 17:30; replay the frozen seed to recover earlier trips.
        with tempfile.TemporaryDirectory() as folder:
            trips = Path(folder)/'trips.xml'
            p.run([*command('pm_peak', controller, 0, p.config()), '-e', 63900,
                   '--tripinfo-output', trips, '--tripinfo-output.write-unfinished', 'true'])
            records = ET.parse(trips).getroot().findall('tripinfo')
        inserted = {v.get('id'): float(v.get('depart')) for v in records if float(v.get('depart')) >= 0}
        arrivals = [float(v.get('arrival')) for v in records if float(v.get('arrival')) >= 0]
        for vid, track in tracks.items():
            first = track[0][0]
            if inserted[vid] >= 63000:
                assert inserted[vid] == first, (controller, vid, inserted[vid], first)
            else:
                assert inserted[vid] <= first
            inserted[vid] = min(first, inserted[vid])
        histories.append([traffic_counts(t, cars, departures, inserted, arrivals) for t, cars in frames])
    with open(p.ROOT/'reports/video_counts.csv', 'w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['controller', 'time_s', 'waiting_on_road', 'blocked_from_entering', 'trips_finished'])
        for controller, (frames, _), history in zip(CONTROLLERS, data, histories):
            writer.writerows((controller, int(t), *counts) for (t, _), counts in zip(frames, history))
    return histories


def segments(track, offsets):
    """Break paths across missing samples/other roads; never join a teleport gap."""
    lines = []
    previous = None
    for time, edge, pos in track:
        point = ((time-63000)/60, offsets[edge]+pos) if edge in offsets else None
        if point is not None and previous is not None and time-previous[0] == 1:
            # A large position jump cannot represent one second of road travel.
            if 0 <= point[1]-previous[1][1] < 40:
                lines.append((previous[1], point))
        previous = (time, point) if point is not None else None
    return lines


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


def caption_script(signals, data, histories):
    """On-screen lines for the silent video; each one is dropped unless the frames back it up."""
    name, centre = next(s for s in signals if s[0].startswith('De Anza'))
    stopped = [[int(np.count_nonzero((cars[:, 2] < .1) & (np.hypot(*(cars[:, :2]-centre).T) < 150)))
                for _, cars in frames] for frames, _ in data]
    script = [(0, 170, 'Same cars, same clock. Left runs the textbook plan, right runs the tuned plan.')]
    peak = max(range(180, 420), key=lambda i: stopped[0][i]-stopped[1][i])
    if stopped[0][peak] > stopped[1][peak]:
        short = name.replace(' Blvd', '')
        script.append((200, 440, f'Cars piling up at {short}: {stopped[0][peak]} stopped on the left, {stopped[1][peak]} on the right.'))
    script.append((520, 720, 'The two lines below are trips finished. The space between them is the whole result.'))
    lead = [b[2]-a[2] for a, b in zip(*histories)]
    if min(lead) > 0:
        script.append((740, 900, f'The tuned plan runs about {round(sum(lead)/len(lead), -1):,.0f} trips ahead the whole time.'))
    return script


def render_media(roads, signals, offsets, distance):
    data = [fcd(p.ROOT/f'reports/fcd_{c}_pm_peak_seed0.xml.gz') for c in CONTROLLERS]
    histories = counter_history(data)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True, layout='constrained')
    for ax, (_, tracks), label, color in zip(axes, data, LABELS, COLORS):
        lines = [line for track in tracks.values() for line in segments(track, offsets)]
        ax.add_collection(LineCollection(lines, colors=color, linewidths=.4, alpha=.5))
        ax.set(xlim=(0, 15), ylim=(0, distance), title=label, xlabel='Minutes after 17:30')
        ax.grid(alpha=.15)
    axes[0].set_ylabel('Eastbound distance from corridor entry (m)')
    fig.suptitle('Stevens Creek • eastbound trajectories • illustrative seed 0')
    fig.savefig(p.ROOT/'reports/time_space.png', dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.add_collection(LineCollection(roads, colors='#9fb0bd', linewidths=1.3))
    for name, (x, y) in signals:
        ax.plot(x, y, 'o', color='#0b7d73', ms=8, zorder=3)
        ax.annotate(name.replace(' Blvd', '').replace(' Rd', ''), (x, y), xytext=(0, 12),
                    textcoords='offset points', ha='center', fontsize=11, color='#13242f')
    ax.autoscale_view(); ax.set_aspect('equal'); ax.axis('off')
    fig.savefig(p.ROOT/'reports/network.png', dpi=180, facecolor='white', bbox_inches='tight', pad_inches=.08)
    plt.close(fig)

    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor('#f7f8fa')
    axes = [fig.add_axes([.03+i*.495, .49, .455, .345]) for i in range(2)]
    dots, counters = [], []
    all_points = np.concatenate([np.array(r) for r in roads])
    xmin, ymin = all_points.min(axis=0); xmax, ymax = all_points.max(axis=0)
    fig.text(.03, .957, 'Cupertino Signal Lab', fontsize=30, fontweight='bold', va='center')
    clock = fig.text(.97, .951, '', fontsize=32, family='monospace', ha='right', va='center')
    fig.text(.03, .912, 'Stevens Creek Boulevard, one rush hour, two traffic light plans',
             fontsize=18, color='#53687a', va='center')
    for ax, label in zip(axes, LABELS):
        ax.set_facecolor('#f7f8fa')
        ax.add_collection(LineCollection(roads, colors='#c3ccd4', linewidths=4))
        for i, (name, (x, y)) in enumerate(signals):
            ax.plot(x, y, 'o', color='#263d50', ms=8)
            ax.annotate(name.replace(' Blvd', '').replace(' Rd', ''), (x, y), xytext=(0, 26 if i%2 else -30), textcoords='offset points', ha='center', fontsize=16)
        ax.set(xlim=(xmin-30, xmax+30), ylim=(ymin-30, ymax+30), aspect='auto')
        ax.axis('off')
        ax.set_title(label, fontsize=26, pad=16)
        dots.append(ax.scatter([], [], c=[], s=24, cmap='RdYlGn', vmin=0, vmax=16, zorder=3))
        counters.append(ax.text(.5, -.06, '', transform=ax.transAxes, ha='center', va='top', fontsize=20, linespacing=1.4))
    caption = fig.text(.5, .340, '', fontsize=25, ha='center', va='center', color='#0b5f58')

    minutes = [(t-63000)/60 for t, _ in data[0][0]]
    totals = [[h[2] for h in history] for history in histories]
    # The lead opens during warmup, so a zero-based axis would hide it; start just under the data.
    chart_ax = fig.add_axes([.10, .115, .82, .175])
    chart_ax.set_facecolor('#f7f8fa')
    chart_ax.set(xlim=(0, 15), ylim=(min(t[0] for t in totals)-200, max(t[-1] for t in totals)+200),
                 xlabel='Minutes after 17:30', ylabel='Trips finished\n(running total)')
    chart_ax.grid(alpha=.18)
    for spine in ('top', 'right'):
        chart_ax.spines[spine].set_visible(False)
    growth = [chart_ax.plot([], [], color=c, lw=3.5, label=l)[0] for c, l in zip(COLORS, LABELS)]
    chart_ax.legend(loc='lower right', fontsize=15, frameon=False)
    fig.text(.5, .046, 'Red = stopped, yellow = slow, green = moving   |   North is up   |   8x speed, same cars and same clock on both sides', ha='center', fontsize=15)
    fig.text(.5, .017, 'Illustration only. Counters include warmup trips. North to south scale expanded. Signal states not recorded. 2018 demand assumptions.', ha='center', fontsize=12, color='#53687a')

    script = caption_script(signals, data, histories)
    # One frame per simulated second at 8 fps gives 112.5 s, exactly 8x.
    writer = FFMpegWriter(fps=8, codec='libx264', extra_args=['-threads', '1', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    output = p.ROOT/'reports/side_by_side.mp4'
    with writer.saving(fig, str(output), dpi=100):
        card = fig.add_axes([0, 0, 1, 1], zorder=5, facecolor='#f7f8fa')
        card.set_xticks([]); card.set_yticks([])  # axis('off') would hide the opaque backdrop too
        for spine in card.spines.values():
            spine.set_visible(False)
        for y, line, size in ((.66, 'Cupertino Signal Lab', 70), (.54, 'The same Stevens Creek rush hour, run twice', 34),
                              (.44, f'Left: {LABELS[0]}.    Right: {LABELS[1]}.', 30),
                              (.34, 'Watch the counters, then watch the line at the bottom', 26)):
            card.text(.5, y, line, ha='center', fontsize=size, fontweight='bold' if size > 60 else 'normal',
                      color='#13242f' if size > 26 else '#53687a')
        for _ in range(24):  # a 3 s title card so the video explains itself without a narrator
            writer.grab_frame()
        card.remove()
        for index in range(900):
            time = data[0][0][index][0]
            clock.set_text(f'{int(time)//3600:02}:{int(time)%3600//60:02}:{int(time)%60:02}')
            caption.set_text(next((line for start, stop, line in script if start <= index < stop), ''))
            for i in range(2):
                other_time, cars = data[i][0][index]
                if other_time != time:
                    raise ValueError('FCD clocks differ')
                dots[i].set_offsets(cars[:, :2]); dots[i].set_array(cars[:, 2])
                waiting, blocked, finished = histories[i][index]
                counters[i].set_text(f'{waiting:,} waiting on the road\n{blocked:,} blocked from entering\n{finished:,} trips finished so far')
                growth[i].set_data(minutes[:index+1], totals[i][:index+1])
            writer.grab_frame()
            if index == 450:
                fig.savefig(p.ROOT/'reports/side_by_side_poster.png', dpi=100)
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


def chart(groups, metrics, title):
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
            parts.append(f'<text x="0" y="{yy+16}" fill="currentColor" font-size="13">{LABELS[i]}</text><rect x="170" y="{yy}" width="{x-170:.2f}" height="22" fill="{COLORS[i]}"/><path d="M {lo} {yy+11} H {hi} M {lo} {yy+5} V {yy+17} M {hi} {yy+5} V {yy+17}" stroke="currentColor" fill="none"/><text x="{hi+12}" y="{yy+16}" fill="currentColor" font-size="14">{mean:.1f} ± {sd:.1f} s</text>')
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
                         f'<rect x="{x-9}" y="{y-62}" width="18" height="34" rx="9" fill="{"#c2443a" if i in reds else "var(--accent)"}"/>')
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
                parts.append(f'<rect x="{left:.1f}" y="{y-10}" width="{right-left:.1f}" height="20" rx="4" fill="var(--accent)"/>')
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
        parts.append(f'<rect x="{x+7:.1f}" y="{230-height:.1f}" width="{width-14:.1f}" height="{height:.1f}" rx="4" fill="var(--accent)"/>')
        parts.append(text(x+width/2, 252, name, 14, 'middle', 'var(--muted)'))
        parts.append(text(x+width/2, 224-height, f'{value:,.0f}', 14, 'middle'))
    parts.append('<line x1="24" y1="230" x2="736" y2="230" stroke="var(--line)" stroke-width="2"/>')
    return svg(''.join(parts), 760, 268, unit)


def grid_svg(hit, total, target):
    """One square per measured count; filled means the simulation landed close to it."""
    columns = 12
    parts = []
    for i in range(total):
        x, y = 2+i % columns*34, 2+i//columns*34
        if i < hit:
            style = 'fill="var(--accent)" stroke="var(--accent)"'
        elif i < target:
            style = 'fill="none" stroke="var(--warn)" stroke-dasharray="4 3"'
        else:
            style = 'fill="none" stroke="var(--line)"'
        parts.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="5" stroke-width="2" {style}/>')
    rows = -(-total//columns)
    legend = rows*34+26
    parts.append(f'<rect x="2" y="{legend}" width="16" height="16" rx="4" fill="var(--accent)"/>'
                 + text(28, legend+14, f'{hit} counts we matched', 15))
    parts.append(f'<rect x="230" y="{legend}" width="16" height="16" rx="4" fill="none" stroke="var(--warn)" stroke-width="2" stroke-dasharray="4 3"/>'
                 + text(256, legend+14, f'{target-hit} short of the usual target', 15))
    return svg(''.join(parts), 560, legend+30, f'{hit} of {total} measured counts matched closely')


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
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="var(--accent)"/>')
    return svg(''.join(parts), 760, 260, 'Best score so far falls as the tuner tries more timing plans')


def seeds_svg(fit, holdout):
    parts = []
    for i, (group, fill, label) in enumerate(((fit, 'var(--road)', 'practice, used while tuning'),
                                              (holdout, 'var(--accent)', 'the fair test, never seen before'))):
        y = 34+i*92
        parts.append(text(0, y-10, f'{len(group)} rush hours for {label}', 16))
        for j in range(len(group)):
            parts.append(f'<rect x="{j*38}" y="{y}" width="30" height="30" rx="8" fill="{fill}"/>')
    return svg(''.join(parts), 390, 160, f'{len(fit)} rush hours used for tuning and {len(holdout)} kept back for testing')


def paired_svg(groups, key, label):
    """One row per test rush hour: both plans, same randomness."""
    values = [[float(r[key]) for r in group] for group in groups]
    low = min(min(v) for v in values)*.985
    high = max(max(v) for v in values)*1.004
    parts = [text(0, 18, label, 15, fill='var(--muted)')]
    for i in range(len(values[0])):
        y = 46+i*26
        a, b = (150+(values[j][i]-low)/(high-low)*520 for j in range(2))
        parts.append(f'<line x1="{a:.1f}" y1="{y}" x2="{b:.1f}" y2="{y}" stroke="var(--line)" stroke-width="3"/>'
                     f'<circle cx="{a:.1f}" cy="{y}" r="6" fill="{COLORS[0]}"/><circle cx="{b:.1f}" cy="{y}" r="6" fill="{COLORS[1]}"/>')
        parts.append(text(0, y+5, f'rush hour {i+1}', 13, fill='var(--muted)'))
    bottom = 46+len(values[0])*26
    for j, name in enumerate(LABELS):
        parts.append(f'<circle cx="{156+j*230}" cy="{bottom+6}" r="6" fill="{COLORS[j]}"/>'+text(170+j*230, bottom+11, name, 14))
    return svg(''.join(parts), 700, bottom+30, f'{label} for both plans in each of the ten test rush hours')


def build_page(rows, tests, roads, signals):
    groups = cohort(rows)
    def means(key): return stats(groups, key)[0]
    def pair(key): return ' → '.join(f'{v:,.1f}' for v in means(key))
    def pv(key):
        matches = [r for r in tests if r['scenario']=='pm_peak' and r['window']=='holdout' and r['seed_group']=='out_of_sample' and r['metric']==key]
        if len(matches)!=1 or int(matches[0]['n'])!=10:
            raise ValueError(f'Missing paired test: {key}')
        return f"{float(matches[0]['p_value']):.6f}"
    completed=means('completed'); eb=means('mainline_travel_eb_s'); side=means('side_time_loss_s')
    side_p = wilcoxon([float(b['side_time_loss_s'])-float(a['side_time_loss_s']) for a, b in zip(*groups)], alternative='less').pvalue
    headline = f'In the simulated rush-hour holdout, the optimized plan completes {completed[1]-completed[0]:,.0f} more requested trips and cuts eastbound corridor travel time by {(1-eb[1]/eb[0])*100:.1f}%, but completed trips from side streets lose {(side[1]/side[0]-1)*100:.1f}% more time.'
    tables=[]
    for scenario in ('pm_peak','night'):
        timing=read_csv(p.ROOT/f'reports/timing_{scenario}.csv')
        names={s['sumo_tls_id']:s['name'] for s in p.config()['signals']}
        body = ''
        seen = set()
        for r in timing:
            signal = r['sumo_tls_id']
            first = signal not in seen
            seen.add(signal)
            values = (names[signal] if first else '', f"{float(r['cycle_s']):.1f}" if first else '',
                      f"{float(r['offset_s']):.1f}" if first else '', r['phase'],
                      f"{float(r['max_green_s']):.1f}", f"{float(r['passage_s']):.1f}")
            body += '<tr>'+''.join(f'<td>{escape(v)}</td>' for v in values)+'</tr>'
        tables.append(f'<details{" open" if scenario == "pm_peak" else ""}><summary>{"Rush-hour" if scenario=="pm_peak" else "Night"} optimized timing · phase rows</summary><div class="scroll"><table><thead><tr><th>Signal</th><th>Cycle (s)</th><th>Offset (s)</th><th>Phase</th><th>Max green (s)</th><th>Passage (s)</th></tr></thead><tbody>{body}</tbody></table></div></details>')
    cfg = p.config()
    with open(p.ROOT/'sim/routes_pm_peak.rou.xml') as stream:
        trips = sum(1 for line in stream if '<vehicle ' in line)
    trials = read_csv(p.ROOT/'reports/optimize_trials.csv')
    curve = best_so_far(trials)
    cycles = [float(r['params_cycle_s']) for r in trials]
    miss_charge = ast.literal_eval(trials[0]['user_attrs_stats'])['vehicle_penalty_s']
    checks = read_csv(p.ROOT/'reports/demand_check.csv')
    close = sum(float(r['geh']) < 5 for r in checks)
    sources = read_csv(p.ROOT/'data/processed/tmc_sources.csv')
    measured = [r for r in sources if r['source'] == 'measured']
    hourly = [r['intersection'] for r in sources if r['source'] != 'measured' and r['count_date']]
    guessed = [r['intersection'] for r in sources if not r['count_date']]
    counts = {}
    for row in read_csv(p.ROOT/'data/processed/tmc.csv'):
        if row['intersection'] == measured[0]['intersection']:
            counts[row['interval_start']] = counts.get(row['interval_start'], 0)+int(row['vehicles'])
    base_cycle, base_svg = offset_svg(p.ROOT/'sim/tls_actuated_pm_peak.add.xml')
    wins = sum(float(b['completed']) > float(a['completed']) for a, b in zip(*groups))
    verdict = f'all {wins}' if wins == len(groups[0]) else f'{wins} of the {len(groups[0])}'
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cupertino Signal Lab</title>
<style>
:root{{color-scheme:light dark;--bg:#f5f7f8;--paper:#fff;--ink:#13242f;--muted:#53687a;--line:#dde4e9;--accent:#0b7d73;--soft:#e6f2f0;--warn:#a6560d;--road:#a9b8c4;--r:14px}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1a23;--paper:#17242e;--ink:#e8eff3;--muted:#a7bac6;--line:#2e414e;--accent:#5ecabd;--soft:#16302d;--warn:#e9a75d;--road:#61788a}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
main{{max-width:1040px;margin:auto;padding:0 28px 72px}}
h1{{font-size:clamp(38px,6.4vw,64px);line-height:1.03;letter-spacing:-.045em;margin:16px 0 20px;max-width:15ch}}
h2{{font-size:clamp(25px,3.5vw,35px);line-height:1.14;letter-spacing:-.03em;margin:0 0 12px;max-width:21ch}}
p{{margin:12px 0;max-width:60ch}}
.lead{{font-size:clamp(19px,2.3vw,22px);color:var(--muted);max-width:42ch}}
.kicker{{font-size:12px;letter-spacing:.17em;text-transform:uppercase;font-weight:700;color:var(--accent);margin:0}}
.muted{{color:var(--muted)}}
small{{display:block;font-size:13.5px;line-height:1.55;color:var(--muted);max-width:84ch;margin-top:14px}}
header{{padding:56px 0 0}}
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
.wide>svg,.wide>img{{min-width:560px}}
.split{{display:grid;grid-template-columns:5fr 6fr;gap:48px;align-items:center}}
.split figure{{margin:0}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 0;padding:0;list-style:none}}
.chips li{{background:var(--soft);color:var(--accent);border-radius:999px;padding:8px 16px;font-size:15px;font-weight:600}}
.scores{{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;margin:30px 0 8px}}
.score strong{{display:block;font-size:clamp(40px,5.6vw,58px);line-height:1;letter-spacing:-.04em;color:var(--accent);font-variant-numeric:tabular-nums}}
.score.cost strong{{color:var(--warn)}}
.score span{{display:block;margin-top:12px;font-size:16.5px;max-width:22ch}}
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
footer{{padding:34px 0;font-size:14px;color:var(--muted);border-top:1px solid var(--line)}}
@keyframes rise{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:none}}}}
@media(prefers-reduced-motion:no-preference){{@supports(animation-timeline:view()){{.step>*,header>*{{animation:rise linear both;animation-timeline:view();animation-range:entry 12% entry 88%}}}}}}
@media(max-width:860px){{.split{{grid-template-columns:1fr;gap:26px}}.split figure{{margin-top:12px}}}}
@media(max-width:720px){{main{{padding:0 18px 52px}}.step{{padding:52px 0}}.scores{{grid-template-columns:1fr;gap:26px}}.card{{padding:16px}}}}
</style><main>
<header><p class="kicker">Cupertino Signal Lab</p><h1>Rush hour on Stevens Creek.</h1><p class="lead">Five traffic lights in a row, and a line of cars that barely moves.</p>
<figure><div class="card tight wide">{map_svg(roads, signals)}</div><figcaption>The stretch we studied, drawn from the real street map. Eastbound runs from Mary Avenue to De Anza Boulevard. North is up, and the north to south distance is stretched so the names fit.</figcaption></figure></header>

<section class="step"><h2>What if the five lights worked as a team?</h2>
<p>Today each light decides on its own. If they turn green in order, a car can roll from one end to the other without stopping. That is the whole idea we tested.</p>
<figure><div class="card">{team_svg()}</div></figure></section>

<section class="step"><div class="split"><div><span class="n">1</span><h2>We rebuilt the real street inside a traffic simulator.</h2>
<p>Every lane and every turn comes from the public street map. All five lights line up with the real ones.</p></div>
<figure><div class="card tight wide"><img src="../reports/network.png" alt="The Stevens Creek corridor road network with the five signals marked" loading="lazy"></div><figcaption>The roads the simulated cars actually drive on, with the five signals marked.</figcaption></figure></div></section>

<section class="step"><span class="n">2</span><h2>The car counts come from City of Cupertino traffic reports.</h2>
<p>People stood at the intersections and wrote down every turn, every 15 minutes. The newest public counts we could find are from {measured[0]['year']}, so that is the traffic we model. It is not today's traffic.</p>
<figure><div class="card wide">{bars_svg(sorted(counts.items()), 'cars through ' + measured[0]['intersection'] + ' per 15 minutes')}</div><figcaption>Counted at {escape(measured[0]['intersection'])} and Stevens Creek on {measured[0]['count_date']}. The rush builds toward 17:15 and stays heavy for an hour.</figcaption></figure>
<ul class="chips"><li>Counted every 15 minutes: {', '.join(escape(r['intersection']) for r in measured)}</li><li>Counted by the hour: {', '.join(escape(n) for n in hourly)}</li><li>No counts, estimated: {', '.join(escape(n) for n in guessed)}</li></ul></section>

<section class="step"><div class="split"><div><span class="n">3</span><h2>Those counts become {trips:,} car trips.</h2>
<p>Every counted turn becomes cars with a real route through the corridor, released across the two hour rush. Then we checked our traffic against the real counts.</p></div>
<figure><div class="card">{grid_svg(close, len(checks), round(len(checks)*.85))}</div><figcaption>One square per measured count. Our traffic is the right shape but not exact, and this is the weakest part of the project. Everything after it inherits the error.</figcaption></figure></div></section>

<section class="step"><span class="n">4</span><h2>First we built the plan an engineer would use.</h2>
<p>A standard textbook formula gives all five lights one shared {base_cycle:.0f} second cycle and starts each main green at a different moment. That plan is what we have to beat. It is not Cupertino's current timing.</p>
<figure><div class="card wide">{base_svg}</div><figcaption>Green bars are the main road's green time at each light through one cycle. Going east, each green starts later than the one before, and the last one wraps into the next cycle.</figcaption></figure></section>

<section class="step"><span class="n">5</span><h2>The computer tried {len(curve)} timing plans and kept the best.</h2>
<p>A tuning tool changes the timing, runs the entire rush hour, scores it, then tries again. Nobody picked the winner by hand.</p>
<figure><div class="card wide">{curve_svg(curve)}</div><figcaption>The best score so far across {len(curve)} tries. Lower is better: the score adds up the time every car loses. Most of the gain arrives early, then the tool fine tunes.</figcaption></figure>
<ul class="chips"><li>How long one full cycle lasts ({min(cycles):.0f} to {max(cycles):.0f} seconds)</li><li>When each light starts its green</li><li>How much of the cycle the main road gets</li></ul>
<p>One rule keeps it honest. A plan cannot win by holding cars out of the corridor: every trip that never finished was charged {miss_charge/60:.0f} minutes of delay, so starving the entrances always scores worse.</p></section>

<section class="step"><div class="split"><div><span class="n">6</span><h2>Then we tested both plans on {len(groups[0])} rush hours the tuner never saw.</h2>
<p>Tuning used {len(cfg['seeds'])} practice rush hours. Scoring used {len(groups[0])} different ones: same road, same demand, new randomness. The tuned plan could not win by memorising its practice runs.</p></div>
<figure><div class="card">{seeds_svg(cfg['seeds'], groups[0])}</div></figure></div></section>

<section class="step"><h2>Watch the same rush hour twice.</h2>
<video controls playsinline preload="metadata" poster="../reports/side_by_side_poster.png" aria-label="Side by side traffic simulation of the textbook plan and the tuned plan"><source src="../reports/side_by_side.mp4" type="video/mp4">Open <a href="../reports/side_by_side.mp4">the video</a>.</video>
<ul class="notes"><li>Left is the textbook plan. Right is the tuned plan. Same cars, same clock.</li><li>Red dots are cars that have stopped. Green dots are moving.</li><li>The two lines at the bottom count trips finished. The tuned plan stays ahead the whole time.</li></ul>
<small>17:30 to 17:45 at 8x speed, from one example run that was also used while tuning, so it shows what the plans look like rather than proving anything. The numbers below come from the ten test rush hours instead. Counts include warmup trips. The north to south scale is stretched and signal states were not recorded.</small></section>

<section class="step"><h2>The result</h2>
<div class="scores"><div class="score"><strong>+{completed[1]-completed[0]:,.0f}</strong><span>more trips finished per rush hour</span></div><div class="score"><strong>{(1-eb[1]/eb[0])*100:.1f}%</strong><span>faster for eastbound drivers</span></div><div class="score cost"><strong>+{(side[1]/side[0]-1)*100:.1f}%</strong><span>more time lost by side street drivers, the honest cost</span></div></div>
<figure><div class="card wide">{paired_svg(groups, 'completed', 'Trips finished in the test hour')}</div><figcaption>Each line is one of the {len(groups[0])} test rush hours, with both plans run on the same randomness. The tuned plan finishes more trips in {verdict}.</figcaption></figure></section>

<section class="step"><h2>What this does not prove</h2>
<ul class="notes"><li>The counts are from {measured[0]['year']} and {len(guessed)} of the five intersections were never counted at all.</li><li>It is a simulation. Nothing was tested on a real street, and these are not Cupertino's current light settings.</li><li>Side street drivers lose time. A real city would have to decide whether that trade is worth making.</li></ul>
<p>What we would do next: ask VTA for newer counts, put pedestrians and bikes in the model, and try a second corridor.</p></section>

<details><summary>For the curious: full numbers, tests and method</summary>
<p>{headline}</p>
<p class="muted">The three counters in the video: waiting on the road means speed below 0.1 m/s; blocked from entering means the scheduled departure has passed with no first insertion yet, and teleported cars are not counted as blocked; trips finished means recorded arrivals so far.</p>
<p class="counts">Requested: <strong>{pair('requested')}</strong><br>Completed: <strong>{pair('completed')}</strong><br>Unfinished: <strong>{pair('unfinished')}</strong> (still running or never inserted).</p>
<div class="card wide">{chart(groups,[('all_vehicle_delay_s','All-requested score, 1800 s unfinished charge'),('all_vehicle_delay_zero_unfinished_s','All-requested score, zero unfinished charge')],'All-requested scores')}<small>Lower is better. Main score p={pv('all_vehicle_delay_s')}; zero-charge p={pv('all_vehicle_delay_zero_unfinished_s')}. Score = [completed time loss + completed insertion delay + 1800 x (unfinished + teleport events)] / requested. The 1800 s charge is a scoring rule, not measured delay. Zero-charge removes only the unfinished charge and retains the teleport charge; it is a lower bound on score, not physical total delay.</small></div>
<div class="card wide">{chart(groups,[('mainline_travel_eb_s','Eastbound corridor travel'),('mainline_travel_wb_s','Westbound corridor travel')],'Corridor travel')}<small>EB p={pv('mainline_travel_eb_s')}; WB p={pv('mainline_travel_wb_s')} (no supported westbound gain). Directional travel excludes pre-insertion delay and teleported vehicles.</small></div>
<div class="card wide">{chart(groups,[('mean_time_loss_s','Completed-only time loss'),('side_time_loss_s','Completed-only side-origin time loss'),('mean_depart_delay_s','Completed-only insertion delay')],'Completed-only outcomes')}<small>Completed-only loss p={pv('mean_time_loss_s')} for improvement: that original outcome worsens. Time loss measures in-road slowing; insertion delay measures waiting to enter; side-origin loss is for trips starting off the mainline. These omit unfinished demand and can carry survivor bias.</small></div>
<small>Bars show mean plus or minus one sample standard deviation across seeds 3 to 12, not confidence intervals and not real-world uncertainty. P-values are paired one-sided Wilcoxon tests, optimized below textbook. Extra completions use the complementary unfinished count. Score and directional tests are post-result exploratory and unadjusted; no overall winner is established. Full PM and holdout windows overlap. Fitted-hour demand is replayed, so these seeds test randomness and later operating conditions, not unseen measured demand. The side-street cost has p={side_p:.6f} when tested for improvement.</small>
<p class="muted">Night is estimated demand and shows no supported gain: all-requested score {' to '.join(f'{v:.2f}' for v in stats(cohort(rows,'night','full'),'all_vehicle_delay_s')[0])} s.</p>
<figure><img src="../reports/time_space.png" alt="Eastbound car trajectories for the textbook and optimized plans" loading="lazy"><figcaption>One path per car while it is on the eastbound corridor. Rising lines mean movement, flat lines mean waiting. Same illustrative seed 0 as the video, not aggregate evidence.</figcaption></figure>
<p class="muted">Data and limits in full: public counts are from {measured[0]['year']}. {' and '.join(escape(r['intersection']) for r in measured)} have measured quarter-hour counts; {', '.join(escape(n) for n in guessed)} and {', '.join(escape(n) for n in hourly)} profiles are estimated, with {', '.join(escape(n) for n in hourly)} built from hourly observations. This is not a picture of current traffic. Mary's mapped layout omits movements totaling 775 vehicles per hour.</p>
<p class="muted">Teleports persist: holdout totals {sum(int(r['teleports']) for r in groups[0])} to {sum(int(r['teleports']) for r in groups[1])} across ten seeds; full PM totals {sum(int(r['teleports']) for r in cohort(rows,window='full')[0])} to {sum(int(r['teleports']) for r in cohort(rows,window='full')[1])}. SUMO can relocate stuck cars after 300 s, which distorts congestion. Completing more trips does not prove more cars entered the road. The simulated counts matched the measured ones on {close} of {len(checks)} movement intervals, below the {round(len(checks)*.85)} an engineer would expect.</p>
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
    tests = read_csv(p.ROOT/'reports/wilcoxon.csv')
    page = build_page(rows, tests, roads, signals)
    render_media(roads, signals, offsets, distance)
    (p.ROOT/'dashboard').mkdir(exist_ok=True)
    (p.ROOT/'dashboard/index.html').write_text(page)
    print('Built dashboard/index.html, side_by_side.mp4, side_by_side_poster.png, time_space.png')
