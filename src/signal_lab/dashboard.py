"""Offline judge demo from frozen evaluation CSVs and illustrative seed-0 FCD."""
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

    fig, axes = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor('#f7f8fa')
    dots, counters = [], []
    all_points = np.concatenate([np.array(r) for r in roads])
    xmin, ymin = all_points.min(axis=0); xmax, ymax = all_points.max(axis=0)
    clock = fig.suptitle('', fontsize=26, y=.94)
    for ax, label in zip(axes, LABELS):
        ax.set_facecolor('#f7f8fa')
        ax.add_collection(LineCollection(roads, colors='#c3ccd4', linewidths=4))
        for i, (name, (x, y)) in enumerate(signals):
            ax.plot(x, y, 'o', color='#263d50', ms=8)
            ax.annotate(name.replace(' Blvd', '').replace(' Rd', ''), (x, y), xytext=(0, 28 if i%2 else -32), textcoords='offset points', ha='center', fontsize=17)
        ax.set(xlim=(xmin-30, xmax+30), ylim=(ymin-30, ymax+30), aspect='auto')
        ax.axis('off')
        ax.set_title(label, fontsize=24, pad=50)
        dots.append(ax.scatter([], [], c=[], s=24, cmap='RdYlGn', vmin=0, vmax=16, zorder=3))
        counters.append(ax.text(.5, -.10, '', transform=ax.transAxes, ha='center', va='top', fontsize=22, linespacing=1.4))
    fig.subplots_adjust(left=.035, right=.965, wspace=.12, bottom=.33, top=.82)
    fig.text(.5, .14, 'Car speed: red = stopped (< 0.1 m/s) • yellow = slow • green = moving', ha='center', fontsize=17)
    fig.text(.5, .095, 'North ↑   |   Same clock, same seed, 8× playback   |   2018 demand assumptions', ha='center', fontsize=16)
    fig.text(.5, .07, 'Illustration only • Counts include warmup trips • North–south scale expanded • Signal states not recorded.', ha='center', fontsize=13)
    # One frame per simulated second at 8 fps gives 112.5 s, exactly 8×.
    writer = FFMpegWriter(fps=8, codec='libx264', extra_args=['-threads', '1', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
    output = p.ROOT/'reports/side_by_side.mp4'
    with writer.saving(fig, str(output), dpi=100):
        for index in range(900):
            time = data[0][0][index][0]
            clock.set_text(f'Stevens Creek Signal Lab     {int(time)//3600:02}:{int(time)%3600//60:02}:{int(time)%60:02}')
            for i in range(2):
                other_time, cars = data[i][0][index]
                if other_time != time:
                    raise ValueError('FCD clocks differ')
                dots[i].set_offsets(cars[:, :2]); dots[i].set_array(cars[:, 2])
                waiting, blocked, finished = histories[i][index]
                counters[i].set_text(f'{waiting:,} waiting on the road\n{blocked:,} blocked from entering\n{finished:,} trips finished so far')
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
        return ((x-low[0])/span[0]*1000+45, 270-(y-low[1])/span[1]*180)
    paths = []
    for road in roads:
        coords = ' '.join(f'{a:.1f},{b:.1f}' for a, b in (xy(*point) for point in road))
        paths.append(f'<polyline points="{coords}" fill="none" stroke="var(--road)" stroke-width="3"/>')
    for i, (name, point) in enumerate(signals):
        x, y = xy(*point)
        paths.append(f'<circle cx="{x}" cy="{y}" r="7" fill="var(--accent)"/><text x="{x}" y="{y-24 if i%2 else y+32}" text-anchor="middle" fill="currentColor" font-size="16">{escape(name)}</text>')
    return '<svg viewBox="0 0 1100 340" role="img" aria-label="Five signals from Mary Avenue in the west to De Anza Boulevard in the east; north up">'+''.join(paths)+'<text x="45" y="35" fill="currentColor">N ↑</text></svg>'


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
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cupertino Signal Lab</title>
<style>
:root{{color-scheme:light dark;--bg:#f7f8fa;--ink:#172f43;--muted:#4e6171;--paper:#fff;--line:#d8e0e5;--accent:#087f78;--road:#a7b6c2}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1120px;margin:auto;padding:48px 28px}}header{{padding:16px 0 32px}}.eyebrow{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:var(--accent)}}h1{{font-size:clamp(40px,7vw,76px);line-height:1.03;letter-spacing:-.055em;margin:18px 0}}h2{{font-size:29px;line-height:1.2;letter-spacing:-.025em;margin:0 0 14px}}p{{margin:12px 0}}.lead{{font-size:23px}}.muted,small,figcaption{{color:var(--muted)}}small{{font-size:13px}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);border-block:1px solid var(--line);margin:24px 0}}.stat{{padding:24px 18px 24px 0}}.stat strong{{font-size:46px;line-height:1.2;display:block;letter-spacing:-.04em;color:var(--accent)}}.stat.cost strong{{color:#b45309}}.stat span{{display:block}}section{{padding:36px 0;border-bottom:1px solid var(--line)}}video,img,svg{{display:block;width:100%;height:auto}}video{{background:var(--paper);border-radius:8px}}figure{{margin:22px 0}}figcaption{{font-size:14px;margin-top:12px}}.panel{{background:var(--paper);border:1px solid var(--line);padding:24px;border-radius:8px;margin:18px 0}}.panel{{overflow-x:auto}}.panel svg{{min-width:680px}}.counts{{font-variant-numeric:tabular-nums}}table{{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}}th,td{{text-align:left;padding:9px;border-bottom:1px solid var(--line);white-space:nowrap}}.scroll{{overflow-x:auto}}summary{{cursor:pointer;padding:16px 0;font-weight:600}}a{{color:var(--accent)}}a:focus-visible,summary:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}ol{{padding-left:25px}}li{{padding:5px 0}}footer{{padding:32px 0;font-size:14px}}@media(prefers-color-scheme:dark){{:root{{--bg:#111d27;--ink:#e9f0f4;--muted:#b4c3cd;--paper:#192934;--line:#3a4d59;--accent:#62c9bc;--road:#6b8292}}.stat.cost strong{{color:#efb26e}}}}@media(max-width:600px){{main{{padding:26px 18px}}.stats{{grid-template-columns:1fr}}.stat{{padding:18px 0;border-bottom:1px solid var(--line)}}.stat strong{{font-size:38px}}.panel{{padding:14px}}}}
</style><main><header><div class="eyebrow">Cupertino Signal Lab · a student simulation study</div><h1>Better flow.<br>Real tradeoffs.</h1><p class="lead">Stevens Creek backs up to Glenbrook at rush hour.</p><p>Cupertino Signal Lab tests whether five coordinated lights can move more traffic through the same roads.</p>
<div class="stats"><div class="stat"><strong>+{completed[1]-completed[0]:,.0f}</strong><span>more requested trips completed</span><small>Mean per holdout hour · unfinished p={pv('unfinished')}</small></div><div class="stat"><strong>{(1-eb[1]/eb[0])*100:.1f}%</strong><span>faster eastbound corridor trips</span><small>In-road travel · p={pv('mainline_travel_eb_s')}</small></div><div class="stat cost"><strong>+{(side[1]/side[0]-1)*100:.1f}%</strong><span>more time lost by side-street trips</span><small>Completed side-origin loss · p={side_p:.6f} for improvement</small></div></div>
<p>{headline}</p><p class="muted">2018 historical counts · 3 of 5 quarter-hour profiles estimated · simulation, not field-tested. No overall or field winner established.</p></header>
<section><div class="eyebrow">01 / Watch the same rush hour</div><h2>Two plans. One clock.</h2><video controls playsinline preload="metadata" poster="../reports/side_by_side_poster.png" aria-label="Side by side traffic simulation"><source src="../reports/side_by_side.mp4" type="video/mp4">Open <a href="../reports/side_by_side.mp4">the video</a>.</video><p class="muted">17:30–17:45 at 8× speed. Seed 0 is illustrative, used during fitting, and is not the ten-seed result above. Waiting on the road = speed below 0.1 m/s. Blocked from entering = scheduled departure reached but no first insertion yet; teleported cars are not counted as blocked. Trips finished = recorded arrivals so far. Counts include warmup trips, not just the holdout cohort. North–south scale is expanded for readability. Signal states were not recorded.</p></section>
<section><div class="eyebrow">02 / The corridor</div><h2>Five signals along Stevens Creek</h2>{map_svg(roads, signals)}<p class="muted">Road shapes and signal positions from the SUMO / OpenStreetMap network. North up; north–south scale expanded for readability. Eastbound runs Mary → De Anza.</p></section>
<section><div class="eyebrow">03 / Check the evidence</div><h2>More trips finish. Some trips lose more time.</h2><p>Textbook coordinated-actuated baseline <strong>(not Cupertino’s current timing)</strong> → optimized plan. Holdout 17:30–18:30; ten paired seeds, 3–12.</p><p class="counts">Requested: <strong>{pair('requested')}</strong><br>Completed: <strong>{pair('completed')}</strong><br>Unfinished: <strong>{pair('unfinished')}</strong> (still running or never inserted).</p>
<div class="panel">{chart(groups,[('all_vehicle_delay_s','All-requested score · 1800 s unfinished charge'),('all_vehicle_delay_zero_unfinished_s','All-requested score · zero unfinished charge')],'All-requested scores')}<small>Lower is better. Main score p={pv('all_vehicle_delay_s')}; zero-charge p={pv('all_vehicle_delay_zero_unfinished_s')}. Score = [completed time loss + completed insertion delay + 1800 × (unfinished + teleport events)] / requested. The 1800 s charge is a scoring rule, not measured delay. Zero-charge removes only the unfinished charge and retains the teleport charge; it is a lower bound on score, not physical total delay.</small></div>
<div class="panel">{chart(groups,[('mainline_travel_eb_s','Eastbound corridor travel'),('mainline_travel_wb_s','Westbound corridor travel')],'Corridor travel')}<small>EB p={pv('mainline_travel_eb_s')}; WB p={pv('mainline_travel_wb_s')} (no supported WB gain). Directional travel excludes pre-insertion delay and teleported vehicles.</small></div>
<div class="panel">{chart(groups,[('mean_time_loss_s','Completed-only time loss'),('side_time_loss_s','Completed-only side-origin time loss'),('mean_depart_delay_s','Completed-only insertion delay')],'Completed-only outcomes')}<small>Completed-only loss p={pv('mean_time_loss_s')} for improvement: the original outcome worsens. Time loss measures in-road slowing; insertion delay measures waiting to enter; side-origin loss is for trips starting off the mainline. These omit unfinished demand and can have survivor bias.</small></div>
<p class="muted">Bars show mean ± one sample standard deviation across seeds 3–12, not confidence intervals or real-world uncertainty. P-values: paired one-sided Wilcoxon, optimized &lt; textbook. Extra completions use the complementary unfinished count. Score and directional tests are post-result exploratory, unadjusted; no overall winner is established. Full PM and holdout overlap. Fitted-hour demand is replayed: these seeds test randomness and later operating conditions, not unseen measured demand.</p>
<p class="muted">Night is estimated demand and shows no supported gain: all-requested score { ' → '.join(f'{v:.2f}' for v in stats(cohort(rows,'night','full'),'all_vehicle_delay_s')[0])} s. <a href="../reports/results.csv">All results (CSV)</a> · <a href="../reports/wilcoxon.csv">Paired tests (CSV)</a></p></section>
<section><div class="eyebrow">04 / Follow the cars</div><h2>Where eastbound cars keep moving</h2><figure><img src="../reports/time_space.png" alt="Eastbound car trajectories: textbook and optimized plans, distance versus minutes after 17:30" loading="lazy"><figcaption>One path per car while observed on the eastbound corridor. Rising lines mean movement; flat lines mean waiting. Gaps are left unconnected. Same seed-0 FCD as the video; not aggregate evidence.</figcaption></figure></section>
<section><div class="eyebrow">05 / The proposed settings</div><h2>A timing sheet, not a live controller</h2><p>Optimized demo assumptions. Phase order and clearance rules are preserved. No settings are sent to city lights.</p>{''.join(tables)}</section>
<section><h2>How it works</h2><ol><li>Build the five-signal road network from OpenStreetMap.</li><li>Replay public turning counts and clearly marked estimates.</li><li>Try timing plans in SUMO, keeping the same safety clearances.</li><li>Freeze the chosen plan and compare it with the textbook plan on ten unused seeds.</li></ol></section>
<section><h2>Data and limits</h2><p>Public counts are from 2018. De Anza and Stelling have measured quarter-hour counts; Bandley, Saich and Mary profiles are estimated (Mary uses hourly observations). This is not a picture of current traffic. Mary’s mapped layout omits movements totaling 775 vehicles/hour.</p><p>Teleports persist: holdout totals {sum(int(r['teleports']) for r in groups[0])} → {sum(int(r['teleports']) for r in groups[1])} across ten seeds; full PM totals {sum(int(r['teleports']) for r in cohort(rows,window='full')[0])} → {sum(int(r['teleports']) for r in cohort(rows,window='full')[1])}. SUMO can relocate stuck cars after 300 s, distorting congestion. Completing more trips does not prove more cars entered the road.</p><p>No field testing. An engineer would need current counts, actual timing sheets and a supervised pilot before considering real changes.</p></section>
<footer><strong>Cupertino Signal Lab</strong> · Student hackathon project<br>Road data: OpenStreetMap contributors, ODbL. Counts: City of Cupertino Vallco and Westport traffic reports. Simulation: SUMO. Built with Python, Matplotlib and ffmpeg. <a href="../data/processed/tmc_sources.csv">Source audit (CSV)</a></footer></main></html>'''


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
