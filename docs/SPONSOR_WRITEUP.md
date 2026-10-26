# Sponsor technology explanation (paste into the submission form)

**Project:** Verified Knockout Agent. An agent proposes gene knockouts for a radiation-surviving tumour cell, an exact
solver proves or refutes each proposal, and the explanation is cut into proof steps that are re-checked against the
model's rules. Track 02, "The Agent That Can Explain Why".

## Zetaris: the agent's data layer
The agent does not carry the biology in its prompt; it reads it live from Zetaris. The 35 Boolean update rules of the
published network, the scenario definitions and a hand-curated drug-evidence table are three tables in the `open_agent`
database, queried through the Zetaris REST gateway with SQL, in two ways. (1) The **LLM calls a `run_sql` tool**: it
writes SELECTs itself (for example "which candidate genes have an approved or clinical drug", "which genes regulate
TP53"), and a guard allows only one SELECT on our three tables with a row limit; failed queries are returned to the model
once so it can repair them. (2) The orchestrator runs a **SQL JOIN** between the network table and the drug table to rank
candidate genes. The benchmark answers are deliberately kept out of the tables so the agent cannot read them. The UI shows
whether the data layer is Zetaris or the local CSV fallback, and every report says so. Code: `agent/tools_zetaris.py`,
`agent/sql_tool.py`.

## Meterless
**Engine: H-MEM.** We use the official H-MEM reference implementation from the Meterless engines repository, vendored
unmodified (commit and SHA-256 per file in `hmem/UPSTREAM.json`, checked by a test). What it does in the project: it is
the agent's memory across runs. Each solver-verified result becomes an H-MEM record with source, confidence and
provenance; before every proposal round the engine's ranked retrieval puts the relevant memories into the prompt (the UI
shows "H-MEM recalled N memories"); recalled facts that are confirmed or contradicted are graded with the engine's
feedback deltas; every operation is in its append-only audit ledger; lessons are mined with the spec's mining prompt;
dream proposals are never approved automatically (human approval boundary).
**The test showing it works:** `python -m pytest tests/test_hmem.py -v` passes (12 tests: the vendored files are
byte-identical to upstream, the committed bridge equals a rebuild from those sources, the official conformance suite
passes 13/13, and the agent's store, recall, feedback and ledger behave as the spec says). `python -m agent.memory status`
shows the live engine.

**Nightshift: the primary AI provider.** Every LLM request of the app goes to the local Meterless Nightshift runtime
(OpenAI-compatible `/v1/chat/completions` on `http://127.0.0.1:8088/v1`) with the runtime token and a `meterless-app`
header. The NVIDIA key is stored in Nightshift's Providers tab and never in the project. A direct NVIDIA call exists only
as a clearly labelled fallback for when Nightshift is not running, and `SAMPLE_MODE=true` switches every network call off
so the project still runs. `tests/test_llm.py` checks the contract against a stand-in runtime (route, headers, routed
model, fallback, no secrets in logs). Evidence is written as JSONL to `logs/`: every LLM request with the model that
handled it, every H-MEM retrieval, and each run's events and H-MEM ledger. Code: `agent/llm.py`, `agent/logs.py`.

## NVIDIA
Nemotron (`nvidia/nemotron-3.5-lightning-30b-a3b`, pinned) is the runtime model, reached through Nightshift: it proposes
knockouts with a rationale, writes the SQL for Zetaris, and words the explanations. Every request is logged with the model
that actually handled it (Nightshift's routed model), and the Agent tab shows it on each request. We measured it: with
thinking on, the model did not answer within 16,000 tokens (268 s); with thinking off it answers in about 2 s, so thinking
is off. We also benchmarked the 550B Nemotron: its explanations were cleaner (99.4% of steps clean against 94.6%) but its
proposals were no better.

## What is unique about this use of the sponsor technology
Nobody in the loop is trusted. Zetaris is queried with SQL the model writes but a guard validates. Nightshift routes the
model's proposals into an exact solver whose counterexamples go back to the model and into a complete search, so a wrong
proposal costs one solver call and the system can answer "impossible" with a proof. H-MEM stores only facts the solver
verified, and a remembered failure becomes a sound shortcut: a stored surviving state refutes later proposals without a
solver call (149 nodes refuted from memory in one live run of five rounds).

## What the numbers say (8 scenarios, exhaustive ground truth)
The LLM alone proposes a wrong knockout set 91% of the time and invents a solution for the one scenario that has none.
With the solver and the complete counterexample-guided search the system is never wrong, needs 34x fewer solver calls than
brute force, and proves that no knockout of up to 4 genes works in 56 solver calls (brute force: 10,903). 96.8% of the
explanation steps the LLM chose stayed inside the proof.

## Honest limits
One published model, Boolean abstraction, results are in-silico hypotheses. The exact engine handles about 21 free nodes
after reduction; a 53-node model returned UNKNOWN. In this network the search itself is symbolic and needs no LLM: the
LLM adds the interface, the SQL and the explanations, not search power.

## Pre-existing components (declare these in the form)
- The published Boolean model of bladder tumorigenesis (Remy et al., Cancer Research 2015, booleanized with GINsim, from the
  PyBoolNet repository): `data/source/remy_tumorigenesis.bnet`. All tables, the solver, the agent, the UI and the benchmark
  were written during the build window (first commit 22 Oct 2026).
- The official Meterless H-MEM reference implementation and conformance suite, vendored unmodified in `hmem/` (Apache-2.0).
- Open-source libraries: Z3, numpy, scipy, requests, python-dotenv, networkx (tests), Tailwind CSS Play CDN build
  (vendored for the offline demo).
- No pre-existing product code. `data/druggability.csv` is hand-curated from general knowledge during the window and is not
  verified.

## Development tool
Written with Claude Code (Anthropic), from the first solver test to the final deck and demo video. Cursor was not used.
