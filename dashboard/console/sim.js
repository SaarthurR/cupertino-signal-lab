'use strict';
// Simulate: two real SUMO runs side by side (SSE /api/sim/stream), or the saved recording of the same evening.

const SPEEDS = [60, 120, 240];
const ARMS = ['old', 'plan'];
const ARM_NAME = { old: 'Current timing', plan: 'Signal Learner plan' };

function simulate(d) {
  const h = heldout(d), begin = seconds(d.info.begin), end = seconds(d.info.end);
  const arrow = up => `<svg viewBox="0 0 12 12" aria-hidden="true"><path d="${up ? 'M6 2 11 9H1z' : 'M6 10 1 3h10z'}"/></svg>`;
  const panel = arm => `<section class="arm ${arm}" aria-labelledby="h-${arm}">
    <div class="arm-head">
      <h2 id="h-${arm}"><span class="sw"></span>${ARM_NAME[arm]}</h2>
      <div class="counter hero"><b data-k="waiting" data-arm="${arm}"><small>–</small></b><span>cars waiting to get onto the road</span></div>
      <div class="counter"><b data-k="finished" data-arm="${arm}"><small>–</small></b><span>trips finished</span></div>
      <div class="counter tiny"><span>Avg delay of finished trips</span><b data-k="delay" data-arm="${arm}"><small>–</small></b></div>
    </div>
    <div class="sim-map" id="map-${arm}" role="img" aria-label="Live map, ${ARM_NAME[arm]}: ${esc(d.info.street)} runs left to right, north on the left. Moving cars green, stopped cars red."></div>
  </section>`;
  return `<div class="page sim-page">
  ${crumbs([['Corridors', '#/corridors'], [d.info.street, `#/${d.road}`], ['Simulate']])}
  <div class="sim-top">
    <div><h1>Simulate · ${esc(d.info.street)}</h1><p class="meta-line">Same traffic, same clock · held-out seed 200</p></div>
    <div class="clock" aria-live="off"><b id="clock">${ampm(begin)}</b><span id="clock-note">${ampm(begin)} to ${ampm(end)}</span></div>
    <div class="right"><span class="pill" id="source">Ready</span>
      <button class="btn" id="play" data-action="toggle" disabled aria-label="Pause"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z"/></svg></button>
      <div class="seg" role="group" aria-label="Speed">${SPEEDS.map(s => `<button type="button" data-speed="${s}" aria-pressed="${s === 120}">${s}×</button>`).join('')}</div></div>
  </div>
  <div class="progress" aria-hidden="true"><i id="progress"></i></div>
  <div class="card stage">
    ${panel('old')}
    <div class="gap even" id="gap">
      <p class="gap-main">${arrow(true)}<b id="gap-n">0</b><span class="gap-on">more cars stuck waiting with current timing</span><span class="gap-off">Same cars, same evening: watch the queues</span></p>
      <p class="gap-sub" id="gap-sub" hidden>${arrow(false)}<b id="gap-f">0</b>more trips finished with the plan</p>
    </div>
    ${panel('plan')}
    <div class="overlay" id="overlay">
      <div class="card pad start" id="start"><h2>Watch both timings handle the same evening</h2>
        <p class="small muted">${ampm(begin)} to ${ampm(end)}, about ${Math.round((end - begin) / 120)} seconds at 120×. Each dot is a car.</p>
        <button class="btn primary lg" data-action="start">Run the simulation</button></div>
    </div>
  </div>
  <div class="sim-foot">
    <span class="legend"><span><i class="dot" style="background:var(--go)"></i>Moving car</span><span><i class="dot" style="background:var(--stop)"></i>Stopped car</span><span><i class="sig"></i>Live signal at each light, one stripe per lane</span></span>
    <span class="hint">Headline result: ${pct(h.oldMean, h.planMean)} delay over ${h.n} new evenings.</span>
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
      <span class="row"><button class="btn" data-action="start">Replay</button><a class="btn primary" href="#/${d.road}/deploy">Deploy &amp; monitor</a></span></div>
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

// One bar per approach at each light, across its stop line, with one stripe per lane (lanes are too close to draw apart).
function approaches(stops, p) {
  const groups = [];
  for (const s of stops) {
    const [ax, ay, bx, by] = s.xy, x = p.x(bx, by), y = p.y(bx, by);
    const dx = x - p.x(ax, ay), dy = y - p.y(ax, ay), l = Math.hypot(dx, dy) || 1, ux = dx / l, uy = dy / l;
    let g = groups.find(g => g.ux * ux + g.uy * uy > 0.8);
    if (!g) groups.push(g = { ux, uy, lanes: [] });
    g.lanes.push({ x, y, links: s.links });
  }
  return groups.map(({ ux, uy, lanes }) => {
    const nx = -uy, ny = ux, cx = mean(lanes.map(l => l.x)), cy = mean(lanes.map(l => l.y));
    const across = l => (l.x - cx) * nx + (l.y - cy) * ny;
    lanes.sort((a, b) => across(a) - across(b));
    return { x: cx - ux * 2, y: cy - uy * 2, nx, ny, len: Math.max(lanes.length * 5, 10), links: lanes.map(l => l.links) };
  });
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
      v.p = fit(this.d.geo, v.w, v.h, 16, true);
      v.bg = document.createElement('canvas');
      v.bg.width = v.canvas.width; v.bg.height = v.canvas.height;
      const bg = v.bg.getContext('2d');
      const r = window.devicePixelRatio || 1;
      bg.setTransform(r, 0, 0, r, 0, 0);
      drawRoads(bg, this.d.geo, v.p);
      nameAlong(bg, this.d.geo, v.p, v.w, v.h, 18);
      v.stops = this.d.geo.signals.map(sig => approaches(sig.stops, v.p));
    }
  }
  async start() {
    this.stopSource();
    this.frames = []; this.idx = 0; this.t = this.begin; this.done = null; this.playing = true; this.last = performance.now(); this.hundred = 0;
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
      const r = Math.max(2.6, 4 * p.k);
      for (const stopped of [0, 1]) {
        ctx.fillStyle = stopped ? '#dc2626' : '#16a34a';
        ctx.beginPath();
        for (let i = 0; i < sb.n; i++) {
          if (sb.stop[i] !== stopped) continue;
          const j = sa.index.get(sb.ids[i]);
          const x = j === undefined ? sb.x[i] : sa.x[j] + (sb.x[i] - sa.x[j]) * u;
          const y = j === undefined ? sb.y[i] : sa.y[j] + (sb.y[i] - sa.y[j]) * u;
          const px = p.x(x, y), py = p.y(x, y);
          ctx.moveTo(px + r, py); ctx.arc(px, py, r, 0, 6.2832);
        }
        ctx.fill();
      }
      v.stops.forEach((bars, k) => {
        const state = sa.lights[k] || '';
        for (const s of bars) {
          const x0 = s.x - s.nx * s.len / 2, y0 = s.y - s.ny * s.len / 2, step = s.len / s.links.length;
          ctx.lineCap = 'round'; ctx.lineWidth = 8; ctx.strokeStyle = '#fff';
          ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + s.nx * s.len, y0 + s.ny * s.len); ctx.stroke();
          ctx.lineCap = 'butt'; ctx.lineWidth = 5;
          s.links.forEach((links, i) => {
            ctx.strokeStyle = lightColor(state, links);
            ctx.beginPath(); ctx.moveTo(x0 + s.nx * step * i, y0 + s.ny * step * i); ctx.lineTo(x0 + s.nx * step * (i + 1), y0 + s.ny * step * (i + 1)); ctx.stroke();
          });
        }
      });
    }
    this.hud(a);
  }
  // Writes only what changed, so it can run every frame.
  hud(a) {
    const set = (el, html) => { if (el._v !== html) { el._v = html; el.innerHTML = html; } };
    const t = Math.min(this.t, this.stop);
    set(document.getElementById('clock'), ampm(t));
    set(document.getElementById('clock-note'), t >= this.end ? 'Evening over: the last cars finish their trips' : `${ampm(this.begin)} to ${ampm(this.end)}`);
    const bar = document.getElementById('progress'), width = `${Math.min(100, (t - this.begin) / (this.stop - this.begin) * 100).toFixed(1)}%`;
    if (bar.style.width !== width) bar.style.width = width;
    const fmt = { waiting: x => x.toLocaleString(), finished: x => x.toLocaleString(), delay: x => `${Math.round(x)}<small>s</small>` };
    for (const el of this.counters) {
      const s = a[el.dataset.arm]; if (!s) continue;
      set(el, fmt[el.dataset.k](s[el.dataset.k]));
      const other = a[el.dataset.arm === 'old' ? 'plan' : 'old'];
      el.parentElement.classList.toggle('better', el.dataset.arm === 'plan' && !!other && el.dataset.k !== 'finished' && s[el.dataset.k] < other[el.dataset.k]);
    }
    if (a.old && a.plan) this.gap(a.old.waiting - a.plan.waiting, a.plan.finished - a.old.finished);
  }
  gap(n, f) {
    const box = document.getElementById('gap'), num = document.getElementById('gap-n');
    box.classList.toggle('even', n <= 0);
    if (n > 0 && num._v !== n) {
      num._v = n; num.textContent = n.toLocaleString();
      const hundred = Math.floor(n / 100);
      if (hundred > (this.hundred || 0) && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
        num.animate([{ transform: 'scale(1.18)' }, { transform: 'none' }], { duration: 700, easing: 'cubic-bezier(.16, 1, .3, 1)' });
      }
      this.hundred = hundred;
    }
    document.getElementById('gap-sub').hidden = f <= 0;
    const fin = document.getElementById('gap-f');
    if (f > 0 && fin._v !== f) { fin._v = f; fin.textContent = f.toLocaleString(); }
  }
  finish() {
    this.done = true; this.playing = false;
    this.draw();
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
