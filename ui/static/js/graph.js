// The gene network as a living SVG picture. Colours follow the displayed attractor.
import { s, esc, showTip, hideTip } from './ui.js';
import { addStrings, t } from './i18n.js';

addStrings({
  en: { 'g.DNA_damage': 'Radiation', 'g.EGFR_stimulus': 'EGF signal', 'g.FGFR3_stimulus': 'FGFR3 signal',
        'g.Growth_inhibitors': 'Growth inhibitors', 'g.Apoptosis': 'APOPTOSIS', 'g.Proliferation': 'Proliferation',
        'g.Growth_arrest': 'Growth arrest', 'tip.click.ko': 'Click to knock out', 'tip.click.undo': 'Click to restore',
        'tip.click.input': 'Click to switch this input', 'tip.drug': 'Drug evidence', 'tip.lost': 'Lost in this tumour',
        'tip.forced': 'Constitutively on in this tumour', 'tip.osc': 'oscillating', 'tip.input': 'input' },
  el: { 'g.DNA_damage': 'Ακτινοβολία', 'g.EGFR_stimulus': 'Σήμα EGF', 'g.FGFR3_stimulus': 'Σήμα FGFR3',
        'g.Growth_inhibitors': 'Αναστολείς ανάπτυξης', 'g.Apoptosis': 'ΑΠΟΠΤΩΣΗ', 'g.Proliferation': 'Πολλαπλασιασμός',
        'g.Growth_arrest': 'Αναστολή ανάπτυξης', 'tip.click.ko': 'Κλικ για knockout', 'tip.click.undo': 'Κλικ για επαναφορά',
        'tip.click.input': 'Κλικ για αλλαγή εισόδου', 'tip.drug': 'Φαρμακευτική τεκμηρίωση', 'tip.lost': 'Χαμένο σε αυτόν τον όγκο',
        'tip.forced': 'Μόνιμα ενεργό σε αυτόν τον όγκο', 'tip.osc': 'ταλαντώνεται', 'tip.input': 'είσοδος' },
});

export const W = 1000, H = 640;
const RAD = 17;

function mulberry32(a) {
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let x = Math.imul(a ^ (a >>> 15), 1 | a); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
}

export function computeLayout(graph) {
  const rnd = mulberry32(11);
  const colX = d => 90 + d * (W - 180) / graph.max_depth;
  const P = graph.genes.map(g => ({ id: g.id, g, x: colX(g.depth) + (rnd() - .5) * 60, y: 70 + rnd() * (H - 140), pin: false }));
  const by = Object.fromEntries(P.map(p => [p.id, p]));
  const ins = P.filter(p => p.g.kind === 'input');
  ins.forEach((p, i) => { p.x = colX(0); p.y = 120 + i * (H - 240) / Math.max(1, ins.length - 1); p.pin = true; });
  const order = ['Apoptosis', 'Growth_arrest', 'Proliferation'];
  const outs = order.map(id => by[id]).filter(Boolean);
  outs.forEach((p, i) => { p.x = colX(graph.max_depth) - 10; p.y = 150 + i * (H - 300) / Math.max(1, outs.length - 1); p.pin = true; });
  const E = graph.edges.map(e => [by[e.source], by[e.target]]);
  const iters = 700;
  for (let it = 0; it < iters; it++) {
    const alpha = Math.pow(1 - it / iters, 1.5) + .03;
    for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
      const a = P[i], b = P[j]; let dx = a.x - b.x, dy = a.y - b.y; const d2 = dx * dx + dy * dy + .5, d = Math.sqrt(d2);
      const f = Math.min(40, 5200 / d2) * alpha; dx /= d; dy /= d;
      if (!a.pin) { a.x += dx * f; a.y += dy * f; } if (!b.pin) { b.x -= dx * f; b.y -= dy * f; }
    }
    for (const [a, b] of E) {
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) + .01, f = (d - 120) * .012 * alpha;
      if (!a.pin) { a.x += dx / d * f; a.y += dy / d * f; } if (!b.pin) { b.x -= dx / d * f; b.y -= dy / d * f; }
    }
    for (const p of P) if (!p.pin) {
      p.x += (colX(p.g.depth) - p.x) * .05 * alpha; p.y += (H / 2 - p.y) * .004;
      p.x = Math.max(60, Math.min(W - 60, p.x)); p.y = Math.max(50, Math.min(H - 50, p.y));
    }
  }
  const free = P.filter(p => !p.pin);
  const xs = free.map(p => p.x), ys = free.map(p => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  free.forEach(p => { p.x = 205 + (p.x - x0) / ((x1 - x0) || 1) * (W - 410); p.y = 55 + (p.y - y0) / ((y1 - y0) || 1) * (H - 110); });
  for (let k = 0; k < 80; k++) for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
    const a = P[i], b = P[j]; const dx = a.x - b.x, dy = a.y - b.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
    if (d < 66) { const push = (66 - d) / 2 / d; if (!a.pin) { a.x += dx * push; a.y += dy * push; } if (!b.pin) { b.x -= dx * push; b.y -= dy * push; } }
  }
  return Object.fromEntries(P.map(p => [p.id, { x: p.x, y: p.y }]));
}

