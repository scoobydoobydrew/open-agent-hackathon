# logs/

Evidence of how the agent reached its output: append-only JSONL, no prompts and no secrets. Everything at the top level of
this directory is produced by running the agent and is git-ignored; `samples/` is committed.

| file | written by | content |
|---|---|---|
| `llm-trace.jsonl` | `agent/llm.py` | one line per LLM request: provider (`nightshift`, or `nvidia-direct` with `fallback: true`), requested model, **routed model that handled it**, latency, tokens, `meterless-*` response headers |
| `hmem-retrieval.jsonl` | `agent/memory.py` | one line per H-MEM retrieval before a proposal round: query, strategy, ranking scores, the memories injected into the prompt |
| `<scenario>-<run>.events.jsonl` | `agent/main.py` | every proposal, solver verdict, counterexample, SQL call, solution and LLM request of one run, in order |
| `<scenario>-<run>.hmem-ledger.jsonl` | the H-MEM engine | its audit ledger (create, read, feedback, ...) at the end of the run |

`samples/` holds one example per input (`fgfr3_wtp53`, `egf_tp53null`, `growthinh_only`) plus the report `<id>.md`, produced by
`python scripts/make_samples.py` (the committed files come from `SAMPLE_MODE=true`, so they contain no LLM requests; a run
with Nightshift also writes `<id>.llm-trace.jsonl`). `AGENT_LOG_DIR` moves this directory, `AGENT_LOG_DIR=off` disables it.
