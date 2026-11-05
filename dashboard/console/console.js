'use strict';
// Every number on screen comes from the copied report files in data/, metrics.json, the recording, or the live run.
// metrics.json panels hide when the file or a field is missing. ?fixture swaps in a fake fixture, with a banner.

const ROADS = ['wolfe', 'deanza'];
const CONTEXT = ['homestead', 'stevens_creek'];
const STORE = 'signal-learner-console-v3';
const FIXTURE = new URLSearchParams(location.search).has('fixture');

const main = document.getElementById('main');
const cache = {};
let route = { road: 'wolfe', screen: 'corridors' };
let state = load();
let form = null;
let player = null;
const drafts = {};
const view = { c15: 'delay_s', s15: 'delay_s', ts: 'proposed' };

const TERMS = {
  score: 'Average extra seconds per requested trip. A trip that never finishes counts 900 s.',
  aog: 'Arrivals on green: share of cars that reach the stop bar while the light is green.',
  sf: 'Split failures: cycles where the queue did not clear before the light turned red.',
  pcd: 'Purdue Coordination Diagram. Each dot is a car arriving: time of day across, seconds into the cycle up. Green bands show when the light was green.',
  cycle: 'One full round of greens for every direction.',
  offset: 'When this light’s cycle starts, relative to the corridor’s reference clock.',
  split: 'Max green + yellow + all-red.',
  unfinished: 'Trips still waiting or on the road when the evening ended.',
  ts: 'Distance along the road (up) against time (across). Lines are car paths; bars show each light’s green.',
  mv: 'Direction of travel and the turns served: L left, T through, R right.',
  worst: 'Average delay for the worst-off group of drivers (same starting point).',
  practice: 'A copy of the road built only from sensor counts. Plans are tried here first.',
  heldout: 'Evenings the learner never saw, tested once with the rules written first.',
  jammed: 'The simulation had to remove stuck cars more often than with the current timing.',
  posthoc: 'Run after the frozen test; not part of the pre-registered result.',
  rollback: 'Watches the sensor feed after a change and tells the engineer to go back if delay rises past its limit. Tested in simulation on deliberately bad plans and on harmless changes.',
};
const term = (key, text) => `<span class="term" tabindex="0">${text}<span class="tip" role="tooltip">${esc(TERMS[key])}</span></span>`;
// Drill-down: a screen, optionally a panel on it (p) and a chart view, e.g. go('wolfe', 'signal/1', { p: 'pcd' }).
const go = (road, sub = '', q = {}) => `#/${road}${sub ? `/${sub}` : ''}${Object.keys(q).length ? `?${new URLSearchParams(q)}` : ''}`;
const dl = (href, html, label = '') => `<a class="dl" href="${href}"${label ? ` aria-label="${esc(label)}"` : ''}>${html}</a>`;

/* ---------- State: decisions and the audit log ---------- */

function load() {
  try { const s = JSON.parse(localStorage.getItem(STORE)); if (s && s.decisions && Array.isArray(s.log)) return s; } catch { /* fall through */ }
  return { decisions: {}, log: [] };
}
function save() {
  try { localStorage.setItem(STORE, JSON.stringify(state)); } catch { /* private mode: keep in memory */ }
}
function act(road, action, decision, note = '') {
  const at = new Date().toISOString();
  if (decision === null) delete state.decisions[road];
  else if (decision) state.decisions[road] = { ...decision, at, note };
  state.log.push({ at, road, action, note });
  save();
}
const dec = d => state.decisions[d.road] || {};

/* ---------- Data ---------- */

function csv(text) {
  const [head, ...rows] = text.trim().split(/\r?\n/);
  const keys = head.split(',');
  return rows.map(row => Object.fromEntries(row.split(',').map((v, i) => [keys[i], v])));
}

function roadYaml(text) {
  const top = key => (text.match(new RegExp(`^${key}:\\s*'?([^'\\n]*)'?`, 'm')) || [])[1];
  const points = [...text.matchAll(/^- name: '?([^'\n]+)'?\n\s+lat: ([\d.-]+)\n\s+lon: ([\d.-]+)/gm)].map(m => ({ name: m[1], lat: +m[2], lon: +m[3] }));
  return { street: top('street'), begin: top('begin'), end: top('end'), drain: Number(top('drain_s')), points };
}

// Yellow and all-red after each green, from the main phase chain (before the first <param>).
function clearances(xml) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  const out = {};
  for (const tl of doc.querySelectorAll('tlLogic')) {
    const chain = [];
    for (const el of tl.children) { if (el.tagName === 'param') break; chain.push(el); }
    const byPhase = {};
    chain.forEach((el, i) => {
      if (!el.hasAttribute('minDur')) return;
      let yellow = 0, red = 0;
      for (let j = i + 1; j < chain.length && !chain[j].hasAttribute('minDur'); j++) {
        const st = chain[j].getAttribute('state'), dur = Number(chain[j].getAttribute('duration'));
        if (st.includes('y')) yellow += dur; else if (/^r+$/.test(st)) red += dur;
      }
      byPhase[i] = { yellow, red };
    });
    out[tl.getAttribute('id')] = byPhase;
  }
  return out;
}

async function get(p, kind = 'text') {
  const response = await fetch(p);
  if (!response.ok) throw new Error(`Could not load ${p}`);
  return response[kind]();
}

// The real path never shows a fixture, even if one is copied into place by mistake.
async function metricsFor(road) {
  try {
    const m = FIXTURE ? (await get('data/_fixture/metrics.json', 'json'))[road] : await get(`data/${road}/metrics.json`, 'json');
    if (!m || typeof m !== 'object' || m.road !== road) return null;
    if (!FIXTURE && (m._fixture || /fixture|fake/i.test(m.source || ''))) return null;
    return m;
  } catch { return null; }
}

async function data(road) {
  if (cache[road]) return cache[road];
  const base = `data/${road}/`;
  const [card, practice, plan, yaml, results, geo, goBack, m] = await Promise.all([
    get(base + 'card.json', 'json'), get(base + 'practice.json', 'json'), get(base + 'plan.add.xml'), get(base + 'road.yaml'),
    get('data/heldout/results.csv'), get(`geo/${road}.json`, 'json'), get('data/heldout/go_back.json', 'json'), metricsFor(road)]);
  const posthoc = road === 'deanza' ? await get('data/deanza/posthoc.json', 'json') : null;
  return (cache[road] = { road, card, practice, clear: clearances(plan), info: roadYaml(yaml), results: csv(results), geo, goBack, posthoc, m });
}

async function contextRoads() {
  if (cache.context) return cache.context;
  const texts = await Promise.all(CONTEXT.map(r => get(`data/${r}/road.yaml`)));
  return (cache.context = texts.map((t, i) => ({ road: CONTEXT[i], ...roadYaml(t) })));
}

function heldout(d) {
  const rows = d.results.filter(r => r.road === d.road);
  const by = (arm, k) => Object.fromEntries(rows.filter(r => r.arm === arm).map(r => [r.seed, Number(r[k])]));
  const old = by('old', 'all_requested_delay_s'), plan = by('learner', 'all_requested_delay_s');
  const seeds = Object.keys(old).filter(s => s in plan).sort((a, b) => a - b);
  const avg = (o) => mean(seeds.map(s => o[s]));
  const per = seeds.map(s => ({ seed: s, v: share(old[s], plan[s]) * 100 }));
  return {
    n: seeds.length, seeds, per, oldMean: avg(old), planMean: avg(plan), better: seeds.filter(s => plan[s] < old[s]).length,
    unfOld: avg(by('old', 'unfinished')), unfPlan: avg(by('learner', 'unfinished')),
    worstOld: avg(by('old', 'worst_origin_delay_s')), worstPlan: avg(by('learner', 'worst_origin_delay_s')),
  };
}
const betterOn = h => h.better === h.n ? `all ${h.n}` : `${h.better} of ${h.n}`;

// De Anza: how many confirmation runs of the best new plan jammed (removed more stuck cars than the margin allows).
function jams(d) {
  const p = d.practice, margin = p.settings.teleport_margin;
  return { n: p.confirm_new.length, jammed: p.confirm_new.filter((run, i) => run.teleports > p.confirm_old[i].teleports + margin).length };
}

function goBack(d) {
  const runs = d.goBack.filter(r => r.road === d.road), bad = runs.filter(r => r.program === 'bad'), noop = runs.filter(r => r.program === 'noop');
  const mins = bad.filter(r => r.go_back).map(r => (r.time_s - r.change_s) / 60).sort((a, b) => a - b);
  return { bad: bad.length, caught: mins.length, noop: noop.length, false: noop.filter(r => r.go_back).length, median: mins[Math.floor(mins.length / 2)] };
}

function phases(d, sig, which) {
  const clear = d.clear[sig.sumo_tls_id] || {};
  return sig[which].greens.map(g => {
    const { yellow = 0, red = 0 } = clear[g.phase] || {};
    return { ...g, yellow, red, split: g.max_green_s + yellow + red };
  });
}

