"""Prompt construction for the knockout proposer and the explainer."""
from __future__ import annotations

from typing import Mapping, Sequence

PROPOSER_SYSTEM = """You are a cancer systems-biology agent working with a formally verified Boolean model of the
DNA-damage response (p53, ATM/CHK, RB/E2F, growth-factor signalling, apoptosis).
Your job: propose minimal sets of gene knockouts that force the tumour cell into committed apoptosis after radiation.

A formal solver checks every proposal exactly. It either proves the set works or returns a counterexample: a long-term
state (attractor) in which the cell still survives. Use the counterexamples: they show which genes keep the cell alive.

How to use the counterexamples:
- A surviving state is kept alive by the genes listed as ACTIVE in it. A knockout set can only break that state if
  it contains at least one of those active genes. Genes listed as INACTIVE are already off there: knocking them out
  changes nothing.
- Strategy: start with 1 or 2 genes. After a failure, take the failed set and change it using the ACTIVE genes of its
  surviving state (extend it with one, or swap one in). Do not jump to unrelated large sets.
- Mind the double role of some genes: a knockout of a gene that holds a pathway in check can switch that pathway on.

Rules:
- Use only gene names from the candidate list, written exactly as given.
- Prefer small sets. A set is only useful if no smaller subset already works, so try 1 and 2 genes before 3.
- Never repeat a set that was already tried.
- Reply with JSON only, no other text."""

PROPOSER_USER = """SCENARIO {sid}: {description}
Fixed conditions (node=value): {fixed}
Goal: in EVERY long-term state of the perturbed cell, {goal} (committed apoptosis).
A knockout clamps every level of the gene to 0 (for example E2F1 sets E2F1_medium and E2F1_high to 0).
Candidate genes: {candidates}
Maximum knockout set size: {max_size}

Boolean update rules of the model (node: rule; ! = NOT, & = AND, | = OR; asynchronous updates):
{rules}

Druggability of the candidate genes (from the data layer):
{drugs}

Results of the SQL queries you ran on the Zetaris data layer:
{data}

Memory from earlier runs:
{memory}

Attempts so far in this run:
{history}

Propose up to {n} NEW knockout sets, most promising first. Reply with exactly this JSON:
{{"proposals": [{{"knockouts": ["GENE", ...], "rationale": "<why this should break the surviving state>"}}], "give_up": false}}
Set "give_up" to true only if you believe no set of at most {max_size} genes can work."""

EXPLAINER_SYSTEM = """You explain verified results of a Boolean-network analysis to a biologist.
You receive numbered derivation steps produced by a solver. Every step is a proven fact: its premises force its
conclusion through the model's rule. You may ONLY tell the story with these steps. Do not add pathway claims,
genes or mechanisms that are not in the steps you choose. Reply with JSON only."""

EXPLAINER_USER = """Scenario: {description}
Verified knockout set: {knockouts}  (the solver proved apoptosis in every long-term state)
Without the knockout the cell survives like this: {baseline}
Selectivity check (same radiation, resting normal cell): {selectivity}
Drug evidence: {drugs}

Derivation steps (causes come before effects; [knockout] and [scenario] mark what was fixed from outside):
{steps}

Choose at most 8 steps that tell the story from the knockout to apoptosis, in causal order, and say each in one plain
sentence. Each sentence must name the premises that actually cause the conclusion (look at the "because" part), and
must not mention any gene that is not in that step. Reply with exactly this JSON:
{{"steps": [{{"id": <step number>, "text": "<one sentence>"}}],
  "caveats": ["<limitation>"]}}"""


def format_steps(steps: Sequence[Mapping], origin: Mapping[str, str]) -> str:
    def lit(n: str, v: int) -> str:
        return f"{n}={v}" + (f" [{origin[n]}]" if n in origin else "")
    return "\n".join(f"[{st['id']}] {st['node']}={st['value']} because "
                     + ", ".join(lit(n, v) for n, v in st["premises"]) + f"    (rule: {st['rule']})"
                     for st in steps)


def format_rules(rows: Sequence[Mapping[str, str]]) -> str:
    return "\n".join(f"{r['node']}: {r['rule']}" + ("   [input]" if r["role"] == "input" else "") for r in rows)


def format_drugs(rows: Sequence[Mapping[str, str]], genes: Sequence[str]) -> str:
    by_gene = {r["gene"]: r for r in rows}
    out = []
    for g in genes:
        r = by_gene.get(g, {})
        evidence = r.get("evidence_level") or "unknown"
        agents = f" ({r['example_agents']})" if r.get("example_agents") else ""
        out.append(f"{g}: druggable={r.get('druggable') or 'unknown'}, evidence={evidence}{agents}")
    return "\n".join(out)


def _trim(text: str, max_lines: int = 14) -> str:
    lines = text.splitlines()
    return "\n".join(lines[:max_lines] + ([f"... ({len(lines) - max_lines} more lines)"] if len(lines) > max_lines else []))


def format_attempt(i: int, knockouts: Sequence[str], verdict: str, ce: Mapping | None, via: str = "") -> str:
    head = f"Attempt {i}: knockout {list(knockouts) or 'none'} -> {verdict}" + (f" [{via}]" if via else "")
    if verdict != "SURVIVES" or not ce:
        return head
    lines = [head, f"  survival state ({ce['kind']}): phenotype {ce['phenotype']}"]
    lines.append(f"  genes still ACTIVE there: {', '.join(ce['active_genes']) or 'none'}")
    lines.append(f"  genes already INACTIVE there (adding them cannot help): {', '.join(ce['inactive_genes']) or 'none'}")
    if ce.get("oscillating_nodes"):
        lines.append(f"  oscillating nodes: {', '.join(ce['oscillating_nodes'][:12])}")
    if ce.get("why_goal_fails"):
        lines.append("  why apoptosis is not reached:\n" + "\n".join("    " + l for l in _trim(ce["why_goal_fails"]).splitlines()))
    return "\n".join(lines)


SQL_SYSTEM = """You are a cancer systems-biology agent. Before proposing knockouts you may look things up in a Zetaris data
layer with SQL. You never answer data questions from memory: you ask the database. Reply with JSON only."""

SQL_USER = """SCENARIO {sid}: {description}
Candidate genes for knockout: {candidates}

{schema}

Write at most {max_queries} SELECT queries whose results would help you choose knockouts (for example: which candidate
genes have a drug that can inhibit them, and how strong the evidence is; or what regulates a gene). Each query must
read only the tables above, use their full names and be a single SELECT (joins between the tables are welcome).
{previous}Reply with exactly this JSON:
{{"queries": [{{"purpose": "<what you want to learn>", "sql": "<SELECT ...>"}}]}}"""
