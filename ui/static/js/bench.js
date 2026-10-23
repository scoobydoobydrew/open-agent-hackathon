// Benchmark: the measured results, drawn from benchmark/results-*.json (no numbers are typed in here).
import { addStrings, onLang, t } from './i18n.js';
import { clear, fmt, h, pct } from './ui.js';
import { SHORT, store } from './store.js';

addStrings({
  en: {
    'b.title': 'What we measured', 'b.sub': 'Scored against exhaustive-solver ground truth: 8 scenarios, 3 repeats per LLM arm, Nemotron 3.5 lightning (thinking off).',
    'b.h1': 'of the LLM’s own proposals were wrong', 'b.h1s': 'asked for knockout sets with no solver', 'b.h2': 'fewer solver calls than brute force', 'b.h2s': 'with no LLM at all, same answers',
    'b.h3': 'calls to prove nothing works', 'b.h3s': 'vs {n} for brute force, in the impossible scenario', 'b.h4': 'of explanation steps stayed inside the proof', 'b.h4s': 'LLM wording checked against the proven steps',
    'b.honest.t': 'Honest reading', 'b.honest.p': 'On this small network the search is carried by the symbolic counterexample-guided algorithm, not by the LLM: with no LLM it already finds every answer and proves impossibility. The LLM alone is wrong most of the time, so every claim must go through the solver. Its role here is the interface, the wording of explanations and cross-run memory.',
    'b.c1': 'Finds a valid minimal knockout set', 'b.c2': 'Solver calls (log scale)', 'b.c3': 'Per scenario: share of all minimal sets recovered', 'b.imp': 'Impossible scenario (no knockout set works)',
    'b.imp.proved': 'proved impossible', 'b.noproof': 'no proof', 'b.imp.hall': 'invented a solution', 'b.na': 'n/a', 'b.calls': 'calls', 'b.scen': 'scenario',
    'arm.brute_force': 'Brute force', 'arm.llm_only': 'LLM only', 'arm.llm_feedback': 'LLM + feedback', 'arm.symbolic_cegar': 'Search, no LLM', 'arm.llm_cegar': 'LLM + search', 'arm.ours_full': 'Full system',
    'b.none': 'No benchmark results found. Run benchmark/run_benchmark.py.',
  },
  el: {
    'b.title': 'Τι μετρήσαμε', 'b.sub': 'Βαθμολόγηση απέναντι σε ground truth εξαντλητικού solver: 8 σενάρια, 3 επαναλήψεις ανά arm με LLM, Nemotron 3.5 lightning (thinking κλειστό).',
    'b.h1': 'των προτάσεων του LLM ήταν λάθος', 'b.h1s': 'όταν ζητήθηκαν knockout sets χωρίς solver', 'b.h2': 'λιγότερες κλήσεις solver από το brute force', 'b.h2s': 'χωρίς καθόλου LLM, ίδιες απαντήσεις',
    'b.h3': 'κλήσεις για να αποδειχθεί ότι τίποτα δεν δουλεύει', 'b.h3s': 'έναντι {n} του brute force, στο αδύνατο σενάριο', 'b.h4': 'των βημάτων εξήγησης έμειναν μέσα στην απόδειξη', 'b.h4s': 'η διατύπωση του LLM ελέγχθηκε με τα αποδεδειγμένα βήματα',
    'b.honest.t': 'Ειλικρινής ανάγνωση', 'b.honest.p': 'Σε αυτό το μικρό δίκτυο την αναζήτηση την κάνει ο συμβολικός αλγόριθμος που καθοδηγείται από counterexamples και όχι το LLM: χωρίς LLM βρίσκει ήδη όλες τις απαντήσεις και αποδεικνύει το αδύνατο. Το LLM μόνο του κάνει λάθος τις περισσότερες φορές, γι’ αυτό κάθε ισχυρισμός περνά από τον solver. Ο ρόλος του εδώ είναι το interface, η διατύπωση των εξηγήσεων και η μνήμη ανάμεσα στα runs.',
    'b.c1': 'Βρίσκει έγκυρο ελάχιστο knockout set', 'b.c2': 'Κλήσεις solver (λογαριθμική κλίμακα)', 'b.c3': 'Ανά σενάριο: ποσοστό των ελάχιστων sets που βρέθηκαν', 'b.imp': 'Αδύνατο σενάριο (κανένα knockout set δεν δουλεύει)',
    'b.imp.proved': 'απέδειξε ότι είναι αδύνατο', 'b.noproof': 'χωρίς απόδειξη', 'b.imp.hall': 'επινόησε λύση', 'b.na': 'n/a', 'b.calls': 'κλήσεις', 'b.scen': 'σενάριο',
    'arm.brute_force': 'Brute force', 'arm.llm_only': 'Μόνο LLM', 'arm.llm_feedback': 'LLM + feedback', 'arm.symbolic_cegar': 'Αναζήτηση, χωρίς LLM', 'arm.llm_cegar': 'LLM + αναζήτηση', 'arm.ours_full': 'Πλήρες σύστημα',
    'b.none': 'Δεν βρέθηκαν αποτελέσματα benchmark. Τρέξε το benchmark/run_benchmark.py.',
  },
});