const LEGS = { N: 'north', S: 'south', E: 'east', W: 'west' };
const TURNS = { L: 'left', T: 'through', R: 'right' };
const serves = codes => codes.map(code => { const [leg, turns] = code.split(':'); return `from ${LEGS[leg] || leg}: ${[...turns].map(t => TURNS[t] || t).join(', ')}`; }).join(' · ');
const BOUND = { N: 'SB', S: 'NB', E: 'WB', W: 'EB' };
const moves = codes => codes.map(c => { const [leg, turns] = c.split(':'); return `<span class="mv">${BOUND[leg] || leg} ${esc(turns)}</span>`; }).join('');
const isChange = d => d.card.decision === 'change';
const metricSignal = (d, sig) => d.m?.signals?.find(s => s.id === sig.sumo_tls_id) || null;
const window_ = d => `${ampm(seconds(d.info.begin))}–${ampm(seconds(d.info.end))}`;
const planName = d => isChange(d) ? 'Proposed' : 'Recommended';
// metrics.json "proposed" for a keep-current road is either the kept timing or the rejected candidate; name it by what it is.
const propName = d => isChange(d) ? 'Proposed' : JSON.stringify(d.m?.corridor?.baseline) === JSON.stringify(d.m?.corridor?.proposed) ? 'Recommended' : 'Rejected candidate';

const STATUS = {
  pending: ['Recommendation pending', 'new'], keep: ['Keep current timing', 'calm'], acknowledged: ['Keep current timing', 'calm'],
  approved: ['Approved', 'ok'], scheduled: ['Scheduled', 'ok'], rejected: ['Rejected', 'bad'],
  deployed: ['Deployed · simulated', 'live'], rolled_back: ['Rolled back', 'bad'],
};
const statusKey = d => dec(d).status || (isChange(d) ? 'pending' : 'keep');
const pill = d => { const [t, c] = STATUS[statusKey(d)]; return `<span class="pill ${c}">${t}</span>`; };

/* ---------- Markup pieces ---------- */

function crumbs(list) {
  return `<nav class="crumbs" aria-label="Breadcrumb"><ol>${list.map(([t, href], i) => i === list.length - 1
    ? `<li><span aria-current="page">${esc(t)}</span></li>` : `<li><a href="${href}">${esc(t)}</a></li>`).join('')}</ol></nav>`;
}
function head(title, { status = '', meta = [], actions = '' } = {}) {
  return `<header class="page-h"><div><div class="title-row"><h1>${esc(title)}</h1>${status}</div>
    ${meta.length ? `<p class="meta-line">${meta.filter(Boolean).join('<span class="sep" aria-hidden="true">·</span>')}</p>` : ''}</div>
    ${actions ? `<div class="actions">${actions}</div>` : ''}</header>`;
}
let panelId = 0;
function panel(title, body, { tools = '', cls = '', anchor = '' } = {}) {
  if (!body) return '';
  const id = `p${++panelId}`;
  return `<section class="panel ${cls}" aria-labelledby="${id}"${anchor ? ` id="${anchor}" tabindex="-1"` : ''}><header class="panel-h"><h2 id="${id}">${title}</h2>${tools}</header><div class="panel-b">${body}</div></section>`;
}
function toggle(name, label, options, current) {
  return `<div class="seg" role="group" aria-label="${esc(label)}">${options.map(([k, t]) =>
    `<button type="button" data-view="${name}" data-val="${k}" aria-pressed="${k === current}">${esc(t)}</button>`).join('')}</div>`;
}
function delta(b, p, dp = 0) {
  if (!ok(b) || !ok(p)) return '';
  const d = p - b, cls = Math.abs(d) < 1e-9 ? 'flat' : d < 0 ? 'good' : 'bad';
  const v = share(b, p) * 100, txt = b ? `${Math.abs(v) < 1 ? signed(v, 1) : signed(Math.round(v))}%` : signed(d, dp);
  return `<span class="delta ${cls}">${cls === 'flat' ? '0%' : txt}</span>`;
}
const cmp = (b, p, dp = 0, unit = '') => ok(b) && ok(p)
  ? `<span class="cmp"><span class="b">${fmt(b, dp)}</span><span class="arr" aria-label="to">→</span><span class="p">${fmt(p, dp)}${unit ? `<small>${unit}</small>` : ''}</span></span>` : '<span class="na">–</span>';
const sameOr = (a, b, dp = 1) => Math.abs(a - b) < 0.05 ? `<span class="num">${fmt(a, dp)}</span>` : `<span class="num">${fmt(a, dp)} <span class="arr">→</span> <b>${fmt(b, dp)}</b></span>`;

function kpi(label, b, p, dp, unit, href) {
  if (!ok(b) || !ok(p)) return '';
  const v = `<span class="p">${fmt(p, dp)}</span><small>${unit}</small>${delta(b, p, dp)}`;
  return `<div class="kpi"><div class="kpi-l">${label}</div>${href ? `<a class="kpi-v dl" href="${href}">${v}</a>` : `<div class="kpi-v">${v}</div>`}
    <div class="kpi-b">was ${fmt(b, dp)}${unit ? ` ${unit}` : ''}</div></div>`;
}

// One cycle as coloured segments, scaled so every bar on the page shares one seconds axis.
function bar(list, cycle, scale, which) {
  const seg = (cls, s, title, text = '') => s > 0 ? `<div class="${cls}" style="width:${s / cycle * 100}%" title="${esc(title)}">${text}</div>` : '';
  const body = list.map((p, i) => seg(`seg-g${i % 2 ? ' alt' : ''}`, p.max_green_s, `Phase ${p.phase} green ${serves(p.serves)}: up to ${f1(p.max_green_s)} s`,
    p.max_green_s / scale > 0.06 ? `${Math.round(p.max_green_s)}` : '')
    + seg('seg-y', p.yellow, `Yellow ${f1(p.yellow)} s`) + seg('seg-r', p.red, `All-red ${f1(p.red)} s`)).join('');
  const label = list.map(p => `phase ${p.phase} green ${f1(p.max_green_s)} s`).join('; ');
  return `<div class="cbar ${which}" style="width:${cycle / scale * 100}%" role="img" aria-label="${which === 'old' ? 'Current' : 'Proposed'} cycle ${f1(cycle)} seconds: ${esc(label)}">${body}</div>`;
}
const LEGEND_PHASE = '<div class="legend"><span><i class="sw g"></i>Green</span><span><i class="sw y"></i>Yellow</span><span><i class="sw r"></i>All-red</span></div>';
const LEGEND_ARMS = d => `<div class="legend"><span><i class="ln base"></i>Current</span><span><i class="ln prop"></i>${propName(d)}</span></div>`;

function by15Panel(d, rows, keys, viewKey, title, w = 640, drill = '') {
  if (!Array.isArray(rows) || !rows.length) return '';
  const avail = keys.filter(([k]) => rows.some(r => ok(r.baseline?.[k]) || ok(r.proposed?.[k])));
  if (!avail.length) return '';
  const cur = avail.find(([k]) => k === view[viewKey]) || avail[0], [k, name, unit] = cur;
  const chart = lineChart({
    labels: rows.map(r => r.t), unit, w, label: `${title}: ${name} by 15 minutes, current and ${propName(d).toLowerCase()} timing`,
    series: [{ name: 'Current', cls: 's-base', values: rows.map(r => r.baseline?.[k]) }, { name: propName(d), cls: 's-prop', values: rows.map(r => r.proposed?.[k]) }],
  });
  return panel(`${esc(title)}`, `${chart}${drill ? `<div class="panel-f">${drill}</div>` : ''}`, { anchor: 'by15', tools: `${LEGEND_ARMS(d)}${avail.length > 1 ? toggle(viewKey, 'Measure', avail.map(([a, b]) => [a, b]), k) : ''}` });
}

/* ---------- 1 · Corridors ---------- */

