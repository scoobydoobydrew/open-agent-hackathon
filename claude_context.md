# Project Context: verified agent for knockouts that force apoptosis

Open Agent Hackathon 2026 (build window 22-27 Oct 2026, 23:45 UTC), Track 02 "The Agent That Can Explain Why".
The independent solver core is reused for the Meta Global AI Developer Hackathon (26 Oct - 4 Nov); Meta-specific code
(Llama adapter, Meta benchmarks) must be written inside Meta's own window, after 26 Oct.

## What exists (all tested: `python -m pytest`, 67 tests)
- `solver/` exact asynchronous attractor analysis + Z3, counterexample-guided complete search (`cegar.py`), checked
  explanations (`explain.py`). No LLM dependency.
- `agent/` orchestrator (`main.py`), Nemotron REST client (`llm.py`), Zetaris tool (`tools_zetaris.py`), H-MEM style memory
  (`memory.py`), prompts.
- `data/` three Zetaris tables built from the published Remy et al. 2015 model (35 nodes, 23 knockable genes).
- `ui/` local demo UI (`python ui/server.py`, port 8765): Explore / Search / Agent / Benchmark / How it works, EN+EL. Plain
  JS modules in `ui/static/js`, Tailwind Play CDN vendored. Replays of real agent runs in `ui/replays/` (re-record with
  `ui/record_replays.py`). Tests in `tests/test_ui.py`.
- `benchmark/` ground truth (exhaustive solver) and runner. Results: `benchmark/RESULTS-nemotron-lightning.md`.
- README.md has the honest results and limitations. Read it before changing claims.

## Facts that differ from the first plan (do not revert)
- Zetaris REST is the gateway on **port 3000**: `POST /api/auth/login` -> `idToken`, `orgId`; queries via
  `POST /api/proxy/query/sql/start` with `{"select": ..., "pageLimit": n}`, headers `Authorization`, `X-Org-ID`,
  `X-Request-ID`. Only SELECT works. Port 8888 / `/api/v1/query` is wrong (404). The `zetaris-driver-1` container had
  stopped and was restarted; check `docker ps` shows postgres, driver, api, ui.
- Zetaris self-heals: `agent/zetaris_heal.py` recreates the driver container after Docker restarts; `ui/server.py` runs it at startup
  and on chip click (`ZETARIS_AUTOHEAL=0` disables). Manual: `scripts/zetaris_up.sh`.
- Tables exist in the Zetaris database `open_agent` (`ZETARIS_DB`); the UI chip shows Zetaris. Originally they had to be created once in the web UI from `file-store/p53/*.csv` (already uploaded). See
  `docs/zetaris_setup.md`. Until then the agent uses local CSV and says so in every report.
- LLM: Nemotron with thinking **off** (`chat_template_kwargs.enable_thinking=false`); thinking mode never finished
  (16000 tokens, 268 s). `nemotron-3-super-120b-a12b` returns 404 for this account; ultra-550b works but did not
  beat lightning-30b.
- The network is the published model, not a mock. Solutions are NOT in the Zetaris tables (they live in
  `benchmark/ground_truth.json`) so the agent cannot read the answers.
- H-MEM: the official Meterless engine is vendored unmodified in `hmem/` (UPSTREAM.json + SHA-256 test); conformance 13/13.
  `agent/memory.py` uses it through `agent/hmem_engine.py` (Node bridge); the counterexample cache is a separate, non-H-MEM structure.

## Key result (shapes the pitch)
The LLM alone is wrong 91% of the time and invents solutions for the impossible scenario. The symbolic
counterexample-guided search, with no LLM, finds all minimal sets with 34x fewer solver calls than brute force and proves
impossibility. The LLM does not improve the search on this small network; its value is the interface, checked
explanation wording and cross-run memory. Do not claim otherwise without new evidence.

## Pending
- Demo video (1-4 min), pitch deck (5-7 slides), commits inside the build window, Cursor usage evidence if required.
- Meta hackathon: Llama adapter in `agent/llm.py` and Meta-specific benchmarks, only after 26 Oct.
- Optional: a larger published network where an LLM prior might matter; thinking-model proposer with a bounded budget.

## Conventions
- Credentials only in `.env` (gitignored); never commit keys. Windows Git Bash mangles leading `/` in arguments: use
  `MSYS_NO_PATHCONV=1` when passing URL paths.
