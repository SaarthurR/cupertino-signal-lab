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
    .replaceAll('veh/15 min', 'cars per 15 min');
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
    const label = `${p.sig.signal}, ${text}. Open signal ${p.i + 1}.`;
    return `<a href="#/${d.road}/signal/${p.i}" aria-label="${esc(label)}">
      <line x1="${p.x - 70}" x2="${p.x + 70}" y1="${p.y}" y2="${p.y}" stroke="#cfd4dc" stroke-width="6" stroke-linecap="round"/>
      <circle class="ring" cx="${p.x}" cy="${p.y}" r="14" fill="#fff" stroke="${color}" stroke-width="3"/>
      <text x="${p.x}" y="${p.y + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#151a22">${p.i + 1}</text>
      <text x="${p.x + 86}" y="${p.y - 2}" font-size="13" font-weight="600" fill="#151a22">${esc(p.sig.signal)}</text>
      <text x="${p.x + 86}" y="${p.y + 14}" font-size="12" fill="${color}">${esc(text)}</text>
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
  const sigs = d.card.signals;
  const approaches = new Set(d.pattern.map(r => r.site + r.approach)).size;
  const ready = isChange(d) ? 'Card ready for the engineer' : 'Keep current timing';
  return `
  <div class="head"><div><h1>${esc(d.info.street)} corridor</h1>
    <p>${sigs.length} signals, evening peak ${esc(d.info.begin)}–${esc(d.info.end)}. Select a signal to see its timing.</p></div>
    ${pill(roadStatus(d))}</div>
  <div class="card" style="margin-bottom:16px"><h2 class="sr">Progress</h2><div class="steps">
    <div class="step done"><b>1 · Watched</b><span>${d.feeds.length} evening rush hours of sensor counts</span></div>
    <div class="step done"><b>2 · Learned</b><span>15-minute traffic pattern on ${approaches} approaches</span></div>
    <div class="step done"><b>3 · Practiced</b><span>${d.practice.trials} timing plans tried on a practice copy</span></div>
    <div class="step now"><b>4 · Recommended</b><span>${ready}</span></div>
  </div></div>
  <div class="grid g-map">
    <div class="card"><h2>Map</h2>${mapSvg(d)}</div>
    <div class="card"><h2>Signals</h2>
      <ul class="signal-list">${sigs.map((s, i) => `<li><a href="#/${d.road}/signal/${i}">
        <span><span class="sig-n">${i + 1}</span>${esc(s.signal)}</span>${pill(signalStatus(d, s))}</a></li>`).join('')}</ul>
      <p class="small muted" style="margin-top:12px">Each signal moves through Watching → Learned → Recommendation ready.</p>
      <div class="actions" style="margin-top:14px"><a class="btn primary" href="#/${d.road}/recommendation">Open the recommendation</a></div>
    </div>
  </div>`;
}

/* ---------- 2. Signal ---------- */

function bar(list, cycle, scale, old) {
  const seg = (cls, s, title, text = '') => s > 0
    ? `<div class="${cls}" style="width:${s / cycle * 100}%" title="${esc(title)}">${text}</div>` : '';
  const body = list.map(p => seg(`seg-g${old ? ' old' : ''}`, p.max_green_s, `Phase ${p.phase} green ${f1(p.max_green_s)} s`,
      p.max_green_s / scale > 0.08 ? `Ph ${p.phase} · ${f1(p.max_green_s)}` : '')
    + seg('seg-y', p.yellow, `Yellow ${f1(p.yellow)} s`) + seg('seg-r', p.red, `All-red ${f1(p.red)} s`)).join('');
  const label = list.map(p => `phase ${p.phase} green ${f1(p.max_green_s)}, yellow ${f1(p.yellow)}, all-red ${f1(p.red)}`).join('; ');
  return `<div class="bar" style="width:${cycle / scale * 100}%" role="img" aria-label="Cycle ${f1(cycle)} seconds: ${esc(label)}">${body}</div>`;
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
  const table = `<details><summary>Show as table</summary><table><thead><tr><th>Start</th>${legs.map(l => `<th class="num">From ${LEGS[l]}</th>`).join('')}</tr></thead><tbody>
    ${times.map(t => `<tr><td>${clock(t)}</td>${legs.map(l => `<td class="num">${f1(rows.find(r => r.approach === l && Number(r.quarter_start_s) === t)?.mean_count ?? NaN)}</td>`).join('')}</tr>`).join('')}
    </tbody></table></details>`;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Learned vehicles per 15 minutes by approach at ${esc(site)}">${grid}${ticks}${lines}</svg>
    <div class="legend">${legs.map((l, i) => `<span><i style="background:${COLORS[i % 4]}"></i>From ${LEGS[l]}</span>`).join('')}</div>${table}`;
}

