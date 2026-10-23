# H-MEM engine (Meterless)

`reference/` and `conformance/` are the official Meterless H-MEM reference implementation and conformance suite,
vendored **unmodified** from https://github.com/Meterless/Meterless/tree/main/engines/hmem (commit in `UPSTREAM.json`,
Apache-2.0, see `LICENSE`). `AGENTS.md` is the spec. `UPSTREAM.json` holds a SHA-256 for every vendored file and
`tests/test_hmem.py` fails if any of them changes.

Our only code here is `bridge.ts`, a JSON-lines wrapper that forwards calls to the reference services; the Python side is
`agent/hmem_engine.py`. `agent/memory.py` uses the engine for the agent's knowledge.

```bash
cd hmem/reference && npm install                              # once (tsx, esbuild)
node reference/node_modules/tsx/dist/cli.mjs conformance/runner.ts   # official suite: 13/13
```
