# Pitch, demo script and honest Q&A

Open Agent Hackathon 2026, Track 02 "The Agent That Can Explain Why". Deadline 27 Oct 2026, 23:45 UTC.

## One line
An LLM proposes gene knockouts for a radiation-surviving tumour cell; an exact solver proves or refutes every proposal;
the explanation is cut into proof steps that are re-checked against the model's rules.

## Three numbers, all measured (benchmark/RESULTS-nemotron-lightning.md, 8 scenarios, exhaustive ground truth)
| claim | number |
|---|---|
| The LLM alone is unreliable | **91%** of its proposed knockout sets are wrong; it invents a solution for the one scenario where none exists |
| Verification plus complete search is cheap | **34x** fewer solver calls than brute force (84 vs 2,876), no LLM needed |
| It can say "impossible" and prove it | **56** solver calls to prove no set of up to 4 genes works (brute force: 10,903) |
| Explanations are checkable | **96.8%** of the steps the LLM chose stayed inside the proof (387 of 400) |

## What to say about the science (and what not to)
Say: "On a published bladder-tumorigenesis model, a tumour with working p53 survives radiation by p53-p21 arrest. The
system found that removing that brake (TP53, p21, or RB1+RBL2) forces apoptosis, and that the effect depends on growth
signalling, so a resting normal cell survives. For one scenario it proved that no knockout of up to 4 genes works."

Do not say: "the only way out is losing p53" (false: there are three minimal solutions), "it exposes gaps in medical
research" (it shows limits of one model), "mathematically safe" (it is proven inside the model, not for a patient).

Say the limits yourself, before a judge does: the answers are loss of tumour suppressors (no drug), no DNA-damage-response
drug target appears in any solution although CHK1 inhibitors are studied as radiosensitisers (so the model misses
mechanisms), one model, Boolean abstraction, no dose or time, ground truth comes from the same model.

## Sponsor use (evidence in the repo)
- **NVIDIA Nemotron**: direct REST calls (`agent/llm.py`) for proposals and for wording explanations. Finding worth
  mentioning: with thinking on, the model did not answer within 16,000 tokens (268 s); thinking off answers in about 2 s.
  The 550B model wrote cleaner explanations (99.4% of steps clean vs 94.6%) but did not propose better knockouts.
- **Zetaris**: the agent reads the network rules, scenarios and drug evidence with SQL through the Zetaris REST gateway
  (`agent/tools_zetaris.py`, database `open_agent`, three tables). The UI shows the data-layer chip; solutions are kept out
  of the tables on purpose so the agent cannot read the answers.
- **Meterless H-MEM**: the official engine is vendored unmodified (`hmem/`, commit and SHA-256 per file in
  `UPSTREAM.json`), the official conformance suite passes 13/13, and the agent stores, recalls, grades and audits its
  knowledge through it (`agent/memory.py`). Dream proposals are never auto-approved.

## 3-minute demo (python ui/server.py, http://localhost:8765)
1. **0:00 Problem (20 s).** Explore tab, scenario "FGFR3 . p53 wild-type": "after radiation this tumour survives" (point at
   CELL SURVIVES and the growth-arrest bar).
2. **0:20 Explore (50 s).** Click `MDM2`: still survives; the panel names the genes keeping it alive. Click `TP53`: APOPTOSIS
   FORCED, then scroll the proof steps ("each step is a rule of the model, re-checked"). Mention selectivity.
3. **1:10 Search (50 s).** Search tab, scenario "Quiescent": press Run. "No solution exists: 139 calls instead of 10,903. A proof,
   not a failure to find one." Then run "EGF . p53 wild-type" and show the tree and the solver-call counter.
4. **2:00 Agent (40 s).** Agent tab, Replay: LLM proposal with its rationale, counterexample fed back, the search, a verified solution
   with checked steps. "The LLM can be wrong; the solver is the judge."
5. **2:40 Benchmark and limits (20 s).** Benchmark tab: 91% / 34x / 56 / 97%, then the amber "honest reading" box.

Tips: record the replay rather than a live LLM run (no latency, no API surprises); the chip must read Zetaris
(`bash scripts/zetaris_up.sh` if it shows local CSV); switch EN/EL in the header if the audience prefers Greek.

## Deck outline (7 slides)
1. Problem: radiation-surviving cells; LLMs hallucinate interventions.
2. Idea: propose, prove, explain (diagram from the How-it-works tab).
3. Exact analysis and a search that cannot miss (one sentence on completeness).
4. Demo screenshot: Explore with proof steps.
5. Results: the four numbers above.
6. Sponsors: Nemotron, Zetaris, H-MEM (one line each, with the conformance 13/13).
7. Honest limits and roadmap: symbolic backend for larger networks (measured limit about 21 free nodes), validation
   against published knockouts and CRISPR screens, tumour-profile scenarios.

## Questions to expect
- **Why an LLM at all?** "On this network the search is symbolic and needs no LLM; we measured that. The LLM gives the
  natural-language interface and the wording of explanations, and every claim it makes goes through the solver."
- **Does it scale?** "The exact engine handles up to about 21 free nodes after reduction. A 53-node model returned UNKNOWN,
  and we say so. Bigger networks need a symbolic attractor backend; the search, memory and UI do not change."
- **Is this medically meaningful?** "It is an in-silico hypothesis tool for prioritising experiments, validated only inside
  one model so far. The next step is checking its predictions against published data."
- **Is the memory really H-MEM?** "The engine is the official reference, unmodified and checksummed, and it passes the
  official conformance suite. The counterexample cache next to it is solver-specific and we label it as such."