const ARMS = ['brute_force', 'llm_only', 'llm_feedback', 'symbolic_cegar', 'llm_cegar', 'ours_full'];
const COLOR = { brute_force: '#94a3b8', llm_only: '#fb7185', llm_feedback: '#fb923c', symbolic_cegar: '#34d399', llm_cegar: '#22d3ee', ours_full: '#a78bfa' };
let root;

export function init(container) { root = container; render(); onLang(render); }
export function onShow() { render(); }

function hero(value, label, sub, tone) {
  return h('div', { class: 'glass relative overflow-hidden rounded-2xl p-5' }, h('div', { class: `absolute -right-6 -top-6 h-28 w-28 rounded-full blur-3xl ${tone}` }),
    h('div', { class: 'relative' }, h('div', { class: 'num bg-gradient-to-br from-white to-slate-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent' }, value),
      h('div', { class: 'mt-1.5 text-sm font-medium text-slate-200' }, label), h('div', { class: 'mt-0.5 text-xs text-slate-500' }, sub)));
}

function bars(title, items, fmtv, maxv, log = false) {
  const scale = v => (v == null ? 0 : log ? Math.log10(Math.max(1, v) + 1) / Math.log10(maxv + 1) : v / maxv);
  return h('div', { class: 'glass rounded-2xl p-5' }, h('div', { class: 'mb-4 text-sm font-semibold text-white' }, title),
    h('div', { class: 'space-y-3' }, ...items.map(([arm, v]) => h('div', {}, h('div', { class: 'mb-1 flex justify-between text-xs' }, h('span', { class: 'text-slate-300' }, t('arm.' + arm)), h('span', { class: 'num font-mono text-slate-400' }, v == null ? t('b.na') : fmtv(v))),
      h('div', { class: 'h-3 overflow-hidden rounded-full bg-white/[.06]' }, h('div', { class: 'h-full rounded-full transition-all duration-1000', style: { width: `${Math.max(v == null ? 0 : 1.5, scale(v) * 100)}%`, background: `linear-gradient(90deg, ${COLOR[arm]}66, ${COLOR[arm]})`, boxShadow: `0 0 14px ${COLOR[arm]}55` } }))))));
}

