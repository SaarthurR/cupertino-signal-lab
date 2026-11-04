'use strict';
// Every number on screen comes from the copied report files in data/, the recording, or the live run.

const ROADS = ['wolfe', 'deanza'];
const STORE = 'signal-learner-console-v2';
const SPEEDS = [60, 120, 240];
const ARMS = ['old', 'plan'];
const ARM_NAME = { old: 'Current timing', plan: 'Signal Learner plan' };

const main = document.getElementById('main');
const cache = {};
let route = { road: 'wolfe', screen: 'overview' };
let decisions = loadDecisions();
let rejecting = false;
let player = null;

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const f1 = x => Number(x).toFixed(1);
const betterOn = h => h.better === h.n ? `all ${h.n}` : `${h.better} of ${h.n}`;
const pct = (from, to) => `${to < from ? '−' : '+'}${Math.abs(Math.round((to - from) / from * 100))}%`;
const mean = v => v.reduce((a, b) => a + b, 0) / v.length;
const LEGS = { N: 'north', S: 'south', E: 'east', W: 'west' };
const TURNS = { L: 'left', T: 'through', R: 'right' };
const seconds = t => { const [h, m] = t.split(':').map(Number); return h * 3600 + m * 60; };
const ampm = s => { const h = Math.floor(s / 3600) % 24, m = Math.floor(s / 60) % 60; return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; };

function loadDecisions() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
}
function saveDecisions() {
  try { localStorage.setItem(STORE, JSON.stringify(decisions)); } catch { /* private mode: keep in memory */ }
}

/* ---------- Data ---------- */

function csv(text) {
  const [head, ...rows] = text.trim().split(/\r?\n/);
  const keys = head.split(',');
  return rows.map(row => Object.fromEntries(row.split(',').map((v, i) => [keys[i], v])));
}

function roadYaml(text) {
  const top = key => (text.match(new RegExp(`^${key}:\\s*'?([^'\\n]*)'?`, 'm')) || [])[1];
  return { street: top('street'), begin: top('begin'), end: top('end'), drain: Number(top('drain_s')) };
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
  const [card, practice, plan, yaml, results, geo] = await Promise.all([
    get(base + 'card.json', 'json'), get(base + 'practice.json', 'json'), get(base + 'plan.add.xml'),
    get(base + 'road.yaml'), get('data/heldout/results.csv'), get(`geo/${road}.json`, 'json')]);
  return (cache[road] = { road, card, practice, clear: clearances(plan), info: roadYaml(yaml), results: csv(results), geo });
}

function heldout(d) {
  const rows = d.results.filter(r => r.road === d.road);
  const by = arm => Object.fromEntries(rows.filter(r => r.arm === arm).map(r => [r.seed, Number(r.all_requested_delay_s)]));
  const old = by('old'), plan = by('learner');
  const seeds = Object.keys(old).filter(s => s in plan);
  const oldMean = mean(seeds.map(s => old[s])), planMean = mean(seeds.map(s => plan[s]));
  return { n: seeds.length, oldMean, planMean, better: seeds.filter(s => plan[s] < old[s]).length };
}

// De Anza: how many confirmation runs of the best new plan jammed (removed more stuck cars than the margin allows).
function jams(d) {
  const p = d.practice, margin = p.settings.teleport_margin;
  return { n: p.confirm_new.length, jammed: p.confirm_new.filter((run, i) => run.teleports > p.confirm_old[i].teleports + margin).length };
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
    return `from ${LEGS[leg] || leg}: ${[...turns].map(t => TURNS[t] || t).join(', ')}`;
  }).join(' · ');
}

const isChange = d => d.card.decision === 'change';
const decision = d => decisions[d.road] || {};

/* ---------- Map (real SUMO lane shapes) ---------- */

// Projection that fits the road's bounds into a w×h box, north up.
function fit(geo, w, h, pad = 14) {
  const [x0, y0, x1, y1] = geo.bounds;
  const k = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
  const ox = (w - (x1 - x0) * k) / 2, oy = (h - (y1 - y0) * k) / 2;
  return { k, x: x => ox + (x - x0) * k, y: y => h - oy - (y - y0) * k };
}

function path(ctx, p, xy) {
  ctx.beginPath();
  ctx.moveTo(p.x(xy[0]), p.y(xy[1]));
  for (let i = 2; i < xy.length; i += 2) ctx.lineTo(p.x(xy[i]), p.y(xy[i + 1]));
}

function canvasFor(box) {
  const canvas = box.querySelector('canvas') || box.appendChild(document.createElement('canvas'));
  const w = box.clientWidth, h = box.clientHeight, r = window.devicePixelRatio || 1;
  canvas.width = Math.round(w * r); canvas.height = Math.round(h * r);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(r, 0, 0, r, 0, 0);
  return { canvas, ctx, w, h };
}