const kindSize = g => (g.kind === 'input' ? { hw: 38, hh: 14 } : g.kind === 'output' ? { hw: 50, hh: 21 } : { hw: RAD + 3, hh: RAD + 3 });
function edgePoint(pos, g, tx, ty) {
  const { hw, hh } = kindSize(g); const dx = tx - pos.x, dy = ty - pos.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
  if (g.kind === 'gene') return { x: pos.x + dx / d * hw, y: pos.y + dy / d * hw };
  const k = Math.min(hw / (Math.abs(dx / d) || 1e-6), hh / (Math.abs(dy / d) || 1e-6));
  return { x: pos.x + dx / d * k, y: pos.y + dy / d * k };
}

const EDGE = { '+': '#34d399', '-': '#fb7185', '+/-': '#fbbf24' };

export const geneLabel = g => (g.kind === 'gene' ? g.id : t('g.' + g.id));

export class NetworkGraph {
  constructor(container, graph, opts = {}) {
    this.graph = graph; this.opts = opts;
    this.state = { values: null, kos: [], fixed: {}, hot: {}, focus: null };
    this.pos = computeLayout(graph);
    this.gene = Object.fromEntries(graph.genes.map(g => [g.id, g]));
    this.svg = s('svg', { viewBox: `0 0 ${W} ${H}`, class: 'h-full w-full select-none', preserveAspectRatio: 'xMidYMid meet' });
    this.svg.append(this._defs());
    this.edgeLayer = s('g'); this.nodeLayer = s('g');
    this.svg.append(this.edgeLayer, this.nodeLayer);
    this.edgeEls = graph.edges.map(e => this._edge(e));
    this.nodeEls = Object.fromEntries(graph.genes.map(g => [g.id, this._node(g)]));
    container.append(this.svg);
    this.update();
  }

  _defs() {
    const defs = s('defs');
    for (const [name, col] of Object.entries({ pos: EDGE['+'], neg: EDGE['-'], mix: EDGE['+/-'] })) {
      const path = name === 'neg' ? s('path', { d: 'M2 -5 L2 5', stroke: col, 'stroke-width': 2.4, fill: 'none' })
        : s('path', { d: 'M0 -4.5 L9 0 L0 4.5 z', fill: col });
      defs.append(s('marker', { id: `arr-${name}`, markerWidth: 10, markerHeight: 10, refX: name === 'neg' ? 3 : 8, refY: 0, orient: 'auto', markerUnits: 'userSpaceOnUse', viewBox: '0 -6 10 12', overflow: 'visible' }, path));
    }
    const glow = (id, dev) => s('filter', { id, x: '-80%', y: '-80%', width: '260%', height: '260%' },
      s('feGaussianBlur', { stdDeviation: dev, result: 'b' }), s('feMerge', {}, s('feMergeNode', { in: 'b' }), s('feMergeNode', { in: 'SourceGraphic' })));
    defs.append(glow('glow', 5), glow('glowBig', 9));
    return defs;
  }

