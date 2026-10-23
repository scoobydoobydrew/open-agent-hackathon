// Agent: the LLM + solver loop as a timeline. Live (needs an API key) or replayed from a recording.
import { NetworkGraph } from './graph.js';
import { getReplay, stream, verify } from './api.js';
import { addStrings, onLang, t } from './i18n.js';
import { badge, chip, clear, fmt, h, verdictTone } from './ui.js';
import { SHORT, current, onScenario, store } from './store.js';

addStrings({
  en: {
    'ag.title': 'The agent at work', 'ag.sub': 'The LLM proposes, the solver checks every proposal exactly, counterexamples go back to the LLM and into the search.',
    'ag.replay': 'Replay recorded run', 'ag.live': 'Run live', 'ag.skip': 'Skip animation', 'ag.stop': 'Stop', 'ag.noreplay': 'No recording for this scenario yet',
    'ag.nokey': 'Needs NVIDIA_API_KEY', 'ag.custom': 'Live runs use the preset scenarios', 'ag.empty.t': 'See the whole loop', 'ag.empty.p': 'Replay a recorded run (works offline) or run it live against Nemotron. Every verdict comes from the exact solver.',
    'ag.scenario': 'Scenario', 'ag.baseline': 'Without any knockout', 'ag.cands': 'candidate genes', 'ag.round': 'Round {n}', 'ag.thinking': 'The LLM is proposing knockouts…',
    'ag.prop': 'Proposal', 'ag.rationale': 'LLM rationale', 'ag.via.solver': 'solver', 'ag.via.mem': 'refuted from memory · no solver call',
    'ag.alive': 'Kept alive by', 'ag.queued': 'These genes go to the search queue and back into the next prompt.', 'ag.survive': 'SURVIVES', 'ag.forced': 'FORCED',
    'ag.invalid': 'INVALID', 'ag.dup': 'DUPLICATE', 'ag.search': 'Counterexample-guided search', 'ag.search.n': '{n} sets tried', 'ag.search.c': '{n} solver calls',
    'ag.search.q': '{n} in queue', 'ag.search.found': 'working', 'ag.shrunk': 'Shrunk {a} to {b}: a smaller subset already works', 'ag.sol': 'Verified solution', 'ag.by': 'found by',
    'ag.by.llm': 'the LLM', 'ag.by.cegar': 'the search', 'ag.sel': 'selective', 'ag.toxic': 'not selective', 'ag.toxic.in': 'also kills the resting normal cell',
    'ag.steps': 'Why it works: proven steps', 'ag.check': '{ok}/{n} steps clean', 'ag.deriv': 'Full solver derivation', 'ag.show': 'Show on network', 'ag.llmerr': 'LLM unavailable this round; the search continued on its own',
    'ag.done': 'Run finished', 'ag.rounds': 'rounds', 'ag.solver': 'solver calls', 'ag.llmcalls': 'LLM calls', 'ag.tokens': 'tokens', 'ag.secs': 'seconds', 'ag.refut': 'memory refutations',
    'ag.proved': 'No solution exists', 'ag.proved.p': 'The complete search ran dry: no knockout set within the size limit forces apoptosis. A proof, not a guess.',
    'ag.net': 'Surviving state of the selected proposal', 'ag.net.p': 'Click any proposal or solution to see its state on the network.', 'ag.live.err': 'Live run failed',
    'ag.stats': 'Run so far', 'ag.props': 'proposals', 'ag.wrong': 'refuted', 'ag.solutions': 'solutions', 'ag.ev': 'drug evidence', 'ag.start': 'Start',
  },
  el: {
    'ag.title': 'Ο agent σε δράση', 'ag.sub': 'Το LLM προτείνει, ο solver ελέγχει κάθε πρόταση ακριβώς, και τα counterexamples γυρίζουν στο LLM και στην αναζήτηση.',
    'ag.replay': 'Αναπαραγωγή καταγεγραμμένου run', 'ag.live': 'Ζωντανή εκτέλεση', 'ag.skip': 'Παράλειψη animation', 'ag.stop': 'Στοπ', 'ag.noreplay': 'Δεν υπάρχει ακόμα καταγραφή για αυτό το σενάριο',
    'ag.nokey': 'Χρειάζεται NVIDIA_API_KEY', 'ag.custom': 'Οι ζωντανές εκτελέσεις χρησιμοποιούν τα έτοιμα σενάρια', 'ag.empty.t': 'Δες ολόκληρο τον βρόχο', 'ag.empty.p': 'Αναπαρήγαγε ένα καταγεγραμμένο run (δουλεύει offline) ή τρέξ’ το ζωντανά με το Nemotron. Κάθε ετυμηγορία προέρχεται από τον ακριβή solver.',
    'ag.scenario': 'Σενάριο', 'ag.baseline': 'Χωρίς κανένα knockout', 'ag.cands': 'υποψήφια γονίδια', 'ag.round': 'Γύρος {n}', 'ag.thinking': 'Το LLM προτείνει knockouts…',
    'ag.prop': 'Πρόταση', 'ag.rationale': 'Αιτιολόγηση LLM', 'ag.via.solver': 'solver', 'ag.via.mem': 'απορρίφθηκε από μνήμη · χωρίς κλήση solver',
    'ag.alive': 'Το κρατούν ζωντανό', 'ag.queued': 'Αυτά τα γονίδια μπαίνουν στην ουρά αναζήτησης και στο επόμενο prompt.', 'ag.survive': 'ΕΠΙΒΙΩΝΕΙ', 'ag.forced': 'ΕΠΙΒΑΛΛΕΤΑΙ',
    'ag.invalid': 'ΜΗ ΕΓΚΥΡΗ', 'ag.dup': 'ΕΠΑΝΑΛΗΨΗ', 'ag.search': 'Αναζήτηση καθοδηγούμενη από counterexamples', 'ag.search.n': '{n} σύνολα δοκιμάστηκαν', 'ag.search.c': '{n} κλήσεις solver',
    'ag.search.q': '{n} στην ουρά', 'ag.search.found': 'δουλεύει', 'ag.shrunk': 'Μίκρυνε από {a} σε {b}: μικρότερο υποσύνολο ήδη δουλεύει', 'ag.sol': 'Επαληθευμένη λύση', 'ag.by': 'βρέθηκε από',
    'ag.by.llm': 'το LLM', 'ag.by.cegar': 'την αναζήτηση', 'ag.sel': 'εκλεκτική', 'ag.toxic': 'μη εκλεκτική', 'ag.toxic.in': 'σκοτώνει και το ήρεμο φυσιολογικό κύτταρο',
    'ag.steps': 'Γιατί δουλεύει: αποδεδειγμένα βήματα', 'ag.check': '{ok}/{n} βήματα καθαρά', 'ag.deriv': 'Πλήρης παραγωγή του solver', 'ag.show': 'Δες στο δίκτυο', 'ag.llmerr': 'Το LLM δεν ήταν διαθέσιμο σε αυτόν τον γύρο· η αναζήτηση συνέχισε μόνη της',
    'ag.done': 'Το run ολοκληρώθηκε', 'ag.rounds': 'γύροι', 'ag.solver': 'κλήσεις solver', 'ag.llmcalls': 'κλήσεις LLM', 'ag.tokens': 'tokens', 'ag.secs': 'δευτερόλεπτα', 'ag.refut': 'απορρίψεις από μνήμη',
    'ag.proved': 'Δεν υπάρχει λύση', 'ag.proved.p': 'Η πλήρης αναζήτηση άδειασε: κανένα σύνολο knockout εντός ορίου μεγέθους δεν επιβάλλει απόπτωση. Απόδειξη, όχι εικασία.',
    'ag.net': 'Κατάσταση επιβίωσης της επιλεγμένης πρότασης', 'ag.net.p': 'Κάνε κλικ σε πρόταση ή λύση για να δεις την κατάστασή της στο δίκτυο.', 'ag.live.err': 'Η ζωντανή εκτέλεση απέτυχε',
    'ag.stats': 'Το run μέχρι τώρα', 'ag.props': 'προτάσεις', 'ag.wrong': 'απορρίφθηκαν', 'ag.solutions': 'λύσεις', 'ag.ev': 'τεκμηρίωση φαρμάκου', 'ag.start': 'Αρχή',
  },
});

