// How it works: the idea in six plain steps, with live pieces of the real model.
import { addStrings, onLang, t } from './i18n.js';
import { badge, chip, clear, h } from './ui.js';
import { store } from './store.js';

addStrings({
  en: {
    'h.title': 'From radiation to a proof, in six steps', 'h.sub': 'A radiation-surviving tumour cell is a puzzle: which genes should we switch off so the cell commits to apoptosis? Here is how the system answers it, and why you can trust the answer.',
    'h.f1': 'Zetaris', 'h.f1s': 'network, scenarios, drug data (SQL)', 'h.f2': 'LLM', 'h.f2s': 'proposes knockouts', 'h.f3': 'Solver', 'h.f3s': 'exact verdict + counterexample',
    'h.f4': 'Search', 'h.f4s': 'complete, guided by counterexamples', 'h.f5': 'Explain', 'h.f5s': 'checked proof steps', 'h.mem': 'Memory: stored counterexamples refute new ideas without a solver call',
    's1.t': 'A published model of the cell', 's1.p': 'The cell is a network of 35 on/off switches (genes), each with a rule. Four inputs describe the situation: radiation, two growth signals (EGF, FGFR3) and growth inhibitors. This is the Remy et al. 2015 bladder tumorigenesis model.', 's1.rule': 'A real rule from the model:',
    's2.t': 'Long-term fates are attractors', 's2.p': 'Let the switches update in any order. The cell ends in a stable state or in a loop. We compute all of them exactly, including loops that a simple stable-state check would miss.', 's2.a': 'stable state', 's2.b': 'oscillation',
    's3.t': 'A knockout and a verdict', 's3.p': 'Switch some genes off and recompute. The set is FORCED only if apoptosis happens in every long-term state from every starting state. A cell that flickers in and out of apoptosis counts as surviving.', 's3.f': 'apoptosis guaranteed', 's3.s': 'the cell can survive',
    's4.t': 'A counterexample says what to try next', 's4.p': 'When a set fails, the solver returns the surviving state. Only the genes that are active in it can break it. Knocking out a gene that is already off changes nothing.',
    's5.t': 'A search that cannot miss', 's5.p': 'Start from the empty set and extend every failing set only with the genes its surviving state keeps active. Any working set must contain such a gene, so nothing is skipped: the search finds every minimal solution, or proves that none exists.',
    's6.t': 'Explanations you can check', 's6.p': 'The proof is cut into numbered steps: premises, conclusion, rule. Each step is re-checked against the model. The LLM may only choose and reword steps, and any gene it mentions outside them is flagged.', 's6.ex': 'Example step:',
    'h.lim.t': 'Where the LLM fits, and where it does not', 'h.lim.p': 'Alone, the LLM proposes wrong knockout sets most of the time and invents answers for impossible cases. The search itself is symbolic. The LLM provides the natural-language interface, the wording of explanations and lessons across runs. Results are in-silico hypotheses on one published model, not clinical claims.',
    'h.lim.l1': 'One published Boolean model, no dose or time', 'h.lim.l2': 'Ground truth comes from the same model, not from literature', 'h.lim.l3': 'Drug annotations are hand-curated and unverified',
  },
  el: {
    'h.title': 'Από την ακτινοβολία στην απόδειξη, σε έξι βήματα', 'h.sub': 'Ένα καρκινικό κύτταρο που επιβιώνει της ακτινοβολίας είναι ένας γρίφος: ποια γονίδια να απενεργοποιήσουμε ώστε το κύτταρο να οδηγηθεί σε απόπτωση; Να πώς απαντά το σύστημα και γιατί μπορείς να εμπιστευτείς την απάντηση.',
    'h.f1': 'Zetaris', 'h.f1s': 'δίκτυο, σενάρια, φάρμακα (SQL)', 'h.f2': 'LLM', 'h.f2s': 'προτείνει knockouts', 'h.f3': 'Solver', 'h.f3s': 'ακριβής ετυμηγορία + counterexample',
    'h.f4': 'Αναζήτηση', 'h.f4s': 'πλήρης, καθοδηγούμενη από counterexamples', 'h.f5': 'Εξήγηση', 'h.f5s': 'ελεγμένα βήματα απόδειξης', 'h.mem': 'Μνήμη: τα αποθηκευμένα counterexamples απορρίπτουν νέες ιδέες χωρίς κλήση solver',
    's1.t': 'Ένα δημοσιευμένο μοντέλο του κυττάρου', 's1.p': 'Το κύτταρο είναι ένα δίκτυο 35 διακοπτών on/off (γονίδια), καθένας με έναν κανόνα. Τέσσερις είσοδοι περιγράφουν την κατάσταση: ακτινοβολία, δύο σήματα ανάπτυξης (EGF, FGFR3) και αναστολείς ανάπτυξης. Είναι το μοντέλο ογκογένεσης κύστης των Remy et al. 2015.', 's1.rule': 'Ένας πραγματικός κανόνας του μοντέλου:',
    's2.t': 'Οι μακροχρόνιες τύχες είναι attractors', 's2.p': 'Άφησε τους διακόπτες να ενημερώνονται με οποιαδήποτε σειρά. Το κύτταρο καταλήγει σε σταθερή κατάσταση ή σε βρόχο. Τις υπολογίζουμε όλες ακριβώς, μαζί με τους βρόχους που ένας απλός έλεγχος σταθερών καταστάσεων θα έχανε.', 's2.a': 'σταθερή κατάσταση', 's2.b': 'ταλάντωση',
    's3.t': 'Ένα knockout και μια ετυμηγορία', 's3.p': 'Απενεργοποίησε κάποια γονίδια και ξαναϋπολόγισε. Το σύνολο είναι FORCED μόνο αν η απόπτωση συμβαίνει σε κάθε μακροχρόνια κατάσταση από κάθε αρχική κατάσταση. Ένα κύτταρο που αναβοσβήνει μέσα και έξω από την απόπτωση θεωρείται ότι επιβιώνει.', 's3.f': 'εγγυημένη απόπτωση', 's3.s': 'το κύτταρο μπορεί να επιβιώσει',
    's4.t': 'Ένα counterexample λέει τι να δοκιμάσεις μετά', 's4.p': 'Όταν ένα σύνολο αποτυγχάνει, ο solver επιστρέφει την κατάσταση επιβίωσης. Μόνο τα γονίδια που είναι ενεργά σε αυτήν μπορούν να τη σπάσουν. Το knockout ενός ήδη ανενεργού γονιδίου δεν αλλάζει τίποτα.',
    's5.t': 'Μια αναζήτηση που δεν χάνει τίποτα', 's5.p': 'Ξεκίνα από το κενό σύνολο και επέκτεινε κάθε σύνολο που αποτυγχάνει μόνο με τα γονίδια που κρατά ενεργά η κατάσταση επιβίωσής του. Κάθε σύνολο που δουλεύει περιέχει τέτοιο γονίδιο, άρα τίποτα δεν παραλείπεται: βρίσκει κάθε ελάχιστη λύση ή αποδεικνύει ότι δεν υπάρχει.',
    's6.t': 'Εξηγήσεις που μπορείς να ελέγξεις', 's6.p': 'Η απόδειξη κόβεται σε αριθμημένα βήματα: προϋποθέσεις, συμπέρασμα, κανόνας. Κάθε βήμα ξαναελέγχεται με το μοντέλο. Το LLM μπορεί μόνο να επιλέξει και να διατυπώσει βήματα, και κάθε γονίδιο που αναφέρει εκτός αυτών σημαίνεται.', 's6.ex': 'Παράδειγμα βήματος:',
    'h.lim.t': 'Πού χωρά το LLM και πού όχι', 'h.lim.p': 'Μόνο του, το LLM προτείνει στις περισσότερες περιπτώσεις λάθος knockout sets και επινοεί απαντήσεις για αδύνατες περιπτώσεις. Η ίδια η αναζήτηση είναι συμβολική. Το LLM δίνει το interface φυσικής γλώσσας, τη διατύπωση των εξηγήσεων και μαθήματα ανάμεσα στα runs. Τα αποτελέσματα είναι in-silico υποθέσεις σε ένα δημοσιευμένο μοντέλο, όχι κλινικοί ισχυρισμοί.',
    'h.lim.l1': 'Ένα δημοσιευμένο Boolean μοντέλο, χωρίς δόση ή χρόνο', 'h.lim.l2': 'Το ground truth προέρχεται από το ίδιο μοντέλο, όχι από βιβλιογραφία', 'h.lim.l3': 'Οι σημειώσεις φαρμάκων είναι χειροποίητες και ανεπιβεβαίωτες',
  },
});