function drawRoads(ctx, geo, p) {
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.fillStyle = '#dfe4ea';
  for (const j of geo.junctions) { path(ctx, p, j); ctx.closePath(); ctx.fill(); }
  ctx.strokeStyle = '#dfe4ea';
  ctx.lineWidth = Math.max(3.2 * p.k, 1.2);
  for (const xy of geo.internal) { path(ctx, p, xy); ctx.stroke(); }
  for (const lane of geo.lanes) {
    ctx.strokeStyle = lane.main ? '#cfd6df' : '#dfe4ea';
    ctx.lineWidth = Math.max(lane.w * p.k, 1.2);
    path(ctx, p, lane.xy); ctx.stroke();
  }
}

const centre = sig => {
  const xs = sig.stops.map(s => s.xy[2]), ys = sig.stops.map(s => s.xy[3]);
  return [mean(xs), mean(ys)];
};

// Static map with named light markers (Overview, De Anza card).
function drawMap(box, geo) {
  const { ctx, w, h } = canvasFor(box);
  const p = fit(geo, w, h, 22);
  drawRoads(ctx, geo, p);
  ctx.font = '600 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  ctx.textBaseline = 'middle';
  geo.signals.forEach(sig => {
    const [cx, cy] = centre(sig), x = p.x(cx), y = p.y(cy);
    ctx.beginPath(); ctx.arc(x, y, 7, 0, 2 * Math.PI);
    ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = '#0369a1'; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, 2.5, 0, 2 * Math.PI); ctx.fillStyle = '#0369a1'; ctx.fill();
    const label = sig.name, tw = ctx.measureText(label).width;
    const lx = x + 14 + tw + 8 < w ? x + 14 : Math.max(4, x - 14 - tw);
    ctx.fillStyle = 'rgba(255,255,255,.88)'; ctx.fillRect(lx - 4, y - 10, tw + 8, 20);
    ctx.fillStyle = '#0f172a'; ctx.fillText(label, lx, y);
  });
}

const mapLabel = geo => `Map of ${geo.street} from the simulation road network, with ${geo.signals.length} traffic lights: ${geo.signals.map(s => s.name).join(', ')}.`;

/* ---------- Overview ---------- */

function overview(w, z) {
  const h = heldout(w), j = jams(z), dec = decision(w);
  const status = dec.status === 'approved' ? ['Approved', 'ok'] : dec.status === 'rejected' ? ['Rejected', 'bad'] : ['Needs review', 'new'];
  return `<div class="page">
  <div class="head"><div><h1>Recommendations</h1>
    <p>You are the traffic engineer. Signal Learner studied two roads in simulation and sent you what it found. Nothing changes until you approve it.</p></div></div>
  <div class="overview">
    <section class="card map-card" aria-labelledby="map-title">
      <div class="row" style="justify-content:space-between"><h2 id="map-title">${esc(w.info.street)}</h2><span class="hint">${w.geo.signals.length} traffic lights</span></div>
      <div class="map" id="overview-map" role="img" aria-label="${esc(mapLabel(w.geo))}"></div>
    </section>
    <section class="inbox" aria-label="Inbox">
      <h2 class="label">Inbox</h2>
      <article class="card rec primary">
        <div class="meta"><span class="pill ${status[1]}">${status[0]}</span><span>Evening peak, ${ampm(seconds(w.info.begin))}–${ampm(seconds(w.info.end))}</span></div>
        <h3>${esc(w.info.street)}: new timing ready for review</h3>
        <p class="muted">Longer greens for the busiest directions, lined up along the road, at all ${w.card.signals.length} lights.</p>
        <div class="proof"><b>${pct(h.oldMean, h.planMean)}</b><span>delay, tested on ${h.n} new evenings. Better on ${betterOn(h)}.</span></div>
        <div class="row"><a class="btn primary lg" href="#/wolfe/review">Review recommendation</a>
          ${dec.status === 'approved' ? '<a class="btn lg" href="#/wolfe/simulate?run">Run the simulation</a>' : ''}</div>
      </article>
      <article class="card rec">
        <div class="meta"><span class="pill">No change</span><span>Evening peak, ${ampm(seconds(z.info.begin))}–${ampm(seconds(z.info.end))}</span></div>
        <h3>${esc(z.info.street)}: no change needed</h3>
        <p class="muted">The best new plan jammed in ${j.jammed} of ${j.n} practice runs, so the current timing stays.</p>
        <div><a class="btn" href="#/deanza/review">Open</a></div>
      </article>
    </section>
  </div></div>`;
}

/* ---------- Review ---------- */

