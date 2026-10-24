import { addStrings, applyStatic, getLang, onLang, setLang, t } from './i18n.js';
import { badge, clear, h, hideTip, $ } from './ui.js';
import { getMeta } from './api.js';
import { INPUTS, SHORT, current, onScenario, setInput, setScenario, store, targets } from './store.js';
import * as explore from './explore.js';
import * as search from './search.js';
import * as agent from './agent.js';
import * as bench from './bench.js';
import * as how from './how.js';

addStrings({
  en: { 'app.title': 'Verified Knockout Agent', 'app.tag': 'Neuro-symbolic · proof-backed', 'tab.explore': 'Explore',
        'tab.search': 'Search', 'tab.agent': 'Agent', 'tab.bench': 'Benchmark', 'tab.how': 'How it works',
        'st.data': 'Data layer', 'st.llm': 'LLM', 'st.solver': 'Solver', 'st.zetaris': 'Zetaris', 'st.local': 'local CSV', 'st.starting': 'starting Zetaris…',
        'st.local.tip': 'Zetaris is not reachable, so the agent reads data/*.csv (shown in every report). Start the Zetaris containers, then click to reconnect.',
        'st.zetaris.tip': 'Network, scenarios and drug data come from Zetaris with SQL.', 'st.llm.off': 'no API key',
        'bar.custom': 'Custom inputs', 'bar.reset': 'reset', 'bar.inputs': 'Conditions', 'bar.lesions': 'Tumour lesions',
        'bar.none': 'none', 'in.DNA_damage': 'Radiation', 'in.EGFR_stimulus': 'EGF', 'in.FGFR3_stimulus': 'FGFR3',
        'in.Growth_inhibitors': 'Anti-growth', 'bar.goal': 'Goal: apoptosis in every long-term state' },
  el: { 'app.title': 'Verified Knockout Agent', 'app.tag': 'Νευρο-συμβολικό · με αποδείξεις', 'tab.explore': 'Εξερεύνηση',
        'tab.search': 'Αναζήτηση', 'tab.agent': 'Agent', 'tab.bench': 'Benchmark', 'tab.how': 'Πώς λειτουργεί',
        'st.data': 'Data layer', 'st.llm': 'LLM', 'st.solver': 'Solver', 'st.zetaris': 'Zetaris', 'st.local': 'τοπικά CSV', 'st.starting': 'εκκίνηση Zetaris…',
        'st.local.tip': 'Το Zetaris δεν είναι προσβάσιμο, οπότε ο agent διαβάζει τα data/*.csv (φαίνεται σε κάθε report). Ξεκίνα τα containers του Zetaris και κάνε κλικ για επανασύνδεση.',
        'st.zetaris.tip': 'Δίκτυο, σενάρια και φάρμακα έρχονται από το Zetaris με SQL.', 'st.llm.off': 'χωρίς API key',
        'bar.custom': 'Προσαρμοσμένες είσοδοι', 'bar.reset': 'επαναφορά', 'bar.inputs': 'Συνθήκες', 'bar.lesions': 'Βλάβες όγκου',
        'bar.none': 'καμία', 'in.DNA_damage': 'Ακτινοβολία', 'in.EGFR_stimulus': 'EGF', 'in.FGFR3_stimulus': 'FGFR3',
        'in.Growth_inhibitors': 'Αντι-ανάπτυξη', 'bar.goal': 'Στόχος: απόπτωση σε κάθε μακροχρόνια κατάσταση' },
});

const TABS = [['explore', explore], ['search', search], ['agent', agent], ['bench', bench], ['how', how]];
let active = 'explore';

function renderTabs() {
  const nav = clear($('#tabs'));
  for (const [id] of TABS) {
    const on = id === active;
    nav.append(h('button', {
      class: `rounded-lg px-4 py-1.5 text-sm font-medium transition ${on ? 'bg-gradient-to-b from-white/15 to-white/5 text-white shadow-inner ring-1 ring-white/15' : 'text-slate-400 hover:text-white'}`,
      onclick: () => show(id),
    }, t('tab.' + id)));
  }
}

function show(id) {
  active = id; hideTip();
  for (const [tid, mod] of TABS) {
    const el = document.getElementById('view-' + tid);
    el.classList.toggle('hidden', tid !== id);
    if (tid === id) { mod.onShow && mod.onShow(); el.classList.add('animate-fadeUp'); setTimeout(() => el.classList.remove('animate-fadeUp'), 500); }
  }
  // the scenario bar is irrelevant for the two static pages
  $('#scenario-bar').classList.toggle('hidden', id === 'bench' || id === 'how');
  location.hash = id; renderTabs();
}

let healing = false;
async function retry() {
  if (healing) return;
  healing = true; renderStatus();
  // the server restarts the Zetaris containers in the background; poll until it is back (or gives up)
  for (let i = 0; i < 50; i++) {
    const r = await fetch('/api/reconnect').then(x => x.json()).catch(() => ({ healing: false }));
    if (r.data_source === 'zetaris' || (!r.healing && i > 0)) break;
    await new Promise(res => setTimeout(res, 4000));
  }
  healing = false; store.meta = await getMeta(); renderStatus();
}