let root, ui = {}, graph, run = null, mode = 'replay';
const card = 'glass rounded-2xl';

export function init(container) {
  root = container; build();
  onScenario(() => { stopRun(); run = null; build(); });
  onLang(() => { build(); });
}
export function onShow() { /* nothing to refresh */ }

const hasReplay = () => store.meta.replays.includes(current().id) && !current().custom;
const canLive = () => store.meta.llm.available && !current().custom;

function build() {
  clear(root);
  const sc = current();
  ui.tl = h('div', { class: 'scroll-thin relative h-[640px] space-y-3 overflow-y-auto pr-1' });
  ui.canvas = h('div', { class: 'relative aspect-[1000/660] w-full overflow-hidden rounded-xl bg-black/20' });
  ui.stats = h('div', {}); ui.final = h('div', {});
  if (run && run.finalEl) ui.final.append(run.finalEl);
  ui.caption = h('div', { class: 'mt-2 text-[11px] text-slate-500' }, t('ag.net.p'));
  const modeBtn = (id, label, ok, why) => h('button', {
    class: `rounded-lg px-3 py-1.5 text-xs font-medium transition ${mode === id ? 'bg-white/15 text-white ring-1 ring-white/25' : 'text-slate-400 hover:text-white'} ${ok ? '' : 'opacity-40'}`,
    title: ok ? '' : why, onclick: () => { if (ok) { mode = id; build(); } },
  }, label);
  if (mode === 'replay' && !hasReplay() && canLive()) mode = 'live';
  const running = run && run.running;
  const go = running
    ? h('button', { class: 'rounded-lg bg-rose-500/80 px-4 py-1.5 text-sm font-semibold text-white hover:bg-rose-400', onclick: stopRun }, '■ ' + t('ag.stop'))
    : h('button', { class: `rounded-lg bg-gradient-to-r from-cyan-400 to-sky-500 px-4 py-1.5 text-sm font-semibold text-ink-950 shadow-[0_0_24px_rgba(34,211,238,.35)] transition hover:brightness-110 ${(mode === 'replay' ? hasReplay() : canLive()) ? '' : 'pointer-events-none opacity-40'}`, onclick: start }, '▶ ' + (mode === 'replay' ? t('ag.replay') : t('ag.live')));
  const hint = mode === 'replay' ? (!hasReplay() ? t('ag.noreplay') : '') : (sc.custom ? t('ag.custom') : !store.meta.llm.available ? t('ag.nokey') : '');
  const head = h('div', { class: 'mb-3 flex flex-wrap items-center gap-3' }, h('div', {}, h('div', { class: 'text-base font-semibold text-white' }, t('ag.title')), h('div', { class: 'max-w-2xl text-xs text-slate-500' }, t('ag.sub'))),
    h('div', { class: 'ml-auto flex flex-wrap items-center gap-2' }, h('div', { class: 'flex rounded-xl bg-white/[.04] p-0.5 ring-1 ring-inset ring-white/10' }, modeBtn('replay', t('ag.replay'), hasReplay(), t('ag.noreplay')), modeBtn('live', t('ag.live'), canLive(), sc.custom ? t('ag.custom') : t('ag.nokey'))),
      running ? h('button', { class: 'text-xs text-slate-400 hover:text-white', onclick: () => { run.skip = true; } }, t('ag.skip')) : null, go));
  const left = h('div', { class: `${card} p-4` }, head, hint ? h('div', { class: 'mb-2 text-xs text-amber-300/80' }, hint) : null, ui.tl);
  const right = h('div', { class: 'flex flex-col gap-4 xl:sticky xl:top-20 xl:self-start' }, h('div', { class: `${card} p-4` }, h('div', { class: 'mb-2 text-sm font-semibold text-white' }, t('ag.net')), ui.canvas, ui.caption), h('div', { class: `${card} p-4` }, ui.stats), ui.final);
  root.append(h('div', { class: 'grid gap-5 xl:grid-cols-[minmax(0,1fr)_480px]' }, left, right));
  graph = new NetworkGraph(ui.canvas, store.meta.graph, {});
  graph.setState({ fixed: sc.fixed });
  if (run && run.dom) { for (const el of run.dom) ui.tl.append(el); } else { empty(); showOnGraph([], true); }
  paintStats();
}