function signal(d) {
  const sigs = d.card.signals;
  const sig = sigs[Math.min(route.index, sigs.length - 1)];
  const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
  const scale = Math.max(sig.old.cycle_s, sig.new.cycle_s);
  const ticks = [];
  for (let t = 0; t <= scale; t += 10) ticks.push(`<span style="left:${t / scale * 100}%">${t}</span>`);
  return `
  <div class="head"><div><h1>${esc(sig.signal)}</h1><p>${esc(d.info.street)} · signal ${sigs.indexOf(sig) + 1} of ${sigs.length}</p></div>${pill(signalStatus(d, sig))}</div>
  <nav class="tabs" aria-label="Signals">${sigs.map((s, i) => `<a href="#/${d.road}/signal/${i}" ${s === sig ? 'aria-current="page"' : ''}>${i + 1} · ${esc(s.signal)}</a>`).join('')}</nav>
  <div class="card" style="margin-bottom:16px">
    <h2>One cycle, old above new</h2>
    <div class="bar-row"><div class="lbl"><b>Old timing</b><span>cycle ${f1(sig.old.cycle_s)} s · offset ${f1(sig.old.offset_s)} s</span></div>${bar(old, sig.old.cycle_s, scale, true)}</div>
    <div class="bar-row"><div class="lbl"><b>New timing</b><span>cycle ${f1(sig.new.cycle_s)} s · offset ${f1(sig.new.offset_s)} s</span></div>${bar(neu, sig.new.cycle_s, scale, false)}</div>
    <div class="axis" aria-hidden="true"><div></div><div class="ticks">${ticks.join('')}</div></div>
    <div class="legend" style="margin:6px 0 14px"><span><i style="background:var(--g)"></i>Green (longest allowed)</span><span><i style="background:var(--y)"></i>Yellow</span><span><i style="background:var(--r)"></i>All-red</span><span><i style="background:#e8ebf0"></i>Rest of cycle</span><span>Seconds</span></div>
    <div class="defs">
      <div class="def"><b>Cycle</b>One full round of greens for every direction.</div>
      <div class="def"><b>Offset</b>When this light starts its round, so greens line up along the road.</div>
      <div class="def"><b>Green per phase</b>The longest green each group of movements may get.</div>
    </div>
  </div>
  <div class="grid g2">
    <div class="card"><h2>Green per phase</h2>
      <table><thead><tr><th>Phase</th><th>Who moves</th><th class="num">Green, s</th></tr></thead><tbody>
      ${old.map((p, i) => `<tr><td>${p.phase}</td><td>${esc(serves(p.serves))}</td><td class="num">${change(p.max_green_s, neu[i].max_green_s, '')}</td></tr>`).join('')}
      </tbody></table>
      <p class="small muted" style="margin-top:10px">Why: ${esc(plainReason(sig.reason))}.</p>
    </div>
    <div class="card"><h2>What the sensors taught it</h2><p class="sub" style="margin-bottom:6px">Average vehicles per 15 minutes, by approach</p>${patternChart(d, sig.signal)}</div>
  </div>`;
}

/* ---------- 3. Recommendation ---------- */

