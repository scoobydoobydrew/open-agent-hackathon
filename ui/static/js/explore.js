// Explore: click genes to knock them out and watch the exact verdict, attractors and proof.
import { NetworkGraph, geneLabel } from './graph.js';
import { verify } from './api.js';
import { addStrings, onLang, t } from './i18n.js';
import { badge, chip, clear, h, fmt } from './ui.js';
import { INPUTS, current, onScenario, setInput } from './store.js';
import { store } from './store.js';

addStrings({
  en: {
    'ex.verdict': 'Verdict', 'ex.forced': 'APOPTOSIS FORCED', 'ex.survives': 'CELL SURVIVES', 'ex.unknown': 'UNDECIDED',
    'ex.solving': 'solving…', 'ex.exact': 'exact', 'ex.hint': 'Click a gene to knock it out', 'ex.kos': 'Knockouts', 'ex.none': 'none yet',
    'ex.clear': 'clear', 'ex.attr': 'Long-term states', 'ex.stable': 'stable state', 'ex.osc': 'oscillation', 'ex.states': 'states',
    'ex.outcome': 'Cell fate in this state', 'ex.apop': 'Committed apoptosis', 'ex.prolif': 'Proliferation', 'ex.arrest': 'Growth arrest',
    'ex.v1': 'yes', 'ex.v0': 'no', 'ex.vosc': 'flickers', 'ex.why.survive': 'Why the cell survives',
    'ex.why.forced': 'Why apoptosis is guaranteed', 'ex.alive': 'Genes keeping it alive',
    'ex.alive.help': 'Only a knockout of one of these can break this state. Click to add.', 'ex.dead': 'Already off here (adding them cannot help)',
    'ex.deriv': 'Show the full derivation', 'ex.proof.help': 'Each step is a rule of the model: if the premises hold, the conclusion follows. All steps were re-checked.',
    'ex.more': 'Show all {n} steps', 'ex.sel': 'Selectivity', 'ex.sel.help': 'Same radiation, but a resting normal cell with the same knockouts',
    'ex.sel.ok': 'Survives: the knockout is selective for the tumour', 'ex.sel.bad': 'Also dies: this knockout is toxic to normal cells',
    'ex.hint2': 'Need a hint?', 'ex.known': 'Known minimal solutions (exhaustive search)', 'ex.nosol': 'None exist: proved by exhaustive search up to 4 genes',
    'ex.selective': 'selective', 'ex.toxic': 'toxic', 'ex.leg.on': 'active', 'ex.leg.off': 'off', 'ex.leg.osc': 'oscillating',
    'ex.leg.ko': 'knocked out', 'ex.leg.lost': 'lost lesion', 'ex.leg.act': 'activates', 'ex.leg.inh': 'inhibits',
    'ex.ce.phen': 'Surviving state', 'ex.no.attr': 'attractor view unavailable for this set', 'ex.premise.ko': 'knockout',
    'ex.premise.sc': 'given',
  },
  el: {
    'ex.verdict': 'Ετυμηγορία', 'ex.forced': 'ΕΠΙΒΑΛΛΕΤΑΙ ΑΠΟΠΤΩΣΗ', 'ex.survives': 'ΤΟ ΚΥΤΤΑΡΟ ΕΠΙΒΙΩΝΕΙ', 'ex.unknown': 'ΑΚΑΤΑΣΤΑΛΤΟ',
    'ex.solving': 'υπολογισμός…', 'ex.exact': 'ακριβής', 'ex.hint': 'Κάνε κλικ σε γονίδιο για knockout', 'ex.kos': 'Knockouts', 'ex.none': 'κανένα ακόμα',
    'ex.clear': 'καθαρισμός', 'ex.attr': 'Μακροχρόνιες καταστάσεις', 'ex.stable': 'σταθερή κατάσταση', 'ex.osc': 'ταλάντωση', 'ex.states': 'καταστάσεις',
    'ex.outcome': 'Τύχη του κυττάρου σε αυτή την κατάσταση', 'ex.apop': 'Δεσμευμένη απόπτωση', 'ex.prolif': 'Πολλαπλασιασμός', 'ex.arrest': 'Αναστολή ανάπτυξης',
    'ex.v1': 'ναι', 'ex.v0': 'όχι', 'ex.vosc': 'αναβοσβήνει', 'ex.why.survive': 'Γιατί επιβιώνει το κύτταρο',
    'ex.why.forced': 'Γιατί εγγυάται η απόπτωση', 'ex.alive': 'Γονίδια που το κρατούν ζωντανό',
    'ex.alive.help': 'Μόνο knockout ενός από αυτά μπορεί να σπάσει αυτή την κατάσταση. Κλικ για προσθήκη.', 'ex.dead': 'Ήδη ανενεργά εδώ (η προσθήκη τους δεν βοηθά)',
    'ex.deriv': 'Δες ολόκληρη την παραγωγή', 'ex.proof.help': 'Κάθε βήμα είναι κανόνας του μοντέλου: αν ισχύουν οι προϋποθέσεις, έπεται το συμπέρασμα. Όλα τα βήματα ελέγχθηκαν ξανά.',
    'ex.more': 'Εμφάνιση και των {n} βημάτων', 'ex.sel': 'Εκλεκτικότητα', 'ex.sel.help': 'Ίδια ακτινοβολία, αλλά σε ήρεμο φυσιολογικό κύτταρο με τα ίδια knockouts',
    'ex.sel.ok': 'Επιβιώνει: το knockout είναι εκλεκτικό για τον όγκο', 'ex.sel.bad': 'Πεθαίνει κι αυτό: το knockout είναι τοξικό για φυσιολογικά κύτταρα',
    'ex.hint2': 'Θες βοήθεια;', 'ex.known': 'Γνωστές ελάχιστες λύσεις (εξαντλητική αναζήτηση)', 'ex.nosol': 'Δεν υπάρχει καμία: αποδείχθηκε εξαντλητικά έως 4 γονίδια',
    'ex.selective': 'εκλεκτική', 'ex.toxic': 'τοξική', 'ex.leg.on': 'ενεργό', 'ex.leg.off': 'ανενεργό', 'ex.leg.osc': 'ταλαντώνεται',
    'ex.leg.ko': 'knockout', 'ex.leg.lost': 'χαμένη βλάβη', 'ex.leg.act': 'ενεργοποιεί', 'ex.leg.inh': 'αναστέλλει',
    'ex.ce.phen': 'Κατάσταση επιβίωσης', 'ex.no.attr': 'η εικόνα attractor δεν είναι διαθέσιμη', 'ex.premise.ko': 'knockout',
    'ex.premise.sc': 'δεδομένο',
  },
});

