'use strict';
// Every number on screen comes from the copied report files in data/ or from the live test endpoint.

const SCREENS = ['corridor', 'signal', 'recommendation', 'test', 'watch', 'connect'];
const ROADS = ['wolfe', 'deanza'];
const STORE = 'signal-learner-console-v1';
// Loaded from the served copy of the frozen go-back rule.
let RULE;
const COLORS = ['#1f4fd6', '#22a05a', '#d97706', '#7c3aed'];
const LEGS = { N: 'north', S: 'south', E: 'east', W: 'west' };
const TURNS = { L: 'left', T: 'through', R: 'right' };

const main = document.getElementById('main');
const cache = {};
let route = { road: 'wolfe', screen: 'corridor', index: 0 };
let decisions = loadDecisions();
let rejecting = false;
let live = null;
let timer = null;
let firstRender = true;

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const f1 = x => Number(x).toFixed(1);
const signed = (x, d = 1) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(d);
const mean = v => v.reduce((a, b) => a + b, 0) / v.length;
const sum = v => v.reduce((a, b) => a + b, 0);
const clock = s => `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}`;
const change = (a, b, unit = ' s') => a === b ? `${f1(a)}${unit}` : `${f1(a)}<span class="arrow">→</span><span class="up">${f1(b)}</span>${unit}`;

function loadDecisions() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
}
function saveDecisions() {
  try { localStorage.setItem(STORE, JSON.stringify(decisions)); } catch { /* private mode: keep in memory */ }
}

function csv(text) {
  const [head, ...rows] = text.trim().split(/\r?\n/);
  const keys = head.split(',');
  return rows.map(row => Object.fromEntries(row.split(',').map((v, i) => [keys[i], v])));
}

function roadYaml(text) {
  const top = key => (text.match(new RegExp(`^${key}:\\s*'?([^'\\n]*)'?`, 'm')) || [])[1];
  const signals = [];
  let inSignals = false, current = null, m;
  for (const line of text.split('\n')) {
    if (/^signals:/.test(line)) { inSignals = true; continue; }
    if (inSignals && /^\S/.test(line) && !line.startsWith('-')) inSignals = false;
    if (!inSignals) continue;
    if ((m = line.match(/^- name: (.+)$/))) signals.push(current = { name: m[1].trim() });
    else if ((m = line.match(/^ {2}(lat|lon): (.+)$/))) current[m[1]] = Number(m[2]);
  }
  return { street: top('street'), begin: top('begin'), end: top('end'), signals };
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
        const state = chain[j].getAttribute('state'), dur = Number(chain[j].getAttribute('duration'));
        if (state.includes('y')) yellow += dur; else if (/^r+$/.test(state)) red += dur;
      }
      byPhase[i] = { yellow, red };
    });
    out[tl.getAttribute('id')] = byPhase;
  }
  return out;
}

async function get(path, kind = 'text') {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response[kind]();
}

async function data(road) {
  if (cache[road]) return cache[road];
  const base = `data/${road}/`;
  const [card, practice, plan, pattern, yaml, results, goBack, rule, ...feeds] = await Promise.all([
    get(base + 'card.json', 'json'), get(base + 'practice.json', 'json'), get(base + 'plan.add.xml'),
    get(base + 'pattern.csv'), get(base + 'road.yaml'), get('data/heldout/results.csv'), get('data/heldout/go_back.json', 'json'), get('data/check-rule.txt'),
    ...[0, 1, 2].map(seed => get(`${base}feed${seed}.csv`))]);
  RULE = Object.fromEntries(Object.entries({ windows: 'WINDOWS', meanRise: 'MEAN_RISE', approachRise: 'APPROACH_RISE',
    approaches: 'APPROACHES', sdFactor: 'SD_FACTOR', countDrop: 'COUNT_DROP' }).map(([key, name]) =>
    [key, Number(rule.match(new RegExp(`^${name} = ([0-9.]+)`, 'm'))[1])]));
  const d = { road, card, practice, clear: clearances(plan), pattern: csv(pattern), info: roadYaml(yaml),
    results: csv(results), goBack, feeds: feeds.map(csv) };
  if (road === 'deanza') d.posthoc = await get(base + 'posthoc.json', 'json');
  return (cache[road] = d);
}

function phases(d, sig, which) {
  const clear = d.clear[sig.sumo_tls_id] || {};
  return sig[which].greens.map(g => {
    const { yellow = 0, red = 0 } = clear[g.phase] || {};
    return { ...g, yellow, red, split: g.max_green_s + yellow + red };
  });
}

function serves(codes) {
  return codes.map(code => {
    const [leg, turns] = code.split(':');
    return `From ${LEGS[leg] || leg}: ${[...turns].map(t => TURNS[t] || t).join(', ')}`;
  }).join(' · ');
}

function plainReason(reason) {
  return reason.replace(/(?:[NSEW]:[LTR]+)(?: [NSEW]:[LTR]+)*/g, codes => serves(codes.split(' ')).replaceAll('From ', 'traffic from '))
    .replaceAll('veh/15 min', 'cars per 15 min').replaceAll(' -> ', ' → ').replace(/^offset|; offset/g, m => m.replace('offset', 'green start'));
}

const isChange = d => d.card.decision === 'change';
const decision = d => decisions[d.road] || {};

function roadStatus(d) {
  if (!isChange(d)) return ['No change · keep current timing', 'idle'];
  const status = decision(d).status;
  if (status === 'approved') return ['Approved · watching', 'info'];
  if (status === 'rejected') return ['Rejected · card archived', 'idle'];
  return ['Recommendation ready', 'ok'];
}

function signalStatus(d, sig) {
  if (sig.reason === 'no material change') return ['Learned · no change', 'idle'];
  const status = decision(d).status;
  if (status === 'approved') return ['Approved · watching', 'info'];
  if (status === 'rejected') return ['Learned · rejected', 'idle'];
  return ['Recommendation ready', 'ok'];
}

