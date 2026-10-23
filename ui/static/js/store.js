// Shared state: loaded metadata and the scenario every view works on.
export const store = { meta: null, scenarioId: 'fgfr3_wtp53', override: null };
const subs = [];
export const onScenario = f => subs.push(f);
const fire = () => subs.forEach(f => f());

export const targets = () => store.meta.scenarios.filter(s => s.kind === 'target');
export function current() {
  const sc = store.meta.scenarios.find(x => x.id === store.scenarioId);
  return { ...sc, fixed: store.override || sc.fixed, custom: !!store.override };
}
export function setScenario(id) { store.scenarioId = id; store.override = null; fire(); }
export function setInput(node, value) {
  const base = current().fixed;
  store.override = { ...base, [node]: value };
  // going back to the preset's own values drops the "custom" flag
  const preset = store.meta.scenarios.find(x => x.id === store.scenarioId).fixed;
  if (Object.keys(preset).every(k => preset[k] === store.override[k])) store.override = null;
  fire();
}
export const INPUTS = ['DNA_damage', 'EGFR_stimulus', 'FGFR3_stimulus', 'Growth_inhibitors'];
export const SHORT = {
  fgfr3_wtp53: 'FGFR3 · p53 wild-type', egf_wtp53: 'EGF · p53 wild-type', egf_growthinh: 'EGF · anti-growth',
  fgfr3_growthinh: 'FGFR3 · anti-growth', egf_tp53null: 'EGF · TP53 lost', egf_mdm2amp: 'EGF · MDM2 amplified',
  fgfr3_rb1loss: 'FGFR3 · RB1 lost', growthinh_only: 'Quiescent · no growth signal',
};