function empty() {
  ui.tl.append(h('div', { class: 'grid h-full place-items-center text-center' }, h('div', { class: 'max-w-sm' },
    h('div', { class: 'mx-auto mb-4 grid h-14 w-14 animate-floaty place-items-center rounded-2xl bg-gradient-to-br from-cyan-400/30 to-fuchsia-400/30 text-2xl ring-1 ring-white/15' }, '🤖'),
    h('div', { class: 'mb-1 text-base font-semibold text-white' }, t('ag.empty.t')), h('div', { class: 'text-xs leading-relaxed text-slate-400' }, t('ag.empty.p')))));
}

// ---------- playback ------------------------------------------------------------------------------
function fresh() { return { queue: [], running: true, skip: false, timer: null, stop: null, dom: [], proposals: 0, wrong: 0, solver: 0, llm: 0, sols: 0, round: 0, search: null, skeleton: null, sel: null, ended: false }; }

async function start() {
  stopRun(); run = fresh(); clear(ui.tl); clear(ui.final); build();
  const sc = current();
  if (mode === 'replay') {
    const rec = await getReplay(sc.id);
    run.queue.push(...rec.events); run.ended = true; run.source = 'replay';
  } else {
    run.source = 'live';
    run.stop = stream('/api/agent', { scenario: sc.id, rounds: 5 }, ev => run.queue.push(ev), () => { run.ended = true; });
  }
  pump();
}
function stopRun() { if (run) { run.running = false; clearTimeout(run.timer); run.stop && run.stop(); } }