let root, graph, ko = [], result = null, pick = 0, token = 0, loading = false, showAll = false;
const parts = {};

export function init(container) {
  root = container;
  build();
  onScenario(() => { ko = []; showAll = false; run(); });
  onLang(() => { build(); paint(); });
}
export function onShow() { if (!result) run(); }

function toggleGene(g) {
  if (g.kind === 'input') {
    const node = g.nodes[0], on = current().fixed[node] === 1;
    setInput(node, on ? 0 : 1);
    return;
  }
  ko = ko.includes(g.id) ? ko.filter(x => x !== g.id) : [...ko, g.id];
  run();
}

async function run() {
  const my = ++token, sc = current();
  loading = true; paint();
  let r;
  try { r = await verify(sc.id, sc.custom ? sc.fixed : null, ko); } catch (e) { r = { error: String(e) }; }
  if (my !== token) return;
  loading = false; result = r.error ? null : r;
  if (result) { const bad = result.attractors.findIndex(a => a.values.Apoptosis_high !== 1); pick = bad >= 0 ? bad : 0; }
  paint();
}

function build() {
  clear(root);
  const card = 'glass rounded-2xl';
  parts.canvas = h('div', { class: 'absolute inset-0' });
  parts.verdict = h('div', { class: 'absolute left-4 top-4 z-10' });
  parts.kos = h('div', { class: 'absolute right-4 top-4 z-10 flex max-w-[55%] flex-wrap items-center justify-end gap-1.5' });
  parts.attr = h('div', { class: 'absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 flex-wrap justify-center gap-1.5' });
  parts.legend = h('div', { class: 'flex flex-wrap items-center gap-x-4 gap-y-1 px-1 pt-2 text-[11px] text-slate-400' });
  parts.hint = h('div', { class: 'absolute bottom-4 right-4 z-10 hidden items-center gap-1.5 text-[11px] text-cyan-300/80 xl:flex' });
  const stage = h('div', { class: `${card} relative aspect-[1000/660] w-full overflow-hidden` }, parts.canvas, parts.verdict, parts.kos, parts.attr, parts.hint);
  parts.outcome = h('div', { class: `${card} p-4` }); parts.why = h('div', { class: `${card} p-4` });
  parts.sel = h('div', { class: `${card} p-4` }); parts.hintCard = h('div', { class: `${card} p-4` });
  clear(root).append(h('div', { class: 'grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]' }, h('div', {}, stage, parts.legend), h('div', { class: 'flex flex-col gap-4' }, parts.outcome, parts.why, parts.sel, parts.hintCard)));
  graph = new NetworkGraph(parts.canvas, store.meta.graph, { onToggle: toggleGene });
  legend();
}