const pill = ([text, kind]) => `<span class="pill ${kind}">${esc(text)}</span>`;
// Hover or keyboard-focus a dotted term to read a one-line explanation.
const tip = (label, text) => `<span class="tip" tabindex="0">${label}<span class="tip-text" role="tooltip">${esc(text)}</span></span>`;
const more = (summary, body) => `<details class="more"><summary>${summary}</summary><div class="more-body stack">${body}</div></details>`;
const hm = t => { const [h, m] = t.split(':').map(Number); return `${h % 12 || 12}:${String(m).padStart(2, '0')}`; };
const peak = info => `${hm(info.begin)}–${hm(info.end)} ${Number(info.end.split(':')[0]) >= 12 ? 'pm' : 'am'}`;
const lights = n => `${n} traffic light${n === 1 ? '' : 's'}`;

const T_ROUND = 'Cycle: one full round of greens for every direction.';
const T_START = 'Offset: when this light starts its round, so greens line up along the road.';
const T_ALLRED = 'Every light shows red for a moment so the crossing clears.';
const T_SCORE = 'Average seconds of delay per trip. Trips that never finish add a penalty.';

function heldout(d, road = d.road) {
  const rows = d.results.filter(r => r.road === road);
  const by = arm => Object.fromEntries(rows.filter(r => r.arm === arm).map(r => [r.seed, Number(r.all_requested_delay_s)]));
  const old = by('old'), plan = by('learner');
  const seeds = Object.keys(old).filter(s => s in plan).sort((a, b) => a - b);
  const pairs = seeds.map(seed => ({ seed: Number(seed), old: old[seed], plan: plan[seed],
    oldUnfinished: Number(rows.find(r => r.arm === 'old' && r.seed === seed).unfinished),
    planUnfinished: Number(rows.find(r => r.arm === 'learner' && r.seed === seed).unfinished) }));
  const oldMean = mean(pairs.map(p => p.old)), planMean = mean(pairs.map(p => p.plan));
  return { pairs, oldMean, planMean, pct: (planMean - oldMean) / oldMean * 100, better: pairs.filter(p => p.plan < p.old).length };
}

/* ---------- 1. Corridor ---------- */

function mapSvg(d) {
  const W = 600, H = 470, padY = 56;
  const pts = d.card.signals.map((sig, i) => {
    const where = d.info.signals.find(s => s.name === sig.signal) || {};
    return { sig, i, lat: where.lat, lon: where.lon };
  });
  const lats = pts.map(p => p.lat), lons = pts.map(p => p.lon);
  const latMin = Math.min(...lats), latMax = Math.max(...lats), lonMid = mean(lons);
  const k = (H - 2 * padY) / (latMax - latMin);
  const cos = Math.cos(mean(lats) * Math.PI / 180);
  const cx = 230;
  pts.forEach(p => { p.x = cx + (p.lon - lonMid) * cos * k; p.y = padY + (latMax - p.lat) * k; });
  const road = [{ x: pts[0].x, y: H - 12 }, ...pts.slice().sort((a, b) => b.y - a.y), { x: pts.at(-1).x, y: 12 }];
  const south = pts.find(p => /I-280 south/.test(p.sig.signal)), north = pts.find(p => /I-280 north/.test(p.sig.signal));
  const freeway = south && north ? (() => {
    const y = (south.y + north.y) / 2;
    return `<rect x="0" y="${y - 9}" width="${W}" height="18" fill="#e8ebf0"/>
      <line x1="0" x2="${W}" y1="${y}" y2="${y}" stroke="#fff" stroke-dasharray="10 8" stroke-width="1.5"/>
      <text x="12" y="${y + 4}" font-size="11" font-weight="600" fill="#5a6371">I-280</text>`;
  })() : '';
  const markers = pts.map(p => {
    const [text, kind] = signalStatus(d, p.sig);
    const color = { ok: '#157a3c', info: '#1f4fd6', idle: '#8a93a1' }[kind];
    const label = `${p.sig.signal}, ${text}. Open light ${p.i + 1}.`;
    return `<a href="#/${d.road}/signal/${p.i}" aria-label="${esc(label)}"><title>${esc(`${p.sig.signal} · ${text}`)}</title>
      <line x1="${p.x - 70}" x2="${p.x + 70}" y1="${p.y}" y2="${p.y}" stroke="#cfd4dc" stroke-width="6" stroke-linecap="round"/>
      <circle class="ring" cx="${p.x}" cy="${p.y}" r="14" fill="#fff" stroke="${color}" stroke-width="3"/>
      <text x="${p.x}" y="${p.y + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#151a22">${p.i + 1}</text>
      <text class="map-name" x="${p.x + 86}" y="${p.y + 5}" font-size="14" font-weight="600" fill="#151a22">${esc(p.sig.signal)}</text>
    </a>`;
  }).join('');
  return `<svg class="map" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(d.info.street)} drawn from the saved road file, north at top">
    <rect width="${W}" height="${H}" rx="8" fill="#f7f8fa"/>
    ${freeway}
    <polyline points="${road.map(p => `${p.x},${p.y}`).join(' ')}" fill="none" stroke="#9aa3b2" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
    <polyline points="${road.map(p => `${p.x},${p.y}`).join(' ')}" fill="none" stroke="#fff" stroke-width="1.5" stroke-dasharray="8 8"/>
    <text transform="translate(${cx - 22} ${H / 2}) rotate(-90)" text-anchor="middle" font-size="12" font-weight="600" fill="#5a6371">${esc(d.info.street)}</text>
    <g transform="translate(${W - 34} 30)" aria-hidden="true"><path d="M0 -14 L7 6 L0 2 L-7 6 Z" fill="#5a6371"/><text y="20" text-anchor="middle" font-size="11" fill="#5a6371">N</text></g>
    ${markers}
  </svg>`;
}

function corridor(d) {
  const sigs = d.card.signals, e = d.card.expected_in_copy;
  const changed = sigs.filter(s => s.reason !== 'no material change').length;
  const lead = isChange(d)
    ? `<h2>New timing for ${changed === sigs.length ? `all ${sigs.length}` : `${changed} of ${sigs.length}`} lights</h2>
      <p class="muted">Forecast on the practice copy: <b>${signed(e.change_share * 100, 0)}%</b> ${tip('delay per trip', T_SCORE)}</p>`
    : `<h2>Keep the current timing</h2><p class="muted">The best new plan caused jams in practice runs, so nothing changes.</p>`;
  return `
  <div class="head"><div><h1>${esc(d.info.street)}</h1><p>Evening rush, ${peak(d.info)} · ${lights(sigs.length)}</p></div></div>
  <ol class="steps" aria-label="Progress">
    <li class="step done"><b>Watched</b><span>${d.feeds.length} evening rush hours</span></li>
    <li class="step done"><b>Learned</b><span>the traffic pattern</span></li>
    <li class="step done"><b>Practiced</b><span>${d.practice.trials} timing plans</span></li>
    <li class="step now"><b>Recommended</b><span>${isChange(d) ? 'new timing' : 'no change'}</span></li>
  </ol>
  <div class="grid g-map">
    <div class="card"><h2 class="sr">Map</h2>${mapSvg(d)}<p class="small muted map-hint">Select a light to see its timing.</p></div>
    <div class="card stack lead">${lead}
      <div class="actions"><a class="btn primary" href="#/${d.road}/recommendation">Open the recommendation</a></div></div>
  </div>`;
}

