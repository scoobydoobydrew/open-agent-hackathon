// Search: the counterexample-guided search growing as a tree, event by event, straight from the solver.
import { stream } from './api.js';
import { addStrings, onLang, t } from './i18n.js';
import { badge, chip, clear, countTo, esc, fmt, h, hideTip, s, showTip } from './ui.js';
import { current, onScenario, store } from './store.js';

addStrings({
  en: {
    'se.title': 'Counterexample-guided search', 'se.idea': 'Start from the empty set. Every failing knockout set comes with a surviving state; only the genes that keep that state alive can break it, so only those are added. Nothing is skipped, so the search either finds every minimal solution or proves that none exists.',
    'se.run': 'Run search', 'se.stop': 'Stop', 'se.reset': 'Reset', 'se.size': 'Max genes', 'se.mem': 'Memory replay',
    'se.mem.tip': 'Reuse stored surviving states to refute new sets without calling the solver', 'se.speed': 'Speed',
    'se.calls': 'Solver calls', 'se.vs': 'Brute force would check', 'se.sets': 'sets', 'se.fewer': '× fewer calls',
    'se.replays': 'Refuted from memory', 'se.frontier': 'Queue', 'se.sols': 'Solutions', 'se.legend': 'How to read the tree',
    'se.l.root': 'start: no knockout', 'se.l.fail': 'still survives', 'se.l.mem': 'refuted from memory, no solver call',
    'se.l.sol': 'minimal solution', 'se.l.nm': 'works, but a subset already works', 'se.running': 'Searching…',
    'se.done': 'Search complete', 'se.proved': 'No solution exists', 'se.proved.help': 'The queue ran dry, so no set of up to {n} genes forces apoptosis. This is a proof, not a failure to find one.',
    'se.found': '{n} minimal solution(s) found', 'se.found.help': 'The queue ran dry, so these are all of them (up to {n} genes).',
    'se.empty.title': 'Watch the search work', 'se.empty.text': 'Press “Run search”. Each box is a set of knockouts the solver checks. The label is the gene that was added; hover for the full set.',
    'se.n.root': 'The cell with no knockout survives. Its surviving state keeps {n} genes active ({genes}). Only these can break it, so only these are tried first.',
    'se.n.fail': '{set} still survives. Its state keeps {genes} active, so those are the only useful additions.',
    'se.n.fail0': '{set} still survives and cannot grow any further.', 'se.n.mem': '{set} is refuted instantly from a stored surviving state. No solver call.',
    'se.n.sol': '{set} forces apoptosis in every long-term state, and no smaller subset does. Minimal solution found.',
    'se.n.nm': '{set} works, but a smaller subset already works, so it is not minimal.', 'se.n.end': 'Queue empty. Every possible extension has been ruled out or solved.',
    'se.tip.alive': 'Keeps the cell alive', 'se.tip.set': 'Knockout set', 'se.tip.mem': 'refuted from memory', 'se.tip.solver': 'solver call',
    'se.err': 'The server could not run the search',
  },
  el: {
    'se.title': 'Αναζήτηση καθοδηγούμενη από counterexamples', 'se.idea': 'Ξεκινά από το κενό σύνολο. Κάθε σύνολο που αποτυγχάνει δίνει μια κατάσταση επιβίωσης: μόνο τα γονίδια που τη διατηρούν μπορούν να τη σπάσουν, άρα προστίθενται μόνο αυτά. Τίποτα δεν παραλείπεται, οπότε η αναζήτηση βρίσκει όλες τις ελάχιστες λύσεις ή αποδεικνύει ότι δεν υπάρχει καμία.',
    'se.run': 'Εκτέλεση', 'se.stop': 'Στοπ', 'se.reset': 'Επαναφορά', 'se.size': 'Μέγ. γονίδια', 'se.mem': 'Επανάληψη από μνήμη',
    'se.mem.tip': 'Επαναχρησιμοποίηση αποθηκευμένων καταστάσεων επιβίωσης για να απορριφθούν νέα σύνολα χωρίς κλήση solver', 'se.speed': 'Ταχύτητα',
    'se.calls': 'Κλήσεις solver', 'se.vs': 'Το brute force θα έλεγχε', 'se.sets': 'σύνολα', 'se.fewer': '× λιγότερες κλήσεις',
    'se.replays': 'Απορρίφθηκαν από μνήμη', 'se.frontier': 'Ουρά', 'se.sols': 'Λύσεις', 'se.legend': 'Πώς διαβάζεται το δέντρο',
    'se.l.root': 'αρχή: κανένα knockout', 'se.l.fail': 'επιβιώνει ακόμα', 'se.l.mem': 'απορρίφθηκε από μνήμη, χωρίς solver',
    'se.l.sol': 'ελάχιστη λύση', 'se.l.nm': 'δουλεύει, αλλά υποσύνολό του ήδη δουλεύει', 'se.running': 'Αναζήτηση…',
    'se.done': 'Η αναζήτηση ολοκληρώθηκε', 'se.proved': 'Δεν υπάρχει λύση', 'se.proved.help': 'Η ουρά άδειασε, άρα κανένα σύνολο έως {n} γονίδια δεν επιβάλλει απόπτωση. Είναι απόδειξη, όχι αποτυχία εύρεσης.',
    'se.found': 'Βρέθηκαν {n} ελάχιστες λύσεις', 'se.found.help': 'Η ουρά άδειασε, άρα είναι όλες (έως {n} γονίδια).',
    'se.empty.title': 'Δες την αναζήτηση να δουλεύει', 'se.empty.text': 'Πάτησε «Εκτέλεση». Κάθε κουτί είναι ένα σύνολο knockouts που ελέγχει ο solver. Η ετικέτα είναι το γονίδιο που προστέθηκε· πέρασε το ποντίκι για ολόκληρο το σύνολο.',
    'se.n.root': 'Το κύτταρο χωρίς knockout επιβιώνει. Η κατάστασή του κρατά ενεργά {n} γονίδια ({genes}). Μόνο αυτά μπορούν να τη σπάσουν, άρα δοκιμάζονται πρώτα.',
    'se.n.fail': 'Το {set} επιβιώνει ακόμα. Η κατάστασή του κρατά ενεργά τα {genes}, άρα αυτές είναι οι μόνες χρήσιμες προσθήκες.',
    'se.n.fail0': 'Το {set} επιβιώνει ακόμα και δεν μπορεί να μεγαλώσει άλλο.', 'se.n.mem': 'Το {set} απορρίπτεται αμέσως από αποθηκευμένη κατάσταση επιβίωσης. Καμία κλήση solver.',
    'se.n.sol': 'Το {set} επιβάλλει απόπτωση σε κάθε μακροχρόνια κατάσταση και κανένα μικρότερο υποσύνολο δεν το κάνει. Βρέθηκε ελάχιστη λύση.',
    'se.n.nm': 'Το {set} δουλεύει, αλλά μικρότερο υποσύνολο ήδη δουλεύει, άρα δεν είναι ελάχιστο.', 'se.n.end': 'Η ουρά άδειασε. Κάθε πιθανή επέκταση έχει αποκλειστεί ή λυθεί.',
    'se.tip.alive': 'Κρατά το κύτταρο ζωντανό', 'se.tip.set': 'Σύνολο knockout', 'se.tip.mem': 'απορρίφθηκε από μνήμη', 'se.tip.solver': 'κλήση solver',
    'se.err': 'Ο server δεν μπόρεσε να τρέξει την αναζήτηση',
  },
});

