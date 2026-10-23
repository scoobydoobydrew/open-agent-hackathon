// Tiny i18n: each module registers its own strings with addStrings({en:{}, el:{}}).
const dict = { en: {}, el: {} };
const listeners = [];
let lang = 'en';
try { lang = localStorage.getItem('lang') || 'en'; } catch (e) { /* private mode */ }

export function addStrings(s) {
  for (const l of ['en', 'el']) Object.assign(dict[l], s[l] || {});
}
export function t(key, vars = {}) {
  const raw = dict[lang][key] ?? dict.en[key] ?? key;
  return String(raw).replace(/\{(\w+)\}/g, (_, n) => (vars[n] ?? ''));
}
export const getLang = () => lang;
export function setLang(l) {
  lang = l;
  try { localStorage.setItem('lang', l); } catch (e) { /* ignore */ }
  document.documentElement.lang = l;
  applyStatic();
  listeners.forEach(f => f());
}
export const onLang = f => listeners.push(f);
export function applyStatic(root = document) {
  root.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
}