function delayOf(ev) {
  if (run.skip) return 0;
  return { start: 500, round: 450, llm_reply: 900, proposal: 800, solution: 1100, shrunk: 500, round_end: 200, llm_error: 600 }[ev.type] ?? (ev.type === 'search_visit' ? 0 : 60);
}
function pump() {
  if (!run || !run.running) return;
  const ev = run.queue.shift();
  if (!ev) { if (run.ended) { run.running = false; build(); } else run.timer = setTimeout(pump, 120); return; }
  // search events arrive in hundreds: batch them so the animation stays smooth
  if (ev.type === 'search_visit') { let k = run.skip ? 400 : 6; handle(ev); while (k-- > 0 && run.queue.length && run.queue[0].type.startsWith('search_')) handle(run.queue.shift()); run.timer = setTimeout(pump, run.skip ? 0 : 35); return; }
  handle(ev); run.timer = setTimeout(pump, delayOf(ev));
}

function add(el, keep = true) {
  const box = ui.tl, near = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
  box.append(el); if (keep) run.dom.push(el);
  if (near) box.scrollTo({ top: box.scrollHeight, behavior: run.skip ? 'auto' : 'smooth' });
}
const pill = (v, tone) => badge(v, tone);

function handle(ev) {
  switch (ev.type) {
    case 'start': return onStart(ev);
    case 'round': run.round = ev.n; run.search = null; return onRound(ev);
    case 'llm_reply': run.llm++; if (run.skeleton) { run.skeleton.remove(); run.dom = run.dom.filter(x => x !== run.skeleton); run.skeleton = null; } return paintStats();
    case 'llm_error': return add(h('div', { class: 'animate-fadeUp rounded-xl border border-amber-300/30 bg-amber-400/10 p-3 text-xs text-amber-200' }, '⚠ ' + t('ag.llmerr') + (ev.message ? ` (${ev.message.slice(0, 80)})` : '')));
    case 'proposal': return onProposal(ev);
    case 'search_visit': return onSearch(ev);
    case 'shrunk': return add(h('div', { class: 'animate-fadeUp pl-4 text-xs text-slate-400' }, '↘ ' + t('ag.shrunk', { a: `{${ev.knockouts.join(', ')}}`, b: `{${ev.minimal.join(', ')}}` })));
    case 'solution': return onSolution(ev);
    case 'round_end': run.solver = ev.solver_calls; if (run.search) run.search.finish(); return paintStats();
    case 'done': return onDone(ev);
    default: return;
  }
}