const COL_W = 88, ROW_H = 27, ROWS = 18, GAP = 46, PILL_W = 80, PILL_H = 20;
const SPEEDS = [['1×', 6], ['4×', 26], ['16×', 110], ['⚡', 1e9]];
let root, ui = {}, st;

function fresh() {
  return { nodes: new Map(), levels: [], queue: [], timer: null, stop: null, running: false, done: null, speed: 1, maxSize: null,
    mem: false, brute: null, calls: 0, replays: 0, frontier: 0, sols: [], narrative: '', last: null, error: null };
}

export function init(container) {
  root = container; st = fresh(); build(); draw(); stats();
  onScenario(() => { reset(); });
  onLang(() => { build(); draw(); stats(); });
}
export function onShow() { measure(); }

function reset() {
  if (st && st.stop) st.stop(); if (st && st.timer) clearInterval(st.timer);
  const keep = { speed: st ? st.speed : 1, maxSize: null, mem: st ? st.mem : false };
  st = Object.assign(fresh(), { speed: keep.speed, mem: keep.mem }); build(); draw(); stats();
}

function build() {
  clear(root);
  const sc = current(), maxSize = st.maxSize ?? sc.max_size ?? 3;
  const card = 'glass rounded-2xl';
  ui.canvas = h('div', { class: 'scroll-thin relative h-[580px] overflow-auto rounded-xl bg-black/20' });
  ui.narr = h('div', { class: 'min-h-[3.2rem] text-sm leading-relaxed text-slate-300' });
  ui.sols = h('div', {}); ui.banner = h('div', {});
  ui.big = h('div', { class: 'num bg-gradient-to-r from-cyan-300 to-fuchsia-300 bg-clip-text text-5xl font-bold text-transparent' }, '0');
  ui.ratio = h('div', { class: 'hidden rounded-full bg-emerald-400/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-300 ring-1 ring-inset ring-emerald-400/30' });
  ui.vs = h('div', { class: 'mt-3 text-[11px] text-slate-500' });
  ui.bar = h('div', { class: 'h-full rounded-full bg-gradient-to-r from-cyan-400 to-fuchsia-400 transition-all duration-300', style: { width: '0%' } });
  const num = tone => h('div', { class: `num text-2xl font-semibold ${tone}` }, '0');
  const tile = (label, el) => h('div', { class: 'rounded-xl bg-white/[.04] p-3 ring-1 ring-inset ring-white/5' }, h('div', { class: 'text-[10px] uppercase leading-tight tracking-wider text-slate-500' }, label), el);
  ui.rep = num('text-amber-300'); ui.fr = num('text-slate-200'); ui.sol = num('text-emerald-300');
  ui.stats = h('div', {}, h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-slate-500' }, t('se.calls')),
    h('div', { class: 'flex items-baseline gap-3' }, ui.big, ui.ratio), ui.vs, h('div', { class: 'mt-1.5 h-2 overflow-hidden rounded-full bg-white/[.07]' }, ui.bar),
    h('div', { class: 'mt-4 grid grid-cols-3 gap-2' }, tile(t('se.replays'), ui.rep), tile(t('se.frontier'), ui.fr), tile(t('se.sols'), ui.sol)));
  const sizeSel = h('select', { class: 'rounded-lg bg-white/10 px-2 py-1 text-xs text-white ring-1 ring-white/15 focus:outline-none', onchange: e => { st.maxSize = +e.target.value; } },
    ...[2, 3, 4].map(n => h('option', { value: n, selected: n === maxSize, class: 'bg-ink-900' }, n)));
  const memBox = h('label', { class: 'flex cursor-pointer items-center gap-1.5 text-xs text-slate-300', title: t('se.mem.tip') },
    h('input', { type: 'checkbox', checked: st.mem, class: 'accent-cyan-400', onchange: e => { st.mem = e.target.checked; } }), t('se.mem'));
  const speed = h('div', { class: 'flex overflow-hidden rounded-lg ring-1 ring-white/15' }, ...SPEEDS.map(([label], i) => h('button', {
    class: `px-2 py-1 text-xs transition ${st.speed === i ? 'bg-white/20 text-white' : 'text-slate-400 hover:text-white'}`, onclick: () => { st.speed = i; build(); draw(); stats(); } }, label)));
  const run = st.running
    ? h('button', { class: 'rounded-lg bg-rose-500/80 px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-rose-400', onclick: stop }, '■ ' + t('se.stop'))
    : h('button', { class: 'rounded-lg bg-gradient-to-r from-cyan-400 to-sky-500 px-4 py-1.5 text-sm font-semibold text-ink-950 shadow-[0_0_24px_rgba(34,211,238,.35)] transition hover:brightness-110', onclick: start }, '▶ ' + t('se.run'));
  const head = h('div', { class: 'mb-3 flex flex-wrap items-center gap-x-4 gap-y-2' }, h('div', { class: 'text-base font-semibold text-white' }, t('se.title')),
    h('div', { class: 'ml-auto flex flex-wrap items-center gap-3' }, h('label', { class: 'flex items-center gap-1.5 text-xs text-slate-400' }, t('se.size'), sizeSel), memBox,
      h('div', { class: 'flex items-center gap-1.5 text-xs text-slate-400' }, t('se.speed'), speed), run,
      h('button', { class: 'text-xs text-slate-400 hover:text-white', onclick: reset }, t('se.reset'))));
  const left = h('div', { class: `${card} p-4` }, head, h('div', { class: 'mb-3 max-w-3xl text-xs leading-relaxed text-slate-500' }, t('se.idea')), ui.canvas,
    h('div', { class: 'mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400' }, h('span', { class: 'text-slate-500' }, t('se.legend') + ':'),
      ...[['#22d3ee', t('se.l.root')], ['#fb7185', t('se.l.fail')], ['#fbbf24', t('se.l.mem')], ['#34d399', t('se.l.sol')], ['#64748b', t('se.l.nm')]].map(([c, l]) =>
        h('span', { class: 'flex items-center gap-1.5' }, h('span', { class: 'inline-block h-2.5 w-4 rounded-sm', style: { background: c } }), l))));
  const right = h('div', { class: 'flex flex-col gap-4' }, h('div', { class: `${card} p-4` }, ui.stats), ui.banner, h('div', { class: `${card} p-4` }, h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-slate-500' }, '◉ live'), ui.narr), h('div', { class: `${card} p-4` }, ui.sols));
  clear(root).append(h('div', { class: 'grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]' }, left, right));
}

function measure() { /* layout depends on the container width only through the scale */ draw(); }

// ---------- running -------------------------------------------------------------------------------
function start() {
  const sc = current(), chosen = st.maxSize;
  reset(); st.maxSize = chosen;
  const maxSize = st.maxSize ?? sc.max_size ?? 3;
  const params = { scenario: sc.id, max_size: maxSize, memory: st.mem ? '1' : '0' };
  if (sc.custom) params.fixed = JSON.stringify(sc.fixed);
  st.running = true; build(); draw(); stats();
  st.stop = stream('/api/search', params, ev => st.queue.push(ev), () => { st.streamEnded = true; });
  const rate = SPEEDS[st.speed][1];
  st.timer = setInterval(() => {
    const n = rate >= 1e8 ? st.queue.length : Math.max(1, Math.round(rate * .05));
    let changed = false;
    for (let i = 0; i < n && st.queue.length; i++) { handle(st.queue.shift()); changed = true; }
    if (changed) { draw(); stats(); }
    if (!st.queue.length && st.streamEnded) { clearInterval(st.timer); st.timer = null; st.running = false; build(); draw(); stats(); }
  }, 50);
}
function stop() { if (st.stop) st.stop(); st.queue.length = 0; clearInterval(st.timer); st.timer = null; st.running = false; build(); draw(); stats(); }

const key = kos => kos.join('|');
function handle(ev) {
  if (ev.type === 'init') { st.brute = ev.brute_force_sets; st.maxSize = ev.max_size; return; }
  if (ev.type === 'error') { st.error = ev.message; return; }
  if (ev.type === 'done') { st.done = ev; return; }
  if (ev.type === 'exhausted') { st.narrative = t('se.n.end'); return; }
  if (ev.type !== 'visit') return;
  const lvl = ev.kos.length, added = ev.parent ? ev.kos.find(g => !ev.parent.includes(g)) : null;
  const node = { ...ev, key: key(ev.kos), level: lvl, added, born: performance.now() };
  while (st.levels.length <= lvl) st.levels.push([]);
  node.idx = st.levels[lvl].length; st.levels[lvl].push(node); st.nodes.set(node.key, node);
  st.calls = ev.calls; st.replays = ev.replays; st.frontier = ev.frontier;
  if (ev.solution) st.sols.push(ev.kos);
  st.last = node;
  const set = ev.kos.length ? `{${ev.kos.join(', ')}}` : '∅';
  const gl = ev.active.join(', ');
  st.narrative = !ev.kos.length ? t('se.n.root', { n: ev.active.length, genes: gl })
    : ev.solution ? t('se.n.sol', { set }) : ev.verdict === 'FORCED' ? t('se.n.nm', { set })
    : ev.via === 'memory' ? t('se.n.mem', { set }) : ev.kos.length >= (st.maxSize || 3) ? t('se.n.fail0', { set }) : t('se.n.fail', { set, genes: gl });
}

// ---------- layout & drawing ----------------------------------------------------------------------
function layout() {
  let x = 24; const origin = [];
  st.levels.forEach((lv, l) => { origin[l] = x; x += Math.max(1, Math.ceil(lv.length / ROWS)) * COL_W + GAP; });
  const maxRows = Math.max(1, ...st.levels.map(lv => Math.min(ROWS, lv.length)));
  st.levels.forEach((lv, l) => lv.forEach(n => {
    const sub = Math.floor(n.idx / ROWS), row = n.idx % ROWS;
    n.x = origin[l] + sub * COL_W; n.y = 30 + row * ROW_H;
  }));
  return { w: Math.max(x, 400), h: maxRows * ROW_H + 60 };
}

function toneOf(n) {
  if (!n.kos.length) return { fill: 'rgba(34,211,238,.18)', stroke: '#22d3ee', text: '#a5f3fc' };
  if (n.solution) return { fill: 'rgba(52,211,153,.35)', stroke: '#34d399', text: '#ecfdf5', glow: true };
  if (n.verdict === 'FORCED') return { fill: 'rgba(100,116,139,.18)', stroke: '#64748b', text: '#94a3b8', dash: true };
  if (n.via === 'memory') return { fill: 'rgba(251,191,36,.14)', stroke: '#fbbf24', text: '#fde68a' };
  return { fill: 'rgba(251,113,133,.13)', stroke: '#fb7185', text: '#fecdd3' };
}

function draw() {
  const box = ui.canvas; if (!box) return;
  clear(box);
  if (!st.levels.length) {
    box.append(h('div', { class: 'grid h-full place-items-center p-6 text-center' }, h('div', { class: 'max-w-sm' },
      h('div', { class: 'mx-auto mb-4 grid h-14 w-14 animate-floaty place-items-center rounded-2xl bg-gradient-to-br from-cyan-400/30 to-fuchsia-400/30 text-2xl ring-1 ring-white/15' }, '🌱'),
      h('div', { class: 'mb-1 text-base font-semibold text-white' }, t('se.empty.title')), h('div', { class: 'text-xs leading-relaxed text-slate-400' }, t('se.empty.text')))));
    return;
  }
  const { w, h: hh } = layout();
  const svg = s('svg', { width: w, height: hh, viewBox: `0 0 ${w} ${hh}` });
  const eg = s('g'), ng = s('g'); svg.append(eg, ng);
  for (const n of st.nodes.values()) {
    if (n.parent) {
      const p = st.nodes.get(key(n.parent));
      if (p) {
        const x0 = p.x + PILL_W, y0 = p.y + PILL_H / 2, x1 = n.x, y1 = n.y + PILL_H / 2, mx = (x0 + x1) / 2;
        eg.append(s('path', { d: `M${x0} ${y0} C${mx} ${y0} ${mx} ${y1} ${x1} ${y1}`, fill: 'none', stroke: n.solution ? '#34d399' : '#475569', 'stroke-width': n.solution ? 2 : 1, opacity: n.solution ? .9 : .35 }));
      }
    }
  }
  for (const n of st.nodes.values()) {
    const tone = toneOf(n), fresh = performance.now() - n.born < 700;
    const outer = s('g', { transform: `translate(${n.x},${n.y})` });   // position lives here: a CSS animation would override it
    const g = s('g', { class: fresh ? 'animate-pop' : '', style: 'transform-box: fill-box; transform-origin: left center; cursor: default' });
    outer.append(g);
    g.append(s('rect', { width: PILL_W, height: PILL_H, rx: 6, fill: tone.fill, stroke: tone.stroke, 'stroke-width': n.solution ? 1.8 : 1.1, 'stroke-dasharray': tone.dash ? '3 3' : '', filter: tone.glow ? 'drop-shadow(0 0 6px rgba(52,211,153,.8))' : '' }),
      s('text', { x: PILL_W / 2, y: 14, 'text-anchor': 'middle', 'font-size': 10.5, 'font-weight': n.solution ? 700 : 500, fill: tone.text, 'font-family': 'ui-monospace, Consolas, monospace' },
        !n.kos.length ? '∅ start' : (n.via === 'memory' ? '↺ ' : '') + (n.added || n.kos[0])));
    g.addEventListener('mousemove', ev => showTip(ev, `<div class="mb-1 text-[10px] uppercase tracking-wider text-slate-500">${t('se.tip.set')}</div><div class="mb-1 font-mono text-sm text-white">${n.kos.length ? esc(n.kos.join(' + ')) : '∅'}</div><div class="text-[11px] ${n.solution ? 'text-emerald-300' : n.verdict === 'FORCED' ? 'text-slate-400' : 'text-rose-300'}">${n.solution ? '✓ ' + t('se.l.sol') : n.verdict === 'FORCED' ? t('se.l.nm') : t('se.l.fail')} · ${n.via === 'memory' ? t('se.tip.mem') : t('se.tip.solver')}</div>${n.active.length && n.verdict !== 'FORCED' ? `<div class="mt-1.5 text-[11px] text-slate-400">${t('se.tip.alive')}: <span class="font-mono text-slate-200">${esc(n.active.join(', '))}</span></div>` : ''}`));
    g.addEventListener('mouseleave', hideTip);
    ng.append(outer);
  }
  box.append(svg);
  if (st.running) box.scrollLeft = box.scrollWidth;
}

function stats() {
  if (!ui.stats) return;
  const ratio = st.brute && st.calls ? st.brute / st.calls : null;
  ui.big.textContent = fmt(st.calls);
  if (ratio && ratio >= 1.2) { ui.ratio.textContent = `${ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)}${t('se.fewer')}`; ui.ratio.classList.remove('hidden'); } else ui.ratio.classList.add('hidden');
  ui.vs.textContent = `${t('se.vs')} ${fmt(st.brute)} ${t('se.sets')}`;
  ui.bar.style.width = `${st.brute ? Math.min(100, (st.calls / st.brute) * 100) : 0}%`;
  ui.rep.textContent = fmt(st.replays); ui.fr.textContent = fmt(st.frontier); ui.sol.textContent = fmt(st.sols.length);
  ui.narr.textContent = st.error ? `${t('se.err')}: ${st.error}` : st.narrative || (st.running ? t('se.running') : '');
  // solutions
  clear(ui.sols).append(h('div', { class: 'mb-2 text-[11px] uppercase tracking-wider text-slate-500' }, t('se.sols')),
    h('div', { class: 'flex flex-wrap gap-2' }, ...(st.sols.length ? st.sols.map(k => h('span', { class: 'animate-pop rounded-lg bg-emerald-400/15 px-2.5 py-1.5 font-mono text-xs text-emerald-200 ring-1 ring-inset ring-emerald-400/40 shadow-[0_0_18px_rgba(52,211,153,.25)]' }, k.join(' + '))) : [h('span', { class: 'text-xs text-slate-500' }, '–')])));
  // banner
  const b = clear(ui.banner);
  if (st.done && !st.running) {
    const proved = st.done.proved_infeasible, n = st.maxSize || 3;
    b.append(h('div', { class: `rounded-2xl p-4 ring-1 ring-inset ${proved ? 'bg-violet-400/10 ring-violet-300/40 shadow-[0_0_40px_rgba(167,139,250,.2)]' : 'bg-emerald-400/10 ring-emerald-300/40'}` },
      h('div', { class: `text-sm font-bold ${proved ? 'text-violet-200' : 'text-emerald-200'}` }, proved ? '∎ ' + t('se.proved') : '✓ ' + t('se.found', { n: st.sols.length })),
      h('div', { class: 'mt-1 text-xs leading-relaxed text-slate-300' }, proved ? t('se.proved.help', { n }) : t('se.found.help', { n })),
      h('div', { class: 'mt-2 text-[11px] text-slate-500' }, `${st.done.seconds}s · ${fmt(st.done.calls)} ${t('se.calls').toLowerCase()}`)));
  }
}