function dot(color, extra = '') { return h('span', { class: `inline-block h-2.5 w-2.5 rounded-full ${extra}`, style: { background: color } }); }
function legend() {
  const row = (d, txt) => h('div', { class: 'flex items-center gap-1.5' }, d, txt);
  clear(parts.legend).append(row(dot('#0891b2', 'ring-1 ring-cyan-200'), t('ex.leg.on')), row(dot('#111a2e', 'ring-1 ring-slate-500'), t('ex.leg.off')),
    row(dot('#b45309', 'ring-1 ring-amber-300'), t('ex.leg.osc')), row(dot('#2a0f1a', 'ring-1 ring-rose-400'), t('ex.leg.ko')),
    row(h('span', { class: 'inline-block h-0.5 w-4 bg-emerald-400' }), t('ex.leg.act')), row(h('span', { class: 'inline-block h-0.5 w-4 bg-rose-400' }), t('ex.leg.inh')));
  clear(parts.hint).append(h('span', { class: 'relative flex h-2 w-2' }, h('span', { class: 'absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75' }), h('span', { class: 'relative inline-flex h-2 w-2 rounded-full bg-cyan-400' })), t('ex.hint'));
}

function attractorOf() { return result && result.attractors.length ? result.attractors[Math.min(pick, result.attractors.length - 1)] : null; }

function paint() {
  const sc = current();
  // verdict HUD
  const v = loading || !result ? null : result.verdict;
  const tone = v === 'FORCED' ? 'text-emerald-300 drop-shadow-[0_0_18px_rgba(52,211,153,.7)]' : v === 'SURVIVES' ? 'text-rose-300 drop-shadow-[0_0_18px_rgba(251,113,133,.55)]' : 'text-amber-300';
  clear(parts.verdict).append(h('div', { class: 'rounded-xl border border-white/10 bg-ink-950/70 px-4 py-2.5 backdrop-blur' },
    h('div', { class: 'text-[10px] uppercase tracking-[.2em] text-slate-500' }, t('ex.verdict')),
    loading || !result ? h('div', { class: 'mt-0.5 animate-pulse text-lg font-semibold text-slate-400' }, t('ex.solving'))
      : h('div', { class: `mt-0.5 text-xl font-bold tracking-wide ${tone}` }, v === 'FORCED' ? t('ex.forced') : v === 'SURVIVES' ? t('ex.survives') : t('ex.unknown')),
    result && !loading ? h('div', { class: 'mt-0.5 text-[11px] text-slate-500' }, `${t('ex.exact')} · ${result.attractors.length} ${t('ex.attr').toLowerCase()} · ${Math.round(result.elapsed_ms)} ms`) : null));
  // knockout chips
  clear(parts.kos).append(h('span', { class: 'text-[10px] uppercase tracking-[.2em] text-slate-500' }, t('ex.kos')),
    ...(ko.length ? ko.map(g => h('button', { onclick: () => toggleGene({ id: g, kind: 'gene' }), class: 'group flex items-center gap-1 rounded-lg bg-rose-500/15 px-2 py-1 font-mono text-xs text-rose-200 ring-1 ring-inset ring-rose-400/40 transition hover:bg-rose-500/30' }, g, h('span', { class: 'text-rose-300/70 group-hover:text-white' }, '✕')))
      : [h('span', { class: 'text-xs text-slate-500' }, t('ex.none'))]),
    ko.length ? h('button', { class: 'ml-1 text-[11px] text-cyan-300 hover:underline', onclick: () => { ko = []; run(); } }, t('ex.clear')) : null);
  // attractor selector
  const at = result ? result.attractors : [];
  clear(parts.attr).append(...(at.length > 1 || (at.length === 1 && at[0].kind === 'cyclic') ? at.map((a, i) => {
    const apop = a.values.Apoptosis_high === 1;
    return h('button', { onclick: () => { pick = i; paint(); }, class: `rounded-lg px-2.5 py-1 text-[11px] ring-1 ring-inset backdrop-blur transition ${i === pick ? 'bg-white/15 text-white ring-white/40' : 'bg-ink-950/60 text-slate-400 ring-white/10 hover:text-white'}` },
      `${apop ? '✓' : '✗'} ${a.kind === 'fixed' ? t('ex.stable') : `${t('ex.osc')} · ${fmt(a.n_states)} ${t('ex.states')}`}`);
  }) : []));
  // graph state
  const a = attractorOf();
  const values = a ? a.values : (result && result.counterexample && result.counterexample.values) || null;
  const hot = {};
  if (result && result.verdict === 'SURVIVES' && result.counterexample) result.counterexample.active_genes.forEach(g => { hot[g] = 'rose'; });
  graph.setState({ values, kos: ko, fixed: sc.fixed, hot });
  panels(a);
}

