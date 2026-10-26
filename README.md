# Verified Knockout Agent: gene knockouts that provably force apoptosis in radiation-resistant tumour cells

An LLM agent finds gene knockouts that push a tumour cell into apoptosis after radiation. **A formal solver checks
every proposal exactly**, a counterexample-guided search finds (or proves there is no) minimal knockout set, and every
explanation is built from solver-proven steps and checked against the model's rules. Network used: the published
2015 bladder-tumorigenesis model (Remy et al.).

> **What we measured, honestly.** An LLM on its own proposes wrong knockout sets 91% of the time and invents an answer
> for a case where none exists. Our verified loop is never wrong. The *search* is carried by the symbolic
> counterexample-guided algorithm, not by the LLM: with no LLM at all it finds every answer using 34 times fewer solver
> calls than brute force. The LLM's job here is the interface, the wording of explanations, and (via memory) lessons
> across runs. See [Results](#results) and [Limitations](#limitations).

Open Agent Hackathon 2026, Track 02 ("The Agent That Can Explain Why"). Sponsor technology: **Zetaris** (data layer),
**Meterless Nightshift** (primary AI provider) and **Meterless H-MEM** (memory engine), **NVIDIA Nemotron** (the model).

## Quick start from a clean clone

```bash
git clone https://github.com/scoobydoobydrew/open-agent-hackathon && cd open-agent-hackathon
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # Windows: copy .env.example .env
SAMPLE_MODE=true python ui/server.py                   # PowerShell: $env:SAMPLE_MODE="true"; python ui/server.py
```

Open http://localhost:8765. **`SAMPLE_MODE=true` needs no account, no key and no running service**: the data comes from
`data/*.csv`, no LLM is called, and Explore, Search and Benchmark are live computations by the real solver. The Agent tab
replays recorded real runs (Zetaris SQL calls, Nemotron proposals, solver counterexamples). Tests: `python -m pytest`.

For the full system (all three sponsor services), see the next two sections.

## Sponsor technology: what is used, where, and how to check it

| sponsor | role in this project | code | check it |
|---|---|---|---|
| **Zetaris** | the agent's data layer: the 35 network rules, the scenarios and a drug-evidence table are SQL tables in the `open_agent` database; the agent reads them over the Zetaris REST gateway, the **LLM writes its own read-only `run_sql` queries**, and a SQL `JOIN` ranks candidate genes | `agent/tools_zetaris.py`, `agent/sql_tool.py`, [docs/zetaris_setup.md](docs/zetaris_setup.md) | the UI chip "Data layer: Zetaris"; `SQL tool call` cards in a run; `tests/test_sql_tool.py` |
| **Meterless Nightshift** | the **primary AI provider**: every LLM request goes to the local Nightshift runtime (`http://127.0.0.1:8088/v1`, OpenAI-compatible) with the runtime token and a `meterless-app` header; Nightshift routes it to Nemotron using the NVIDIA key stored in *its* Providers tab, so no NVIDIA key lives in this project | `agent/llm.py` | the UI chip "LLM: Nightshift · nemotron-…"; every request is logged with the model that handled it ([Logs and traces](#logs-and-traces)); `tests/test_llm.py` (contract, headers, routed model, fallback) |
| **Meterless H-MEM** (engine) | the agent's memory across runs: every verified result is an H-MEM record, the next prompt gets the engine's ranked recall, recalled facts are graded with the engine's feedback deltas, every operation is in the audit ledger | `agent/memory.py`, `agent/hmem_engine.py`, `hmem/` (official reference, vendored unmodified) | `python -m pytest tests/test_hmem.py -v` (conformance 13/13 included when `npm install` was run); `python -m agent.memory status`; the "H-MEM recalled N memories" lines in the Agent tab |
| **NVIDIA Nemotron** | the runtime LLM (`nvidia/nemotron-3.5-lightning-30b-a3b`, pinned): proposes knockouts, writes the SQL, words the explanations; a 550B model was benchmarked for explanations | requests through Nightshift (`agent/llm.py`) | the model id in the Agent timeline (`LLM request · proposals · Meterless Nightshift · nemotron-3.5-lightning-30b-a3b`) |

What is unique about this use of the sponsor technology: the LLM is not trusted anywhere. Zetaris is queried with SQL the
model writes but a guard validates (single `SELECT`, our three tables, row limit); Nightshift/Nemotron proposals are
checked by an exact solver and fed back as counterexamples; H-MEM remembers only solver-verified facts, and the memory of
a failure becomes a sound shortcut (a stored surviving state refutes later proposals without a solver call). See
[How we built it](#how-we-built-it).

### Meterless engine requirement: where it is used and how to check it in one minute

- **Engine:** H-MEM, the official reference implementation, vendored unmodified in `hmem/` (checksums in `hmem/UPSTREAM.json`).
- **Working feature that depends on it:** the agent's memory across runs. Every verified proposal and solution is stored as
  an H-MEM record (with `source`, `confidence`, `provenance`); the next run recalls the best ones with the engine's
  ranking into the proposer prompt; recalled facts are graded with the engine's feedback deltas; every operation lands in
  the engine's audit ledger. Code: `agent/memory.py`, `agent/hmem_engine.py`, `hmem/bridge.ts`.
- **Passing test:**
  ```bash
  python -m pytest tests/test_hmem.py -v    # needs only Node.js: the built bridge is committed (hmem/dist/bridge.mjs)
  python -m agent.memory status             # live engine state: records, layers, ledger
  (cd hmem/reference && npm install)        # optional: also runs the official conformance suite (13/13) and the rebuild check
  ```
  Without Node.js the H-MEM tests are skipped, and the agent says in its report that it ran without the engine.

## Dependencies and configuration

| need | for | required? |
|---|---|---|
| Python 3.10+ and `pip install -r requirements.txt` (Z3, numpy, scipy, requests, python-dotenv) | everything | yes |
| Node.js 18+ | the H-MEM engine (no `npm install` needed to run it) | for memory; the agent runs without it and says so |
| **Zetaris** platform (Docker, `docker compose up -d`, three tables in the `open_agent` database) | the data layer | for the full system; without it the agent reads `data/*.csv` and says `local-csv` in every report |
| **Meterless Nightshift** running locally, with the NVIDIA key set in its Providers tab | the primary AI provider | for live LLM runs; without it the agent falls back to NVIDIA directly (labelled "fallback") or, with no key, to the symbolic search |

Configuration lives in `.env` (git-ignored; `.env.example` has placeholders only):

| variable | meaning |
|---|---|
| `NIGHTSHIFT_TOKEN` or `NIGHTSHIFT_TOKEN_FILE` | the Nightshift runtime token (or the path of its `proxy-token` file). Never the NVIDIA key |
| `NIGHTSHIFT_BASE_URL` | default `http://127.0.0.1:8088/v1` |
| `NIGHTSHIFT_APP` | value of the `meterless-app` header, default `verified-knockout-agent` |
| `NEMOTRON_MODEL` | default `nvidia/nemotron-3.5-lightning-30b-a3b`; any id Nightshift serves works (for example `meterless/auto`) |
| `ZETARIS_GATEWAY_URL`, `ZETARIS_USER`, `ZETARIS_PASS`, `ZETARIS_DB` | the Zetaris gateway (port 3000) and the database name (`open_agent`) |
| `NVIDIA_API_KEY` | optional **fallback only**, used when Nightshift is not reachable; the UI and every trace line then say "NVIDIA direct (fallback)" |
| `SAMPLE_MODE=true` | no call to Zetaris, Nightshift or NVIDIA: local files, symbolic search, recorded replays |

## Usage and sample inputs

```bash
python ui/server.py                                     # the interactive UI: http://localhost:8765
python -m agent.main --scenario fgfr3_wtp53             # the agent from the command line, prints a ranked report
python -m agent.main --scenario growthinh_only          # a scenario where no solution exists: the agent proves it
python scripts/make_samples.py                          # rewrites logs/samples/ (3 scenarios: reports and logs)
```

Scenario ids (the input of the agent): `fgfr3_wtp53`, `egf_wtp53`, `egf_growthinh`, `fgfr3_growthinh`, `egf_tp53null`,
`egf_mdm2amp`, `fgfr3_rb1loss`, `growthinh_only` (no solution exists). The UI also lets you set your own inputs
(radiation, EGF, FGFR3, anti-growth signal, tumour lesions) in the bar at the top.

**Three sample inputs and their outputs** (committed in [`logs/samples/`](logs/samples/): the report `<id>.md`, the ordered event
log `<id>.events.jsonl`, and, for runs with an LLM, `<id>.llm-trace.jsonl` with the provider and model of every request):

| input (`--scenario`) | meaning | output |
|---|---|---|
| `fgfr3_wtp53` | FGFR3-driven tumour, wild-type p53, after radiation | three minimal sets, all selective: `TP53`, `p21CIP`, `RB1 + RBL2`, each with a solver derivation of why apoptosis holds |
| `egf_tp53null` | EGF-driven tumour that already lost TP53 | one minimal set: `GRB2` (selective); a drug-evidence line for it from Zetaris |
| `growthinh_only` | quiescent anti-growth tissue, no growth signal | **no solution exists**: the search proves that no set of up to 3 genes forces apoptosis |

The committed samples are produced by `SAMPLE_MODE=true python scripts/make_samples.py` (no LLM, no network, reproducible by
anyone): the solutions and proofs come from the solver and the search, which need no LLM. Runs with an LLM add the
proposals with their rationale, the Zetaris SQL the model wrote, the H-MEM recall lines and the worded explanation steps,
and a trace of which model handled each request; they are produced by the same script without `SAMPLE_MODE`.

## Logs and traces

Evidence of how the agent reached each output is written as JSONL to `logs/` (see [logs/README.md](logs/README.md); no
prompts, no keys):

- `logs/llm-trace.jsonl`: one line per LLM request: provider (`nightshift`, or `nvidia-direct` with `fallback: true`), the
  requested model, **the routed model that actually handled the request** (read from Nightshift's receipt), latency, tokens,
  and any `meterless-*` response headers.
- `logs/hmem-retrieval.jsonl`: one line per H-MEM retrieval before a proposal round: the query, the strategy and ranking
  scores, and the memories injected into the prompt.
- `logs/<scenario>-<run>.events.jsonl` and `logs/<scenario>-<run>.hmem-ledger.jsonl`: every proposal, solver verdict,
  counterexample, SQL call and LLM request of a run, in order, and the H-MEM audit ledger.
- The Agent tab shows the same trail live: every `LLM request` line names the provider and the model, every `SQL tool
  call` card shows the query Zetaris ran, every `H-MEM recalled N memories` line shows what the memory engine injected.
- `logs/samples/` holds committed examples for the three sample inputs. `python scripts/check_nightshift.py` checks the
  Nightshift connection and prints which model answers (no secrets).

## What it does

Given a scenario (for example "FGFR3-driven tumour, wild-type p53, after radiation"), the agent:

1. reads the network, the scenario and drug annotations from **Zetaris** with SQL;
2. asks **Nemotron** for knockout hypotheses and sends each one to the **solver**;
3. on failure, receives a *counterexample*: a long-term cell state in which the tumour survives, with the genes that
   keep it alive;
4. runs a counterexample-guided search that is **complete**, so it either returns every minimal knockout set or proves
   that none exists up to the size limit;
5. checks selectivity (does the same knockout also kill a resting normal cell that gets the same radiation?);
6. explains each answer as numbered proof steps and flags any wording that goes beyond them;
7. remembers failures across runs.

Example (real output, `egf_wtp53`): knocking out `TP53` alone fails because the surviving state has `GRB2` oscillating
with `EGFR`; the pair `GRB2 + TP53` is proved to force apoptosis, and is flagged *not selective* because `GRB2` loss
switches EGFR/RAS signalling on without a ligand and kills the resting normal cell too.

## Architecture

```
 Zetaris (SQL over REST)  --network, scenarios, drugs-->  Agent (agent/main.py)
                                                           |  propose              ^ counterexample
                                                           v                       | (surviving state,
                          Nemotron via Meterless Nightshift (agent/llm.py)         |  active genes)
                                                           |                       |
                                                           v                       |
                          Solver (solver/): Z3 stable states + exact asynchronous attractor analysis
                                                           |
                                counterexample-guided search (solver/cegar.py, complete, no LLM)
                                                           |
                                      H-MEM memory (agent/memory.py): episodes -> refuters -> lessons
```

| path | role |
|---|---|
| `solver/boolean_net.py` | rule parser (no `eval`), Z3 encoding, percolation |
| `solver/attractors.py` | exact attractors of the asynchronous Boolean network (terminal SCCs), including oscillations |
| `solver/verifier.py` | FORCED / SURVIVES / SAFE / TOXIC verdicts, counterexamples, Z3 stable-state check |
| `solver/cegar.py` | counterexample-guided minimal-set search with a completeness argument |
| `solver/explain.py` | derivation trees, numbered proof steps, entailment and wording checks |
| `solver/knockout_opt.py` | brute-force enumeration (ground truth and baseline) |
| `agent/` | orchestrator, Nemotron client, Zetaris tool, memory, prompts |
| `data/` | the three tables ingested into Zetaris |
| `benchmark/` | exhaustive ground truth, benchmark runner, results |

### The model
The published Boolean model of bladder tumorigenesis by Remy et al. (Cancer Research, 2015), booleanized with GINsim
(Didier et al., 2011), as distributed in the PyBoolNet repository: 35 nodes, 4 inputs (`DNA_damage`, `EGFR_stimulus`,
`FGFR3_stimulus`, `Growth_inhibitors`), 23 knockable genes. "Radiation" is the `DNA_damage` input; "survives" means no
committed apoptosis (`Apoptosis_high = 1`). The model is a model of tumorigenesis, not of radio-resistance specifically,
so scenarios are defined by growth signals and lesions in this network.

### What "forced" means
Asynchronous updates, **every** initial state: a knockout set is FORCED when `Apoptosis_high = 1` in every state of every
attractor of the perturbed network. This is stronger than checking stable states: the EGFR/GRB2 loop oscillates, and an
oscillating attractor in which apoptosis flickers counts as survival. Attractors are computed exactly (percolation of
the fixed nodes, then terminal SCCs of the asynchronous state graph) and cross-checked against an independent naive
enumeration and against Z3 in the tests.

### Why the search is complete
If a knockout set K fails, the solver returns a surviving state A. Any superset of K that only adds genes already
*inactive* in A still has A as a surviving state. So every working superset of K contains a gene that is **active** in A.
A minimal solution has only failing proper subsets, so extending failing sets from the empty set by their active genes
reaches every minimal solution (induction along its subsets). When the queue runs dry, no solution of that size exists.
This is checked against exhaustive enumeration on all benchmark scenarios. The LLM can reorder the queue (its failed
proposals go first) but cannot make the search miss anything.

### Explanations that are checked
Each solution comes with a derivation of `Apoptosis_high = 1` split into numbered steps (premises, conclusion, rule).
Every step is proven by construction and re-checked with three-valued rule evaluation. The LLM only chooses steps and
words them; the headline is assembled deterministically; any gene named outside the chosen steps is flagged in the
report. A free-text version of this earlier produced real errors (it said `TP53` loss sets an input to zero), which is
why the free summary was removed.

### Memory: the official Meterless H-MEM engine (`agent/memory.py`, `hmem/`)
The H-MEM reference implementation and conformance suite from
[Meterless/engines/hmem](https://github.com/Meterless/Meterless/tree/main/engines/hmem) are vendored **unmodified**
(commit and SHA-256 of every file in `hmem/UPSTREAM.json`, checked by a test). The official conformance suite passes
**13/13** here. Our own code is only a JSON bridge (`hmem/bridge.ts`) and the Python client (`agent/hmem_engine.py`), so
the spec behaviour is the reference's, not a re-implementation.

The agent uses these H-MEM services:

| H-MEM service | what the agent does with it |
|---|---|
| store | every verified proposal and solution is a record with the mandatory `source`, `confidence` and `provenance` |
| retrieval | the canonical hybrid ranking selects what is recalled; the domain-grouped `[MEMORY CONTEXT]` block goes into the next prompt |
| feedback | a recalled fact that is confirmed gets `helpful` (+0.05), a recalled fact that turns out wrong gets `wrong` (-0.20, `review` tag) |
| ledger | append-only audit of every create, read and feedback (`memory/hmem-engine/.../ledger.jsonl`) |
| mining | lessons are mined from a finished plan with a strict-JSON-array prompt, tolerant parsing and the model-free fallback |
| sleep, dreaming, conflicts | available through `python -m agent.memory status / sleep / dream`; sleep is preview-first and **dream proposals are never approved automatically** (human approval boundary) |

One structure is deliberately *not* part of H-MEM: the **counterexample cache**. A stored surviving state is replayed
against new proposals, and if it is still stable the proposal is refuted without a solver call. It is sound and
property-tested, but it is solver-specific, so it lives beside the memory records and is described as such.

Known limits: the reference's numeric-conflict heuristic reads digits inside gene symbols (`E2F1` vs `E2F3`) as
conflicting numbers, so `status` reports false conflicts. They are only queued for review and the agent never calls
`autoResolve`. Dream proposals live in the engine process, so approve them in the same `agent.memory dream` session.
The engine needs only Node.js (the built bridge `hmem/dist/bridge.mjs` is committed; `npm install` in `hmem/reference` is for
the conformance suite and the rebuild check); without Node.js the agent still runs, says so in the
report, and uses only the counterexample cache.

## Results

Scored against exhaustive-solver ground truth, 8 scenarios, 3 repeats per LLM arm, model
`nvidia/nemotron-3.5-lightning-30b-a3b` (thinking off). Full tables: `benchmark/RESULTS-nemotron-lightning.md`.

| approach | finds a valid minimal set | wrong proposals | solver calls (mean) | proves "no solution" | time (mean) |
|---|---|---|---|---|---|
| brute force | 100% | n/a | 2,876 | yes | 22 s |
| LLM only, no solver | 26% | **91%** | 0 | no (claimed solutions in 100% of runs on the impossible scenario) | 7 s |
| LLM + solver feedback | 29% | n/a | 14 | no | 53 s |
| **symbolic search, no LLM** | **100%** | n/a | **84** | **yes** | **0.9 s** |
| LLM + search | 100% | n/a | 105 | yes | 30 s |
| full system (adds explanations) | 100% | n/a | 114 | yes | 43 s |

- On the impossible scenario (`growthinh_only`) the search proves in about 56 solver calls that no set of up to 4 genes
  works; brute force needs 10,903. (The Search tab without memory replay uses 139 solver calls for the same proof: the
  benchmark shares counterexamples across a session, so about 95 nodes are refuted from memory and only 56 reach the solver.)
- Explanations: of 400 chosen steps, 387 (96.8%) stayed inside the proven steps; 42 of 50 explanations were fully clean.
  The steps themselves are correct by construction, so this measures the LLM's wording.
- LLM time is dominated by API latency. API errors affected the LLM arms: 11 of 192 LLM rounds in `llm_feedback` failed
  (HTTP 429 or a reply cut off mid-JSON), 2 of 24 `llm_only` runs failed and are excluded, and 3 `llm_cegar` runs lost
  their first round to a 429. The searching arms still reached 100% because the search does not need the LLM; the
  weak LLM-only numbers are not explained by these errors alone (they were already poor in earlier smoke runs).

Reproduce: `python scripts/build_tables.py` (about 3 min, regenerates ground truth) then
`python benchmark/run_benchmark.py --repeats 3 --workers 4`.

## Interactive demo UI

```bash
python ui/server.py          # http://localhost:8765 (standard library only, no extra dependencies)
```

Everything on screen comes from the real solver and agent; nothing is mocked. English and Greek (EN/EL switch).

| tab | what it shows |
|---|---|
| Explore | the network as a living picture; click a gene to knock it out and see the exact verdict, every long-term state (including oscillations), the counterexample or the proof steps, and selectivity |
| Search | the counterexample-guided search growing as a tree, event by event, with the solver-call counter against brute force and the "no solution exists" proof |
| Agent | the LLM + solver loop as a timeline (proposals, rationale, counterexamples, search, verified solutions with checked explanation steps). Replay a recording offline, or run it live against Nemotron |
| Benchmark | the measured results, read from `benchmark/results-*.json` |
| How it works | the idea in six steps, using a real rule from the model |

Record runs for the offline replay with `python ui/record_replays.py fgfr3_wtp53 egf_wtp53` (uses the LLM once per
round; the recordings in `ui/replays/` are real runs). Styling uses Tailwind (the Play CDN build is vendored in
`ui/static/vendor/` so the demo works without internet; it is a demo tool, not a production build). Scenario inputs can
be switched in the bar at the top, which creates a custom scenario that Explore and Search use.

## Responsible use

The outputs are **in-silico hypotheses on one published model, not medical advice or a treatment recommendation**. Any
use beyond prioritising experiments needs validation in the lab and review by a domain expert. Safeguards in the code:
inputs are validated (gene names must belong to the network; SQL from the model is limited to one `SELECT` on our three
tables with a row limit), every claim is checked by the exact solver and unsupported wording is flagged, the memory never
approves its own "dream" proposals, every LLM request and every retrieval is logged, and failures of any service degrade to a
labelled fallback instead of an invented answer.

## Limitations

- **The LLM adds no search power on this network.** With 23 candidate genes and size-3 sets the symbolic search is
  already tiny. A larger network is where an LLM prior could matter; we have not shown that.
- **Thinking models were unusable:** Nemotron with thinking on did not produce an answer within 16,000 tokens on our
  prompts (minutes of latency), so thinking is off; this makes the LLM a weak proposer.
- **Scale limit, measured.** The exact attractor engine needs at most about 21 free nodes after reducing the fixed
  ones; the Remy model stays below that in every scenario. On a second published model (`grieco_mapk`, 53 nodes) the
  reduced network is a single 35 to 37 node component, so the verdict is `UNKNOWN`: bigger models need a symbolic
  (BDD or SAT based) attractor backend behind `solver/attractors.py` (`scripts/scale_check.py` reproduces this).
- **A better LLM helps the wording, not the proposals** (same 4 scenarios, small sample): `nemotron-3-ultra-550b` wrote
  explanations whose steps stayed inside the proof 99.4% of the time (lightning-30B: 94.6%) and 95% of explanations were
  fully clean (73%), at 2 to 3 times the latency. Its own unverified proposals were not better (97% wrong vs 85%).
- **Does the model reproduce known biology?** In no scenario does a druggable DNA-damage-response target (ATM, CHK1/2)
  appear in a minimal solution, although CHK1 inhibitors are studied as radiosensitisers. That is a sign the model
  misses mechanisms (for example replication stress); check it before drawing any medical conclusion.
- Boolean abstraction, one published model, no dose, time or off-target effects. Results are in-silico hypotheses to
  prioritise experiments, not clinical claims.
- "FORCED" is over all initial states, which is conservative: a set that works from the realistic pre-treatment state
  but not from some exotic state is reported as failing.
- Selectivity is only tested against a resting normal cell with the same radiation.
- `data/druggability.csv` is hand-curated from general knowledge and not verified; check before citing.
- Ground truth is model-derived (exhaustive on the same model), not literature-derived.

## How we built it
- **Development tooling:** the code, tests and documents were written in agentic coding sessions with **Claude Code**
  (Anthropic). Every claim in this README was checked against a measurement in the repo before it was written.
- **Runtime LLM:** NVIDIA Nemotron (`nemotron-3.5-lightning-30b-a3b`, pinned) through **Meterless Nightshift**, the
  primary provider (OpenAI-compatible `/v1/chat/completions` on the local runtime, runtime token plus `meterless-app`
  header). The NVIDIA key is configured in Nightshift's Providers tab, not here. If Nightshift is not reachable the
  client says so and, only if `NVIDIA_API_KEY` is set, calls NVIDIA directly and labels every request as a fallback.
  Keys live only in `.env` (ignored by git). The benchmark numbers below were measured with direct NVIDIA calls before
  Nightshift was the provider; the model and the prompts are the same.
- **Meterless:** we use the **H-MEM** engine from the Meterless engines repository (vendored unmodified, conformance
  13/13, see above). The prompt for lesson mining follows the spec's mining pipeline.
- **Zetaris:** three tables in the `open_agent` database; the LLM queries them itself through a read-only `run_sql` tool
  (single `SELECT`, our three tables only, row limit), and the agent also runs a `JOIN` between the network rules and the
  drug-evidence table. See [docs/zetaris_setup.md](docs/zetaris_setup.md).
- **Tool-calling loop with a cost cap:** at most 2 SQL turns, 5 to 6 proposal rounds, and a bounded solver budget per round.

## More setup notes

Without Zetaris credentials or tables the agent reads `data/*.csv` and says `data layer: local-csv (...)` in every
report. To use Zetaris see [docs/zetaris_setup.md](docs/zetaris_setup.md): the gateway is on port 3000, only `SELECT` is
accepted, and the three tables live in the `open_agent` database (`ZETARIS_DB`). The quick start and the dependency
table above are the whole setup; the only service that needs manual work is Zetaris (creating the three tables once).

## Portability

`agent/llm.py` is the only file that knows the model provider (`complete(messages) -> LLMResponse`). The solver has no
LLM dependency, and `benchmark/run_benchmark.py --model <id>` reruns the same suite against another model.

## Credits and data provenance

Boolean model: E. Remy et al., *A modelling approach to explain mutually exclusive and co-occurring genetic alterations
in bladder tumorigenesis*, Cancer Research, 2015; booleanized with GINsim following G. Didier et al., J. Theor. Biol.,
2011; obtained from the PyBoolNet model repository (`remy_tumorigenesis`). The original header is kept in
`data/source/remy_tumorigenesis.bnet`. Check the upstream licence terms before redistributing the model files.