function corridorsScreen(ds, ctx) {
  const roads = [...ctx.map(r => ({ ...r, context: true })), ...ds.map(d => ({
    road: d.road, street: d.info.street, points: d.info.points, status: STATUS[statusKey(d)][0], cls: STATUS[statusKey(d)][1] }))];
  const nSig = ds.reduce((a, d) => a + d.card.signals.length, 0);
  const inbox = ds.map(d => {
    const h = heldout(d), change = isChange(d);
    return `<li class="inbox-item${statusKey(d) === 'pending' ? ' unread' : ''}">
      <div class="inbox-top">${pill(d)}<span class="meta-line">${esc(window_(d))}</span></div>
      <h3><a href="${go(d.road, 'review')}">${esc(d.info.street)} · ${change ? 'new PM peak timing' : 'keep current timing'}</a></h3>
      <div class="inbox-facts">${change
        ? `<span>${dl(go(d.road, 'review', { p: 'impact' }), `<b class="good-t">${pct(h.oldMean, h.planMean)}</b>`)} ${term('score', 'delay score')}</span><span>better on ${dl(go(d.road, 'review', { p: 'impact' }), betterOn(h))} ${term('heldout', 'test evenings')}</span><span>${dl(go(d.road, '', { p: 'signals' }), `${d.card.signals.length} signals`)}</span>`
        : `<span>Candidate ${term('jammed', 'jammed')} in ${dl(go(d.road, 'review', { p: 'impact' }), `<b>${jams(d).jammed} of ${jams(d).n}</b>`)} practice runs</span><span>${dl(go(d.road, '', { p: 'signals' }), `${d.card.signals.length} signals`)}</span>`}</div>
    </li>`;
  }).join('');
  const withM = ds.some(d => d.m?.corridor);
  const mcell = (d, f, dp, unit, v) => { const c = d.m?.corridor, b = c && f(c.baseline || {}), p = c && f(c.proposed || {});
    return `<td class="n">${ok(b) && ok(p) ? dl(go(d.road, '', { p: 'by15', c15: v }), Math.abs(p - b) < 1e-9 ? `${fmt(b, dp)}<small>${unit}</small>` : `${cmp(b, p, dp, unit)} ${delta(b, p)}`) : '<span class="na">–</span>'}</td>`; };
  const rows = ds.map(d => {
    const h = heldout(d), change = Math.abs(h.planMean - h.oldMean) > 1e-6, imp = go(d.road, 'review', { p: 'impact' });
    return `<tr><td><a class="strong" href="${go(d.road)}">${esc(d.info.street)}</a></td><td>${dl(go(d.road, 'review', { p: 'decision' }), pill(d))}</td><td class="n">${dl(go(d.road, '', { p: 'signals' }), d.card.signals.length)}</td>
      <td class="n">${change ? dl(imp, `${cmp(h.oldMean, h.planMean, 0, 's')} ${delta(h.oldMean, h.planMean)}`) : dl(imp, '<span class="na">No change</span>')}</td>
      <td class="n">${dl(imp, change ? `${cmp(h.unfOld, h.unfPlan)} ${delta(h.unfOld, h.unfPlan)}` : fmt(h.unfOld))}</td>
      ${withM ? [mcell(d, c => c.travel_time_s?.NB, 0, 's', 'tt_nb_s'), mcell(d, c => c.travel_time_s?.SB, 0, 's', 'tt_sb_s')].join('') : ''}
      <td class="nw">${dl(imp, `${h.n} evenings`)}</td>
      <td class="n"><a class="chev" href="${go(d.road)}" aria-label="Open ${esc(d.info.street)}">›</a></td></tr>`;
  }).join('');
  const first = ds.find(d => statusKey(d) === 'pending') || ds[0];
  return `<div class="page">
    ${head('Corridors', { meta: [`${ds.length} corridors`, `${nSig} signals`, `PM peak ${esc(window_(ds[0]))}`, 'SUMO simulation'],
      actions: `<a class="btn primary" href="${go(first.road)}">Open ${esc(first.info.street)} ›</a>` })}
    <div class="grid g-map">
      ${panel('Map', cityMap(roads), { tools: '<div class="legend"><span><i class="ln prop"></i>Recommendation</span><span><i class="ln calm"></i>No change</span><span><i class="ln ctx"></i>Training road</span></div>' })}
      ${panel(`Inbox <span class="count">${ds.filter(d => statusKey(d) === 'pending').length}</span>`, `<ul class="inbox">${inbox}</ul>`)}
    </div>
    ${panel('All corridors', `<table class="tbl"><thead><tr><th>Corridor</th><th>Status</th><th class="n">Signals</th>
      <th class="n">${term('score', 'Delay score')}</th><th class="n">${term('unfinished', 'Unfinished trips')}</th>${withM ? '<th class="n">Travel time NB</th><th class="n">Travel time SB</th>' : ''}<th>${term('heldout', 'Analysed')}</th><th class="n"><span class="sr">Open</span></th></tr></thead><tbody>${rows}</tbody></table>`)}
  </div>`;
}

/* ---------- 2 · Corridor ---------- */

function kpiPanel(d) {
  const h = heldout(d), c = d.m?.corridor, b = c?.baseline || {}, p = c?.proposed || {};
  const imp = go(d.road, 'review', { p: 'impact' }), by = v => go(d.road, '', { p: 'by15', c15: v });
  // Seed-200 totals with no 15-minute series are explained by watching that evening (Wolfe) or the corridor chart.
  const sim = d.road === 'wolfe' ? '#/wolfe/simulate' : by('delay_s');
  const test = [kpi(term('score', 'Delay score'), h.oldMean, h.planMean, 0, 's', imp), kpi(term('unfinished', 'Unfinished trips'), h.unfOld, h.unfPlan, 0, '', imp),
    isChange(d) ? `<div class="kpi"><div class="kpi-l">Better on</div><a class="kpi-v dl" href="${imp}"><span class="p">${h.better}</span><small>of ${h.n}</small></a><div class="kpi-b">evenings</div></div>` : ''].join('');
  const seed = c ? [kpi(term('score', 'Delay per car'), b.avg_delay_s_per_veh, p.avg_delay_s_per_veh, 1, 's', by('delay_s')), kpi('Stops per car', b.stops_per_veh, p.stops_per_veh, 2, '', sim),
    kpi('Travel time NB', b.travel_time_s?.NB, p.travel_time_s?.NB, 0, 's', by('tt_nb_s')), kpi('Travel time SB', b.travel_time_s?.SB, p.travel_time_s?.SB, 0, 's', by('tt_sb_s')),
    kpi('CO₂', b.co2_kg, p.co2_kg, 0, 'kg', sim)].join('') : '';
  return `<section class="panel kpis" id="kpis" tabindex="-1" aria-label="Key results, current vs ${propName(d).toLowerCase()}">
    <div class="kpi-group"><h2 class="kpi-h">${term('heldout', `Held-out test · ${h.n} evenings`)}</h2><div class="kpi-row">${test}</div></div>
    ${seed ? `<div class="kpi-group"><h2 class="kpi-h">Seed ${esc((d.m.seeds || []).join(', '))} · ${propName(d).toLowerCase()} vs current</h2><div class="kpi-row">${seed}</div></div>` : ''}
  </section>`;
}

function signalsTable(d) {
  const any = d.card.signals.some(s => metricSignal(d, s));
  const lead = ms => ms?.approaches?.find(a => a.approach === ms.pcd?.approach) || ms?.approaches?.[0];
  return `<table class="tbl"><thead><tr><th class="n">#</th><th>Signal</th><th class="n">${term('cycle', 'Cycle')} s</th><th class="n">${term('offset', 'Offset')} s</th>
    ${any ? `<th class="n">${term('aog', 'AOG')} %</th><th class="n">Delay s</th>` : ''}<th class="n"><span class="sr">Open</span></th></tr></thead>
    <tbody>${d.card.signals.map((s, i) => {
      const a = lead(metricSignal(d, s)), sp = `signal/${i + 1}`, timing = go(d.road, sp, { p: 'timing' }), appr = go(d.road, sp, { p: 'approaches' });
      return `<tr><td class="n"><span class="badge">${i + 1}</span></td><td><a class="strong" href="${go(d.road, sp)}">${esc(s.signal)}</a></td>
        <td class="n">${dl(timing, sameOr(s.old.cycle_s, s.new.cycle_s))}</td><td class="n">${dl(timing, sameOr(s.old.offset_s, s.new.offset_s))}</td>
        ${any ? `<td class="n">${a ? dl(go(d.road, sp, { p: 'pcd' }), cmp(a.baseline?.aog_pct, a.proposed?.aog_pct)) : cmp()}</td><td class="n">${a ? dl(appr, cmp(a.baseline?.avg_delay_s, a.proposed?.avg_delay_s, 1)) : cmp()}</td>` : ''}
        <td class="n"><a class="chev" href="#/${d.road}/signal/${i + 1}" aria-label="Open ${esc(s.signal)}">›</a></td></tr>`;
    }).join('')}</tbody></table>`;
}

function timeSpacePanel(d) {
  const ts = d.m?.time_space, sigs = d.m?.signals;
  if (!ts || !Array.isArray(ts.window_s) || !Array.isArray(sigs)) return '';
  const arm = ts[view.ts] ? view.ts : 'baseline', side = ts[arm];
  if (!side?.green || !side?.trajectories) return '';
  const opts = [['baseline', 'Current'], ['proposed', propName(d)]].filter(([k]) => ts[k]?.green);
  return panel(`${term('ts', 'Time-space diagram')} <span class="h-sub">${clock(ts.window_s[0])}–${clock(ts.window_s[1])}</span>`,
    timeSpace(side, sigs, `Time-space diagram, ${arm === 'baseline' ? 'current' : propName(d).toLowerCase()} timing`, ts.window_s,
      s => { const i = d.card.signals.findIndex(c => c.sumo_tls_id === s.id); return i < 0 ? '' : go(d.road, `signal/${i + 1}`, { p: 'timing' }); }),
    { anchor: 'ts', tools: `<div class="legend"><span><i class="ln green"></i>Green</span><span><i class="ln red"></i>Red</span><span><i class="ln nb"></i>NB car</span><span><i class="ln sb"></i>SB car</span></div>${toggle('ts', 'Timing', opts, arm)}` });
}