function gauge(label, val, color) {
  const osc = val === null || val === undefined;
  const bar = osc ? 'bg-[repeating-linear-gradient(45deg,#f59e0b_0_6px,#78350f_6px_12px)] animate-pulse w-full' : val === 1 ? `${color} w-full shadow-[0_0_14px_currentColor]` : 'w-0';
  return h('div', {}, h('div', { class: 'mb-1 flex justify-between text-xs' }, h('span', { class: 'text-slate-300' }, label), h('span', { class: `font-mono ${osc ? 'text-amber-300' : val === 1 ? 'text-white' : 'text-slate-500'}` }, osc ? t('ex.vosc') : val === 1 ? t('ex.v1') : t('ex.v0'))),
    h('div', { class: 'h-2.5 overflow-hidden rounded-full bg-white/[.06]' }, h('div', { class: `h-full rounded-full transition-all duration-700 ${bar}` })));
}

function panels(a) {
  const r = result;
  // outcome
  clear(parts.outcome).append(h('div', { class: 'mb-3 text-sm font-semibold text-white' }, t('ex.outcome')),
    a ? h('div', { class: 'space-y-3' }, gauge(t('ex.apop'), a.values.Apoptosis_high, 'bg-gradient-to-r from-emerald-500 to-teal-300 text-emerald-400'),
      gauge(t('ex.prolif'), a.values.Proliferation, 'bg-gradient-to-r from-violet-500 to-fuchsia-400 text-violet-400'),
      gauge(t('ex.arrest'), a.values.Growth_arrest, 'bg-gradient-to-r from-amber-500 to-yellow-300 text-amber-400'),
      h('div', { class: 'pt-1 text-[11px] text-slate-500' }, a.kind === 'fixed' ? t('ex.stable') : `${t('ex.osc')} · ${fmt(a.n_states)} ${t('ex.states')}`))
      : h('div', { class: 'text-xs text-slate-500' }, loading ? t('ex.solving') : t('ex.no.attr')));
  // why
  const why = clear(parts.why);
  if (r && !loading && r.verdict === 'SURVIVES' && r.counterexample) {
    const ce = r.counterexample;
    why.append(h('div', { class: 'mb-1 text-sm font-semibold text-white' }, t('ex.why.survive')),
      h('div', { class: 'mb-3 text-[11px] text-slate-500' }, t('ex.alive.help')),
      h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-rose-300/80' }, t('ex.alive')),
      h('div', { class: 'mb-3 flex flex-wrap gap-1.5' }, ...ce.active_genes.map(g => h('button', { onclick: () => toggleGene({ id: g, kind: 'gene' }), class: 'rounded-md bg-rose-400/10 px-1.5 py-0.5 font-mono text-[11px] text-rose-200 ring-1 ring-inset ring-rose-400/30 transition hover:bg-rose-400/25' }, '+ ' + g))),
      h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-slate-500' }, t('ex.dead')),
      h('div', { class: 'mb-3 flex flex-wrap gap-1.5' }, ...ce.inactive_genes.map(g => h('span', { class: 'rounded-md px-1.5 py-0.5 font-mono text-[11px] text-slate-500 line-through ring-1 ring-inset ring-white/10' }, g))),
      ce.why_goal_fails ? h('details', { class: 'rounded-lg bg-black/30 p-2' }, h('summary', { class: 'text-xs text-cyan-300' }, t('ex.deriv')),
        h('pre', { class: 'scroll-thin mt-2 max-h-60 overflow-auto font-mono text-[10.5px] leading-snug text-slate-400' }, ce.why_goal_fails)) : null);
  } else if (r && !loading && r.verdict === 'FORCED') {
    const steps = r.steps, shown = showAll ? steps : steps.slice(0, 7);
    why.append(h('div', { class: 'mb-1 text-sm font-semibold text-white' }, t('ex.why.forced')), h('div', { class: 'mb-3 text-[11px] text-slate-500' }, t('ex.proof.help')),
      h('ol', { class: 'scroll-thin max-h-[22rem] space-y-1.5 overflow-auto pr-1' }, ...shown.map((st, i) => h('li', { class: 'rounded-lg bg-white/[.03] p-2 text-[11px] ring-1 ring-inset ring-white/5' },
        h('div', { class: 'flex flex-wrap items-center gap-1' }, h('span', { class: 'mr-1 text-slate-600' }, i + 1),
          ...st.premises.map(([n, v, o]) => chip(`${n}=${v}`, o === 'knockout' ? 'red' : o === 'scenario' ? 'violet' : 'slate')),
          h('span', { class: 'px-0.5 text-slate-500' }, '⇒'), chip(`${st.node}=${st.value}`, 'green'), st.entailed ? h('span', { class: 'ml-auto text-emerald-400' }, '✓') : h('span', { class: 'ml-auto text-rose-400' }, '✗'))))),
      steps.length > 7 && !showAll ? h('button', { class: 'mt-2 text-xs text-cyan-300 hover:underline', onclick: () => { showAll = true; panels(a); } }, t('ex.more', { n: steps.length })) : null);
  } else why.append(h('div', { class: 'text-xs text-slate-500' }, loading ? t('ex.solving') : ''));
  // selectivity
  const sel = clear(parts.sel);
  if (r && ko.length && !loading) {
    sel.append(h('div', { class: 'mb-0.5 text-sm font-semibold text-white' }, t('ex.sel')), h('div', { class: 'mb-2 text-[11px] text-slate-500' }, t('ex.sel.help')),
      h('div', { class: `rounded-lg p-2.5 text-xs ring-1 ring-inset ${r.selective ? 'bg-emerald-400/10 text-emerald-200 ring-emerald-400/30' : 'bg-rose-400/10 text-rose-200 ring-rose-400/30'}` }, r.selective ? '✓ ' + t('ex.sel.ok') : '✗ ' + t('ex.sel.bad')));
    parts.sel.classList.remove('hidden');
  } else parts.sel.classList.add('hidden');
  // hint
  const sc = current(), known = store.meta.known_solutions[sc.id];
  const hc = clear(parts.hintCard);
  if (known && !sc.custom) {
    hc.append(h('details', {}, h('summary', { class: 'flex items-center gap-2 text-sm font-semibold text-cyan-200' }, '💡 ' + t('ex.hint2')),
      h('div', { class: 'mt-3 text-[11px] uppercase tracking-wider text-slate-500' }, t('ex.known')),
      h('div', { class: 'mt-2 flex flex-wrap gap-2' }, ...(known.length ? known.map(s => h('button', { onclick: () => { ko = [...s.knockouts]; run(); }, class: 'flex items-center gap-1.5 rounded-lg bg-white/[.05] px-2.5 py-1.5 font-mono text-xs text-slate-100 ring-1 ring-inset ring-white/15 transition hover:bg-cyan-400/15' }, s.knockouts.join(' + '), badge(s.selective ? t('ex.selective') : t('ex.toxic'), s.selective ? 'green' : 'red')))
        : [h('div', { class: 'text-xs text-amber-200' }, t('ex.nosol'))]))));
    parts.hintCard.classList.remove('hidden');
  } else parts.hintCard.classList.add('hidden');
}
