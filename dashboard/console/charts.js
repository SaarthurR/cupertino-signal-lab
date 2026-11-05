'use strict';
// Shared helpers, the canvas road map and the SVG charts. Charts take data and return markup; they never invent values.

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const f1 = x => Number(x).toFixed(1);
const fmt = (x, dp = 0) => Number(x).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });
const mean = v => v.reduce((a, b) => a + b, 0) / v.length;
const ok = v => typeof v === 'number' && Number.isFinite(v);
const seconds = t => { const [h, m] = t.split(':').map(Number); return h * 3600 + m * 60; };
const ampm = s => { const h = Math.floor(s / 3600) % 24, m = Math.floor(s / 60) % 60; return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; };
const clock = s => `${Math.floor(s / 3600) % 24}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}`;
const share = (from, to) => (to - from) / from;
const signed = (x, dp = 0) => `${x < 0 ? '−' : x > 0 ? '+' : ''}${fmt(Math.abs(x), dp)}`;
const pct = (from, to) => `${signed(Math.round(share(from, to) * 100))}%`;
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif';

function niceStep(x) {
  const p = 10 ** Math.floor(Math.log10(x || 1)), f = x / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}
function ticks(lo, hi, n = 4) {
  const step = niceStep((hi - lo) / n || 1), a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
  for (let v = a; v <= b + step / 2; v += step) out.push(+v.toFixed(6));
  return out;
}