let root;
export function init(container) { root = container; render(); onLang(render); }
export function onShow() { render(); }

function step(n, title, body, extra, tone) {
  return h('div', { class: 'glass relative overflow-hidden rounded-2xl p-5' }, h('div', { class: `absolute -left-8 -top-8 h-32 w-32 rounded-full blur-3xl ${tone}` }),
    h('div', { class: 'relative flex gap-4' }, h('div', { class: 'grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-white/20 to-white/5 text-lg font-bold text-white ring-1 ring-white/20' }, n),
      h('div', { class: 'min-w-0' }, h('div', { class: 'text-base font-semibold text-white' }, title), h('p', { class: 'mt-1 text-sm leading-relaxed text-slate-400' }, body), extra ? h('div', { class: 'mt-3' }, extra) : null)));
}

function flow() {
  const box = (icon, name, sub, tone) => h('div', { class: `relative rounded-2xl p-3 text-center ring-1 ring-inset ${tone}` }, h('div', { class: 'text-xl' }, icon), h('div', { class: 'text-sm font-semibold text-white' }, name), h('div', { class: 'text-[11px] text-slate-400' }, sub));
  const arrow = () => h('div', { class: 'relative mx-1 hidden h-0.5 w-8 shrink-0 self-center overflow-hidden rounded bg-white/10 lg:block' }, h('div', { class: 'absolute inset-y-0 w-1/2 animate-shimmer bg-gradient-to-r from-transparent via-cyan-300 to-transparent', style: { backgroundSize: '200% 100%' } }));
  return h('div', { class: 'glass rounded-2xl p-5' }, h('div', { class: 'flex flex-wrap items-stretch justify-center gap-2 lg:flex-nowrap' },
    box('🗄️', t('h.f1'), t('h.f1s'), 'bg-emerald-400/10 ring-emerald-300/30'), arrow(), box('🧠', t('h.f2'), t('h.f2s'), 'bg-cyan-400/10 ring-cyan-300/30'), arrow(),
    box('⚖️', t('h.f3'), t('h.f3s'), 'bg-violet-400/10 ring-violet-300/30'), arrow(), box('🌳', t('h.f4'), t('h.f4s'), 'bg-fuchsia-400/10 ring-fuchsia-300/30'), arrow(), box('📜', t('h.f5'), t('h.f5s'), 'bg-amber-400/10 ring-amber-300/30')),
    h('div', { class: 'mt-3 text-center text-xs text-slate-500' }, '↺ ' + t('h.mem')));
}