function sheet(d) {
  const at = new Date(decision(d).at);
  return `<section class="sheet" aria-labelledby="sheet-title">
    <div class="sheet-head"><div><h2 id="sheet-title">Timing change sheet</h2><p class="muted small">Prepared from the approved Signal Learner card · simulation result</p></div><span class="stamp">Draft for engineer entry</span></div>
    <dl>
      <dt>Corridor</dt><dd>${esc(d.info.street)}, ${d.card.signals.length} intersections</dd>
      <dt>Coordination plan</dt><dd>Evening peak, time-of-day plan ${esc(d.info.begin)}–${esc(d.info.end)}</dd>
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
    <p class="small muted" style="margin-top:12px">Seconds. Split = max green + yellow + all-red. Phase numbers are the simulator's; map them to the controller's phase numbers when entering.</p>
    <div class="sign"><div>Reviewed by (traffic engineer)</div><div>Entered into controller / central system by</div><div>Date entered</div></div>
  </section>`;
}

function decisionBlock(d) {
  const dec = decision(d);
  if (dec.status === 'approved') {
    return `<div class="banner ok no-print"><span><b>Approved.</b> The timing change sheet below is ready to print for entry. Watching starts after entry.</span>
      <span class="actions"><button class="btn primary" data-action="print">Print sheet</button><a class="btn" href="#/${d.road}/watch">Go to watch</a><button class="btn ghost" data-action="reopen">Undo</button></span></div>
      <div style="margin-top:16px">${sheet(d)}</div>`;
  }
  if (dec.status === 'rejected') {
    return `<div class="banner bad"><span><b>Rejected and archived</b> ${esc(new Date(dec.at).toLocaleString())}.${dec.note ? ` Note: “${esc(dec.note)}”` : ''} Current timing stays.</span>
      <button class="btn" data-action="reopen">Reopen card</button></div>`;
  }
  if (rejecting) {
    return `<div class="card"><label class="field" for="note">Why reject? (kept with the archived card)</label>
      <textarea id="note" placeholder="For example: conflicts with the school-zone plan"></textarea>
      <div class="actions" style="margin-top:10px"><button class="btn danger" data-action="archive">Reject and archive</button><button class="btn ghost" data-action="cancel">Cancel</button></div></div>`;
  }
  return `<div class="actions"><button class="btn primary" data-action="approve">Approve</button><button class="btn" data-action="reject">Reject</button>
    <span class="small muted">The engineer decides. Nothing is sent to any signal.</span></div>`;
}

function recommendation(d) {
  const c = d.card, e = c.expected_in_copy, sigs = c.signals;
  const table = `<table><thead><tr><th>Signal</th><th class="num">Cycle</th><th class="num">Offset</th><th class="num">Main green</th><th>Reason</th></tr></thead><tbody>
    ${sigs.map(s => `<tr><td>${esc(s.signal)}</td><td class="num">${change(s.old.cycle_s, s.new.cycle_s)}</td><td class="num">${change(s.old.offset_s, s.new.offset_s)}</td>
      <td class="num">${change(s.old.greens[0].max_green_s, s.new.greens[0].max_green_s)}</td><td class="small">${esc(plainReason(s.reason))}</td></tr>`).join('')}
    </tbody></table>`;
  if (!isChange(d)) return deanzaCard(d, table);
  const minSame = sigs.every(s => s.old.greens.every((g, i) => g.min_green_s === s.new.greens[i].min_green_s && g.phase === s.new.greens[i].phase));
  const oldCycles = [...new Set(sigs.map(s => s.old.cycle_s))], newCycles = [...new Set(sigs.map(s => s.new.cycle_s))];
  const plain = oldCycles.length === 1 && newCycles.length === 1
    ? `All ${sigs.length} lights move together from a ${f1(oldCycles[0])} s to a ${f1(newCycles[0])} s cycle. The extra time goes to the busiest movements the sensors counted, and offsets shift so greens line up along ${esc(d.info.street)}.`
    : 'Cycles, offsets and the longest greens change so the busiest movements the sensors counted get more time.';
  return `
  <div class="no-print">
  <div class="head"><div><h1>Recommendation</h1><p>${esc(d.info.street)} · evening peak ${esc(d.info.begin)}–${esc(d.info.end)} · ${sigs.length} signals</p></div>${pill(roadStatus(d))}</div>
  <div class="grid g2" style="margin-bottom:16px">
    <div class="card stack"><h2>Reason</h2><p>${plain}</p><p class="small muted">Card: “${esc(c.why)}”</p></div>
    <div class="card stack"><h2>Expected effect in the practice copy</h2>
      <div class="effect"><span class="big">${f1(e.old_delay_s)} s<span class="arrow">→</span>${f1(e.new_delay_s)} s</span><span class="delta">${signed(e.change_share * 100)}%</span></div>
      <p class="small muted">Average delay per trip over ${e.copy_seeds.length} practice rush hours (range ${signed(e.change_range_s[0])} to ${signed(e.change_range_s[1])} s). The practice copy is a simulated road built only from sensor counts.</p></div>
  </div>
  <div class="card" style="margin-bottom:16px"><h2>Old → new, per signal</h2>${table}</div>
  <div class="card stack" style="margin-bottom:16px"><h2>Guardrails</h2>
    <div class="chips"><span class="small muted" style="align-self:center">Unchanged:</span><span class="chip">Phase order</span><span class="chip">Yellow</span><span class="chip">All-red</span><span class="chip">Minimum greens${minSame ? ' ✓' : ''}</span>
      <span class="small muted" style="align-self:center;margin-left:10px">Changed, within bounds:</span><span class="chip changed">Cycle</span><span class="chip changed">Offsets</span><span class="chip changed">Longest greens</span></div>
    <p class="small muted">${esc(c.limits)}</p></div>
  </div>
  ${decisionBlock(d)}`;
}