function srTable(caption, head, rows) {
  return `<div class="sr"><table><caption>${esc(caption)}</caption><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

/* ---------- Line chart: one value per 15 minutes, current vs proposed ---------- */

function lineChart({ labels, series, unit, label, w = 640, h = 230 }) {
  const m = { l: 46, r: 14, t: 14, b: 28 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const all = series.flatMap(s => s.values).filter(ok);
  if (!all.length) return '';
  const ys = ticks(0, Math.max(...all)), top = ys[ys.length - 1] || 1;
  const x = i => m.l + (labels.length < 2 ? iw / 2 : i * iw / (labels.length - 1)), y = v => m.t + ih - v / top * ih;
  const grid = ys.map(v => `<line class="gl" x1="${m.l}" x2="${w - m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${fmt(v, v % 1 ? 1 : 0)}</text>`).join('');
  const xl = labels.map((t, i) => `<text class="tick" x="${x(i)}" y="${h - 8}" text-anchor="middle">${esc(t)}</text>`).join('');
  const lines = series.map(s => {
    const pts = s.values.map((v, i) => ok(v) ? [x(i), y(v)] : null).filter(Boolean);
    return `<g class="${s.cls}"><polyline class="line" points="${pts.map(p => p.join(',')).join(' ')}"/>
      ${s.values.map((v, i) => ok(v) ? `<circle class="pt" cx="${x(i)}" cy="${y(v)}" r="2.6"><title>${esc(`${s.name}, ${labels[i]}: ${fmt(v, 1)} ${unit}`)}</title></circle>` : '').join('')}</g>`;
  }).join('');
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${grid}
    <text class="unit" x="${m.l}" y="${m.t - 3}">${esc(unit)}</text>${xl}${lines}</svg>
    ${srTable(label, ['Time', ...series.map(s => s.name)], labels.map((t, i) => [t, ...series.map(s => ok(s.values[i]) ? fmt(s.values[i], 1) : '–')]))}`;
}

/* ---------- Time-space diagram ---------- */

function timeSpace(ts, signals, label, [t0, t1], hrefOf = () => '') {
  const w = 1120, h = 320, m = { l: 132, r: 14, t: 12, b: 28 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const xs = signals.map(s => s.x_m).filter(ok);
  const pts = ts.trajectories.flatMap(tr => tr.pts.map(p => p[1]));
  const lo = Math.min(...xs, ...pts), hi = Math.max(...xs, ...pts), span = hi - lo || 1;
  const x = t => m.l + (t - t0) / (t1 - t0) * iw, y = d => m.t + ih - (d - lo) / span * ih;
  const minute = ticks(t0, t1, 10).filter(t => t >= t0 && t <= t1 && t % 60 === 0);
  const grid = minute.map(t => `<line class="gl" x1="${x(t)}" x2="${x(t)}" y1="${m.t}" y2="${m.t + ih}"/><text class="tick" x="${x(t)}" y="${h - 8}" text-anchor="middle">${clock(t)}</text>`).join('');
  // Labels keep 13 px apart; the lines stay at their true distance.
  const placed = signals.filter(s => ok(s.x_m)).sort((a, b) => y(b.x_m) - y(a.x_m));
  const labelY = new Map();
  placed.forEach((s, i) => labelY.set(s, i ? Math.min(y(s.x_m), labelY.get(placed[i - 1]) - 13) : y(s.x_m)));
  const rows = placed.map(s => {
    const greens = ts.green.filter(g => g.signal === s.id);
    const name = `<text class="tick strong" x="${m.l - 10}" y="${labelY.get(s) + 4}" text-anchor="end">${esc(s.name)}</text>`;
    return `<g>${hrefOf(s) ? `<a class="ts-link" href="${hrefOf(s)}">${name}</a>` : name}
      <line class="ts-red" x1="${m.l}" x2="${m.l + iw}" y1="${y(s.x_m)}" y2="${y(s.x_m)}"/>
      ${greens.map(g => `<line class="ts-green" x1="${x(Math.max(t0, g.start_s))}" x2="${x(Math.min(t1, g.end_s))}" y1="${y(s.x_m)}" y2="${y(s.x_m)}"/>`).join('')}</g>`;
  }).join('');
  const paths = ts.trajectories.filter(tr => tr.pts.length > 1).map(tr =>
    `<polyline class="traj ${tr.dir === 'SB' ? 'sb' : 'nb'}" points="${tr.pts.filter(p => p[0] >= t0 && p[0] <= t1).map(p => `${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>`).join('');
  const nb = ts.trajectories.filter(t => t.dir !== 'SB').length, sb = ts.trajectories.length - nb;
  return `<svg class="chart ts" viewBox="0 0 ${w} ${h}" role="group" aria-label="${esc(`${label}. ${clock(t0)} to ${clock(t1)}. ${signals.length} signals by distance; ${nb} northbound and ${sb} southbound car paths.`)}">
    <defs><clipPath id="ts-clip"><rect x="${m.l}" y="${m.t - 4}" width="${iw}" height="${ih + 8}"/></clipPath></defs>
    ${grid}${rows}<g clip-path="url(#ts-clip)">${paths}</g></svg>`;
}

/* ---------- Purdue Coordination Diagram ---------- */