/* ---------- 2. Signal ---------- */

function bar(list, cycle, scale, old) {
  const seg = (cls, s, title, text = '') => s > 0
    ? `<div class="${cls}" style="width:${s / cycle * 100}%" title="${esc(title)}">${text}</div>` : '';
  const body = list.map(p => seg(`seg-g${old ? ' old' : ''}`, p.max_green_s, `${serves(p.serves)}: green up to ${f1(p.max_green_s)} s`,
      p.max_green_s / scale > 0.06 ? `${Math.round(p.max_green_s)} s` : '')
    + seg('seg-y', p.yellow, `Yellow ${f1(p.yellow)} s`) + seg('seg-r', p.red, `All-red ${f1(p.red)} s`)).join('');
  const label = list.map(p => `${serves(p.serves)}: green ${f1(p.max_green_s)}, yellow ${f1(p.yellow)}, all-red ${f1(p.red)}`).join('; ');
  return `<div class="bar" style="width:${cycle / scale * 100}%" role="img" aria-label="Round of ${f1(cycle)} seconds: ${esc(label)}">${body}</div>`;
}

function patternChart(d, site) {
  const rows = d.pattern.filter(r => r.site === site);
  const legs = [...new Set(rows.map(r => r.approach))];
  const times = [...new Set(rows.map(r => Number(r.quarter_start_s)))].sort((a, b) => a - b);
  const W = 520, H = 190, L = 40, R = 12, T = 10, B = 26;
  const top = Math.ceil(Math.max(...rows.map(r => Number(r.mean_count))) / 100) * 100 || 100;
  const x = t => L + (times.indexOf(t) / Math.max(times.length - 1, 1)) * (W - L - R);
  const y = v => T + (1 - v / top) * (H - T - B);
  const grid = [0, 0.25, 0.5, 0.75, 1].map(f => `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(top * f)}" y2="${y(top * f)}"/>
    <text x="${L - 6}" y="${y(top * f) + 4}" text-anchor="end">${top * f}</text>`).join('');
  const ticks = times.map((t, i) => i % 2 ? '' : `<text x="${x(t)}" y="${H - 8}" text-anchor="middle">${clock(t)}</text>`).join('');
  const lines = legs.map((leg, i) => {
    const pts = rows.filter(r => r.approach === leg).map(r => [x(Number(r.quarter_start_s)), y(Number(r.mean_count))]);
    return `<polyline points="${pts.map(p => p.join(',')).join(' ')}" fill="none" stroke="${COLORS[i % 4]}" stroke-width="2"/>`
      + pts.map(([px, py]) => `<circle cx="${px}" cy="${py}" r="2.5" fill="${COLORS[i % 4]}"/>`).join('');
  }).join('');
  const table = more('Show as table', `<table><thead><tr><th>Start</th>${legs.map(l => `<th class="num">From ${LEGS[l]}</th>`).join('')}</tr></thead><tbody>
    ${times.map(t => `<tr><td>${clock(t)}</td>${legs.map(l => `<td class="num">${f1(rows.find(r => r.approach === l && Number(r.quarter_start_s) === t)?.mean_count ?? NaN)}</td>`).join('')}</tr>`).join('')}
    </tbody></table>`);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cars per 15 minutes by direction at ${esc(site)}">${grid}${ticks}${lines}</svg>
    <div class="legend">${legs.map((l, i) => `<span><i style="background:${COLORS[i % 4]}"></i>From the ${LEGS[l]}</span>`).join('')}</div>${table}`;
}

function signal(d) {
  const sigs = d.card.signals;
  const sig = sigs[Math.min(route.index, sigs.length - 1)];
  const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
  const scale = Math.max(sig.old.cycle_s, sig.new.cycle_s);
  const ticks = [];
  for (let t = 0; t <= scale; t += 10) ticks.push(`<span style="left:${t / scale * 100}%">${t}</span>`);
  const same = sig.reason === 'no material change';
  const why = same ? '<p class="small muted">No change at this light.</p>'
    : more('Why it changed', `<ul class="why">${plainReason(sig.reason).split('; ').map(r => `<li>${esc(r)}</li>`).join('')}</ul>`);
  return `
  <div class="head"><div><h1>${esc(sig.signal)}</h1><p>Light ${sigs.indexOf(sig) + 1} of ${sigs.length} on ${esc(d.info.street)}</p></div></div>
  <nav class="tabs" aria-label="Lights">${sigs.map((s, i) => `<a href="#/${d.road}/signal/${i}" ${s === sig ? 'aria-current="page"' : ''}>${i + 1} · ${esc(s.signal)}</a>`).join('')}</nav>
  <div class="card" style="margin-bottom:16px">
    <h2>One ${tip('full round', T_ROUND)} of greens</h2>
    <div class="bar-row"><div class="lbl"><b>Old</b><span>${f1(sig.old.cycle_s)} s</span></div>${bar(old, sig.old.cycle_s, scale, true)}</div>
    <div class="bar-row"><div class="lbl"><b>New</b><span>${f1(sig.new.cycle_s)} s</span></div>${bar(neu, sig.new.cycle_s, scale, false)}</div>
    <div class="axis" aria-hidden="true"><div></div><div class="ticks">${ticks.join('')}</div></div>
    <div class="legend" style="margin-top:6px"><span><i style="background:var(--g)"></i>Green</span><span><i style="background:var(--y)"></i>Yellow</span><span><i style="background:var(--r)"></i>${tip('All-red', T_ALLRED)}</span><span>Seconds</span></div>
    ${more('How to read this', `<p class="small">Each bar is one full round. Green blocks show the longest green each direction may get.</p>
      <p class="small">Green starts at ${f1(sig.old.offset_s)} s (old) and ${f1(sig.new.offset_s)} s (new). ${esc(T_START)}</p>`)}
  </div>
  <div class="grid g2">
    <div class="card stack"><h2>Green time by direction</h2>
      <table><thead><tr><th>Who moves</th><th class="num">Green, s</th></tr></thead><tbody>
      ${old.map((p, i) => `<tr><td>${esc(serves(p.serves))}</td><td class="num">${change(p.max_green_s, neu[i].max_green_s, '')}</td></tr>`).join('')}
      </tbody></table>${why}
    </div>
    <div class="card"><h2>Cars per 15 minutes</h2>${patternChart(d, sig.signal)}</div>
  </div>`;
}

/* ---------- 3. Recommendation ---------- */

function sheet(d) {
  const at = new Date(decision(d).at);
  return `<section class="sheet" aria-labelledby="sheet-title">
    <div class="sheet-head"><div><h2 id="sheet-title">Timing change sheet</h2><p class="muted small">From the approved Signal Learner card · simulation result</p></div><span class="stamp">Draft for engineer entry</span></div>
    <dl>
      <dt>Corridor</dt><dd>${esc(d.info.street)}, ${d.card.signals.length} intersections</dd>
      <dt>Plan</dt><dd>Evening peak, ${esc(d.info.begin)}–${esc(d.info.end)}</dd>
      <dt>Approved</dt><dd>${esc(at.toLocaleString())} (in this console)</dd>
      <dt>Unchanged</dt><dd>Phase order, yellow, all-red and minimum greens</dd>
    </dl>
    ${d.card.signals.map(sig => {
      const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
      return `<div class="int"><h3>${esc(sig.signal)}</h3>
        <p class="small">Cycle ${change(sig.old.cycle_s, sig.new.cycle_s)} · Offset ${change(sig.old.offset_s, sig.new.offset_s)}</p>
        <table><thead><tr><th>Phase</th><th>Movements</th><th class="num">Min green</th><th class="num">Max green</th><th class="num">Yellow</th><th class="num">All-red</th><th class="num">Split</th></tr></thead><tbody>
        ${old.map((p, i) => `<tr><td>${p.phase}</td><td>${esc(serves(p.serves))}</td><td class="num">${f1(p.min_green_s)}</td>
          <td class="num">${change(p.max_green_s, neu[i].max_green_s, '')}</td><td class="num">${f1(p.yellow)}</td><td class="num">${f1(p.red)}</td>
          <td class="num">${change(p.split, neu[i].split, '')}</td></tr>`).join('')}
        </tbody></table></div>`;
    }).join('')}
    <p class="small muted" style="margin-top:12px">Seconds. Split = max green + yellow + all-red. Phase numbers come from the simulation; match them to the controller's phases when entering.</p>
    <div class="sign"><div>Reviewed by (traffic engineer)</div><div>Entered into controller / central system by</div><div>Date entered</div></div>
  </section>`;
}

function decisionBlock(d) {
  const dec = decision(d);
  if (dec.status === 'approved') {
    return `<div class="banner ok no-print"><span><b>Approved.</b> Print the sheet for the engineer, then test it.</span>
      <span class="actions"><button class="btn primary" data-action="print">Print sheet</button><a class="btn" href="#/${d.road}/test">Test it</a><button class="btn ghost" data-action="reopen">Undo</button></span></div>`;
  }
  if (dec.status === 'rejected') {
    return `<div class="banner bad"><span><b>Rejected</b> ${esc(new Date(dec.at).toLocaleString())}.${dec.note ? ` Note: “${esc(dec.note)}”` : ''} Current timing stays.</span>
      <button class="btn" data-action="reopen">Reopen</button></div>`;
  }
  if (rejecting) {
    return `<div class="card"><label class="field" for="note">Why reject? (optional, kept with the card)</label>
      <textarea id="note" maxlength="500" placeholder="For example: conflicts with the school-zone plan"></textarea>
      <div class="actions" style="margin-top:10px"><button class="btn danger" data-action="archive">Reject</button><button class="btn ghost" data-action="cancel">Cancel</button></div></div>`;
  }
  return '';
}

function timingTable(d) {
  return `<table><thead><tr><th>Light</th><th class="num">${tip('Full round', T_ROUND)}</th><th class="num">${tip('Green starts at', T_START)}</th><th class="num">Main green</th></tr></thead><tbody>
    ${d.card.signals.map((s, i) => `<tr><td><a href="#/${d.road}/signal/${i}">${esc(s.signal)}</a></td><td class="num">${change(s.old.cycle_s, s.new.cycle_s)}</td><td class="num">${change(s.old.offset_s, s.new.offset_s)}</td>
      <td class="num">${change(s.old.greens[0].max_green_s, s.new.greens[0].max_green_s)}</td></tr>`).join('')}
    </tbody></table>`;
}

function recommendation(d) {
  const c = d.card, e = c.expected_in_copy, sigs = c.signals;
  if (!isChange(d)) return deanzaCard(d);
  const dec = decision(d);
  const head = `<div class="head"><div><h1>Recommendation</h1><p>${esc(d.info.street)} · evening rush, ${peak(d.info)}</p></div>
    ${dec.status || rejecting ? '' : `<div class="head-actions"><div class="actions"><button class="btn primary" data-action="approve">Approve</button><button class="btn" data-action="reject">Reject</button></div><span class="small muted">Nothing is sent to any light.</span></div>`}</div>`;
  if (dec.status === 'approved') return `<div class="no-print">${head}</div>${decisionBlock(d)}<div style="margin-top:16px">${sheet(d)}</div>`;
  const oldCycles = [...new Set(sigs.map(s => s.old.cycle_s))], newCycles = [...new Set(sigs.map(s => s.new.cycle_s))];
  const plain = oldCycles.length === 1 && newCycles.length === 1
    ? `All ${sigs.length} lights go from a ${f1(oldCycles[0])} s to a ${f1(newCycles[0])} s ${tip('round', T_ROUND)}. The busiest directions get more green, and greens line up along ${esc(d.info.street)}.`
    : 'The busiest directions get more green, and greens line up along the road.';
  return `
  ${head}
  ${decisionBlock(d)}
  <div class="grid g2" style="margin:16px 0">
    <div class="card stack"><h2>What changes</h2><p>${plain}</p>
      <p class="small muted">Stays the same: phase order, yellow, all-red, minimum greens.</p></div>
    <div class="card stack"><h2>Forecast (practice copy)</h2>
      <div class="effect"><span class="big">${f1(e.old_delay_s)} s<span class="arrow">→</span>${f1(e.new_delay_s)} s</span><span class="delta">${signed(e.change_share * 100)}%</span></div>
      <p class="small muted">${tip('Delay per trip', T_SCORE)} over ${e.copy_seeds.length} practice rush hours.</p>
      ${more('Details', `<p class="small">Range across practice runs: ${signed(e.change_range_s[0])} to ${signed(e.change_range_s[1])} s per trip. Practice runs use a simulated road built only from sensor counts.</p>
        <p class="small">Card: “${esc(c.why)}” ${esc(c.limits)}</p>`)}</div>
  </div>
  <div class="card"><h2>Old → new, per light</h2>${timingTable(d)}</div>`;
}

function deanzaCard(d) {
  const p = d.practice, e = d.card.expected_in_copy, margin = p.settings.teleport_margin;
  const failed = p.confirm_new.filter((run, i) => run.teleports > p.confirm_old[i].teleports + margin).length;
  const post = d.posthoc, postPlan = post.rejected_plan.all_requested_delay_s.mean;
  return `
  <div class="head"><div><h1>Recommendation</h1><p>${esc(d.info.street)} · evening rush, ${peak(d.info)}</p></div></div>
  <div class="card stack" style="margin-bottom:16px">
    <h2 class="h-lg">No change: keep the current timing</h2>
    <p>The best new plan looked faster (${f1(e.old_delay_s)} → ${f1(e.new_delay_s)} s per trip) but jammed on ${failed} of ${p.confirm_new.length} practice rush hours.</p>
    ${more('Details', `<p class="small">“Jammed” means the simulation had to remove more than ${margin} extra stuck cars. That check failed, so the card keeps the current timing.</p>
      <p class="small">The archived card says “${esc(d.card.why)}” That sentence was inaccurate; the failed check is the real reason.</p>
      <p class="small">A later check on ${post.seeds.length} new traffic days found the rejected plan ${signed((postPlan - post.old_delay_s) / post.old_delay_s * 100)}% worse: ${f1(post.old_delay_s)} → ${f1(postPlan)} s.</p>`)}
  </div>
  <div class="card"><h2>Current timing, per light</h2>${timingTable(d)}</div>`;
}

/* ---------- 4. Test it ---------- */

function compare(old, neu, extra = '') {
  const top = Math.max(old, neu), pct = (neu - old) / old * 100;
  const row = (k, v, cls) => `<div class="cmp-row"><span class="k">${k}</span><span class="cmp-track"><i class="${cls}" style="width:${v / top * 100}%"></i></span><b>${f1(v)} s</b></div>`;
  return `<div class="compare">
    <div class="cmp-pct ${pct > 0 ? 'worse' : ''}">${signed(pct)}%<span>${pct > 0 ? 'more' : 'less'} delay</span></div>
    ${row('Old timing', old, 'old')}${row('New plan', neu, 'new')}${extra}</div>`;
}

function pairedChart(h) {
  const W = 500, H = 190, L = 44, R = 10, T = 10, B = 26;
  const values = h.pairs.flatMap(p => [p.old, p.plan]);
  const lo = Math.floor(Math.min(...values) / 100) * 100, hi = Math.ceil(Math.max(...values) / 100) * 100;
  const x = i => L + (i + 0.5) / h.pairs.length * (W - L - R);
  const y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const grid = [];
  for (let v = lo; v <= hi; v += 100) grid.push(`<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`);
  const marks = h.pairs.map((p, i) => `<line x1="${x(i)}" x2="${x(i)}" y1="${y(p.old)}" y2="${y(p.plan)}" stroke="#cfd4dc" stroke-width="2"/>
    <circle cx="${x(i)}" cy="${y(p.old)}" r="4" fill="var(--old)"/><circle cx="${x(i)}" cy="${y(p.plan)}" r="4" fill="var(--accent)"/>`).join('');
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Delay score on ${h.pairs.length} new traffic days, old timing versus new plan">${grid.join('')}${marks}
    <text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">Each pair is one traffic day</text></svg>
    <div class="legend"><span><i style="background:var(--old)"></i>Old timing</span><span><i style="background:var(--accent)"></i>New plan</span><span>Delay score, s</span></div>`;
}

