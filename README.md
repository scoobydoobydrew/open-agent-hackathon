# A verified agent for radiation-resistant tumours: knockouts that provably force apoptosis, and why

An LLM agent finds gene knockouts that push a tumour cell into apoptosis after radiation. **A formal solver checks
every proposal exactly**, a counterexample-guided search finds (or proves there is no) minimal knockout set, and every
explanation is built from solver-proven steps and checked against the model's rules.

> **What we measured, honestly.** An LLM on its own proposes wrong knockout sets 91% of the time and invents an answer
> for a case where none exists. Our verified loop is never wrong. The *search* is carried by the symbolic
> counterexample-guided algorithm, not by the LLM: with no LLM at all it finds every answer using 34 times fewer solver
> calls than brute force. The LLM's job here is the interface, the wording of explanations, and (via memory) lessons
> across runs. See [Results](#results) and [Limitations](#limitations).

Track 02 ("The Agent That Can Explain Why"). Built with NVIDIA Nemotron, Zetaris and the official Meterless H-MEM engine.

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
                                       Nemotron (agent/llm.py)                     |  active genes)
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
The engine needs Node.js (`cd hmem/reference && npm install` once); without it the agent still runs, says so in the
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
  works; brute force needs 10,903.
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
- **Runtime LLM:** NVIDIA Nemotron (`nemotron-3.5-lightning-30b-a3b` by default) over an OpenAI-compatible REST endpoint.
  The client uses Meterless' endpoint when `METERLESS_API_KEY` and `METERLESS_BASE_URL` are set and NVIDIA's otherwise.
  Keys live only in `.env` (ignored by git); the code reads them at runtime.
- **Meterless:** we use the **H-MEM** engine from the Meterless engines repository (vendored unmodified, conformance
  13/13, see above). The prompt for lesson mining follows the spec's mining pipeline.
- **Zetaris:** three tables in the `open_agent` database; the LLM queries them itself through a read-only `run_sql` tool
  (single `SELECT`, our three tables only, row limit), and the agent also runs a `JOIN` between the network rules and the
  drug-evidence table. See [docs/zetaris_setup.md](docs/zetaris_setup.md).
- **Tool-calling loop with a cost cap:** at most 2 SQL turns, 5 to 6 proposal rounds, and a bounded solver budget per round.

## Setup

```bash
python -m venv venv && venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env                                # add NVIDIA_API_KEY (and Zetaris credentials)
(cd hmem/reference && npm install)                  # once: the official H-MEM engine
python -m pytest                                    # 61 tests, about a minute
python -m agent.main --scenario egf_wtp53 --memory session
```

Without Zetaris credentials or tables the agent reads `data/*.csv` and says `data layer: local-csv (...)` in every
report. To use Zetaris see [docs/zetaris_setup.md](docs/zetaris_setup.md): the gateway is on port 3000, only `SELECT` is
accepted, and the three tables live in the `open_agent` database (`ZETARIS_DB`).

Scenarios: `fgfr3_wtp53`, `egf_wtp53`, `egf_growthinh`, `fgfr3_growthinh`, `egf_tp53null`, `egf_mdm2amp`,
`fgfr3_rb1loss`, `growthinh_only` (no solution exists).

## Portability

`agent/llm.py` is the only file that knows the model provider (`complete(messages) -> LLMResponse`). The solver has no
LLM dependency, and `benchmark/run_benchmark.py --model <id>` reruns the same suite against another model.

## Credits and data provenance

Boolean model: E. Remy et al., *A modelling approach to explain mutually exclusive and co-occurring genetic alterations
in bladder tumorigenesis*, Cancer Research, 2015; booleanized with GINsim following G. Didier et al., J. Theor. Biol.,
2011; obtained from the PyBoolNet model repository (`remy_tumorigenesis`). The original header is kept in
`data/source/remy_tumorigenesis.bnet`. Check the upstream licence terms before redistributing the model files.