function onStart(ev) {
  run.baselineCe = ev.baseline_counterexample;
  const ph = ev.baseline_counterexample ? ev.baseline_counterexample.phenotype : {};
  add(h('div', { class: 'animate-fadeUp rounded-xl bg-gradient-to-br from-white/[.06] to-transparent p-3 ring-1 ring-inset ring-white/10' },
    h('div', { class: 'flex flex-wrap items-center gap-2' }, h('span', { class: 'text-[11px] uppercase tracking-wider text-slate-500' }, t('ag.start')), h('span', { class: 'font-semibold text-white' }, SHORT[ev.scenario] || ev.scenario),
      badge(ev.data_source.startsWith('zetaris') ? 'Zetaris' : 'local CSV', ev.data_source.startsWith('zetaris') ? 'green' : 'amber'), badge(ev.model.split('/').pop(), 'cyan'), badge(`${ev.candidates.length} ${t('ag.cands')}`, 'slate')),
    h('div', { class: 'mt-1.5 text-xs text-slate-400' }, ev.description + '.'),
    h('div', { class: 'mt-2 flex flex-wrap items-center gap-1.5 text-xs' }, h('span', { class: 'text-slate-500' }, t('ag.baseline') + ':'), badge(ev.baseline === 'FORCED' ? t('ag.forced') : t('ag.survive'), verdictTone(ev.baseline)),
      ...Object.entries(ph).map(([k, v]) => chip(`${k.replace('Apoptosis_high', 'apoptosis').replace('Apoptosis_medium', 'apop.partial').replace('Growth_arrest', 'arrest').replace('Proliferation', 'prolif.')}=${v}`, 'slate')))));
  showOnGraph([], true);
}

function onRound(ev) {
  add(h('div', { class: 'flex items-center gap-3 pt-1' }, h('div', { class: 'h-px flex-1 bg-white/10' }, ''), h('div', { class: 'rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-300' }, t('ag.round', { n: ev.n })), h('div', { class: 'h-px flex-1 bg-white/10' }, '')));
  const sk = h('div', { class: 'animate-fadeUp flex items-center gap-2 rounded-xl border border-dashed border-cyan-300/30 p-3 text-xs text-cyan-200' },
    h('span', { class: 'flex gap-1' }, ...[0, 1, 2].map(i => h('span', { class: 'h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300', style: { animationDelay: `${i * 120}ms` } }))), t('ag.thinking'));
  run.skeleton = sk; add(sk);
}

function genesRow(list, tone = 'cyan', big = false) { return h('div', { class: 'flex flex-wrap items-center gap-1.5' }, ...list.map(g => chip(g, tone, big ? 'text-xs px-2 py-1' : ''))); }