function corridorScreen(d) {
  const len = d.m?.corridor?.length_m;
  const actions = `<a class="btn" href="${go(d.road, 'review')}">${isChange(d) ? 'Review recommendation' : 'Open recommendation'}</a>
    <a class="btn primary" href="${go(d.road, 'signal/1')}">Inspect signals ›</a>`;
  const drill = d.road === 'wolfe' ? '<a class="btn sm ghost" href="#/wolfe/simulate">Watch this evening ›</a>' : `<a class="btn sm ghost" href="${go(d.road, 'review', { p: 'impact' })}">Why keep current ›</a>`;
  return `<div class="page">
    ${crumbs([['Corridors', '#/corridors'], [d.info.street]])}
    ${head(d.info.street, { status: pill(d), meta: [`${d.card.signals.length} signals`, ok(len) ? `${fmt(len / 1000, 2)} km` : '', `PM peak ${esc(window_(d))}`, d.m?.source ? `<span class="term" tabindex="0">SUMO simulation<span class="tip wide" role="tooltip">${esc(d.m.source)}</span></span>` : 'SUMO simulation'], actions })}
    ${kpiPanel(d)}
    <div class="grid g-2">
      ${panel('Signals', `<div class="map strip" data-road="${d.road}" data-along data-links role="group" aria-label="Map of ${esc(d.info.street)}, north on the left, signals numbered 1 to ${d.card.signals.length}."></div>${signalsTable(d)}`, { anchor: 'signals' })}
      ${by15Panel(d, d.m?.corridor?.by15, [['delay_s', 'Delay', 's'], ['queue_veh', 'Queue', 'veh'], ['tt_nb_s', 'Travel time NB', 's'], ['tt_sb_s', 'Travel time SB', 's']], 'c15', 'By 15 minutes', 640, drill)}
    </div>
    ${timeSpacePanel(d)}
  </div>`;
}

/* ---------- 3 · Signal ---------- */

function timingSheet(d, sig) {
  const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
  const scale = Math.max(sig.old.cycle_s, sig.new.cycle_s);
  const dlt = (a, b) => Math.abs(b - a) < 0.05 ? '<span class="na">–</span>' : `<span class="delta ${b > a ? 'up' : 'down'}">${signed(b - a, 1)}</span>`;
  return `<dl class="kv">
      <div><dt>${term('cycle', 'Cycle')}</dt><dd>${sameOr(sig.old.cycle_s, sig.new.cycle_s)} <small>s</small></dd></div>
      <div><dt>${term('offset', 'Offset')}</dt><dd>${sameOr(sig.old.offset_s, sig.new.offset_s)} <small>s</small></dd></div>
      <div><dt>Plan</dt><dd>${dl(go(d.road, 'deploy', { p: 'rollout' }), `PM peak ${esc(window_(d))}`)}</dd></div>
      <div><dt>Controller</dt><dd class="mono" title="${esc(sig.sumo_tls_id)}">${dl(go(d.road, 'deploy', { p: 'controllers' }), esc(sig.sumo_tls_id))}</dd></div></dl>
    <div class="cycles"><span class="k">Current</span>${bar(old, sig.old.cycle_s, scale, 'old')}<span class="c num">${f1(sig.old.cycle_s)} s</span>
      <span class="k">${planName(d)}</span>${bar(neu, sig.new.cycle_s, scale, 'new')}<span class="c num strong">${f1(sig.new.cycle_s)} s</span></div>
    <table class="tbl sheet-t"><thead><tr><th rowspan="2">Phase</th><th rowspan="2">${term('mv', 'Movements')}</th><th class="n" rowspan="2">Min green</th>
      <th class="n grp" colspan="3">Max green</th><th class="n" rowspan="2">Yellow</th><th class="n" rowspan="2">All-red</th><th class="n grp" colspan="2">${term('split', 'Split')}</th></tr>
      <tr><th class="n">Now</th><th class="n">Plan</th><th class="n">Δ</th><th class="n">Now</th><th class="n">Plan</th></tr></thead>
    <tbody>${old.map((p, i) => `<tr><td class="n">${p.phase}</td><td>${moves(p.serves)}</td><td class="n">${f1(p.min_green_s)}</td>
      <td class="n">${f1(p.max_green_s)}</td><td class="n strong">${f1(neu[i].max_green_s)}</td><td class="n">${dlt(p.max_green_s, neu[i].max_green_s)}</td>
      <td class="n">${f1(p.yellow)}</td><td class="n">${f1(p.red)}</td><td class="n">${f1(p.split)}</td><td class="n strong">${f1(neu[i].split)}</td></tr>`).join('')}</tbody></table>
    ${sig.reason && isChange(d) ? `<p class="reason"><span>Reason</span>${esc(sig.reason.replace(/\b([NSEW]):([LRT]+)/g, (_, leg, t) => `${BOUND[leg]} ${t}`))}</p>` : ''}`;
}