function deanzaCard(d, table) {
  const p = d.practice, e = d.card.expected_in_copy, margin = p.settings.teleport_margin;
  const failed = p.confirm_new.filter((run, i) => run.teleports > p.confirm_old[i].teleports + margin).length;
  const post = d.posthoc, postPlan = post.rejected_plan.all_requested_delay_s.mean;
  return `
  <div class="head"><div><h1>Recommendation</h1><p>${esc(d.info.street)} · evening peak ${esc(d.info.begin)}–${esc(d.info.end)} · ${d.card.signals.length} signals</p></div>${pill(roadStatus(d))}</div>
  <div class="card stack" style="margin-bottom:16px">
    <h2 style="font-size:20px">No change — keep current timing</h2>
    <p>The best practice plan looked faster in the practice copy (${f1(e.old_delay_s)} → ${f1(e.new_delay_s)} s per trip), but it failed the feasibility check:
      on ${failed} of ${p.confirm_new.length} practice rush hours it jammed badly enough that the simulator removed more than ${margin} extra stuck cars. So the card keeps the current timing.</p>
    <p class="small muted">The archived card says “${esc(d.card.why)}” That sentence was inaccurate; the failed check is the real reason. A later check (post-hoc, ${post.seeds.length} new traffic days) found the rejected plan ${signed((postPlan - post.old_delay_s) / post.old_delay_s * 100)}% worse: ${f1(post.old_delay_s)} → ${f1(postPlan)} s.</p>
  </div>
  <div class="card" style="margin-bottom:16px"><h2>Current timing, per signal</h2>${table}</div>
  <div class="banner idle"><span>Nothing to approve or enter. The console keeps watching the sensors.</span></div>`;
}

/* ---------- 4. Test it ---------- */