function onProposal(ev) {
  run.proposals++;
  const idx = run.proposals, ce = ev.counterexample, v = ev.verdict;
  if (v === 'SURVIVES') run.wrong++;
  const tone = verdictTone(v), vText = v === 'FORCED' ? t('ag.forced') : v === 'SURVIVES' ? t('ag.survive') : v === 'INVALID' ? t('ag.invalid') : t('ag.dup');
  const el = h('div', { class: `animate-fadeUp cursor-pointer rounded-xl p-3 ring-1 ring-inset transition hover:bg-white/[.06] ${v === 'FORCED' ? 'bg-emerald-400/10 ring-emerald-300/40' : 'bg-white/[.03] ring-white/10'}`, onclick: () => { showOnGraph(ev.knockouts); } },
    h('div', { class: 'flex flex-wrap items-center gap-2' }, h('span', { class: 'font-mono text-[11px] text-slate-500' }, `${t('ag.prop')} #${idx}`), genesRow(ev.knockouts, v === 'FORCED' ? 'green' : 'cyan', true),
      h('span', { class: 'ml-auto flex items-center gap-1.5' }, ev.via === 'memory-replay' ? badge('↺ ' + t('ag.via.mem'), 'amber') : ev.via === 'solver' ? badge(t('ag.via.solver'), 'slate') : null, pill(vText, tone))),
    ev.rationale ? h('div', { class: 'mt-2 border-l-2 border-cyan-300/30 pl-2.5 text-xs italic leading-relaxed text-slate-400' }, '🧠 ' + ev.rationale) : null,
    ev.note && v !== 'SURVIVES' && v !== 'FORCED' ? h('div', { class: 'mt-1.5 text-xs text-amber-200/80' }, ev.note) : null,
    ce && v === 'SURVIVES' ? h('div', { class: 'mt-2.5 rounded-lg bg-black/25 p-2.5' },
      h('div', { class: 'mb-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500' }, t('ag.alive'), ...Object.entries(ce.phenotype || {}).filter(([k]) => ['Apoptosis_high', 'Proliferation', 'Growth_arrest'].includes(k)).map(([k, x]) => chip(`${k === 'Apoptosis_high' ? 'apoptosis' : k === 'Growth_arrest' ? 'arrest' : 'prolif.'}=${x}`, 'slate'))),
      genesRow((ce.active_genes || []).slice(0, 14), 'red'), h('div', { class: 'mt-1.5 text-[10.5px] text-slate-500' }, '→ ' + t('ag.queued'))) : null);
  add(el); run.cards = run.cards || []; run.cards.push(el);
  if (v !== 'INVALID' && v !== 'DUPLICATE') showOnGraph(ev.knockouts);
  paintStats();
}

function onSearch(ev) {
  run.solver = Math.max(run.solver, 0);
  if (!run.search) {
    const bar = h('div', { class: 'h-1.5 w-full overflow-hidden rounded-full bg-white/10' }, h('div', { class: 'h-full w-1/3 animate-shimmer rounded-full bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-cyan-400', style: { backgroundSize: '200% 100%' } }));
    const line = h('div', { class: 'flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-300' }); const found = h('div', { class: 'mt-2 flex flex-wrap gap-1.5' });
    const el = h('div', { class: 'animate-fadeUp rounded-xl bg-violet-400/[.07] p-3 ring-1 ring-inset ring-violet-300/25' }, h('div', { class: 'mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-violet-200' }, '⌖ ' + t('ag.search')), line, h('div', { class: 'mt-2' }, bar), found);
    const s = { el, line, bar, found, tried: 0, calls: 0, frontier: 0, sols: 0,
      finish() { bar.firstChild.classList.remove('animate-shimmer'); bar.firstChild.style.width = '100%'; bar.firstChild.className = 'h-full w-full rounded-full bg-violet-400/60'; } };
    run.search = s; add(el);
  }
  const s = run.search; s.tried++; s.calls = ev.calls; s.frontier = ev.frontier;
  if (ev.solution) { s.found.append(h('span', { class: 'animate-pop rounded-md bg-emerald-400/20 px-2 py-0.5 font-mono text-[11px] text-emerald-200 ring-1 ring-inset ring-emerald-300/40' }, '✓ ' + ev.kos.join(' + '))); }
  clear(s.line).append(h('span', {}, t('ag.search.n', { n: fmt(s.tried) })), h('span', { class: 'text-slate-500' }, '·'), h('span', {}, t('ag.search.c', { n: fmt(s.calls) })), h('span', { class: 'text-slate-500' }, '·'), h('span', {}, t('ag.search.q', { n: fmt(s.frontier) })));
  run.searchCalls = ev.calls;
}

