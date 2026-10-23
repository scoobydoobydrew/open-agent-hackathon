// DOM helpers (no framework): h() builds HTML, s() builds SVG.
const SVG_NS = 'http://www.w3.org/2000/svg';

// Element.append(null) would print "null": skip empty children and accept arrays everywhere.
const nativeAppend = Element.prototype.append;
Element.prototype.append = function (...kids) {
  return nativeAppend.apply(this, kids.flat(Infinity).filter(k => k != null && k !== false));
};

function apply(node, attrs) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
    else if (k === 'html') node.innerHTML = v;
    else node.setAttribute(k, v === true ? '' : v);
  }
}
function append(node, kids) {
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
}
export function h(tag, attrs, ...kids) { const n = document.createElement(tag); apply(n, attrs); append(n, kids); return n; }
export function s(tag, attrs, ...kids) { const n = document.createElementNS(SVG_NS, tag); apply(n, attrs); append(n, kids); return n; }

export const $ = (sel, root = document) => root.querySelector(sel);
export const clear = node => { while (node.firstChild) node.removeChild(node.firstChild); return node; };
export const fmt = n => (n == null ? '–' : Number(n).toLocaleString('en-US'));
export const pct = x => (x == null ? '–' : `${Math.round(x * 100)}%`);

const TONES = {
  green: 'bg-emerald-400/15 text-emerald-300 ring-emerald-400/30',
  red: 'bg-rose-400/15 text-rose-300 ring-rose-400/30',
  amber: 'bg-amber-400/15 text-amber-300 ring-amber-400/30',
  cyan: 'bg-cyan-400/15 text-cyan-300 ring-cyan-400/30',
  violet: 'bg-violet-400/15 text-violet-300 ring-violet-400/30',
  slate: 'bg-slate-400/10 text-slate-300 ring-slate-400/20',
};
export function badge(text, tone = 'slate', extra = '') {
  return h('span', { class: `inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TONES[tone]} ${extra}` }, text);
}
export function chip(text, tone = 'cyan', extra = '') {
  return h('span', { class: `inline-flex items-center rounded-md px-1.5 py-0.5 font-mono text-[11px] ring-1 ring-inset ${TONES[tone]} ${extra}` }, text);
}
export const verdictTone = v => ({ FORCED: 'green', SAFE: 'green', SURVIVES: 'red', TOXIC: 'red', UNKNOWN: 'amber', INVALID: 'amber', DUPLICATE: 'slate' }[v] || 'slate');

// floating tooltip
const tip = () => document.getElementById('tip');
export function showTip(evt, html) {
  const el = tip(); if (!el) return;
  el.innerHTML = html; el.classList.remove('hidden');
  const pad = 14, w = el.offsetWidth, hh = el.offsetHeight;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
  if (y + hh > innerHeight - 8) y = evt.clientY - hh - pad;
  el.style.left = `${Math.max(8, x)}px`; el.style.top = `${Math.max(8, y)}px`;
}
export const hideTip = () => tip()?.classList.add('hidden');
export const esc = str => String(str).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// animate a number towards a target
export function countTo(node, target, ms = 450) {
  const from = Number(node.dataset.v || 0); node.dataset.v = target;
  const t0 = performance.now();
  const step = now => {
    const k = Math.min(1, (now - t0) / ms);
    node.textContent = fmt(Math.round(from + (target - from) * (1 - Math.pow(1 - k, 3))));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
