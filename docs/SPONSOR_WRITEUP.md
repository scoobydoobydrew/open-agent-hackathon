# Sponsor integration write-up (paste into the submission form)

**Project:** a verified agent that proposes gene knockouts for a radiation-surviving tumour cell, proves or refutes each
proposal with an exact solver, and explains the result with proof steps that are re-checked against the model.

**Zetaris (data layer).** The agent does not carry the biology in its prompt; it reads it live. The network rules (35 Boolean
update rules from a published bladder-tumorigenesis model), the scenario definitions and a hand-curated drug-evidence table
sit in three tables of the `open_agent` database, ingested from CSV files. The agent queries them over the Zetaris REST
gateway with SQL in two ways: (1) the **LLM calls a `run_sql` tool** that it writes SELECTs for (for example "which candidate
genes have an approved or clinical drug"), with read-only validation, a table allow-list and a row limit; (2) the
orchestrator runs a **single SQL JOIN** between the network table and the drug table to rank candidates. The answers to the
benchmark scenarios are deliberately kept out of the tables so the agent cannot read them. The UI shows whether the
data layer is Zetaris or the local CSV fallback, and the agent says so in every report.

**NVIDIA Nemotron (runtime LLM) and Meterless.** Nemotron proposes knockouts, writes the SQL for the data layer, and words the
explanations; it is called over an OpenAI-compatible REST endpoint (Meterless' endpoint when configured, NVIDIA's otherwise).
We measured it: with thinking on, the model did not answer within 16,000 tokens (268 s), with thinking off it answers in about
2 s, so thinking is off; the 550B model wrote cleaner explanations (99.4% of steps clean vs 94.6%) but proposed no better.
From **Meterless** we use the **H-MEM** engine: the official reference implementation and conformance suite are vendored
unmodified (SHA-256 per file checked by a test; conformance 13/13), and the agent stores each verified result as a record
with source, confidence and provenance, retrieves it with the canonical ranking for the next prompt, grades recalled facts
with the exact feedback deltas and keeps an append-only ledger. Dream proposals are never approved automatically.

**Development tool.** Written with Claude Code (Anthropic). [Add here if you also used Cursor, and which models.]

**What the numbers say (8 scenarios, exhaustive ground truth).** The LLM alone proposes a wrong knockout set 91% of the time
and invents a solution for the one scenario that has none. With the solver and the complete counterexample-guided search the
system is never wrong, needs 34x fewer solver calls than brute force, and proves that no knockout of up to 4 genes works in
56 calls (brute force: 10,903). 96.8% of the explanation steps the LLM chose stayed inside the proof.

**Honest limits.** One published model, Boolean abstraction, results are in-silico hypotheses. The exact engine handles about 21
free nodes after reduction; a 53-node model returned UNKNOWN. In this network the search itself is symbolic and needs no LLM.