function render() {
  clear(root);
  const p21 = store.meta.graph.genes.find(g => g.id === 'p21CIP');
  const rule = p21 ? p21.rules.p21CIP : '';
  const orbit = h('div', { class: 'flex items-center gap-8' },
    h('div', { class: 'flex items-center gap-2 text-xs text-slate-400' }, h('span', { class: 'h-4 w-4 rounded-full bg-cyan-400 shadow-[0_0_16px_#22d3ee]' }), t('s2.a')),
    h('div', { class: 'flex items-center gap-2 text-xs text-slate-400' }, h('span', { class: 'relative inline-block h-8 w-8 rounded-full border border-dashed border-amber-300/50' }, h('span', { class: 'absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-400 shadow-[0_0_12px_#fbbf24]', style: { animation: 'spin 2.4s linear infinite', transformOrigin: '50% 16px' } })), t('s2.b')));
  const tree = h('div', { class: 'flex items-center gap-1.5 font-mono text-[11px]' }, chip('∅', 'cyan'), h('span', { class: 'text-slate-600' }, '→'), chip('TP53', 'red'), h('span', { class: 'text-slate-600' }, '→'), chip('TP53 + GRB2', 'green'));
  root.append(h('style', {}, '@keyframes spin{to{transform:translate(-50%,-50%) rotate(360deg)}}'),
    h('div', { class: 'mb-6' }, h('div', { class: 'text-2xl font-semibold text-white' }, t('h.title')), h('div', { class: 'mt-1 max-w-3xl text-sm text-slate-400' }, t('h.sub'))), flow(),
    h('div', { class: 'mt-5 grid gap-4 lg:grid-cols-2' },
      step(1, t('s1.t'), t('s1.p'), h('div', {}, h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-slate-500' }, t('s1.rule')), h('div', { class: 'rounded-lg bg-black/40 p-2.5 font-mono text-xs text-cyan-200' }, `p21CIP = ${rule}`)), 'bg-cyan-500/30'),
      step(2, t('s2.t'), t('s2.p'), orbit, 'bg-amber-500/25'),
      step(3, t('s3.t'), t('s3.p'), h('div', { class: 'flex flex-wrap gap-2' }, badge('FORCED · ' + t('s3.f'), 'green'), badge('SURVIVES · ' + t('s3.s'), 'red')), 'bg-emerald-500/25'),
      step(4, t('s4.t'), t('s4.p'), h('div', { class: 'flex flex-wrap items-center gap-1.5' }, chip('ATM', 'red'), chip('RB1', 'red'), chip('TP53', 'red'), h('span', { class: 'px-1 text-slate-600' }, '|'), chip('MDM2', 'slate', 'line-through opacity-60'), chip('AKT', 'slate', 'line-through opacity-60')), 'bg-rose-500/25'),
      step(5, t('s5.t'), t('s5.p'), tree, 'bg-fuchsia-500/25'),
      step(6, t('s6.t'), t('s6.p'), h('div', {}, h('div', { class: 'mb-1 text-[11px] uppercase tracking-wider text-slate-500' }, t('s6.ex')), h('div', { class: 'flex flex-wrap items-center gap-1 text-[11px]' }, chip('TP53=0', 'red'), chip('Growth_inhibitors=0', 'violet'), h('span', { class: 'px-1 text-slate-500' }, '⇒'), chip('p21CIP=0', 'green'), h('span', { class: 'ml-1 text-emerald-400' }, '✓'))), 'bg-violet-500/25')),
    h('div', { class: 'mt-5 rounded-2xl border border-amber-300/25 bg-amber-400/[.07] p-5' }, h('div', { class: 'mb-1 text-sm font-semibold text-amber-200' }, '⚖ ' + t('h.lim.t')), h('p', { class: 'text-xs leading-relaxed text-amber-100/80' }, t('h.lim.p')),
      h('ul', { class: 'mt-3 space-y-1 text-xs text-amber-100/70' }, ...['h.lim.l1', 'h.lim.l2', 'h.lim.l3'].map(k => h('li', {}, '• ' + t(k))))));
}