function bar(list, cycle, scale, old) {
  const seg = (cls, s, title, text = '') => s > 0 ? `<div class="${cls}" style="width:${s / cycle * 100}%" title="${esc(title)}">${text}</div>` : '';
  const body = list.map((p, i) => seg(`seg-g${i % 2 ? ' alt' : ''}`, p.max_green_s, `Green ${serves(p.serves)}: up to ${f1(p.max_green_s)} s`,
      p.max_green_s / scale > 0.07 ? `${Math.round(p.max_green_s)}` : '')
    + seg('seg-y', p.yellow, `Yellow ${f1(p.yellow)} s`) + seg('seg-r', p.red, `All-red ${f1(p.red)} s`)).join('');
  const label = list.map(p => `green ${serves(p.serves)} ${f1(p.max_green_s)} seconds`).join('; ');
  return `<div class="bar${old ? ' old' : ''}" style="width:${cycle / scale * 100}%" role="img" aria-label="${old ? 'Now' : 'New'}: one round of ${f1(cycle)} seconds; ${esc(label)}">${body}</div>`;
}

function changes(d) {
  const sigs = d.card.signals;
  const oldC = [...new Set(sigs.map(s => s.old.cycle_s))], newC = [...new Set(sigs.map(s => s.new.cycle_s))];
  const gains = sigs.flatMap(s => s.new.greens.map((g, i) => g.max_green_s - s.old.greens[i].max_green_s));
  return [
    oldC.length === 1 && newC.length === 1
      ? `All ${sigs.length} lights go from a ${f1(oldC[0])} s round to a ${f1(newC[0])} s round.`
      : 'Each light gets a new round length.',
    `The busiest directions get up to ${Math.round(Math.max(...gains))} s more green each round.`,
    `Greens start at new times so cars meet more greens along ${esc(d.info.street)}. Phase order, yellow, all-red and minimum greens stay the same.`];
}