// green holds one [start, end] per cycle with no cycle start times, so cycles are spread evenly over the arrivals' time span.
function pcd(side, label) {
  const arr = side.arrivals || [], green = side.green || [];
  if (!arr.length) return '';
  const w = 540, h = 260, m = { l: 40, r: 10, t: 12, b: 28 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const t0 = Math.min(...arr.map(a => a[0])), t1 = Math.max(...arr.map(a => a[0])), span = t1 - t0 || 1;
  const ymax = ticks(0, Math.max(...arr.map(a => a[1]), ...green.map(g => g[1])), 4);
  const top = ymax[ymax.length - 1] || 1;
  const x = t => m.l + (t - t0) / span * iw, y = v => m.t + ih - v / top * ih, cw = iw / (green.length || 1);
  const bands = green.map((g, k) => g[1] > g[0] ? `<rect x="${(m.l + k * cw).toFixed(1)}" width="${(cw + .4).toFixed(1)}" y="${y(g[1]).toFixed(1)}" height="${(y(g[0]) - y(g[1])).toFixed(1)}"/>` : '').join('');
  const grid = ymax.map(v => `<line class="gl" x1="${m.l}" x2="${w - m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`).join('');
  const xt = ticks(t0, t1, 4).filter(t => t >= t0 && t <= t1).map(t => `<text class="tick" x="${x(t)}" y="${h - 8}" text-anchor="middle">${clock(t)}</text>`).join('');
  const dots = arr.map(a => `M${x(a[0]).toFixed(1)} ${y(a[1]).toFixed(1)}h0`).join('');
  return `<svg class="chart pcd" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(`${label}: ${arr.length} arrivals over ${green.length} cycles.`)}">
    <g class="pcd-green">${bands}</g>${grid}${xt}<text class="unit" x="${m.l}" y="${m.t - 3}">s in cycle</text><path class="pcd-dots" d="${dots}"/></svg>`;
}

/* ---------- Per-evening change, with a forecast band ---------- */

function eveningsChart({ rows, band, label }) {
  const w = 1120, h = 230, m = { l: 46, r: 14, t: 14, b: 30 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const vals = rows.map(r => r.v), lo = Math.min(0, ...vals, band ? band.lo : 0), hi = Math.max(0, ...vals, band ? band.hi : 0);
  const ys = ticks(lo, hi, 5), a = ys[0], b = ys[ys.length - 1];
  const y = v => m.t + (b - v) / (b - a) * ih, bw = iw / rows.length;
  const grid = ys.map(v => `<line class="gl${v === 0 ? ' zero' : ''}" x1="${m.l}" x2="${w - m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${signed(v)}%</text>`).join('');
  const bars = rows.map((r, i) => `<rect class="bar ${r.v <= 0 ? 'good' : 'bad'}" x="${(m.l + i * bw + bw * .18).toFixed(1)}" width="${(bw * .64).toFixed(1)}" y="${y(Math.max(0, r.v)).toFixed(1)}" height="${Math.max(1, Math.abs(y(r.v) - y(0))).toFixed(1)}"><title>${esc(`${r.label}: ${signed(r.v, 1)}%`)}</title></rect>
    <text class="tick" x="${(m.l + (i + .5) * bw).toFixed(1)}" y="${h - 10}" text-anchor="middle">${esc(r.short)}</text>`).join('');
  const fc = band ? `<rect class="band" x="${m.l}" width="${iw}" y="${y(band.hi)}" height="${y(band.lo) - y(band.hi)}"/><line class="band-mid" x1="${m.l}" x2="${w - m.r}" y1="${y(band.mid)}" y2="${y(band.mid)}"/>` : '';
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${fc}${grid}${bars}</svg>
    ${srTable(label, ['Evening', 'Change'], rows.map(r => [r.label, `${signed(r.v, 1)}%`]))}`;
}

/* ---------- Range bar: one result with its spread ---------- */

function rangeBar({ lo, hi, mid, domain }) {
  const [a, b] = domain, w = 240, x = v => 8 + (v - a) / (b - a) * (w - 16);
  return `<svg class="range" viewBox="0 0 ${w} 22" aria-hidden="true"><line class="axis" x1="8" x2="${w - 8}" y1="11" y2="11"/>
    <line class="zero" x1="${x(0)}" x2="${x(0)}" y1="3" y2="19"/><line class="spread" x1="${x(lo)}" x2="${x(hi)}" y1="11" y2="11"/>
    <circle class="mid" cx="${x(mid)}" cy="11" r="5"/></svg>`;
}

/* ---------- City map from each road's signal coordinates ---------- */

function cityMap(roads, w = 640, h = 330) {
  const all = roads.flatMap(r => r.points), lat0 = mean(all.map(p => p.lat)) * Math.PI / 180;
  const px = p => [p.lon * Math.cos(lat0), p.lat];
  const X = all.map(p => px(p)[0]), Y = all.map(p => px(p)[1]);
  const [x0, x1, y0, y1] = [Math.min(...X), Math.max(...X), Math.min(...Y), Math.max(...Y)], pad = 46;
  const k = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0)), ox = (w - (x1 - x0) * k) / 2, oy = (h - (y1 - y0) * k) / 2;
  const P = p => { const [a, b] = px(p); return [ox + (a - x0) * k, h - oy - (b - y0) * k]; };
  const draw = r => {
    const ns = Math.abs(r.points[0].lat - r.points.at(-1).lat) > Math.abs(r.points[0].lon - r.points.at(-1).lon) * Math.cos(lat0);
    const pts = [...r.points].sort((a, b) => ns ? b.lat - a.lat : a.lon - b.lon).map(P);
    const line = `<polyline points="${pts.map(p => p.map(v => v.toFixed(1)).join(',')).join(' ')}"/>`;
    const dots = pts.map(([x, y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.context ? 3 : 4.5}"/>`).join('');
    const mx = mean(pts.map(p => p[0])), my = mean(pts.map(p => p[1]));
    const name = ns ? `<text x="${(mx - 12).toFixed(1)}" y="${my.toFixed(1)}" text-anchor="middle" transform="rotate(-90 ${(mx - 12).toFixed(1)} ${my.toFixed(1)})">${esc(r.street)}</text>`
      : `<text x="${pts[0][0].toFixed(1)}" y="${(pts[0][1] - 12).toFixed(1)}">${esc(r.street)}</text>`;
    if (r.context) return `<g class="ctx"><title>${esc(r.street)}: training road</title>${line}${dots}${name}</g>`;
    return `<a href="#/${r.road}" class="cor ${r.cls}" aria-label="${esc(`${r.street}: ${r.status}, ${r.points.length} signals`)}"><title>${esc(`${r.street}: ${r.status}`)}</title>${line}${dots}${name}</a>`;
  };
  return `<svg class="city" viewBox="0 0 ${w} ${h}" role="group" aria-label="Map of Cupertino corridors, north up">
    <text class="north" x="${w - 18}" y="22" text-anchor="middle">N</text><path class="north" d="M${w - 18} 28l-5 12h10z"/>
    ${roads.filter(r => r.context).map(draw).join('')}${roads.filter(r => !r.context).map(draw).join('')}</svg>`;
}