// Plain words for the server's reasons; the exact text stays one click away.
function liveError(reason) {
  if (/already running/.test(reason)) return 'A test is already running. Wait a moment, then try again.';
  if (/not installed|not on this laptop|not running/.test(reason)) return 'The simulator is not set up on this laptop.';
  return 'The test could not finish.';
}

function liveBlock(d) {
  if (!live) return `<div class="live-empty"><p>Runs the old and new timing on a day the learner never saw.</p>
    <button class="btn primary big" data-action="run-test">Run the test</button><p class="small muted">Takes about 20 seconds.</p></div>`;
  if (live.state === 'running') return `<div role="status" class="live-empty"><p><b>Running the simulation…</b></p>
    <div class="progress"><i id="live-bar" style="width:${runShare()}%"></i></div><p class="small muted"><span id="elapsed">${elapsed()}</span> s · about 20 s</p></div>`;
  if (live.state === 'error') return `<div role="status" class="stack"><div class="banner idle"><span><b>${esc(liveError(live.reason))}</b> The saved result is on the right.</span></div>
    ${more('Details', `<p class="small">${esc(live.reason)}</p>`)}
    <div class="actions"><button class="btn" data-action="run-test">Try again</button></div></div>`;
  const r = live.result, saved = heldout(d).pairs.find(p => p.seed === r.seed);
  const match = saved && f1(saved.old) === f1(r.old.delay_s) && f1(saved.plan) === f1(r.learner.delay_s);
  return `<div role="status" class="stack">${compare(r.old.delay_s, r.learner.delay_s)}
    <p class="small muted">Trips that never finished: ${r.old.unfinished} → ${r.learner.unfinished}.${match ? ' Same as the saved run for this day.' : ''}</p>
    <div class="actions"><button class="btn" data-action="run-test">Run again</button></div></div>`;
}