  _edge(e) {
    const a = this.gene[e.source], b = this.gene[e.target], pa = this.pos[e.source], pb = this.pos[e.target];
    const dx = pb.x - pa.x, dy = pb.y - pa.y, len = Math.sqrt(dx * dx + dy * dy) || 1;
    const c = { x: (pa.x + pb.x) / 2 - dy / len * len * .13, y: (pa.y + pb.y) / 2 + dx / len * len * .13 };
    const p0 = edgePoint(pa, a, c.x, c.y), p1 = edgePoint(pb, b, c.x, c.y);
    const mark = e.sign === '+' ? 'pos' : e.sign === '-' ? 'neg' : 'mix';
    const path = s('path', { d: `M${p0.x.toFixed(1)} ${p0.y.toFixed(1)} Q${c.x.toFixed(1)} ${c.y.toFixed(1)} ${p1.x.toFixed(1)} ${p1.y.toFixed(1)}`, fill: 'none', stroke: EDGE[e.sign] || '#94a3b8', 'stroke-width': 1.5, 'marker-end': `url(#arr-${mark})`, opacity: .16, style: 'transition: opacity .4s' });
    this.edgeLayer.append(path);
    return { path, e };
  }

  _node(g) {
    const { x, y } = this.pos[g.id]; const grp = s('g', { class: 'node', transform: `translate(${x.toFixed(1)},${y.toFixed(1)})` });
    const els = { grp };
    if (g.kind === 'gene') {
      els.halo = s('circle', { r: RAD + 9, fill: 'none', 'stroke-width': 2, opacity: 0 });
      els.ping = s('circle', { r: RAD + 2, fill: 'none', 'stroke-width': 2, opacity: 0, class: 'ping' });
      els.ring = s('circle', { r: RAD + 5, fill: 'none', 'stroke-width': 2.2, opacity: 0 });
      els.body = s('circle', { r: RAD, class: 'node-body', 'stroke-width': 2 });
      els.ko = s('path', { d: 'M-8 -8 L8 8 M8 -8 L-8 8', stroke: '#fb7185', 'stroke-width': 3.2, 'stroke-linecap': 'round', opacity: 0 });
      els.label = s('text', { y: RAD + 14, 'text-anchor': 'middle', 'font-size': 11, 'font-weight': 600, fill: '#cbd5e1', 'paint-order': 'stroke', stroke: '#050912', 'stroke-width': 3.5 }, g.id);
      els.tag = s('text', { y: -RAD - 8, 'text-anchor': 'middle', 'font-size': 8.5, 'font-weight': 700, fill: '#c4b5fd', 'letter-spacing': '.08em', opacity: 0 });
      grp.append(els.halo, els.ping, els.ring, els.body, els.ko, els.label, els.tag);
    } else {
      const { hw, hh } = kindSize(g);
      els.halo = s('rect', { x: -hw - 8, y: -hh - 8, width: 2 * hw + 16, height: 2 * hh + 16, rx: hh + 8, fill: 'none', 'stroke-width': 2, opacity: 0 });
      els.body = s('rect', { x: -hw, y: -hh, width: 2 * hw, height: 2 * hh, rx: g.kind === 'input' ? 10 : 14, class: 'node-body', 'stroke-width': 2 });
      els.label = s('text', { y: 4, 'text-anchor': 'middle', 'font-size': g.kind === 'input' ? 10.5 : 12.5, 'font-weight': 700, fill: '#e2e8f0' });
      grp.append(els.halo, els.body, els.label);
    }
    const clickable = g.knockable || g.kind === 'input';
    grp.style.cursor = clickable ? 'pointer' : 'default';
    grp.addEventListener('click', () => clickable && this.opts.onToggle && this.opts.onToggle(g));
    grp.addEventListener('mouseenter', () => { this.state.focus = g.id; this._focus(); });
    grp.addEventListener('mousemove', ev => showTip(ev, this._tip(g)));
    grp.addEventListener('mouseleave', () => { this.state.focus = null; this._focus(); hideTip(); });
    this.nodeLayer.append(grp);
    return els;
  }