function onSolution(ev) {
  run.sols++;
  const ex = ev.explanation;
  const el = h('div', { class: 'animate-pop rounded-2xl bg-gradient-to-br from-emerald-400/15 via-emerald-400/5 to-transparent p-4 ring-1 ring-inset ring-emerald-300/50 shadow-[0_0_44px_rgba(52,211,153,.18)]' },
    h('div', { class: 'flex flex-wrap items-center gap-2' }, h('span', { class: 'text-[11px] font-bold uppercase tracking-[.18em] text-emerald-300' }, '✓ ' + t('ag.sol') + ` #${run.sols}`), genesRow(ev.knockouts, 'green', true),
      h('span', { class: 'ml-auto flex flex-wrap items-center gap-1.5' }, badge(`${t('ag.by')} ${ev.found_by === 'llm' ? t('ag.by.llm') : t('ag.by.cegar')}`, ev.found_by === 'llm' ? 'cyan' : 'violet'), badge(ev.selective ? '✓ ' + t('ag.sel') : '✗ ' + t('ag.toxic'), ev.selective ? 'green' : 'red'))),
    !ev.selective ? h('div', { class: 'mt-1.5 text-xs text-rose-200/80' }, t('ag.toxic.in')) : null,
    h('div', { class: 'mt-2.5 flex flex-wrap gap-1.5 text-[11px]' }, ...ev.drugs.map(d => h('span', { class: 'rounded-md bg-white/[.05] px-2 py-1 ring-1 ring-inset ring-white/10' }, h('span', { class: 'font-mono text-slate-200' }, d.gene), h('span', { class: 'text-slate-500' }, ` · ${d.evidence_level || '?'}`), d.example_agents ? h('span', { class: 'text-slate-600' }, ` (${d.example_agents.split(';')[0]})`) : null))),
    ex ? h('div', { class: 'mt-3' }, h('div', { class: 'mb-1.5 flex items-center justify-between text-[11px] uppercase tracking-wider text-slate-500' }, t('ag.steps'), badge(t('ag.check', { ok: ex.steps_ok, n: ex.steps_total }), ex.faithful ? 'green' : 'amber')),
      h('ol', { class: 'space-y-1.5' }, ...ex.steps.map((st, i) => h('li', { class: 'rounded-lg bg-black/25 p-2 text-xs' }, h('div', { class: 'flex gap-2' }, h('span', { class: st.ok ? 'text-emerald-400' : 'text-amber-400' }, st.ok ? '✓' : '⚠'), h('div', {}, h('div', { class: 'text-slate-200' }, st.text),
        h('div', { class: 'mt-1 flex flex-wrap items-center gap-1 text-[10.5px]' }, ...st.premises.map(([n, v]) => chip(`${n}=${v}`, 'slate')), h('span', { class: 'text-slate-600' }, '⇒'), chip(`${st.node}=${st.value}`, 'green'),
          st.stray_mentions.length ? h('span', { class: 'ml-1 text-amber-300' }, `⚠ ${st.stray_mentions.join(', ')}`) : null)))))),
      ex.caveats && ex.caveats.length ? h('div', { class: 'mt-2 text-[11px] text-slate-500' }, 'ⓘ ' + ex.caveats.join(' · ')) : null) : null,
    ev.derivation ? h('details', { class: 'mt-3 rounded-lg bg-black/25 p-2' }, h('summary', { class: 'text-xs text-cyan-300' }, t('ag.deriv')), h('pre', { class: 'scroll-thin mt-2 max-h-56 overflow-auto font-mono text-[10.5px] leading-snug text-slate-400' }, ev.derivation)) : null,
    h('button', { class: 'mt-3 text-xs text-cyan-300 hover:underline', onclick: () => showOnGraph(ev.knockouts) }, '⌖ ' + t('ag.show')));
  add(el); showOnGraph(ev.knockouts); paintStats();
}