const elapsed = () => Math.round((Date.now() - live.started) / 1000);
const runShare = () => Math.min(95, (Date.now() - live.started) / 200);

function test(d) {
  const h = heldout(d);
  const head = `<div class="head"><div><h1>Test it</h1><p><b>Delay score</b>: average seconds of delay per trip, with a penalty for trips that never finish. Lower is better.</p></div></div>`;
  if (!isChange(d)) {
    return `${head}<div class="card stack"><h2>Nothing new to test</h2><p>The timing stays the same, so the score stays at ${f1(h.oldMean)} s over ${h.pairs.length} traffic days.</p>
        <p class="small muted">Switch to Wolfe to run a live test.</p></div>`;
  }
  return `${head}
  <div class="grid g2">
    <div class="card stack"><h2>Live test: one new traffic day</h2><div id="live">${liveBlock(d)}</div></div>
    <div class="card stack"><h2>Saved result: ${tip(`${h.pairs.length} new traffic days`, 'Days the learner never saw. The test rules were set before the run.')}</h2>
      ${compare(h.oldMean, h.planMean)}
      <p class="small muted">New plan better on ${h.better} of ${h.pairs.length} days.</p>
      ${pairedChart(h)}
      <div class="actions"><button class="btn" data-action="video">Play side-by-side video</button></div>
    </div>
  </div>`;
}