  geneState(g) {
    const v = this.state.values;
    if (!v) return { lvl: 0, osc: false, known: false };
    const vals = g.nodes.map(n => v[n]);
    if (vals.some(x => x === null)) return { lvl: 1, osc: true, known: true };
    return { lvl: vals.reduce((a, b) => a + (b === 1 ? 1 : 0), 0), osc: false, known: true };
  }

  _lesion(g) {
    const f = this.state.fixed; const vals = g.nodes.map(n => f[n]);
    if (g.kind === 'input') return null;
    if (vals.every(x => x === 0)) return 'lost';
    if (vals.some(x => x === 1)) return 'on';
    return null;
  }

  _tip(g) {
    const v = this.state.values || {}; const ko = this.state.kos.includes(g.id);
    const rows = g.nodes.map(n => `<div class="flex justify-between gap-3"><span class="font-mono text-slate-300">${esc(n)}</span><span class="font-mono ${v[n] === 1 ? 'text-cyan-300' : v[n] === null ? 'text-amber-300' : 'text-slate-500'}">${v[n] === null ? t('tip.osc') : v[n] ?? '–'}</span></div>`).join('');
    const rule = g.nodes.length === 1 ? `<div class="mt-1.5 rounded-md bg-black/40 p-1.5 font-mono text-[10px] leading-snug text-slate-400">${esc(g.rules[g.nodes[0]])}</div>` : '';
    const les = this._lesion(g);
    const drug = g.kind === 'gene' && g.evidence ? `<div class="mt-1.5 text-[11px] text-slate-400">${t('tip.drug')}: <span class="text-slate-200">${esc(g.evidence)}</span>${g.agents ? ` <span class="text-slate-500">(${esc(g.agents)})</span>` : ''}</div>` : '';
    const hint = g.kind === 'input' ? t('tip.click.input') : g.knockable ? (ko ? t('tip.click.undo') : t('tip.click.ko')) : '';
    return `<div class="mb-1 text-sm font-semibold text-white">${esc(geneLabel(g))} <span class="text-[10px] font-normal uppercase tracking-wider text-slate-500">${g.kind === 'input' ? t('tip.input') : ''}</span></div>${les ? `<div class="mb-1 text-[11px] text-violet-300">${les === 'lost' ? t('tip.lost') : t('tip.forced')}</div>` : ''}${rows}${rule}${drug}${hint ? `<div class="mt-2 text-[11px] font-medium text-cyan-300">${hint}</div>` : ''}`;
  }

  _focus() {
    const f = this.state.focus;
    for (const { path, e } of this.edgeEls) {
      const related = f && (e.source === f || e.target === f);
      path.setAttribute('stroke-width', related ? 2.6 : 1.5);
      if (f) path.setAttribute('opacity', related ? .95 : .05);
      else this._edgeOpacity({ path, e });
    }
  }

  _edgeOpacity({ path, e }) {
    const src = this.gene[e.source], st = this.geneState(src), ko = this.state.kos.includes(e.source);
    const live = st.known && st.lvl > 0 && !ko;
    path.setAttribute('opacity', !st.known ? .2 : live ? .8 : .07);
    path.classList.toggle('flow-edge', live);
  }

