export const getMeta = () => fetch('/api/meta').then(r => r.json());
export const getReplay = name => fetch(`/api/replay?name=${encodeURIComponent(name)}`).then(r => r.json());
export const verify = (scenario, fixed, knockouts) =>
  fetch('/api/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario, fixed, knockouts }) }).then(r => r.json());

// Server-sent events. Returns a function that stops the stream.
export function stream(path, params, onEvent, onEnd) {
  const es = new EventSource(`${path}?${new URLSearchParams(params)}`);
  let finished = false;
  const end = () => { if (!finished) { finished = true; es.close(); onEnd && onEnd(); } };
  es.onmessage = e => {
    const ev = JSON.parse(e.data);
    onEvent(ev);
    if (ev.type === 'done' || ev.type === 'error') end();
  };
  es.onerror = end;
  return () => { finished = true; es.close(); };
}