function render() {
  clear(root);
  const b = store.meta.benchmark;
  if (!b) { root.append(h('div', { class: 'glass rounded-2xl p-8 text-center text-slate-400' }, t('b.none'))); return; }
  const A = b.arms, P = b.per_scenario;
  const ratio = A.brute_force.solver_calls / A.symbolic_cegar.solver_calls;
  const bf = P.brute_force.growthinh_only.solver_calls, sym = P.symbolic_cegar.growthinh_only.solver_calls;
  const scen = Object.keys(P.brute_force).filter(s => P.brute_force[s].recall != null);
  const heat = h('div', { class: 'glass overflow-x-auto rounded-2xl p-5' }, h('div', { class: 'mb-4 text-sm font-semibold text-white' }, t('b.c3')),
    h('table', { class: 'w-full min-w-[640px] text-xs' }, h('thead', {}, h('tr', {}, h('th', { class: 'pb-2 text-left font-normal text-slate-500' }, t('b.scen')), ...ARMS.map(a => h('th', { class: 'pb-2 text-center font-normal text-slate-400' }, t('arm.' + a))))),
      h('tbody', {}, ...scen.map(sid => h('tr', { class: 'border-t border-white/5' }, h('td', { class: 'py-2 pr-3 text-slate-300' }, SHORT[sid] || sid),
        ...ARMS.map(a => { const c = P[a] && P[a][sid]; const r = c ? c.recall : null; const hue = r == null ? 0 : Math.round(r * 130);
          return h('td', { class: 'p-1 text-center' }, c ? h('div', { class: 'rounded-lg py-1.5 font-semibold', style: { background: `hsla(${hue},70%,45%,${.18 + (r || 0) * .35})`, color: `hsl(${hue},80%,78%)` } }, pct(r), h('div', { class: 'text-[10px] font-normal text-slate-400' }, `${fmt(Math.round(c.solver_calls))} ${t('b.calls')}`)) : '–'); }))))));
  const imp = h('div', { class: 'glass rounded-2xl p-5' }, h('div', { class: 'mb-4 text-sm font-semibold text-white' }, t('b.imp')),
    h('div', { class: 'grid gap-2 sm:grid-cols-2 xl:grid-cols-3' }, ...ARMS.map(a => { const c = P[a] && P[a].growthinh_only; const hall = c && a === 'llm_only' ? A.llm_only.infeasible_hallucinated : null; const proved = c ? (A[a].infeasible_proved) : null;
      const good = proved === 1, bad = hall === 1 || (a === 'llm_feedback');
      return h('div', { class: `rounded-xl p-3 ring-1 ring-inset ${good ? 'bg-violet-400/10 ring-violet-300/40' : 'bg-rose-400/10 ring-rose-300/30'}` }, h('div', { class: 'text-xs text-slate-300' }, t('arm.' + a)),
        h('div', { class: `mt-1 text-sm font-semibold ${good ? 'text-violet-200' : 'text-rose-200'}` }, good ? '∎ ' + t('b.imp.proved') : (a === 'llm_only' ? '✗ ' + t('b.imp.hall') : '✗ ' + t('b.noproof'))), h('div', { class: 'text-[11px] text-slate-500' }, c ? `${fmt(Math.round(c.solver_calls))} ${t('b.calls')}` : ''));
    })));
  root.append(h('div', { class: 'mb-5' }, h('div', { class: 'text-2xl font-semibold text-white' }, t('b.title')), h('div', { class: 'text-sm text-slate-400' }, t('b.sub'))),
    h('div', { class: 'grid gap-4 sm:grid-cols-2 xl:grid-cols-4' },
      hero(pct(A.llm_only.wrong_claim_rate), t('b.h1'), t('b.h1s'), 'bg-rose-500/40'), hero(`${Math.round(ratio)}×`, t('b.h2'), t('b.h2s'), 'bg-emerald-500/40'),
      hero(fmt(Math.round(sym)), t('b.h3'), t('b.h3s', { n: fmt(bf) }), 'bg-violet-500/40'), hero(pct(A.ours_full.explanation_steps_verified), t('b.h4'), t('b.h4s'), 'bg-cyan-500/40')),
    h('div', { class: 'mt-4 rounded-2xl border border-amber-300/25 bg-amber-400/[.07] p-4' }, h('div', { class: 'mb-1 text-sm font-semibold text-amber-200' }, '⚖ ' + t('b.honest.t')), h('div', { class: 'text-xs leading-relaxed text-amber-100/80' }, t('b.honest.p'))),
    h('div', { class: 'mt-4 grid gap-4 lg:grid-cols-2' }, bars(t('b.c1'), ARMS.map(a => [a, A[a].solved_rate]), pct, 1), bars(t('b.c2'), ARMS.map(a => [a, A[a].solver_calls || null]), v => fmt(Math.round(v)), Math.max(...ARMS.map(a => A[a].solver_calls || 0)), true)),
    h('div', { class: 'mt-4' }, heat), h('div', { class: 'mt-4' }, imp));
}