  update() {
    const { kos, fixed, hot } = this.state;
    for (const g of this.graph.genes) {
      const els = this.nodeEls[g.id], st = this.geneState(g), ko = kos.includes(g.id), les = this._lesion(g);
      let fill = '#111a2e', stroke = '#3b4a68', glow = null, ringCol = null, halo = null, text = '#cbd5e1';
      if (g.kind === 'gene') {
        if (!st.known) { fill = '#131c31'; stroke = '#475569'; }
        else if (ko) { fill = '#2a0f1a'; stroke = '#fb7185'; }
        else if (st.osc) { fill = '#b45309'; stroke = '#fbbf24'; glow = 'glow'; }
        else if (st.lvl > 0) { fill = '#0891b2'; stroke = '#67e8f9'; glow = 'glow'; if (st.lvl > 1) ringCol = '#a5f3fc'; }
        els.body.setAttribute('fill', fill); els.body.setAttribute('stroke', stroke);
        els.body.setAttribute('filter', glow ? `url(#${glow})` : '');
        els.body.setAttribute('stroke-dasharray', les && !ko ? '3 3' : '');
        if (les && !ko && st.known && st.lvl === 0) els.body.setAttribute('stroke', '#a78bfa');
        els.ring.setAttribute('stroke', ringCol || 'none'); els.ring.setAttribute('opacity', ringCol ? .85 : 0);
        els.ko.setAttribute('opacity', ko ? 1 : 0);
        els.ping.setAttribute('stroke', '#fbbf24'); els.ping.setAttribute('opacity', st.osc && !ko ? .7 : 0);
        els.tag.textContent = ko ? 'KO' : les === 'lost' ? t('tip.lost').split(' ')[0].toUpperCase() : les === 'on' ? 'ON' : '';
        els.tag.setAttribute('opacity', ko || les ? 1 : 0); els.tag.setAttribute('fill', ko ? '#fda4af' : '#c4b5fd');
        els.label.setAttribute('fill', ko ? '#fda4af' : st.lvl > 0 || st.osc ? '#f1f5f9' : '#94a3b8');
        const h = hot[g.id];
        els.halo.setAttribute('stroke', h === 'rose' ? '#fb7185' : h === 'green' ? '#34d399' : '#22d3ee');
        els.halo.setAttribute('stroke-dasharray', '5 4');
        els.halo.setAttribute('opacity', h ? .9 : 0);
      } else {
        const isIn = g.kind === 'input';
        const on = isIn ? (fixed[g.nodes[0]] === 1) : st.lvl > 0;
        let tone = { fill: '#111a2e', stroke: '#3b4a68', text: '#94a3b8', glow: null };
        if (isIn) tone = on ? { fill: '#064e3b', stroke: '#34d399', text: '#d1fae5', glow: 'glow' } : { fill: '#111a2e', stroke: '#3b4a68', text: '#94a3b8', glow: null };
        else if (!st.known) tone = { fill: '#131c31', stroke: '#475569', text: '#94a3b8', glow: null };
        else if (g.id === 'Apoptosis') tone = st.lvl === 2 ? { fill: '#047857', stroke: '#6ee7b7', text: '#ecfdf5', glow: 'glowBig' } : st.lvl === 1 || st.osc ? { fill: '#78350f', stroke: '#fbbf24', text: '#fef3c7', glow: null } : { fill: '#2a0f1a', stroke: '#9f1239', text: '#fda4af', glow: null };
        else if (g.id === 'Proliferation') tone = on ? { fill: '#5b21b6', stroke: '#c4b5fd', text: '#f5f3ff', glow: 'glow' } : { fill: '#111a2e', stroke: '#3b4a68', text: '#94a3b8', glow: null };
        else tone = st.osc ? { fill: '#b45309', stroke: '#fbbf24', text: '#fff', glow: 'glow' } : on ? { fill: '#92400e', stroke: '#fcd34d', text: '#fffbeb', glow: 'glow' } : { fill: '#111a2e', stroke: '#3b4a68', text: '#94a3b8', glow: null };
        els.body.setAttribute('fill', tone.fill); els.body.setAttribute('stroke', tone.stroke);
        els.body.setAttribute('filter', tone.glow ? `url(#${tone.glow})` : '');
        els.label.setAttribute('fill', tone.text);
        els.label.textContent = geneLabel(g);
        els.halo.setAttribute('stroke', '#34d399'); els.halo.setAttribute('opacity', g.id === 'Apoptosis' && st.lvl === 2 ? .7 : 0);
      }
    }
    this.edgeEls.forEach(x => this._edgeOpacity(x));
  }

  setState(patch) { Object.assign(this.state, patch); this.update(); }
}