// Each cell links to what explains it: PCD for arrivals on green (its approach only), the timing sheet for volume and split
// failures (the plan's reason and splits), the signal's 15-minute chart for delay and queue.
function approachTable(d, ms, i) {
  const rows = ms?.approaches;
  if (!Array.isArray(rows) || !rows.length) return '';
  const sp = `signal/${i + 1}`, timing = go(d.road, sp, { p: 'timing' }), by = v => go(d.road, sp, { p: 'by15', s15: v });
  const pcdOf = r => r.approach === ms.pcd?.approach ? go(d.road, sp, { p: 'pcd' }) : by('aog_pct');
  const cols = [['volume_vph', 'Volume', 'vph', 0, () => timing], ['aog_pct', term('aog', 'AOG'), '%', 0, pcdOf], ['split_failures', term('sf', 'Split fail.'), '', 0, () => timing],
    ['avg_delay_s', 'Delay', 's', 1, () => by('delay_s')], ['max_queue_veh', 'Max queue', 'veh', 0, () => by('queue_veh')]]
    .filter(([k]) => rows.some(r => ok(r.baseline?.[k])));
  return `<table class="tbl compact"><thead><tr><th>Approach</th>${cols.map(([, t, u]) => `<th class="n">${t}${u ? ` <small>${u}</small>` : ''}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr><td class="strong">${dl(pcdOf(r), esc(r.approach), `${r.approach} approach: ${r.approach === ms.pcd?.approach ? 'coordination diagram' : 'by 15 minutes'}`)}</td>${cols.map(([k, , , dp, href]) => `<td class="n">${ok(r.baseline?.[k]) ? dl(href(r), k === 'volume_vph' && r.baseline?.[k] === r.proposed?.[k] ? fmt(r.baseline[k]) : cmp(r.baseline?.[k], r.proposed?.[k], dp)) : cmp()}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function pcdPanel(d, ms) {
  const p = ms?.pcd;
  if (!p || (!p.baseline?.arrivals?.length && !p.proposed?.arrivals?.length)) return '';
  const a = ms.approaches?.find(x => x.approach === p.approach);
  const one = (k, name) => p[k]?.arrivals?.length ? `<figure class="pcd-fig"><figcaption><b>${name}</b>${ok(a?.[k]?.aog_pct) ? `<span>${term('aog', 'AOG')} ${fmt(a[k].aog_pct)}%</span>` : ''}<span>${fmt(p[k].arrivals.length)} arrivals</span></figcaption>
    ${pcd(p[k], `Purdue Coordination Diagram, ${esc(p.approach || '')} approach, ${name.toLowerCase()} timing`)}</figure>` : '';
  return panel(`${term('pcd', 'Purdue Coordination Diagram')}${p.approach ? ` <span class="h-sub">${esc(p.approach)} approach</span>` : ''}`,
    `<div class="pcd-pair">${one('baseline', 'Current')}${one('proposed', propName(d))}</div>`,
    { anchor: 'pcd', tools: '<div class="legend"><span><i class="sw gband"></i>Green</span><span><i class="dot"></i>Car arrival</span></div>' });
}

function signalScreen(d, i) {
  const sig = d.card.signals[i], ms = metricSignal(d, sig), n = d.card.signals.length;
  const nav = `${i > 0 ? `<a class="btn" href="${go(d.road, `signal/${i}`)}" aria-label="Previous signal: ${esc(d.card.signals[i - 1].signal)}">‹ Prev</a>` : ''}
    ${i < n - 1 ? `<a class="btn" href="${go(d.road, `signal/${i + 2}`)}" aria-label="Next signal: ${esc(d.card.signals[i + 1].signal)}">Next ›</a>` : ''}
    <a class="btn primary" href="${go(d.road, 'review')}">${isChange(d) ? 'Review recommendation' : 'Open recommendation'} ›</a>`;
  return `<div class="page">
    ${crumbs([['Corridors', '#/corridors'], [d.info.street, `#/${d.road}`], [sig.signal]])}
    ${head(sig.signal, { status: `<span class="badge lg">${i + 1}</span>`, meta: [`Signal ${i + 1} of ${n}`, dl(go(d.road), esc(d.info.street)), `${sig.old.greens.length} phases`], actions: nav })}
    <div class="grid g-sig">
      ${panel('Timing sheet', timingSheet(d, sig), { tools: LEGEND_PHASE, anchor: 'timing' })}
      <div class="col">
        ${panel('Location', `<div class="map loc" data-road="${d.road}" data-pick="${i}" data-along data-links role="group" aria-label="Map of ${esc(d.info.street)} with ${esc(sig.signal)} highlighted."></div>`)}
        ${panel('Approaches', approachTable(d, ms, i), { tools: LEGEND_ARMS(d).replace('legend', 'legend txt'), anchor: 'approaches' })}
      </div>
    </div>
    ${pcdPanel(d, ms)}
    ${by15Panel(d, ms?.by15, [['delay_s', 'Delay', 's'], ['queue_veh', 'Queue', 'veh'], ['aog_pct', 'AOG', '%']], 's15', 'By 15 minutes', 1120)}
  </div>`;
}

/* ---------- 4 · Recommendation review ---------- */

function diffTable(d) {
  const scale = Math.max(...d.card.signals.flatMap(s => [s.old.cycle_s, s.new.cycle_s]));
  return `<table class="tbl diff"><thead><tr><th class="n">#</th><th>Signal</th><th class="n">${term('cycle', 'Cycle')} s</th><th class="n">${term('offset', 'Offset')} s</th>
    <th>Max green by phase, s</th><th class="w-bars">One cycle</th><th class="n"><span class="sr">Evidence</span></th></tr></thead>
    <tbody>${d.card.signals.map((s, i) => {
      const old = phases(d, s, 'old'), neu = phases(d, s, 'new');
      const greens = old.map((p, k) => {
        const a = p.max_green_s, b = neu[k].max_green_s, same = Math.abs(a - b) < 0.05;
        return `<span class="chip${same ? ' same' : ''}" title="Phase ${p.phase}: ${esc(serves(p.serves))}"><b>Φ${p.phase}</b> ${same ? f1(a) : `${f1(a)} → ${f1(b)}`}${same ? '' : ` <i class="${b > a ? 'up' : 'down'}">${signed(b - a, 1)}</i>`}</span>`;
      }).join('');
      const timing = go(d.road, `signal/${i + 1}`, { p: 'timing' });
      return `<tr><td class="n"><span class="badge">${i + 1}</span></td><td><a class="strong" href="${go(d.road, `signal/${i + 1}`)}">${esc(s.signal)}</a></td>
        <td class="n">${dl(timing, sameOr(s.old.cycle_s, s.new.cycle_s))}</td><td class="n">${dl(timing, sameOr(s.old.offset_s, s.new.offset_s))}</td>
        <td><a class="chips dl" href="${timing}" aria-label="Timing sheet: ${esc(s.signal)}">${greens}</a></td>
        <td class="w-bars"><a class="mini dl" href="${timing}" aria-label="Cycle bars: ${esc(s.signal)}">${bar(old, s.old.cycle_s, scale, 'old')}${bar(neu, s.new.cycle_s, scale, 'new')}</a></td>
        <td class="n"><a class="chev" href="#/${d.road}/signal/${i + 1}" aria-label="Signal page: ${esc(s.signal)}">›</a></td></tr>`;
    }).join('')}</tbody></table>`;
}

function impactRows(rows) {
  const vals = rows.flatMap(r => [r.lo, r.hi, r.mid]).filter(ok), domain = [Math.min(-10, ...vals) - 4, Math.max(10, ...vals) + 4];
  return `<table class="tbl impact"><tbody>${rows.map(r => `<tr><th scope="row">${r.label}<small>${r.sub}</small></th>
    <td class="n big ${r.mid < 0 ? 'good-t' : 'bad-t'}">${signed(Math.round(r.mid))}%</td>
    <td>${ok(r.lo) ? rangeBar({ ...r, domain }) : ''}<small class="rng">${ok(r.lo) ? `${signed(Math.round(r.lo))}% to ${signed(Math.round(r.hi))}%` : ''}</small></td></tr>`).join('')}</tbody></table>`;
}

// The runs behind every impact number: the practice-copy range is the min and max of these rows; the held-out means average the test rows.
function eachEvening(d) {
  const p = d.practice, margin = p.settings.teleport_margin;
  const tbl = (cap, cols, rows) => `<table class="tbl compact"><caption>${cap}</caption><thead><tr>${cols.map((c, i) => `<th${i ? ' class="n"' : ''}>${c}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td${i ? ' class="n"' : ''}>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  const practice = tbl(`${term('practice', 'Practice copy')} · ${isChange(d) ? 'plan' : 'candidate'}`, ['Evening', 'Delay score s', 'Change', term('jammed', 'Stuck cars removed')],
    p.confirm_old.map((o, i) => { const n = p.confirm_new[i], jam = n.teleports > o.teleports + margin;
      return [o.seed, cmp(o.all_requested_delay_s, n.all_requested_delay_s), delta(o.all_requested_delay_s, n.all_requested_delay_s), `${cmp(o.teleports, n.teleports)}${jam ? ' <span class="pill bad">Jammed</span>' : ''}`]; }));
  const row = (arm, s) => d.results.find(r => r.road === d.road && r.arm === arm && r.seed === s);
  const test = isChange(d) ? tbl(term('heldout', 'Held-out test'), ['Evening', 'Delay score s', 'Change', 'Unfinished', 'Worst-off s'], heldout(d).seeds.map(s => {
    const o = row('old', s), n = row('learner', s), v = k => [Number(o[k]), Number(n[k])];
    return [s, cmp(...v('all_requested_delay_s')), delta(...v('all_requested_delay_s')), cmp(...v('unfinished')), cmp(...v('worst_origin_delay_s'))];
  })) : '';
  return `<details class="each"${route.p === 'impact' ? ' open' : ''}><summary>Each evening</summary><div class="each-grid">${practice}${test}</div></details>`;
}

function impactPanel(d) {
  const e = d.card.expected_in_copy, h = heldout(d), per = h.per.map(p => p.v);
  if (!isChange(d)) {
    const j = jams(d), ph = d.posthoc;
    return panel('Why keep current timing', `${impactRows([
      { label: `${term('practice', 'Practice copy')}`, sub: `candidate · ${e.copy_seeds.length} evenings`, mid: e.change_share * 100, lo: e.change_range_s[0] / e.old_delay_s * 100, hi: e.change_range_s[1] / e.old_delay_s * 100 },
      ...(ph ? [{ label: term('posthoc', 'Post-hoc check'), sub: `candidate · ${ph.seeds.length} evenings`, mid: ph.change_share * 100 }] : [])])}
      <dl class="facts">
        <div><dt>${term('jammed', 'Jam check')}</dt><dd><span class="bad-t strong">Failed</span> · jammed in ${j.jammed} of ${j.n} practice runs</dd></div>
        ${ph ? `<div><dt>Worse on</dt><dd>${ph.seeds_worse} of ${ph.seeds.length} post-hoc evenings</dd></div>` : ''}
        <div><dt>Decision</dt><dd>Keep current timing at all ${d.card.signals.length} signals</dd></div></dl>${eachEvening(d)}`, { anchor: 'impact' });
  }
  return panel('Expected impact', `${impactRows([
    { label: term('practice', 'Practice copy'), sub: `forecast · ${e.copy_seeds.length} evenings`, mid: e.change_share * 100, lo: e.change_range_s[0] / e.old_delay_s * 100, hi: e.change_range_s[1] / e.old_delay_s * 100 },
    { label: term('heldout', 'Held-out test'), sub: `${h.n} evenings · better on ${betterOn(h)}`, mid: share(h.oldMean, h.planMean) * 100, lo: Math.min(...per), hi: Math.max(...per) }])}
    <dl class="facts">
      <div><dt>${term('score', 'Delay score')}</dt><dd>${cmp(h.oldMean, h.planMean, 0, 's')}</dd></div>
      <div><dt>${term('unfinished', 'Unfinished trips')}</dt><dd>${cmp(h.unfOld, h.unfPlan)} ${delta(h.unfOld, h.unfPlan)}</dd></div>
      <div><dt>${term('worst', 'Worst-off group')}</dt><dd>${cmp(h.worstOld, h.worstPlan, 0, 's')} ${delta(h.worstOld, h.worstPlan)}</dd></div></dl>${eachEvening(d)}`, { anchor: 'impact' });
}

function decisionPanel(d) {
  const s = statusKey(d), x = dec(d), note = drafts[d.road] ?? '';
  const when = x.when ? new Date(x.when).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '';
  if (!isChange(d)) {
    return panel('Decision', s === 'acknowledged'
      ? `<p class="done"><b>Acknowledged</b> · ${new Date(x.at).toLocaleTimeString()}</p><div class="row"><a class="btn primary" href="#/corridors">Back to corridors</a><button class="btn ghost" data-action="reopen">Undo</button></div>`
      : `<div class="row"><button class="btn primary" data-action="acknowledge">Acknowledge · keep current</button></div>`);
  }
  if (s !== 'pending') {
    const next = { approved: `<a class="btn primary" href="#/wolfe/simulate?run">Run side-by-side simulation</a><a class="btn" href="#/${d.road}/deploy">Deploy &amp; monitor</a>`,
      scheduled: `<a class="btn primary" href="#/${d.road}/deploy">Deploy &amp; monitor</a>`, deployed: `<a class="btn primary" href="#/${d.road}/deploy">Monitor</a>`,
      rolled_back: `<a class="btn" href="#/${d.road}/deploy">Deploy &amp; monitor</a>`, rejected: '' }[s];
    return panel('Decision', `<div class="done" role="status">${pill(d)}<span>${new Date(x.at).toLocaleTimeString()}</span>${when ? `<span>for ${esc(when)}</span>` : ''}</div>
      ${x.note ? `<blockquote class="note-q">${esc(x.note)}</blockquote>` : ''}
      <div class="row">${next}${['approved', 'scheduled', 'rejected'].includes(s) ? '<button class="btn ghost" data-action="reopen">Reopen</button>' : ''}</div>`);
  }
  return panel('Decision', `<label class="field" for="note">Notes</label>
    <textarea id="note" maxlength="500" data-road="${d.road}" placeholder="Kept with the decision in the audit log">${esc(note)}</textarea>
    ${form === 'schedule' ? `<div class="sched"><label class="field" for="when">Deploy on</label><input id="when" type="datetime-local" required>
      <div class="row"><button class="btn primary" data-action="schedule-confirm">Confirm schedule</button><button class="btn ghost" data-action="cancel">Cancel</button></div>
      <p class="error-t" id="when-err" role="alert" hidden>Pick a date and time.</p></div>`
      : `<div class="row decide"><button class="btn primary" data-action="approve">Approve</button><button class="btn" data-action="schedule">Schedule</button><button class="btn danger" data-action="reject">Reject</button></div>`}`);
}

function reviewScreen(d) {
  const ev = `<ul class="links">${d.card.signals.map((s, i) => `<li><a href="#/${d.road}/signal/${i + 1}"><span class="badge">${i + 1}</span>${esc(s.signal)}</a></li>`).join('')}
    <li><a href="#/${d.road}">Corridor · ${esc(d.info.street)}</a></li>${d.road === 'wolfe' ? '<li><a href="#/wolfe/simulate">Side-by-side simulation</a></li>' : ''}
    <li><a href="../cards/${d.road}.md">Engineer card (text)</a></li></ul>`;
  return `<div class="page">
    ${crumbs([['Corridors', '#/corridors'], [d.info.street, `#/${d.road}`], ['Recommendation']])}
    ${head(`${d.info.street} · ${isChange(d) ? 'new PM peak timing' : 'keep current timing'}`, { status: pill(d),
      meta: [`${d.card.signals.length} signals`, `PM peak ${esc(window_(d))}`, 'Phase order, yellow, all-red, min greens unchanged'],
      actions: isChange(d) ? '<button class="btn" data-action="print">Download timing sheet</button>' : '' })}
    <div class="grid g-review">
      <div class="col">${panel(isChange(d) ? 'Changes by signal' : 'Timing by signal', diffTable(d), { tools: LEGEND_PHASE, anchor: 'changes' })}${impactPanel(d)}</div>
      <div class="col" id="decision" tabindex="-1">${decisionPanel(d)}${panel('Evidence', ev)}</div>
    </div>
  </div>`;
}

function sheet(d) {
  const x = dec(d), at = x.status === 'approved' || x.status === 'scheduled' ? new Date(x.at).toLocaleString() : 'Not approved yet';
  const ch = (a, b) => Math.abs(a - b) < 0.05 ? f1(a) : `${f1(a)} → ${f1(b)}`;
  return `<section class="sheet">
    <div class="sheet-head"><div><h2>Timing change sheet</h2><p class="small muted">Signal Learner · simulation result, not city timing</p></div><span class="stamp">Draft for engineer entry</span></div>
    <dl><dt>Road</dt><dd>${esc(d.info.street)}, ${d.card.signals.length} intersections</dd>
      <dt>Plan</dt><dd>PM peak, ${esc(d.info.begin)}–${esc(d.info.end)}</dd>
      <dt>Approved</dt><dd>${esc(at)} (in this console)</dd>
      <dt>Unchanged</dt><dd>Phase order, yellow, all-red and minimum greens</dd></dl>
    ${d.card.signals.map(sig => {
      const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
      return `<div class="int"><h3>${esc(sig.signal)}</h3>
        <p class="small">Cycle ${ch(sig.old.cycle_s, sig.new.cycle_s)} s · Offset ${ch(sig.old.offset_s, sig.new.offset_s)} s</p>
        <table><thead><tr><th>Phase</th><th>Movements</th><th class="n">Min green</th><th class="n">Max green</th><th class="n">Yellow</th><th class="n">All-red</th><th class="n">Split</th></tr></thead><tbody>
        ${old.map((p, i) => `<tr><td>${p.phase}</td><td>${esc(serves(p.serves))}</td><td class="n">${f1(p.min_green_s)}</td><td class="n">${ch(p.max_green_s, neu[i].max_green_s)}</td>
          <td class="n">${f1(p.yellow)}</td><td class="n">${f1(p.red)}</td><td class="n">${ch(p.split, neu[i].split)}</td></tr>`).join('')}
        </tbody></table></div>`;
    }).join('')}
    <p class="small muted" style="margin-top:12px">Seconds. Split = max green + yellow + all-red. Phase numbers come from the simulation; match them to the controller's phases when entering.</p>
    <div class="sign"><div>Reviewed by (traffic engineer)</div><div>Entered into controller / central system by</div><div>Date entered</div></div>
  </section>`;
}

/* ---------- 6 · Deploy & monitor ---------- */

// Where each logged action can be seen.
const actionHref = r => /simulation/.test(r.action) ? '#/wolfe/simulate' : /Deployed|Rolled back/.test(r.action) ? go(r.road, 'deploy', { p: 'controllers' }) : go(r.road, 'review', { p: 'decision' });

function auditPanel() {
  const rows = [...state.log].reverse();
  const name = r => cache[r]?.info.street || r;
  return panel(`Audit log <span class="count">${rows.length}</span>`, rows.length
    ? `<table class="tbl"><thead><tr><th>Time</th><th>Corridor</th><th>Action</th><th>Note</th></tr></thead><tbody>${rows.map(r =>
      `<tr><td class="num">${new Date(r.at).toLocaleTimeString()}</td><td>${dl(go(r.road), esc(name(r.road)))}</td><td class="strong">${dl(actionHref(r), esc(r.action))}</td><td>${esc(r.note || '')}</td></tr>`).join('')}</tbody></table>`
    : '<p class="empty">No actions yet this session</p>', { anchor: 'audit', tools: '<button class="btn sm ghost" data-action="reset">Reset demo</button>' });
}

function deployScreen(d) {
  const s = statusKey(d), n = d.card.signals.length, sigs = d.card.signals;
  const ctlStatus = { deployed: ['New plan', 'live'], rolled_back: ['Rolled back', 'bad'] }[s] || (isChange(d) ? ['Waiting', 'calm'] : ['Current kept', 'calm']);
  const actions = !isChange(d) ? `<a class="btn" href="${go(d.road, 'review')}">Open recommendation</a>`
    : s === 'deployed' ? '<button class="btn danger" data-action="rollback">Roll back</button>'
      : ['approved', 'scheduled', 'rolled_back'].includes(s) ? `<button class="btn primary" data-action="deploy">${s === 'rolled_back' ? 'Deploy again' : `Deploy to ${n} controllers`}</button>`
        : `<a class="btn primary" href="#/${d.road}/review">Review recommendation</a>`;
  const steps = [['Review', true], ['Approve', !['pending', 'rejected'].includes(s)], ['Deploy', ['deployed', 'rolled_back'].includes(s)], ['Watch', s === 'deployed']];
  const stepper = isChange(d) ? `<ol class="steps" aria-label="Progress">${steps.map(([t, on]) => `<li class="${on ? 'on' : ''}">${t}</li>`).join('')}</ol>` : '';
  const sig0 = sigs[0];
  const plan = isChange(d) ? `<table class="tbl"><thead><tr><th>Time-of-day plan</th><th>Window</th><th class="n">${term('cycle', 'Cycle')} s</th><th>Controllers</th></tr></thead><tbody>
      <tr><td class="strong">PM peak · Signal Learner</td><td>${esc(window_(d))}</td><td class="n">${dl(go(d.road, 'review', { p: 'changes' }), f1(sig0.new.cycle_s))}</td><td>${dl(go(d.road, 'deploy', { p: 'controllers' }), `${n} of ${n}`)}</td></tr>
      <tr><td>All other times</td><td>–</td><td class="n na">unchanged</td><td>–</td></tr></tbody></table>`
    : '<p class="empty">Nothing to deploy · current timing kept</p>';
  const ctl = `<table class="tbl"><thead><tr><th class="n">#</th><th>Intersection</th><th>Controller</th><th class="n">${term('cycle', 'Cycle')} s</th><th class="n">${term('offset', 'Offset')} s</th><th>Status</th></tr></thead>
    <tbody>${sigs.map((x, i) => { const timing = go(d.road, `signal/${i + 1}`, { p: 'timing' }); return `<tr><td class="n"><span class="badge">${i + 1}</span></td><td><a class="strong" href="${go(d.road, `signal/${i + 1}`)}">${esc(x.signal)}</a></td>
      <td class="mono" title="${esc(x.sumo_tls_id)}">${esc(x.sumo_tls_id)}</td><td class="n">${dl(timing, sameOr(x.old.cycle_s, x.new.cycle_s))}</td><td class="n">${dl(timing, sameOr(x.old.offset_s, x.new.offset_s))}</td>
      <td><span class="pill ${ctlStatus[1]}">${ctlStatus[0]}</span></td></tr>`; }).join('')}</tbody></table>`;
  let watch = '';
  if (isChange(d)) {
    const e = d.card.expected_in_copy, h = heldout(d), g = goBack(d), per = h.per;
    const band = { lo: e.change_range_s[0] / e.old_delay_s * 100, hi: e.change_range_s[1] / e.old_delay_s * 100, mid: e.change_share * 100 };
    const each = go(d.road, 'review', { p: 'impact' });
    watch = ['deployed', 'rolled_back'].includes(s) ? `<div class="kpi-row">
        <div class="kpi"><div class="kpi-l">Forecast · ${term('practice', 'practice copy')}</div><a class="kpi-v dl" href="${each}"><span class="p">${signed(Math.round(band.mid))}%</span></a><div class="kpi-b">${signed(Math.round(band.lo))}% to ${signed(Math.round(band.hi))}%</div></div>
        <div class="kpi"><div class="kpi-l">Measured · ${term('heldout', `${h.n} test evenings`)}</div><a class="kpi-v dl" href="${each}"><span class="p">${pct(h.oldMean, h.planMean)}</span></a><div class="kpi-b">${signed(Math.round(Math.min(...per.map(p => p.v))))}% to ${signed(Math.round(Math.max(...per.map(p => p.v))))}% · better on ${betterOn(h)}</div></div>
        <div class="kpi"><div class="kpi-l">${term('rollback', 'Roll-back rule')} · bad plan</div><div class="kpi-v"><span class="p">${g.caught}</span><small>of ${g.bad} caught</small></div><div class="kpi-b">median ${fmt(g.median)} min after change</div></div>
        <div class="kpi"><div class="kpi-l">${term('rollback', 'Roll-back rule')} · harmless change</div><div class="kpi-v"><span class="p">${g.false}</span><small>of ${g.noop} false alarms</small></div><div class="kpi-b">simulated feed</div></div></div>
      <div class="chart-h"><span>${term('score', 'Delay score')} change per evening</span><div class="legend"><span><i class="sw bar-good"></i>Measured</span><span><i class="sw band"></i>Forecast range</span></div></div>
      ${eveningsChart({ rows: per.map(p => ({ v: p.v, label: `Seed ${p.seed}`, short: String(p.seed) })), band, label: `Delay score change on each of ${h.n} held-out evenings, with the practice-copy forecast range ${signed(Math.round(band.lo))}% to ${signed(Math.round(band.hi))}%.` })}
      <div class="panel-f"><a class="btn sm ghost" href="${each}">Each evening, in numbers ›</a></div>`
      : '';
  }
  return `<div class="page">
    ${crumbs([['Corridors', '#/corridors'], [d.info.street, `#/${d.road}`], ['Deploy & monitor']])}
    ${head(`Deploy & monitor · ${d.info.street}`, { status: pill(d), meta: [`${n} controllers`, `PM peak ${esc(window_(d))}`, 'Simulated rollout · no real controller is touched'], actions })}
    ${stepper}
    <div class="grid g-deploy">${panel('Rollout plan', plan, { anchor: 'rollout' })}${panel('Controllers', ctl, { anchor: 'controllers' })}</div>
    ${panel('Watch after deploy', watch, { anchor: 'watch' })}
    ${auditPanel()}
  </div>`;
}

/* ---------- 7 · How it connects ---------- */

function box(x, y, w, h, title, lines, opts = {}) {
  return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${opts.fill || '#fff'}" stroke="${opts.stroke || '#cfd7e1'}" ${opts.dash ? 'stroke-dasharray="6 4"' : ''} stroke-width="1.5"/>
    <text class="t" x="${x + 12}" y="${y + 22}">${title}</text>${lines.map((l, i) => `<text x="${x + 12}" y="${y + 42 + i * 16}">${l}</text>`).join('')}</g>`;
}
const arrow = (x1, y1, x2, y2, opts = {}) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${opts.color || '#5a6371'}" stroke-width="1.8" ${opts.dash ? 'stroke-dasharray="5 4"' : ''} marker-end="url(#${opts.color ? 'ha' : 'h'})"/>`;

function connect() {
  const A = '#1d4ed8';
  const svg = `<svg class="diagram" viewBox="-2 0 1064 400" role="img" aria-label="Road sensors feed the signal cabinet. The cabinet links to the city's central system, which the engineer uses. Signal Learner sits beside them, read-only, and gives the engineer a recommendation.">
    <defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#5a6371"/></marker>
      <marker id="ha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="${A}"/></marker></defs>
    ${box(0, 20, 170, 150, 'Road sensors', ['Loops: wires cut', 'into the pavement', 'Video cameras', 'Radar'])}
    <rect x="200" y="10" width="330" height="220" rx="10" fill="#f6f8fa" stroke="#cfd7e1" stroke-width="1.5"/>
    <text class="t" x="214" y="32">Signal cabinet, at the corner</text>
    ${box(214, 44, 302, 84, 'Controller', ['A computer that runs the stored timing plan'])}
    ${box(214, 138, 302, 80, 'Conflict monitor', ['A separate safety device. If it sees conflicting', 'greens, it puts the intersection into flash.'], { stroke: '#dc2626' })}
    ${box(560, 20, 140, 110, 'Network link', ['Cabinet to the', 'central system'])}
    ${box(730, 20, 150, 130, 'Central system', ['City staff monitor', 'and manage', 'controllers remotely'])}
    ${box(910, 20, 130, 130, 'City engineer', ['Decides, and enters', 'any timing change'], { fill: '#e7f3fb', stroke: A })}
    ${arrow(170, 86, 212, 86)}${arrow(516, 86, 558, 86)}${arrow(700, 76, 728, 76)}
    ${arrow(880, 66, 908, 66)}${arrow(908, 110, 882, 110)}
    <text x="880" y="170" text-anchor="middle">enters changes</text>
    ${box(200, 290, 680, 96, 'Signal Learner (this software) · READ-ONLY', ['Reads counts, controller logs and timing sheets. Never writes to the cabinet or central system.', 'Learns the pattern, practices plans on a copy, and gives the engineer one recommendation to approve or reject.'], { stroke: A, dash: true })}
    ${arrow(290, 228, 290, 288, { dash: true, color: A })}<text x="300" y="262" style="fill:${A}">counts and logs (read)</text>
    ${arrow(805, 150, 805, 288, { dash: true, color: A })}<text x="797" y="262" text-anchor="end" style="fill:${A}">timing sheets (read)</text>
    ${arrow(880, 330, 975, 152, { color: A })}<text x="935" y="262" style="fill:${A}">recommendation</text>
  </svg>`;
  return `<p class="muted">Example city workflow. This demo uses simulation files only, with no city connection.</p>
  ${svg}
  <div class="path3">
    <div class="card stack"><h3><span class="n">1</span>Read</h3><p class="small">Counts, controller logs (every signal and sensor event, to 0.1 s) and timing sheets, requested from the city.<sup>[2]</sup></p></div>
    <div class="card stack"><h3><span class="n">2</span>Recommend</h3><p class="small">The engineer reviews the recommendation and enters any change. Google's Project Green Light also gives city engineers recommendations.<sup>[6]</sup></p></div>
    <div class="card stack later"><h3><span class="n">3</span>Much later</h3><p class="small">A direct link to the central system, only with city approval and a safety review.<sup>[7]</sup></p></div>
  </div>
  <div class="stack"><h3>Good to know</h3>
    <ul class="facts small">
      <li>A time-of-day schedule picks which timing plan runs when.<sup>[1]</sup></li>
      <li>The conflict monitor is separate from the controller. Our software never touches it.<sup>[5]</sup></li>
      <li>Timing changes are made at the cabinet or from the central system.<sup>[4]</sup> Some city codes give this to the city traffic engineer.<sup>[10]</sup></li>
      <li>Cupertino chose Cubic Trafficware for its central system (2019).<sup>[8]</sup></li>
      <li>Why read-only: a 2023 US cybersecurity advisory says to keep signal networks off the internet.<sup>[9]</sup></li>
    </ul>
    <details><summary>Sources (10)</summary><ol class="sources">
    <li>FHWA, Traffic Signal Timing Manual (archived), ch. 6 — ops.fhwa.dot.gov/publications/fhwahop08024/chapter6.htm</li>
    <li>UDOT, ATSPM FAQ — udottraffic.utah.gov/atspm/FAQs/Display</li>
    <li>FHWA, Traffic Detector Handbook, ch. 5 (loops) — fhwa.dot.gov/publications/research/operations/ITS/06139/chapt5c.cfm</li>
    <li>Hennepin County, signal operations concept — hennepin.us (concept-ops-systems.pdf)</li>
    <li>Texas DOT, malfunction flash — txdot.gov/manuals/trf/tff</li>
    <li>Google, Project Green Light, Oct 10, 2023 — blog.google</li>
    <li>ITE, NTCIP 1202 v04 — ite.org/technical-resources/topics/standards</li>
    <li>Cubic, Trafficware selected by the City of Cupertino, Apr 8, 2019 — cubic.com</li>
    <li>CISA, ICSA-23-026-02 — cisa.gov/uscert/ics/advisories/icsa-23-026-02</li>
    <li>Example city code on signal-timing authority — ecode360.com/43392255</li>
  </ol></details></div>`;
}

function connectScreen() {
  return `<div class="page">${crumbs([['Corridors', '#/corridors'], ['How it connects']])}${head('How it connects')}<div class="connect">${connect()}</div></div>`;
}

/* ---------- Shell ---------- */

// Old deck links keep working: #/overview, #/wolfe/recommendation, #/wolfe/test, #/wolfe/connect.
// ?p=<panel id> scrolls to that panel; ?c15= / ?s15= / ?ts= pick a chart view; ?run starts the simulation.
function parseRoute() {
  const [hash, query = ''] = location.hash.split('?');
  const q = new URLSearchParams(query);
  for (const [k, v] of q) if (k in view) view[k] = v;
  const p = q.get('p') || '';
  const [a, b, c] = hash.replace(/^#\/?/, '').split('/');
  if (a === 'connect') return { road: route.road, screen: 'connect', p };
  if (!ROADS.includes(a)) return { road: route.road, screen: 'corridors', p };
  if (b === 'review' || b === 'recommendation') return { road: a, screen: 'review', p };
  if (b === 'simulate' || b === 'test') return { road: 'wolfe', screen: 'simulate', run: q.has('run') };
  if (b === 'deploy') return { road: a, screen: 'deploy', p };
  if (b === 'connect') return { road: a, screen: 'connect', p };
  if (b === 'signal') return { road: a, screen: 'signal', i: Number(c) - 1, p };
  return { road: a, screen: 'corridor', p };
}

const TITLES = { corridors: 'Corridors', corridor: 'Corridor', signal: 'Signal', review: 'Review', simulate: 'Simulate', deploy: 'Deploy & monitor', connect: 'How it connects' };
const NAV_OF = { corridor: 'corridors', signal: 'corridors' };

function shell(ds) {
  const r = route.road;
  document.getElementById('nav-review').href = `#/${r}/review`;
  document.getElementById('nav-deploy').href = `#/${r}/deploy`;
  const active = NAV_OF[route.screen] || route.screen;
  document.querySelectorAll('#nav a[data-screen]').forEach(a => {
    if (a.dataset.screen === active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  document.getElementById('nav-roads').innerHTML = ds.map(d => `<li><a href="#/${d.road}"${['corridor', 'signal', 'review', 'deploy'].includes(route.screen) && route.road === d.road ? ' class="here"' : ''}>
    <i class="dot ${STATUS[statusKey(d)][1]}" aria-hidden="true"></i>${esc(d.info.street)}<span class="sr">, ${STATUS[statusKey(d)][0]}</span></a></li>`).join('');
  const pending = ds.filter(d => statusKey(d) === 'pending').length;
  document.getElementById('nav-count').textContent = pending || '';
  document.getElementById('fixture').hidden = !FIXTURE;
}

function drawMaps() {
  document.querySelectorAll('.map[data-road]').forEach(box => {
    const d = cache[box.dataset.road], pick = box.dataset.pick === undefined ? -1 : Number(box.dataset.pick);
    if (!d) return;
    const links = 'links' in box.dataset ? d.card.signals.map((s, i) => i === pick ? null : { href: go(d.road, `signal/${i + 1}`), label: `Signal ${i + 1}: ${s.signal}` }) : [];
    drawMap(box, d.geo, pick, links);
  });
}

async function render() {
  player?.destroy(); player = null;
  const next = parseRoute();
  const moved = next.screen !== route.screen || next.road !== route.road || next.i !== route.i;
  if (moved) form = null;
  route = next;
  try {
    const ds = await Promise.all(ROADS.map(data));
    const d = ds[ROADS.indexOf(route.road)];
    if (route.screen === 'signal' && !(route.i >= 0 && route.i < d.card.signals.length)) route.screen = 'corridor';
    shell(ds);
    document.title = `${TITLES[route.screen]} · Signal Learner`;
    if (route.screen === 'corridors') main.innerHTML = corridorsScreen(ds, await contextRoads());
    else if (route.screen === 'corridor') main.innerHTML = corridorScreen(d);
    else if (route.screen === 'signal') main.innerHTML = signalScreen(d, route.i);
    else if (route.screen === 'review') main.innerHTML = reviewScreen(d);
    else if (route.screen === 'deploy') main.innerHTML = deployScreen(d);
    else if (route.screen === 'connect') main.innerHTML = connectScreen();
    else {
      main.innerHTML = simulate(ds[0]);
      player = new Player(ds[0]);
      player.draw();
      if (route.run) { history.replaceState(null, '', '#/wolfe/simulate'); act('wolfe', 'Ran side-by-side simulation'); player.start(); }
    }
    drawMaps();
  } catch (err) {
    main.innerHTML = `<div class="page"><div class="error"><b>Could not load the saved files.</b> ${esc(err.message)}. Start the console with python3 -m tools.demo, then reload.</div></div>`;
  }
  const target = route.p && main.querySelector(`#${CSS.escape(route.p)}`);
  if (target) {
    target.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    target.focus({ preventScroll: true });
    target.classList.add('flash');
  } else if (moved) {
    const h1 = main.querySelector('h1');
    if (h1 && document.activeElement !== document.body) { h1.tabIndex = -1; h1.focus({ preventScroll: true }); }
    window.scrollTo(0, 0);
  }
}

// A drill-down link to the panel already in the URL fires no hashchange; scroll to it again.
document.addEventListener('click', event => {
  const a = event.target.closest('a[href^="#/"]');
  if (a && a.getAttribute('href') === location.hash) { event.preventDefault(); render(); }
});

async function rerender(focusSel) {
  await render();
  (focusSel && main.querySelector(focusSel))?.focus();
}

main.addEventListener('input', event => {
  if (event.target.id === 'note') drafts[event.target.dataset.road] = event.target.value;
});

main.addEventListener('click', async event => {
  const speed = event.target.closest('[data-speed]');
  if (speed && player) {
    player.setSpeed(Number(speed.dataset.speed));
    document.querySelectorAll('[data-speed]').forEach(b => b.setAttribute('aria-pressed', String(b === speed)));
    return;
  }
  const v = event.target.closest('[data-view]');
  if (v) { view[v.dataset.view] = v.dataset.val; return rerender(`[data-view="${v.dataset.view}"][data-val="${v.dataset.val}"]`); }
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'start') { act('wolfe', 'Ran side-by-side simulation'); return player?.start(); }
  if (action === 'toggle') return player?.toggle();
  const d = await data(route.road), note = (drafts[d.road] || '').trim();
  const done = () => { delete drafts[d.road]; form = null; };
  if (action === 'approve') { act(d.road, 'Approved recommendation', { status: 'approved' }, note); done(); }
  else if (action === 'reject') { act(d.road, 'Rejected recommendation', { status: 'rejected' }, note); done(); }
  else if (action === 'schedule') { form = 'schedule'; return rerender('#when'); }
  else if (action === 'cancel') { form = null; return rerender('[data-action="schedule"]'); }
  else if (action === 'schedule-confirm') {
    const when = document.getElementById('when').value;
    if (!when) { document.getElementById('when-err').hidden = false; return document.getElementById('when').focus(); }
    act(d.road, `Scheduled for ${new Date(when).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}`, { status: 'scheduled', when }, note); done();
  }
  else if (action === 'acknowledge') act(d.road, 'Acknowledged: keep current timing', { status: 'acknowledged' }, note);
  else if (action === 'reopen') act(d.road, 'Reopened recommendation', null);
  else if (action === 'deploy') act(d.road, `Deployed PM peak plan to ${d.card.signals.length} controllers (simulated)`, { ...dec(d), status: 'deployed' });
  else if (action === 'rollback') act(d.road, 'Rolled back to current timing (simulated)', { ...dec(d), status: 'rolled_back' });
  else if (action === 'reset') { state = { decisions: {}, log: [] }; save(); }
  else if (action === 'print') { document.getElementById('print').innerHTML = sheet(d); return window.print(); }
  await rerender('.panel .done ~ .row .btn, .actions .btn.primary, .actions .btn.danger, .decide .btn.primary');
});

document.addEventListener('keydown', event => {
  if (event.key === ' ' && player && !event.target.closest('button, a, textarea, input')) { event.preventDefault(); player.toggle(); }
});
window.addEventListener('hashchange', render);
let resizeTimer;
window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawMaps, 120); });
render();