async function runTest() {
  live = { state: 'running', started: Date.now() };
  render();
  const tick = setInterval(() => {
    const el = document.getElementById('elapsed'), barEl = document.getElementById('live-bar');
    if (el) el.textContent = elapsed();
    if (barEl) barEl.style.width = `${runShare()}%`;
  }, 250);
  try {
    const response = await fetch('/api/test-run', { method: 'POST' });
    const result = await response.json();
    live = result.ok ? { state: 'done', result } : { state: 'error', reason: result.reason };
  } catch {
    live = { state: 'error', reason: 'The local test service is not running; start the console with python3 -m tools.demo.' };
  }
  clearInterval(tick);
  if (route.screen === 'test') render();
}

/* ---------- 5. Watch & roll back ---------- */

function watchModel(d) {
  const key = r => `${r.window_end}|${r.site}|${r.approach}`;
  const watched = {};
  d.feeds.forEach(rows => rows.forEach(r => (watched[key(r)] ||= []).push([Number(r.occupancy), Number(r.count)])));
  const day = d.feeds.at(-1);
  const times = [...new Set(day.map(r => r.window_end))].sort();
  const served = [], expected = [];
  let streak = 0, trip = null;
  const points = times.map(t => {
    const rows = day.filter(r => r.window_end === t && r.ok === '1');
    const parts = rows.map(r => {
      const base = watched[key(r)], m = mean(base.map(b => b[0]));
      const sd = Math.sqrt(mean(base.map(b => (b[0] - m) ** 2)));
      return { occ: Number(r.occupancy), m, sd, count: Number(r.count), expected: mean(base.map(b => b[1])) };
    });
    const value = mean(parts.map(p => p.occ)), level = mean(parts.map(p => p.m));
    const line = level + Math.max(RULE.meanRise, RULE.sdFactor * mean(parts.map(p => p.sd)));
    const high = parts.filter(p => p.occ - p.m > Math.max(RULE.approachRise, RULE.sdFactor * p.sd)).length;
    served.push(sum(parts.map(p => p.count)));
    expected.push(sum(parts.map(p => p.expected)));
    const drop = served.length >= RULE.windows ? 1 - sum(served.slice(-RULE.windows)) / sum(expected.slice(-RULE.windows)) : 0;
    const flagged = value > line || high >= RULE.approaches || drop > RULE.countDrop;
    streak = flagged ? streak + 1 : 0;
    if (streak === RULE.windows && !trip) trip = t;
    return { t: t.slice(11, 16), value, level, line, flagged };
  });
  return { points, trip: trip && trip.slice(11, 16) };
}