/* ---------- Road map (real SUMO lane shapes, canvas) ---------- */

// along: the road's length runs left→right across the full width (north on the left); side streets past the box edge are cut off.
function fit(geo, w, h, pad = 14, along = false) {
  const [x0, y0, x1, y1] = geo.bounds;
  if (along) {
    const k = (w - 2 * pad) / (y1 - y0), mid = (x0 + x1) / 2;
    return { k, x: (x, y) => pad + (y1 - y) * k, y: (x, y) => h / 2 - (x - mid) * k };
  }
  const k = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
  const ox = (w - (x1 - x0) * k) / 2, oy = (h - (y1 - y0) * k) / 2;
  return { k, x: (x, y) => ox + (x - x0) * k, y: (x, y) => h - oy - (y - y0) * k };
}

function path(ctx, p, xy) {
  ctx.beginPath();
  ctx.moveTo(p.x(xy[0], xy[1]), p.y(xy[0], xy[1]));
  for (let i = 2; i < xy.length; i += 2) ctx.lineTo(p.x(xy[i], xy[i + 1]), p.y(xy[i], xy[i + 1]));
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
  ctx.fillStyle = '#e1e5ea';
  for (const j of geo.junctions) { path(ctx, p, j); ctx.closePath(); ctx.fill(); }
  ctx.strokeStyle = '#e1e5ea';
  ctx.lineWidth = Math.max(3.2 * p.k, 1.2);
  for (const xy of geo.internal) { path(ctx, p, xy); ctx.stroke(); }
  for (const lane of geo.lanes) {
    ctx.strokeStyle = lane.main ? '#cdd3db' : '#e1e5ea';
    ctx.lineWidth = Math.max(lane.w * p.k, 1.2);
    path(ctx, p, lane.xy); ctx.stroke();
  }
}