function pairedChart(h) {
  const W = 500, H = 200, L = 44, R = 10, T = 10, B = 26;
  const values = h.pairs.flatMap(p => [p.old, p.plan]);
  const lo = Math.floor(Math.min(...values) / 100) * 100, hi = Math.ceil(Math.max(...values) / 100) * 100;
  const x = i => L + (i + 0.5) / h.pairs.length * (W - L - R);
  const y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const grid = [];
  for (let v = lo; v <= hi; v += 100) grid.push(`<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`);
  const marks = h.pairs.map((p, i) => `<line x1="${x(i)}" x2="${x(i)}" y1="${y(p.old)}" y2="${y(p.plan)}" stroke="#cfd4dc" stroke-width="2"/>
    <circle cx="${x(i)}" cy="${y(p.old)}" r="4" fill="var(--old)"/><circle cx="${x(i)}" cy="${y(p.plan)}" r="4" fill="var(--accent)"/>`).join('');
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Delay score on ${h.pairs.length} held-out traffic days, old timing versus new plan">${grid.join('')}${marks}
    <text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${h.pairs.length} held-out traffic days (seeds ${h.pairs[0].seed}–${h.pairs.at(-1).seed})</text></svg>
    <div class="legend"><span><i style="background:var(--old)"></i>Old timing</span><span><i style="background:var(--accent)"></i>Signal Learner plan</span><span>Delay score, s</span></div>`;
}

function liveBlock(d) {
  if (!live) return `<p class="small muted">Not run yet.</p>`;
  if (live.state === 'running') return `<div role="status"><div class="progress"><i></i></div><p>Running the simulator for the old timing and the new plan… <span id="elapsed">0</span> s</p></div>`;
  if (live.state === 'error') return `<div role="status" class="banner idle"><span><b>Live test unavailable.</b> ${esc(live.reason)} The saved held-out result is shown instead.</span></div>`;
  const r = live.result, saved = heldout(d).pairs.find(p => p.seed === r.seed), pct = (r.learner.delay_s - r.old.delay_s) / r.old.delay_s * 100;
  const match = saved && f1(saved.old) === f1(r.old.delay_s) && f1(saved.plan) === f1(r.learner.delay_s);
  return `<div role="status" class="stack">
    <div class="score"><div><div class="k">Old timing</div><div class="v">${f1(r.old.delay_s)} s</div><div class="small muted">${r.old.unfinished} trips unfinished</div></div>
      <div><div class="k">New plan</div><div class="v">${f1(r.learner.delay_s)} s</div><div class="small muted">${r.learner.unfinished} trips unfinished</div></div>
      <div class="pct">${signed(pct)}%</div></div>
    <p class="small muted">Traffic day ${r.seed} · simulator time ${f1(r.wall_s)} s.${match ? ` Matches the saved held-out run for day ${r.seed}.` : ''}</p></div>`;
}

function test(d) {
  if (!isChange(d)) {
    const h = heldout(d);
    return `<div class="head"><div><h1>Test it</h1><p>${esc(d.info.street)}</p></div>${pill(roadStatus(d))}</div>
      <div class="card stack"><h2>Nothing new to test</h2><p>The card keeps the current timing, so in the held-out test the “learner” arm ran the old timing:
        ${f1(h.oldMean)} s average delay score on ${h.pairs.length} traffic days, the same as before.</p>
        <p class="small muted">Switch to Wolfe to run a live test.</p></div>`;
  }
  const h = heldout(d), busy = live && live.state === 'running';
  const unavailable = live && live.state === 'error';
  return `
  <div class="head"><div><h1>Test it</h1><p>Run the new plan on simulated traffic the learner never saw, next to the old timing.</p></div>${pill(roadStatus(d))}</div>
  <div class="grid g2">
    <div class="card stack"><h2>Live test on new traffic</h2>
      <p class="sub">Runs ${esc(d.info.street)} twice on one held-out traffic day: once with the old timing, once with the new plan.</p>
      <div class="actions"><button class="btn primary" data-action="run-test" ${busy ? 'disabled' : ''}>${busy ? 'Running…' : unavailable ? 'Simulator not available · try again' : live ? 'Run again' : 'Run test on new traffic'}</button></div>
      <div id="live">${liveBlock(d)}</div>
      <p class="small muted">Delay score: average delay per requested trip, including the penalty for every trip that never finished.</p>
    </div>
    <div class="card stack"><h2>Saved held-out result</h2>
      <div class="score"><div><div class="k">Old timing</div><div class="v">${f1(h.oldMean)} s</div></div>
        <div><div class="k">New plan</div><div class="v">${f1(h.planMean)} s</div></div><div class="pct">${signed(h.pct)}%</div></div>
      <p class="small muted">Average of ${h.pairs.length} runs · new plan better on ${h.better} of ${h.pairs.length}. Test rules were written before the one-time run.</p>
      ${pairedChart(h)}
      <div class="actions"><button class="btn" data-action="video">Watch the replay</button></div>
    </div>
  </div>`;
}

async function runTest() {
  live = { state: 'running', started: Date.now() };
  render();
  const tick = setInterval(() => {
    const el = document.getElementById('elapsed');
    if (el) el.textContent = Math.round((Date.now() - live.started) / 1000);
  }, 500);
  try {
    const response = await fetch('/api/test-run', { method: 'POST' });
    const result = await response.json();
    live = result.ok ? { state: 'done', result } : { state: 'error', reason: result.reason };
  } catch {
    live = { state: 'error', reason: 'The local test service is not running; open the console through python3 -m tools.demo.' };
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
  const labels = [{ text: 'Rollback line', y: y(end.line), color: 'var(--r)' }, { text: 'Replay', y: y(end.value), color: 'var(--accent)' },
    { text: 'Watched level', y: y(end.level), color: 'var(--muted)' }].sort((a, b) => a.y - b.y);
  labels.forEach((l, i) => { if (i) l.y = Math.max(l.y, labels[i - 1].y + 14); });
  const last = now.at(-1);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Average sensor occupancy every five minutes against the rollback line">
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
  return `<table><thead><tr><th>Held-out check of this rule (simulation)</th><th class="num">Wolfe</th><th class="num">De Anza</th></tr></thead><tbody>
    <tr><td>Deliberately bad change: rolled back</td><td class="num">${count('wolfe', 'bad')}</td><td class="num">${count('deanza', 'bad')}</td></tr>
    <tr><td>Harmless change: rolled back by mistake</td><td class="num">${count('wolfe', 'noop')}</td><td class="num">${count('deanza', 'noop')}</td></tr>
    </tbody></table>`;
}

function watch(d) {
  const head = `<div class="head"><div><h1>Watch &amp; roll back</h1><p>After an approved change is entered, the console keeps reading the sensors.</p></div>${pill(roadStatus(d))}</div>`;
  const rule = `<p><b>Rule:</b> go back to the old timing if the sensors show clearly worse traffic for ${RULE.windows * 5} minutes in a row (${RULE.windows} five-minute windows): queues above the watched range, or fewer cars served.</p>`;
  if (!isChange(d) || decision(d).status !== 'approved') {
    const why = !isChange(d) ? 'No change was recommended, so there is nothing to roll back.'
      : decision(d).status === 'rejected' ? 'The card was rejected, so the current timing stays and there is nothing to roll back.'
      : 'Approve the recommendation first. Watching starts once an approved change is entered.';
    return `${head}<div class="card stack">${rule}<div class="banner idle"><span>${why}</span>${isChange(d) && !decision(d).status ? `<a class="btn primary" href="#/${d.road}/recommendation">Go to recommendation</a>` : ''}</div></div>
      <div class="card" style="margin-top:16px">${goBackTable(d)}</div>`;
  }
  const model = watchModel(d);
  const state = model.trip ? [`Would roll back at ${model.trip}`, 'bad'] : ['Watching · no rollback', 'ok'];
  return `${head}
    <div class="card stack" style="margin-bottom:16px">
      <div class="actions" style="justify-content:space-between"><span class="actions">${pill(state)}<span class="pill idle">Replay</span><span class="small muted" id="replay-clock">${model.points.at(-1).t}</span></span>
        <button class="btn" data-action="replay">Play replay</button></div>
      <div id="watch-chart">${watchChart(model, model.points.length)}</div>
      <p class="small muted">Replay of the saved sensor feed (watch day ${d.feeds.length}, ${esc(d.info.street)}), average queue-sensor occupancy across all approaches, %. A live install would read the feed after the change is entered.</p>
      ${rule}
      <p class="small muted">The full rule also flags a window when ${RULE.approaches} or more approaches rise over ${RULE.approachRise} points, or when cars served over ${RULE.windows * 5} minutes fall more than ${RULE.countDrop * 100}% below the watched level.</p>
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
    ${box(214, 138, 302, 80, 'Conflict monitor (MMU)', ['A separate safety device. If it sees conflicting', 'greens, it puts the intersection into flash.'], { stroke: '#d6453a' })}
    ${box(560, 20, 140, 110, 'Network link', ['Cabinet to the', 'central system'])}
    ${box(730, 20, 150, 130, 'Central system', ['(ATMS) City staff', 'monitor and manage', 'controllers remotely'])}
    ${box(910, 20, 130, 130, 'City engineer', ['Decides, and enters', 'any timing change'], { fill: '#eaf0fe', stroke: '#1f4fd6' })}
    ${arrow(170, 86, 212, 86)}${arrow(516, 86, 558, 86)}${arrow(700, 76, 728, 76)}
    ${arrow(880, 66, 908, 66)}${arrow(908, 110, 882, 110)}
    <text x="880" y="170" text-anchor="middle">enters changes</text>
    ${box(200, 290, 680, 96, 'Signal Learner (this software) · READ-ONLY', ['Reads counts, high-resolution logs and timing sheets. Never writes to the cabinet or central system.', 'Learns the pattern, practices plans on a copy, and gives the engineer one card to approve or reject.'], { fill: '#fff', stroke: '#1f4fd6', dash: true })}
    ${arrow(290, 228, 290, 288, { dash: true, color: '#1f4fd6' })}<text x="300" y="262" style="fill:#1f4fd6">counts and logs (read)</text>
    ${arrow(805, 150, 805, 288, { dash: true, color: '#1f4fd6' })}<text x="700" y="262" style="fill:#1f4fd6">timing sheets (read)</text>
    ${arrow(880, 330, 975, 152, { color: '#1f4fd6' })}<text x="935" y="262" style="fill:#1f4fd6">card</text>
  </svg>`;
  return `
  <div class="head"><div><h1>How it connects</h1><p>What is already on the street, and where our software would sit. It reads; the engineer decides and enters.</p></div></div>
  <div class="card" style="margin-bottom:16px">${svg}</div>
  <div class="path3" style="margin-bottom:16px">
    <div class="card stack"><h2><span class="n">1</span>Read</h2><p class="small">Counts, high-resolution controller logs (ATSPM: events logged to the nearest 100 ms, pulled from the controller) and current timing sheets. Proposed first step: request these records from the city.<sup>[2]</sup></p></div>
    <div class="card stack"><h2><span class="n">2</span>Recommend</h2><p class="small">The engineer compares the card with their own plan and enters any change in their own system. Google's Project Green Light works this way: recommendations go to city engineers, who apply them.<sup>[6]</sup></p></div>
    <div class="card stack later"><h2><span class="n">3</span>Much later</h2><p class="small">Only with city approval and a safety review: a central-system connection through NTCIP 1202, the standard for central-to-controller data (version v04 uses SNMPv3).<sup>[7]</sup></p></div>
  </div>
  <div class="grid g2" style="margin-bottom:16px">
    <div class="card stack"><h2>Plain facts</h2>
      <p class="small"><b>The controller</b> steps through phases using the stored plan, detector calls and the clock.<sup>[4]</sup> <b>A time-of-day schedule</b> picks which plan runs when.<sup>[1]</sup> <b>Loops</b> are wires cut into the pavement.<sup>[3]</sup></p>
      <p class="small"><b>The conflict monitor</b> is separate from the controller; on a malfunction the intersection goes to flash.<sup>[5]</sup> Our software never touches it.</p>
      <p class="small"><b>Timing changes</b> are made at the cabinet or remotely through a central system.<sup>[4]</sup> Some city codes give the city traffic engineer signal-timing authority.<sup>[10]</sup></p></div>
    <div class="card stack"><h2>Cupertino and safety</h2>
      <p class="small"><b>Cupertino</b> chose Cubic Trafficware for its central system (2019 announcement).<sup>[8]</sup></p>
      <p class="small"><b>Why read-only:</b> a 2023 US cybersecurity advisory on one signal-controller product recommends keeping control networks behind firewalls and off the internet.<sup>[9]</sup></p></div>
  </div>
  <div class="card"><h2>Sources</h2><ol class="sources">
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
  </ol></div>`;
}

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
    document.getElementById('top-title').innerHTML = `${esc(d.info.street)} · ${d.card.signals.length} signals · <span class="dot" style="background:${color}"></span>${esc(text)}`;
    document.title = `${route.screen[0].toUpperCase() + route.screen.slice(1)} · ${d.info.street} · Signal Learner`;
    main.innerHTML = VIEWS[route.screen](d);
  } catch (err) {
    main.innerHTML = `<div class="card"><h1>Could not load the saved files</h1><p class="muted">${esc(err.message)}. Start the console with python3 -m tools.demo.</p></div>`;
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