function sheet(d) {
  const at = decision(d).at ? new Date(decision(d).at).toLocaleString() : 'Not approved yet';
  const ch = (a, b) => a === b ? f1(a) : `${f1(a)} → ${f1(b)}`;
  return `<section class="sheet">
    <div class="sheet-head"><div><h2>Timing change sheet</h2><p class="small muted">Signal Learner · simulation result, not city timing</p></div><span class="stamp">Draft for engineer entry</span></div>
    <dl><dt>Road</dt><dd>${esc(d.info.street)}, ${d.card.signals.length} intersections</dd>
      <dt>Plan</dt><dd>Evening peak, ${esc(d.info.begin)}–${esc(d.info.end)}</dd>
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

function review(d) {
  if (!isChange(d)) return calm(d);
  const c = d.card, e = c.expected_in_copy, h = heldout(d), dec = decision(d);
  const scale = Math.max(...c.signals.flatMap(s => [s.old.cycle_s, s.new.cycle_s]));
  const actions = dec.status ? '' : `<div class="decide"><button class="btn lg" data-action="reject">Reject</button><button class="btn primary lg" data-action="approve">Approve</button></div>`;
  const state = dec.status === 'approved'
    ? `<div class="status ok" role="status"><span><b>Approved.</b> Nothing was sent to any real light. Next, watch it run on the same traffic as today’s timing.</span>
        <span class="row"><button class="btn ghost" data-action="reopen">Undo</button><a class="btn primary lg" href="#/wolfe/simulate?run">Run the simulation</a></span></div>`
    : dec.status === 'rejected'
      ? `<div class="status bad" role="status"><span><b>Rejected.</b> ${dec.note ? `Note: “${esc(dec.note)}”. ` : ''}The current timing stays.</span><button class="btn" data-action="reopen">Reopen</button></div>`
      : rejecting
        ? `<div class="card pad" style="margin-bottom:16px"><label class="field" for="note">Why reject? (optional, kept with the recommendation)</label>
          <textarea id="note" maxlength="500" placeholder="For example: conflicts with the school-zone plan"></textarea>
          <div class="row" style="margin-top:10px"><button class="btn danger" data-action="archive">Reject recommendation</button><button class="btn ghost" data-action="cancel">Cancel</button></div></div>`
        : '';
  return `<div class="page">
  <a class="back" href="#/overview">← Overview</a>
  <div class="head"><div><h1>${esc(d.info.street)}: new timing</h1>
    <p>Evening peak, ${ampm(seconds(d.info.begin))}–${ampm(seconds(d.info.end))}, all ${c.signals.length} lights. You approve or reject; an engineer enters any change.</p></div>${actions}</div>
  ${state}
  <div class="review">
    <section class="card lights" aria-labelledby="lights-title">
      <div class="lights-head"><h2 id="lights-title">One round of each light, now and new</h2>
        <div class="legend"><span><i style="background:var(--go)"></i>Green (seconds)</span><span><i style="background:var(--amber)"></i>Yellow</span><span><i style="background:var(--stop)"></i>All-red</span></div></div>
      ${c.signals.map(sig => {
        const old = phases(d, sig, 'old'), neu = phases(d, sig, 'new');
        return `<div class="light"><div class="name">${esc(sig.signal)}</div>
          <div class="bars"><span class="k">Now</span>${bar(old, sig.old.cycle_s, scale, true)}<span class="c num">${f1(sig.old.cycle_s)} s</span>
            <span class="k">New</span>${bar(neu, sig.new.cycle_s, scale, false)}<span class="c num chg">${f1(sig.new.cycle_s)} s</span></div></div>`;
      }).join('')}
    </section>
    <aside class="stack">
      <section class="card facts-card"><h2>What changes</h2>
        <ul class="changes small" style="margin-top:10px">${changes(d).map(t => `<li>${t}</li>`).join('')}</ul>
        <div class="forecast"><h3 class="small muted">Tested on ${h.n} new evenings</h3>
          <p class="big num" style="color:var(--go-deep)">${pct(h.oldMean, h.planMean)} delay</p>
          <p class="xs muted">Better on ${betterOn(h)}. ${f1(h.oldMean)} → ${f1(h.planMean)} s average delay score.</p></div>
        <div class="forecast"><h3 class="small muted">Forecast on the practice copy</h3>
          <p class="num"><b>${pct(e.old_delay_s, e.new_delay_s)}</b> <span class="xs muted">${f1(e.old_delay_s)} → ${f1(e.new_delay_s)} s, ${e.copy_seeds.length} practice evenings on a copy of the road built from sensor counts</span></p></div>
      </section>
      <button class="btn" data-action="print" style="width:100%">Download timing sheet</button>
    </aside>
  </div></div>`;
}

function calm(d) {
  const j = jams(d);
  return `<div class="page">
  <a class="back" href="#/overview">← Overview</a>
  <div class="card calm">
    <div class="stack"><span class="pill">No change</span>
      <h1>${esc(d.info.street)}: no change needed</h1>
      <p class="muted" style="max-width:56ch">The best new plan jammed in ${j.jammed} of ${j.n} practice runs, so Signal Learner keeps the current timing at all ${d.card.signals.length} lights.</p>
      <p class="xs faint">Jammed: the simulation had to remove stuck cars more often than the current timing does.</p>
      <div class="row" style="margin-top:16px"><a class="btn" href="#/overview">Back to inbox</a></div></div>
    <div class="map" id="calm-map" role="img" aria-label="${esc(mapLabel(d.geo))}"></div>
  </div></div>`;
}

/* ---------- Simulate ---------- */

function simulate(d) {
  const h = heldout(d), begin = seconds(d.info.begin), end = seconds(d.info.end);
  const panel = (arm, side) => `<section class="card side-panel ${side}" aria-labelledby="h-${arm}">
    <h2 id="h-${arm}"><span class="sw" style="background:${arm === 'old' ? 'var(--faint)' : 'var(--accent)'}"></span>${ARM_NAME[arm]}</h2>
    <div class="counter"><span>Cars waiting to get onto the road</span><b data-k="waiting" data-arm="${arm}">–</b></div>
    <div class="counter"><span>Average delay so far</span><b data-k="delay" data-arm="${arm}">–</b></div>
    <div class="counter"><span>Trips finished</span><b data-k="finished" data-arm="${arm}">–</b></div>
    <div class="panel-foot">${arm === 'old'
      ? '<span class="legend"><span><i class="dot" style="background:var(--go)"></i>Moving car</span><span><i class="dot" style="background:var(--stop)"></i>Stopped car</span></span><span class="hint">Short bars at each light show its live signal.</span>'
      : `<span class="hint">Headline result: ${pct(h.oldMean, h.planMean)} delay over ${h.n} new evenings.</span>`}</div>
  </section>`;
  return `<div class="page" style="max-width:1180px">
  <div class="sim-top">
    <div><h1>One evening on ${esc(d.info.street)}</h1><p class="small muted" style="margin-top:4px">Same traffic, same clock. Left: today’s timing. Right: the Signal Learner plan.</p></div>
    <div class="clock" aria-live="off"><b id="clock">${ampm(begin)}</b><span id="clock-note">${ampm(begin)} to ${ampm(end)}</span></div>
    <div class="right"><span class="pill" id="source">Ready</span>
      <button class="btn" id="play" data-action="toggle" disabled aria-label="Pause"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z"/></svg></button>
      <div class="seg" role="group" aria-label="Speed">${SPEEDS.map(s => `<button type="button" data-speed="${s}" aria-pressed="${s === 120}">${s}×</button>`).join('')}</div></div>
  </div>
  <div class="progress" aria-hidden="true"><i id="progress"></i></div>
  <div class="stage">
    ${panel('old', 'left')}
    <div class="sim-map" id="map-old" role="img" aria-label="Live map, current timing: moving cars green, stopped cars red."><span class="caption">Current</span></div>
    <div class="sim-map" id="map-plan" role="img" aria-label="Live map, Signal Learner plan: moving cars green, stopped cars red."><span class="caption">Signal Learner</span></div>
    ${panel('plan', 'right')}
    <div class="overlay" id="overlay">
      <div class="card pad start" id="start"><h2>Watch both timings handle the same evening</h2>
        <p class="small muted">${ampm(begin)} to ${ampm(end)}, about ${Math.round((end - begin) / 120)} seconds at 120×. Each dot is a car.</p>
        <button class="btn primary lg" data-action="start">Run the simulation</button></div>
    </div>
  </div>
  <p class="sr" aria-live="polite" id="sim-status"></p>
</div>`;
}

function endCard(d, final, recorded) {
  const h = heldout(d), o = final.old.delay_s, p = final.plan.delay_s;
  return `<div class="card endcard" role="dialog" aria-labelledby="end-title" tabindex="-1">
    <div><h2 id="end-title">This one evening</h2>
      <p class="score">${f1(o)} s → <b>${f1(p)} s</b></p>
      <p class="pct">${pct(o, p)}</p>
      <p class="xs muted" style="margin-top:6px">Delay score: average extra seconds per trip. A trip that never finishes counts 900 s. ${recorded ? 'From the recorded run.' : 'From this live run.'}</p></div>
    <div><h2>Tested on ${h.n} new evenings</h2>
      <p class="score">${f1(h.oldMean)} s → <b>${f1(h.planMean)} s</b></p>
      <p class="pct">${pct(h.oldMean, h.planMean)}</p>
      <p class="xs muted" style="margin-top:6px">Better on ${betterOn(h)}. This is the headline result.</p></div>
    <div class="foot"><span class="small">After approval, Signal Learner keeps watching and switches back if traffic gets worse.</span>
      <span class="row"><button class="btn" data-action="start">Replay</button><a class="btn primary" href="#/overview">Done</a></span></div>
  </div>`;
}

// One side of one frame: car arrays (metres) + lights + counters.
function side(cars, lights, waiting, finished, delay) {
  const n = cars.ids.length;
  return { ...cars, n, lights, waiting, finished, delay };
}

function fromLive(f) {
  const out = { t: f.t };
  for (const arm of ARMS) {
    const s = f[arm]; if (!s) continue;
    const c = s.cars, n = c.length / 4, ids = new Uint32Array(n), x = new Float32Array(n), y = new Float32Array(n), stop = new Uint8Array(n);
    for (let i = 0; i < n; i++) { ids[i] = c[4 * i]; x[i] = c[4 * i + 1] / 10; y[i] = c[4 * i + 2] / 10; stop[i] = c[4 * i + 3]; }
    out[arm] = side({ ids, x, y, stop }, s.lights, s.waiting, s.finished, s.delay);
  }
  return out;
}

// Recording: see tools/live_sim.py write_recording for the byte layout.
async function loadRecording() {
  const response = await fetch('geo/wolfe_seed200.rec.gz');
  if (!response.ok) throw new Error('The recording is missing.');
  const buf = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const dv = new DataView(buf), td = new TextDecoder();
  if (td.decode(new Uint8Array(buf, 0, 4)) !== 'SLR1') throw new Error('The recording is not readable.');
  const len = dv.getUint32(4, true), head = JSON.parse(td.decode(new Uint8Array(buf, 8, len)));
  const lightLen = head.lights.reduce((a, b) => a + b, 0);
  let o = 8 + len;
  const frames = [];
  for (let k = 0; k < head.frames; k++) {
    const f = { t: dv.getUint32(o, true) }; o += 4;
    for (const arm of ARMS) {
      const n = dv.getUint16(o, true); o += 2;
      const ids = new Uint32Array(n), x = new Float32Array(n), y = new Float32Array(n), stop = new Uint8Array(n);
      for (let i = 0; i < n; i++) ids[i] = dv.getUint16(o + 2 * i, true);
      o += 2 * n;
      for (let i = 0; i < n; i++) x[i] = dv.getUint16(o + 2 * i, true) / 10;
      o += 2 * n;
      for (let i = 0; i < n; i++) y[i] = dv.getUint16(o + 2 * i, true) / 10;
      o += 2 * n;
      for (let i = 0; i < n; i++) stop[i] = dv.getUint8(o + i);
      o += n;
      const text = td.decode(new Uint8Array(buf, o, lightLen)); o += lightLen;
      const lights = []; let at = 0;
      for (const l of head.lights) { lights.push(text.slice(at, at + l)); at += l; }
      f[arm] = side({ ids, x, y, stop }, lights, dv.getUint16(o, true), dv.getUint16(o + 2, true), dv.getUint16(o + 4, true) / 10);
      o += 6;
    }
    frames.push(f);
  }
  return { frames, final: head.final };
}

const lightColor = (state, links) => {
  let c = 'r';
  for (const i of links) { const s = state[i]; if (s === 'G' || s === 'g') return '#16a34a'; if (s === 'y' || s === 'Y') c = 'y'; }
  return c === 'y' ? '#d4a106' : '#dc2626';
};

class Player {
  constructor(d) {
    this.d = d;
    this.begin = seconds(d.info.begin); this.end = seconds(d.info.end); this.stop = this.end + d.info.drain;
    this.frames = []; this.t = this.begin; this.speed = 120; this.playing = false; this.done = null;
    this.views = ARMS.map(arm => ({ arm, box: document.getElementById(`map-${arm}`) }));
    this.counters = [...document.querySelectorAll('[data-k]')];
    this.layout();
    this.resize = () => { this.layout(); this.draw(); };
    window.addEventListener('resize', this.resize);
  }
  layout() {
    for (const v of this.views) {
      Object.assign(v, canvasFor(v.box));
      v.p = fit(this.d.geo, v.w, v.h, 16);
      v.bg = document.createElement('canvas');
      v.bg.width = v.canvas.width; v.bg.height = v.canvas.height;
      const bg = v.bg.getContext('2d');
      const r = window.devicePixelRatio || 1;
      bg.setTransform(r, 0, 0, r, 0, 0);
      drawRoads(bg, this.d.geo, v.p);
      bg.font = '500 10.5px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      bg.fillStyle = '#64748b'; bg.textBaseline = 'middle';
      bg.textAlign = v.arm === 'old' ? 'left' : 'right';
      for (const sig of this.d.geo.signals) bg.fillText(sig.name, v.arm === 'old' ? 6 : v.w - 6, v.p.y(centre(sig)[1]) - 9);
      v.stops = this.d.geo.signals.map(sig => sig.stops.map(s => {
        const [ax, ay, bx, by] = s.xy, dx = bx - ax, dy = by - ay, l = Math.hypot(dx, dy) || 1;
        return { x: v.p.x(bx), y: v.p.y(by), nx: -dy / l, ny: -dx / l, links: s.links };
      }));
    }
  }
  async start() {
    this.stopSource();
    this.frames = []; this.idx = 0; this.t = this.begin; this.done = null; this.playing = true; this.last = performance.now();
    document.getElementById('overlay').hidden = true;
    document.getElementById('play').disabled = false;
    this.say('Starting the simulation');
    document.getElementById('clock-note').textContent = 'Filling the road with traffic first';
    this.setSource('Starting…', '');
    this.abort = new AbortController();
    try {
      const response = await fetch('/api/sim/stream', { signal: this.abort.signal });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).reason || `HTTP ${response.status}`);
      this.live = true;
      this.setSource('Live · SUMO', 'live');
      this.control({ speed: this.speed, paused: false });
      this.loop();
      await this.read(response.body.getReader());
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (this.live && this.frames.length) return this.fail(err.message);
      this.live = false;
      this.reason = err.message;
      try {
        this.setSource('Loading recording…', '');
        const rec = await loadRecording();
        this.frames = rec.frames; this.final = rec.final;
        this.setSource('Recording', '');
        document.getElementById('source').title = `Live simulation unavailable: ${this.reason}`;
        this.t = this.frames[0].t; this.last = performance.now();
        this.loop();
      } catch (e2) { this.fail(e2.message); }
    }
  }
  async read(reader) {
    const dec = new TextDecoder();
    let text = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      text += dec.decode(value, { stream: true });
      let cut;
      while ((cut = text.indexOf('\n\n')) >= 0) {
        const block = text.slice(0, cut); text = text.slice(cut + 2);
        const kind = (block.match(/^event: (.+)$/m) || [])[1], body = (block.match(/^data: (.+)$/m) || [])[1];
        if (!kind || !body) continue;
        const value = JSON.parse(body);
        if (kind === 'frame') this.frames.push(fromLive(value));
        else if (kind === 'end') this.final = value;
        else if (kind === 'failed') throw new Error(value.reason);
      }
    }
    if (!this.final) throw new Error('The simulation stopped early.');
  }
  control(body) {
    if (this.live) fetch('/api/sim/control', { method: 'POST', body: JSON.stringify(body) }).catch(() => {});
  }
  setSpeed(s) { this.speed = s; this.control({ speed: s }); }
  toggle() {
    if (!this.frames.length || this.done) return;
    this.playing = !this.playing; this.last = performance.now();
    this.control({ paused: !this.playing });
    const b = document.getElementById('play');
    b.setAttribute('aria-label', this.playing ? 'Pause' : 'Play');
    b.innerHTML = this.playing ? '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z"/></svg>'
      : '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg>';
    this.say(this.playing ? 'Playing' : 'Paused');
  }
  loop() {
    cancelAnimationFrame(this.raf);
    const tick = now => {
      const dt = Math.min(0.1, (now - this.last) / 1000); this.last = now;
      const f = this.frames;
      if (this.playing && f.length) {
        this.t += dt * this.speed * (this.t >= this.end ? 4 : 1);
        const newest = f[f.length - 1].t;
        if (this.live && !this.final) {
          // Stay just behind the newest frame from the server so there is always a next frame to move toward.
          const lag = this.speed * 0.15;
          this.t = Math.min(Math.max(this.t, newest - lag * 4), Math.max(f[0].t, newest - lag));
        }
        if (this.t >= newest) {
          this.t = newest;
          if (this.final) return this.finish();
        }
      }
      this.draw();
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }
  frameAt(t) {
    const f = this.frames;
    if (this.live) while (f.length > 2 && f[1].t <= t) f.shift();
    else { while (this.idx < f.length - 2 && f[this.idx + 1].t <= t) this.idx++; while (this.idx > 0 && f[this.idx].t > t) this.idx--; }
    const i = this.live ? 0 : this.idx;
    return [f[i], f[i + 1] || f[i]];
  }
  draw() {
    if (!this.frames.length) { for (const v of this.views) { v.ctx.clearRect(0, 0, v.w, v.h); v.ctx.drawImage(v.bg, 0, 0, v.w, v.h); } return; }
    const [a, b] = this.frameAt(this.t);
    const u = b.t > a.t ? Math.min(1, Math.max(0, (this.t - a.t) / (b.t - a.t))) : 0;
    for (const v of this.views) {
      const sa = a[v.arm], sb = b[v.arm] || sa, { ctx, p } = v;
      ctx.clearRect(0, 0, v.w, v.h);
      ctx.drawImage(v.bg, 0, 0, v.w, v.h);
      if (!sa) continue;
      if (!sa.index) { sa.index = new Map(); for (let i = 0; i < sa.n; i++) sa.index.set(sa.ids[i], i); }
      const r = Math.max(1.4, 2.2 * p.k * 1.4);
      for (const stopped of [0, 1]) {
        ctx.fillStyle = stopped ? '#dc2626' : '#16a34a';
        ctx.beginPath();
        for (let i = 0; i < sb.n; i++) {
          if (sb.stop[i] !== stopped) continue;
          const j = sa.index.get(sb.ids[i]);
          const x = j === undefined ? sb.x[i] : sa.x[j] + (sb.x[i] - sa.x[j]) * u;
          const y = j === undefined ? sb.y[i] : sa.y[j] + (sb.y[i] - sa.y[j]) * u;
          const px = p.x(x), py = p.y(y);
          ctx.moveTo(px + r, py); ctx.arc(px, py, r, 0, 6.2832);
        }
        ctx.fill();
      }
      ctx.lineWidth = 2.5; ctx.lineCap = 'butt';
      v.stops.forEach((stops, k) => {
        const state = sa.lights[k] || '';
        for (const s of stops) {
          ctx.strokeStyle = lightColor(state, s.links);
          ctx.beginPath(); ctx.moveTo(s.x - s.nx * 3, s.y - s.ny * 3); ctx.lineTo(s.x + s.nx * 3, s.y + s.ny * 3); ctx.stroke();
        }
      });
    }
    this.hud(a);
  }
  hud(a) {
    const now = performance.now();
    if (now - (this.hudAt || 0) < 200) return;
    this.hudAt = now;
    const t = Math.min(this.t, this.stop);
    document.getElementById('clock').textContent = ampm(t);
    document.getElementById('clock-note').textContent = t >= this.end ? 'Evening over: the last cars finish their trips' : `${ampm(this.begin)} to ${ampm(this.end)}`;
    document.getElementById('progress').style.width = `${Math.min(100, (t - this.begin) / (this.stop - this.begin) * 100)}%`;
    const fmt = { waiting: x => x.toLocaleString(), finished: x => x.toLocaleString(), delay: x => `${Math.round(x)}<small>s</small>` };
    const val = {};
    for (const arm of ARMS) if (a[arm]) val[arm] = a[arm];
    for (const el of this.counters) {
      const s = val[el.dataset.arm]; if (!s) continue;
      el.innerHTML = fmt[el.dataset.k](s[el.dataset.k]);
      const other = val[el.dataset.arm === 'old' ? 'plan' : 'old'];
      el.parentElement.classList.toggle('better', el.dataset.arm === 'plan' && !!other && el.dataset.k !== 'finished' && s[el.dataset.k] < other[el.dataset.k]);
    }
  }
  finish() {
    this.done = true; this.playing = false;
    this.hudAt = 0; this.draw();
    document.getElementById('play').disabled = true;
    const overlay = document.getElementById('overlay');
    overlay.innerHTML = endCard(this.d, this.final, !this.live);
    overlay.hidden = false;
    overlay.querySelector('.endcard').focus();
    this.say('The evening is over. Results are shown.');
  }
  fail(message) {
    this.playing = false;
    cancelAnimationFrame(this.raf);
    const overlay = document.getElementById('overlay');
    overlay.innerHTML = `<div class="card pad start"><h2>The simulation stopped</h2><p class="small error">${esc(message)}</p><button class="btn primary" data-action="start">Try again</button></div>`;
    overlay.hidden = false;
    this.setSource('Stopped', 'bad');
  }
  setSource(text, kind) { const s = document.getElementById('source'); if (s) { s.textContent = text; s.className = `pill ${kind}`; } }
  say(text) { const s = document.getElementById('sim-status'); if (s) s.textContent = text; }
  stopSource() { this.abort?.abort(); cancelAnimationFrame(this.raf); this.live = false; this.final = null; }
  destroy() { this.stopSource(); window.removeEventListener('resize', this.resize); }
}

/* ---------- How it connects (dialog) ---------- */

function box(x, y, w, h, title, lines, opts = {}) {
  return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${opts.fill || '#fff'}" stroke="${opts.stroke || '#cfd7e1'}" ${opts.dash ? 'stroke-dasharray="6 4"' : ''} stroke-width="1.5"/>
    <text class="t" x="${x + 12}" y="${y + 22}">${title}</text>${lines.map((l, i) => `<text x="${x + 12}" y="${y + 42 + i * 16}">${l}</text>`).join('')}</g>`;
}
const arrow = (x1, y1, x2, y2, opts = {}) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${opts.color || '#5a6371'}" stroke-width="1.8" ${opts.dash ? 'stroke-dasharray="5 4"' : ''} marker-end="url(#${opts.color ? 'ha' : 'h'})"/>`;

function connect() {
  const A = '#0369a1';
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

const dialog = document.getElementById('connect');
function openConnect() {
  document.getElementById('connect-body').innerHTML = connect();
  dialog.showModal();
}
document.getElementById('connect-open').addEventListener('click', openConnect);
document.getElementById('connect-close').addEventListener('click', () => dialog.close());

/* ---------- Shell ---------- */

// Old deck links keep working: recommendation → review, test → simulate, connect → the dialog.
function parseRoute() {
  const [hash, query = ''] = location.hash.split('?');
  const [, a, b] = hash.split('/');
  if (!ROADS.includes(a)) return { road: 'wolfe', screen: 'overview' };
  if (b === 'review' || b === 'recommendation') return { road: a, screen: 'review' };
  if (b === 'simulate' || b === 'test') return { road: 'wolfe', screen: 'simulate', run: query === 'run' };
  return { road: a, screen: 'overview', connect: b === 'connect' };
}

const TITLES = { overview: 'Overview', review: 'Review', simulate: 'Simulate' };

async function render() {
  player?.destroy(); player = null;
  const next = parseRoute();
  const moved = next.screen !== route.screen || next.road !== route.road;
  if (moved) rejecting = false;
  route = next;
  document.querySelectorAll('#nav a').forEach(a => {
    if (a.dataset.screen === route.screen) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  try {
    const [w, z] = await Promise.all(ROADS.map(data));
    const d = route.road === 'deanza' ? z : w;
    document.title = `${TITLES[route.screen]} · Signal Learner`;
    if (route.screen === 'overview') {
      main.innerHTML = overview(w, z);
      drawMap(document.getElementById('overview-map'), w.geo);
    } else if (route.screen === 'review') {
      main.innerHTML = review(d);
      const m = document.getElementById('calm-map');
      if (m) drawMap(m, d.geo);
    } else {
      main.innerHTML = simulate(w);
      player = new Player(w);
      player.draw();
      if (route.run) { history.replaceState(null, '', '#/wolfe/simulate'); player.start(); }
    }
  } catch (err) {
    main.innerHTML = `<div class="page"><div class="error"><b>Could not load the saved files.</b> ${esc(err.message)}. Start the console with python -m tools.demo, then reload.</div></div>`;
  }
  if (route.connect) openConnect();
  if (moved) {
    const h1 = main.querySelector('h1');
    if (h1 && document.activeElement !== document.body) { h1.tabIndex = -1; h1.focus({ preventScroll: true }); }
    window.scrollTo(0, 0);
  }
}

main.addEventListener('click', async event => {
  const speed = event.target.closest('[data-speed]');
  if (speed && player) {
    player.setSpeed(Number(speed.dataset.speed));
    document.querySelectorAll('[data-speed]').forEach(b => b.setAttribute('aria-pressed', String(b === speed)));
    return;
  }
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'start') return player?.start();
  if (action === 'toggle') return player?.toggle();
  const d = await data(route.road);
  if (action === 'approve') decisions[d.road] = { status: 'approved', at: new Date().toISOString() };
  else if (action === 'archive') decisions[d.road] = { status: 'rejected', at: new Date().toISOString(), note: document.getElementById('note').value.trim() };
  else if (action === 'reopen') delete decisions[d.road];
  else if (action === 'reject') { rejecting = true; await render(); return document.getElementById('note')?.focus(); }
  else if (action === 'print') {
    document.getElementById('print').innerHTML = sheet(d);
    return window.print();
  }
  rejecting = false;
  saveDecisions();
  await render();
  main.querySelector('.status .btn.primary, .decide .btn.primary, .status .btn')?.focus();
});

document.addEventListener('keydown', event => {
  if (event.key === ' ' && player && !event.target.closest('button, a, textarea, input')) { event.preventDefault(); player.toggle(); }
});
window.addEventListener('hashchange', render);
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const o = document.getElementById('overview-map') || document.getElementById('calm-map');
    if (o) drawMap(o, cache[route.road === 'deanza' && route.screen === 'review' ? 'deanza' : 'wolfe'].geo);
  }, 120);
});
render();