const centre = sig => [mean(sig.stops.map(s => s.xy[2])), mean(sig.stops.map(s => s.xy[3]))];

function halo(ctx, text, x, y, color) {
  ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,.92)'; ctx.lineJoin = 'round';
  ctx.strokeText(text, x, y);
  ctx.fillStyle = color; ctx.fillText(text, x, y);
}

// Names for a left→right map: lights above the road (or below when two are close), the ends, and the freeway.
function nameAlong(ctx, geo, p, w, h, gapFromRoad) {
  ctx.textBaseline = 'middle';
  ctx.font = `600 11px ${FONT}`;
  ctx.textAlign = 'left'; halo(ctx, '← North', 8, 12, '#6b7685');
  ctx.textAlign = 'right'; halo(ctx, 'South →', w - 8, 12, '#6b7685');
  ctx.textAlign = 'center';
  let free = 8 + ctx.measureText('← North').width + 10;
  const below = [];
  const sigs = geo.signals.map(sig => { const [cx, cy] = centre(sig); return { name: sig.name, x: p.x(cx, cy), y: p.y(cx, cy) }; }).sort((a, b) => a.x - b.x);
  ctx.font = `600 12px ${FONT}`;
  for (const s of sigs) {
    const half = ctx.measureText(s.name).width / 2, top = s.x - half > free;
    const ly = top ? 12 : h - 12;
    if (top) free = s.x + half + 40; else below.push([s.x - half, s.x + half]);
    ctx.strokeStyle = '#d5dbe2'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(s.x, top ? ly + 9 : ly - 9); ctx.lineTo(s.x, top ? s.y - gapFromRoad : s.y + gapFromRoad); ctx.stroke();
    halo(ctx, s.name, s.x, ly, '#2b3442');
  }
  const ramps = sigs.filter(s => s.name.startsWith('I-280'));
  if (ramps.length === 2) {
    ctx.font = `700 11px ${FONT}`;
    const x = (ramps[0].x + ramps[1].x) / 2, half = ctx.measureText('I-280').width / 2;
    if (!below.some(([a, b]) => x + half > a && x - half < b)) halo(ctx, 'I-280', x, h - 12, '#6b7685');
  }
}

// Static map with numbered signal markers; `pick` highlights one signal (0-based). links[i] = {href, label} makes marker i a real link.
function drawMap(box, geo, pick = -1, links = []) {
  const { ctx, w, h } = canvasFor(box);
  const along = box.hasAttribute('data-along');
  const p = fit(geo, w, h, 22, along);
  drawRoads(ctx, geo, p);
  ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
  box.querySelectorAll('a.mk').forEach(a => a.remove());
  geo.signals.forEach((sig, i) => {
    const [cx, cy] = centre(sig), x = p.x(cx, cy), y = p.y(cx, cy), on = pick < 0 || pick === i;
    if (links[i]) box.insertAdjacentHTML('beforeend', `<a class="mk" href="${links[i].href}" style="left:${x.toFixed(1)}px;top:${y.toFixed(1)}px" aria-label="${esc(links[i].label)}" title="${esc(links[i].label)}"></a>`);
    ctx.beginPath(); ctx.arc(x, y, 9, 0, 2 * Math.PI);
    ctx.fillStyle = on ? '#1d4ed8' : '#fff'; ctx.fill();
    ctx.lineWidth = 2; ctx.strokeStyle = on ? '#fff' : '#94a0b0'; ctx.stroke();
    ctx.font = `700 10px ${FONT}`; ctx.fillStyle = on ? '#fff' : '#526072';
    ctx.fillText(String(i + 1), x, y + .5);
  });
  if (along) {
    ctx.font = `600 11px ${FONT}`; ctx.textBaseline = 'middle';
    ctx.textAlign = 'left'; halo(ctx, '← North', 8, 12, '#6b7685');
    ctx.textAlign = 'right'; halo(ctx, 'South →', w - 8, 12, '#6b7685');
  }
}