function onDone(ev) {
  const r = ev.report; run.solver = r.solver_calls; run.llm = r.llm_calls;
  const tile = (label, v) => h('div', { class: 'rounded-xl bg-white/[.04] p-2.5 text-center ring-1 ring-inset ring-white/5' }, h('div', { class: 'num text-lg font-semibold text-white' }, fmt(v)), h('div', { class: 'text-[10px] uppercase tracking-wider text-slate-500' }, label));
  run.finalEl = h('div', { class: `${card} animate-fadeUp p-4` }, h('div', { class: 'mb-2 text-sm font-semibold text-white' }, '🏁 ' + t('ag.done')),
    r.certified_infeasible ? h('div', { class: 'mb-3 rounded-xl bg-violet-400/10 p-3 ring-1 ring-inset ring-violet-300/40' }, h('div', { class: 'text-sm font-bold text-violet-200' }, '∎ ' + t('ag.proved')), h('div', { class: 'mt-1 text-xs text-slate-300' }, t('ag.proved.p'))) : null,
    h('div', { class: 'grid grid-cols-3 gap-2' }, tile(t('ag.rounds'), r.rounds), tile(t('ag.solver'), r.solver_calls), tile(t('ag.llmcalls'), r.llm_calls), tile(t('ag.tokens'), r.tokens), tile(t('ag.secs'), r.seconds), tile(t('ag.refut'), r.memory_refutations + r.cegar_replays)));
  clear(ui.final).append(run.finalEl);
  paintStats();
}

function paintStats() {
  if (!ui.stats) return;
  const r = run || { proposals: 0, wrong: 0, solver: 0, llm: 0, sols: 0 };
  const tile = (label, v, tone) => h('div', { class: 'rounded-xl bg-white/[.04] p-2.5 ring-1 ring-inset ring-white/5' }, h('div', { class: 'text-[10px] uppercase tracking-wider text-slate-500' }, label), h('div', { class: `num text-xl font-semibold ${tone}` }, fmt(v)));
  clear(ui.stats).append(h('div', { class: 'mb-2 text-sm font-semibold text-white' }, t('ag.stats')), h('div', { class: 'grid grid-cols-4 gap-2' },
    tile(t('ag.props'), r.proposals, 'text-white'), tile(t('ag.wrong'), r.wrong, 'text-rose-300'), tile(t('ag.llmcalls'), r.llm, 'text-cyan-300'), tile(t('ag.solutions'), r.sols, 'text-emerald-300')));
}

async function showOnGraph(kos, quiet = false) {
  const sc = current();
  const r = await verify(sc.id, null, kos);
  if (r.error || !graph) return;
  const at = r.attractors.find(a => a.values.Apoptosis_high !== 1) || r.attractors[0];
  const hot = {};
  if (r.verdict === 'SURVIVES' && r.counterexample) r.counterexample.active_genes.forEach(g => { hot[g] = 'rose'; });
  graph.setState({ values: at ? at.values : null, kos, fixed: sc.fixed, hot });
  ui.caption.textContent = `${kos.length ? '{' + kos.join(', ') + '}' : '∅'} → ${r.verdict === 'FORCED' ? t('ag.forced') : t('ag.survive')}`;
  ui.caption.className = `mt-2 text-xs font-semibold ${r.verdict === 'FORCED' ? 'text-emerald-300' : 'text-rose-300'}`;
}
