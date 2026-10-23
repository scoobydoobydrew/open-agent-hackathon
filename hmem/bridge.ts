// JSON-lines bridge between the Python agent and the OFFICIAL H-MEM reference implementation in ./reference
// (vendored unmodified, see UPSTREAM.json). One request per line on stdin, one response per line on stdout:
//   {"id": 1, "method": "add", "params": {...}}  ->  {"id": 1, "result": ...}  or  {"id": 1, "error": "..."}
// Nothing here re-implements the spec: every method forwards to the reference services.

import readline from "node:readline";
import { HMEM } from "./reference/src/index.ts";

const persistDir = process.argv[2] && process.argv[2] !== "-" ? process.argv[2] : undefined;
const actor = process.argv[3] || "agent";
const hmem = new HMEM({ persistDir, actor });

// Embeddings are an internal ranking detail; keep them out of the wire format.
const strip = (m: any) => {
  if (!m) return m;
  const { embedding: _e, ...rest } = m;
  return rest;
};

const methods: Record<string, (p: any) => unknown | Promise<unknown>> = {
  add: (p) => strip(hmem.add(p)),
  get: (p) => strip(hmem.store.get(p.id)),
  all: () => hmem.store.all().map(strip),
  update: (p) => strip(hmem.store.update(p.id, p.patch)),
  query: (p) => {
    const r = hmem.query(p.query, p.opts);
    return { context: r.context, trace: r.trace, memories: r.memories.map((x) => ({ relevance: x.relevance, memory: strip(x.memory) })) };
  },
  feedback: (p) => {
    hmem.feedback(p.id, p.kind);
    return strip(hmem.store.get(p.id));
  },
  mine: async (p) => (await hmem.mine(p.event, p.text, p.opts)).map(strip),
  ledger_history: (p) => hmem.ledger.history(p.id),
  ledger_stats: () => hmem.ledger.stats(),
  ledger_all: () => hmem.ledger.all(),
  conflicts_scan: () => hmem.conflicts.scan(),
  conflicts_auto_resolve: (p) => hmem.conflicts.autoResolve(p.conflict),
  conflicts_queue: () => hmem.conflicts.queue(),
  sleep_preview: () => hmem.sleep.preview(),
  sleep_execute: (p) => hmem.sleep.execute(p?.preview),
  sleep_restore: (p) => hmem.sleep.restore(p.backupId),
  dream: () => hmem.dreaming.dream(),
  dream_pending: () => hmem.dreaming.pending(),
  dream_approve: (p) => strip(hmem.dreaming.approve(p.id)) ?? null,
  dream_reject: (p) => hmem.dreaming.reject(p.id),
  ping: () => "pong",
};

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", async (line) => {
  if (!line.trim()) return;
  let id: unknown = null;
  try {
    const req = JSON.parse(line);
    id = req.id;
    const fn = methods[req.method];
    if (!fn) throw new Error(`unknown method ${req.method}`);
    const result = await fn(req.params ?? {});
    process.stdout.write(JSON.stringify({ id, result: result ?? null }) + "\n");
  } catch (err) {
    process.stdout.write(JSON.stringify({ id, error: (err as Error).message }) + "\n");
  }
});
rl.on("close", () => process.exit(0));