function renderStatus() {
  const m = store.meta, box = clear($('#status'));
  const zet = m.data_source === 'zetaris';
  const cell = 'flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[.03] px-2.5 py-1 text-xs';
  box.append(
    h('div', { class: cell + (zet ? '' : ' cursor-pointer hover:bg-white/10'), title: zet ? t('st.zetaris.tip') : t('st.local.tip'), onclick: zet ? null : retry },
      h('span', { class: 'text-slate-500' }, t('st.data')), badge(zet ? t('st.zetaris') : healing ? t('st.starting') : t('st.local'), zet ? 'green' : 'amber')),
    h('div', { class: cell },
      h('span', { class: 'text-slate-500' }, t('st.llm')), badge(m.llm.available ? m.llm.model.split('/').pop() : t('st.llm.off'), m.llm.available ? 'cyan' : 'amber')),
    h('div', { class: cell },
      h('span', { class: 'text-slate-500' }, t('st.solver')), badge('Z3 + exact attractors', 'violet')),
    h('div', { class: 'flex overflow-hidden rounded-lg border border-white/10 text-xs' },
      ...['en', 'el'].map(l => h('button', { class: `px-2.5 py-1 font-semibold uppercase transition ${getLang() === l ? 'bg-white/15 text-white' : 'text-slate-400 hover:text-white'}`, onclick: () => setLang(l) }, l))));
}

function renderScenarioBar() {
  const bar = clear($('#scenario-bar')), sc = current();
  const pills = h('div', { class: 'scroll-thin flex gap-2 overflow-x-auto pb-1' },
    ...targets().map(s => h('button', {
      title: s.description,
      class: `shrink-0 rounded-xl px-3.5 py-2 text-left text-sm transition ring-1 ring-inset ${s.id === store.scenarioId ? 'bg-gradient-to-br from-cyan-400/25 to-fuchsia-400/20 text-white ring-cyan-300/40 shadow-[0_0_24px_rgba(34,211,238,.15)]' : 'bg-white/[.03] text-slate-300 ring-white/10 hover:bg-white/[.07]'}`,
      onclick: () => setScenario(s.id),
    }, h('div', { class: 'font-medium' }, SHORT[s.id] || s.id), h('div', { class: 'font-mono text-[10px] text-slate-500' }, s.id))));
  const lesions = Object.entries(sc.fixed).filter(([n]) => !INPUTS.includes(n));
  const toggles = INPUTS.map(n => {
    const on = sc.fixed[n] === 1;
    return h('button', { onclick: () => setInput(n, on ? 0 : 1), class: 'group flex items-center gap-2 rounded-lg bg-white/[.03] px-2.5 py-1.5 text-xs ring-1 ring-inset ring-white/10 transition hover:bg-white/[.08]' },
      h('span', { class: `relative h-4 w-7 rounded-full transition ${on ? 'bg-emerald-400/80 shadow-[0_0_12px_rgba(52,211,153,.6)]' : 'bg-slate-600'}` },
        h('span', { class: `absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${on ? 'left-[14px]' : 'left-0.5'}` })),
      h('span', { class: on ? 'text-slate-100' : 'text-slate-400' }, t('in.' + n)));
  });
  bar.append(pills, h('div', { class: 'mt-3 flex flex-wrap items-center gap-x-5 gap-y-2' },
    h('div', { class: 'text-xs text-slate-400' }, sc.description + '.'),
    h('div', { class: 'flex flex-wrap items-center gap-2' }, h('span', { class: 'text-[11px] uppercase tracking-wider text-slate-500' }, t('bar.inputs')), ...toggles),
    h('div', { class: 'flex items-center gap-1.5 text-xs' }, h('span', { class: 'text-[11px] uppercase tracking-wider text-slate-500' }, t('bar.lesions')),
      ...(lesions.length ? lesions.map(([n, v]) => badge(`${n} = ${v}`, 'violet')) : [h('span', { class: 'text-slate-500' }, t('bar.none'))])),
    sc.custom ? h('div', { class: 'flex items-center gap-2' }, badge(t('bar.custom'), 'amber'), h('button', { class: 'text-xs text-cyan-300 underline-offset-2 hover:underline', onclick: () => setScenario(store.scenarioId) }, t('bar.reset'))) : null,
    h('div', { class: 'ml-auto text-xs text-slate-500' }, t('bar.goal'))));
}

async function boot() {
  store.meta = await getMeta();
  store.scenarioId = targets()[0].id;
  document.documentElement.lang = getLang(); applyStatic();
  TABS.forEach(([id, mod]) => mod.init(document.getElementById('view-' + id)));
  renderStatus(); renderScenarioBar();
  onScenario(renderScenarioBar);
  onLang(() => { renderStatus(); renderScenarioBar(); renderTabs(); });
  if (store.meta.data_source !== 'zetaris') retry();
  const start = location.hash.slice(1);
  show(TABS.some(([id]) => id === start) ? start : 'explore');
}
boot().catch(err => { document.body.append(h('pre', { class: 'm-6 rounded-xl bg-rose-950/60 p-4 text-rose-200' }, 'Failed to start: ' + err.stack)); });