function watchChart(model, shown) {
  const pts = model.points, W = 760, H = 230, L = 40, R = 110, T = 12, B = 26;
  const top = Math.ceil(Math.max(...pts.map(p => Math.max(p.value, p.line))) / 5) * 5;
  const x = i => L + i / (pts.length - 1) * (W - L - R);
  const y = v => T + (1 - v / top) * (H - T - B);
  const path = (list, f) => list.map((p, i) => `${x(i)},${y(f(p))}`).join(' ');
  const grid = [0, 0.25, 0.5, 0.75, 1].map(f => `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(top * f)}" y2="${y(top * f)}"/><text x="${L - 6}" y="${y(top * f) + 4}" text-anchor="end">${top * f}</text>`).join('');
  const ticks = pts.map((p, i) => i % 3 ? '' : `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${p.t}</text>`).join('');
  const now = pts.slice(0, shown);
  const end = pts.at(-1);
  const labels = [{ text: 'Roll-back line', y: y(end.line), color: 'var(--r)' }, { text: 'Sensors', y: y(end.value), color: 'var(--accent)' },
    { text: 'Normal level', y: y(end.level), color: 'var(--muted)' }].sort((a, b) => a.y - b.y);
  labels.forEach((l, i) => { if (i) l.y = Math.max(l.y, labels[i - 1].y + 14); });
  const last = now.at(-1);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="How busy the road sensors are every five minutes, against the roll-back line">
    ${grid}${ticks}
    <polyline points="${path(pts, p => p.line)}" fill="none" stroke="var(--r)" stroke-width="1.5" stroke-dasharray="6 4"/>
    <polyline points="${path(pts, p => p.level)}" fill="none" stroke="var(--old)" stroke-width="1.5" stroke-dasharray="2 3"/>
    <polyline id="replay-line" points="${path(now, p => p.value)}" fill="none" stroke="var(--accent)" stroke-width="2.5"/>
    ${last ? `<circle cx="${x(now.length - 1)}" cy="${y(last.value)}" r="4.5" fill="var(--accent)"/>` : ''}
    ${labels.map(l => `<text x="${W - R + 8}" y="${l.y + 4}" style="fill:${l.color}">${l.text}</text>`).join('')}
  </svg>`;
}

function goBackTable(d) {
  const count = (road, program) => {
    const runs = d.goBack.filter(r => r.road === road && r.program === program);
    return `${runs.filter(r => r.go_back).length} of ${runs.length}`;
  };
  return `<table><thead><tr><th>Rule tested on new simulated days</th><th class="num">Wolfe</th><th class="num">De Anza</th></tr></thead><tbody>
    <tr><td>Bad change: rolled back</td><td class="num">${count('wolfe', 'bad')}</td><td class="num">${count('deanza', 'bad')}</td></tr>
    <tr><td>Harmless change: rolled back by mistake</td><td class="num">${count('wolfe', 'noop')}</td><td class="num">${count('deanza', 'noop')}</td></tr>
    </tbody></table>`;
}

function watch(d) {
  const head = `<div class="head"><div><h1>Watch &amp; roll back</h1><p>Go back to the old timing if traffic is clearly worse for ${RULE.windows * 5} minutes in a row.</p></div></div>`;
  const fullRule = more('How this works', `<p class="small">This demo replays saved simulated sensor readings in 5-minute windows. A window counts as worse when the sensors run above their normal range,
    when ${RULE.approaches} or more directions rise over ${RULE.approachRise} points, or when cars served fall more than ${RULE.countDrop * 100}% below normal.
    ${RULE.windows} worse windows in a row trigger the roll-back.</p>`);
  if (!isChange(d) || decision(d).status !== 'approved') {
    const why = !isChange(d) ? 'No change was recommended, so there is nothing to watch.'
      : decision(d).status === 'rejected' ? 'The change was rejected, so there is nothing to watch.'
      : 'Approve the recommendation first.';
    return `${head}<div class="banner idle" style="margin-bottom:16px"><span>${why}</span>${isChange(d) && !decision(d).status ? `<a class="btn primary" href="#/${d.road}/recommendation">Go to recommendation</a>` : ''}</div>
      <div class="card stack">${goBackTable(d)}${fullRule}</div>`;
  }
  const model = watchModel(d);
  const state = model.trip ? [`Would roll back at ${model.trip}`, 'bad'] : ['No roll-back needed', 'ok'];
  return `${head}
    <div class="card stack" style="margin-bottom:16px">
      <div class="actions" style="justify-content:space-between"><span class="actions">${pill(state)}<span class="small muted" id="replay-clock">${model.points.at(-1).t}</span></span>
        <button class="btn primary" data-action="replay">Play sensor replay</button></div>
      <div id="watch-chart">${watchChart(model, model.points.length)}</div>
      <p class="small muted">${tip('How busy the road sensors are', 'Occupancy: the share of time a car sits over the sensor. Higher means longer queues.')} (%), every 5 minutes, on a saved evening.</p>
      ${fullRule}
    </div>
    <div class="card">${goBackTable(d)}</div>`;
}

function replay(d) {
  clearInterval(timer);
  const model = watchModel(d);
  let shown = 1;
  timer = setInterval(() => {
    const chart = document.getElementById('watch-chart'), stamp = document.getElementById('replay-clock');
    if (!chart) return clearInterval(timer);
    chart.innerHTML = watchChart(model, shown);
    stamp.textContent = model.points[shown - 1].t;
    if (++shown > model.points.length) clearInterval(timer);
  }, 140);
}

/* ---------- 6. How it connects ---------- */

function box(x, y, w, h, title, lines, opts = {}) {
  return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${opts.fill || '#fff'}" stroke="${opts.stroke || '#cfd4dc'}" ${opts.dash ? 'stroke-dasharray="6 4"' : ''} stroke-width="1.5"/>
    <text class="t" x="${x + 12}" y="${y + 22}">${title}</text>${lines.map((l, i) => `<text x="${x + 12}" y="${y + 42 + i * 16}">${l}</text>`).join('')}</g>`;
}
const arrow = (x1, y1, x2, y2, opts = {}) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${opts.color || '#5a6371'}" stroke-width="1.8" ${opts.dash ? 'stroke-dasharray="5 4"' : ''} marker-end="url(#${opts.color ? 'ha' : 'h'})"/>`;

function connect() {
  const svg = `<svg class="diagram" viewBox="-2 0 1064 400" role="img" aria-label="Road sensors feed the signal cabinet. The cabinet links to the city's central system, which the engineer uses. Signal Learner sits beside them, read-only, and gives the engineer a card.">
    <defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#5a6371"/></marker>
      <marker id="ha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#1f4fd6"/></marker></defs>
    ${box(0, 20, 170, 150, 'Road sensors', ['Loops: wires cut', 'into the pavement', 'Video cameras', 'Radar'])}
    <rect x="200" y="10" width="330" height="220" rx="10" fill="#f5f6f8" stroke="#cfd4dc" stroke-width="1.5"/>
    <text class="t" x="214" y="32">Signal cabinet, at the corner</text>
    ${box(214, 44, 302, 84, 'Controller', ['A computer that runs the stored timing plan'])}
    ${box(214, 138, 302, 80, 'Conflict monitor', ['A separate safety device. If it sees conflicting', 'greens, it puts the intersection into flash.'], { stroke: '#d6453a' })}
    ${box(560, 20, 140, 110, 'Network link', ['Cabinet to the', 'central system'])}
    ${box(730, 20, 150, 130, 'Central system', ['City staff monitor', 'and manage', 'controllers remotely'])}
    ${box(910, 20, 130, 130, 'City engineer', ['Decides, and enters', 'any timing change'], { fill: '#eaf0fe', stroke: '#1f4fd6' })}
    ${arrow(170, 86, 212, 86)}${arrow(516, 86, 558, 86)}${arrow(700, 76, 728, 76)}
    ${arrow(880, 66, 908, 66)}${arrow(908, 110, 882, 110)}
    <text x="880" y="170" text-anchor="middle">enters changes</text>
    ${box(200, 290, 680, 96, 'Signal Learner (this software) · READ-ONLY', ['Reads counts, controller logs and timing sheets. Never writes to the cabinet or central system.', 'Learns the pattern, practices plans on a copy, and gives the engineer one card to approve or reject.'], { fill: '#fff', stroke: '#1f4fd6', dash: true })}
    ${arrow(290, 228, 290, 288, { dash: true, color: '#1f4fd6' })}<text x="300" y="262" style="fill:#1f4fd6">counts and logs (read)</text>
    ${arrow(805, 150, 805, 288, { dash: true, color: '#1f4fd6' })}<text x="797" y="262" text-anchor="end" style="fill:#1f4fd6">timing sheets (read)</text>
    ${arrow(880, 330, 975, 152, { color: '#1f4fd6' })}<text x="935" y="262" style="fill:#1f4fd6">card</text>
  </svg>`;
  return `
  <div class="head"><div><h1>How it connects</h1><p>Example city workflow below. This demo uses saved simulation files, with no city connection.</p></div></div>
  <div class="card" style="margin-bottom:16px">${svg}</div>
  <div class="path3" style="margin-bottom:16px">
    <div class="card stack"><h2><span class="n">1</span>Read</h2><p class="small">Counts, ${tip('controller logs', 'High-resolution logs: every signal and sensor event, to the nearest 0.1 s.')} and timing sheets, requested from the city.<sup>[2]</sup></p></div>
    <div class="card stack"><h2><span class="n">2</span>Recommend</h2><p class="small">The engineer reviews the card and enters any change. Google's Project Green Light also gives city engineers recommendations.<sup>[6]</sup></p></div>
    <div class="card stack later"><h2><span class="n">3</span>Much later</h2><p class="small">A direct link to the central system, only with city approval and a safety review.<sup>[7]</sup></p></div>
  </div>
  <div class="card stack"><h2>Good to know</h2>
    <ul class="facts small">
      <li>A time-of-day schedule picks which timing plan runs when.<sup>[1]</sup></li>
      <li>The conflict monitor is separate from the controller. Our software never touches it.<sup>[5]</sup></li>
      <li>Timing changes are made at the cabinet or from the central system.<sup>[4]</sup> Some city codes give this to the city traffic engineer.<sup>[10]</sup></li>
      <li>Cupertino chose Cubic Trafficware for its central system (2019).<sup>[8]</sup></li>
      <li>Why read-only: a 2023 US cybersecurity advisory says to keep signal networks off the internet.<sup>[9]</sup></li>
    </ul>
    ${more('Sources (10)', `<ol class="sources">
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
  </ol>`)}
  </div>`;
}

/* ---------- Next cue: Corridor → Recommendation → Test it → Watch → How it connects ---------- */

const NEXT = { corridor: 'recommendation', signal: 'recommendation', recommendation: 'test', test: 'watch', watch: 'connect' };
const NAMES = { recommendation: 'Recommendation', test: 'Test it', watch: 'Watch & roll back', connect: 'How it connects' };
const nextCue = d => NEXT[route.screen]
  ? `<a class="next no-print" href="#/${d.road}/${NEXT[route.screen]}">Next: ${esc(NAMES[NEXT[route.screen]])} <span aria-hidden="true">→</span></a>` : '';

/* ---------- Shell ---------- */

function parseRoute() {
  const [, road, screen, index] = location.hash.split('/');
  return { road: ROADS.includes(road) ? road : 'wolfe', screen: SCREENS.includes(screen) ? screen : 'corridor',
    index: Math.max(0, parseInt(index, 10) || 0) };
}

const VIEWS = { corridor, signal, recommendation, test, watch, connect };

async function render() {
  clearInterval(timer);
  const next = parseRoute();
  const moved = next.screen !== route.screen || next.road !== route.road || next.index !== route.index;
  if (next.road !== route.road || next.screen !== route.screen) rejecting = false;
  route = next;
  document.querySelectorAll('#nav a').forEach(a => {
    const screen = a.dataset.screen;
    a.href = `#/${route.road}/${screen}${screen === 'signal' ? `/${route.screen === 'signal' ? route.index : 0}` : ''}`;
    if (screen === route.screen) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  document.querySelectorAll('[data-road]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.road === route.road)));
  try {
    const d = await data(route.road);
    const [text, kind] = roadStatus(d);
    const color = { ok: 'var(--ok)', info: 'var(--accent)', idle: 'var(--faint)' }[kind];
    document.getElementById('top-title').innerHTML = `${esc(d.info.street)} · <span class="dot" style="background:${color}"></span>${esc(text)}`;
    document.title = `${route.screen[0].toUpperCase() + route.screen.slice(1)} · ${d.info.street} · Signal Learner`;
    main.innerHTML = VIEWS[route.screen](d) + nextCue(d);
  } catch (err) {
    main.innerHTML = `<div class="card"><h1>Could not load the saved files</h1><p class="muted">${esc(err.message)}. Start the console with python3 -m tools.demo, then reload.</p></div>`;
  }
  if (moved && !firstRender) {
    const h1 = main.querySelector('h1');
    if (h1) { h1.tabIndex = -1; h1.focus({ preventScroll: true }); }
    window.scrollTo(0, 0);
  }
  firstRender = false;
}

main.addEventListener('click', async event => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const d = await data(route.road);
  const action = button.dataset.action;
  if (action === 'approve') decisions[d.road] = { status: 'approved', at: new Date().toISOString() };
  else if (action === 'archive') decisions[d.road] = { status: 'rejected', at: new Date().toISOString(), note: document.getElementById('note').value.trim() };
  else if (action === 'reopen') delete decisions[d.road];
  else if (action === 'reject') { rejecting = true; render().then(() => document.getElementById('note')?.focus()); return; }
  else if (action === 'cancel') rejecting = false;
  else if (action === 'print') return window.print();
  else if (action === 'run-test') return runTest();
  else if (action === 'replay') return replay(d);
  else if (action === 'video') {
    const dialog = document.getElementById('video-dialog');
    dialog.showModal();
    return document.getElementById('video').play().catch(() => {});
  }
  if (['approve', 'archive', 'reopen', 'cancel'].includes(action)) rejecting = false;
  saveDecisions();
  render();
});

document.querySelectorAll('[data-road]').forEach(b => b.addEventListener('click', () => {
  const screen = route.screen === 'signal' ? 'signal/0' : route.screen;
  location.hash = `#/${b.dataset.road}/${screen}`;
}));
document.getElementById('video-close').addEventListener('click', () => document.getElementById('video-dialog').close());
document.getElementById('video-dialog').addEventListener('close', () => document.getElementById('video').pause());
window.addEventListener('hashchange', render);
render();
