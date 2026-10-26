"""CEGAR orchestrator: the LLM proposes knockouts, the solver verifies them, counterexamples refine the search.

    python -m agent.main --scenario fgfr3_wtp53

Three cooperating parts:
  * the LLM proposes knockout sets from biological reasoning and the counterexamples it has seen;
  * the solver verifies every set exactly and returns a surviving state when it fails;
  * a counterexample-guided search (solver/cegar.py) expands those surviving states, putting the LLM's failed
    proposals first. It is complete up to the size limit, so when it runs dry the absence of a solution is proved.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from solver.boolean_net import BooleanNetwork
from solver.cegar import CegarSearch
from solver.explain import step_entailed, steps_from_tree, ungrounded_mentions
from solver.knockout_opt import candidate_genes
from solver.verifier import (FORCED, SAFE, SURVIVES, Scenario, Verification, Verifier,
                             knockout_constants)

from . import prompts
from .llm import ChatClient, LLMError, NemotronClient, NoLLM, extract_json
from .logs import write_jsonl
from .memory import DEFAULT_PATH, HMem
from .sql_tool import run_sql, schema_text, summarise
from .tools_zetaris import DataLayer

EVIDENCE_RANK = {"approved": 0, "approved_other_indication": 1, "clinical": 2, "preclinical": 3, "none": 4}
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


@dataclass
class Attempt:
    round: int
    knockouts: list[str]
    verdict: str                      # FORCED | SURVIVES | INVALID | DUPLICATE
    via: str                          # solver | memory-replay | agent | cegar
    note: str = ""
    counterexample: dict | None = None


@dataclass
class Solution:
    knockouts: list[str]
    found_by: str                     # llm | cegar
    selective: bool = True
    toxic_in: list[str] = field(default_factory=list)
    drugs: list[dict] = field(default_factory=list)
    derivation: str = ""
    explanation: dict | None = None     # checked explanation, see _explain


@dataclass
class RunReport:
    scenario: str
    description: str
    data_source: str
    model: str
    memory_mode: str
    baseline: str
    solutions: list[Solution] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    rounds: int = 0
    solver_calls: int = 0              # every solver call of the run
    cegar_solver_calls: int = 0        # of which made by the counterexample-guided search
    sql_calls: int = 0                 # SQL queries the LLM ran on the data layer (run_sql tool)
    fallback_solver_calls: int = 0     # of which made while completing the search after the LLM rounds
    calls_to_first_solution: int | None = None
    first_solution_found_by: str = ""
    memory_refutations: int = 0        # LLM proposals refuted from memory
    cegar_replays: int = 0             # search nodes refuted from memory
    llm_calls: int = 0
    llm_provider: str = ""             # Meterless Nightshift, or a labelled fallback
    llm_models: list[str] = field(default_factory=list)   # models that actually handled the requests
    tokens: int = 0
    seconds: float = 0.0
    certified_infeasible: bool | None = None
    notes: list[str] = field(default_factory=list)


class CEGARAgent:
    def __init__(self, llm: ChatClient, data: DataLayer | None = None, memory_mode: str = "persistent",
                 memory_path=DEFAULT_PATH, max_size: int = 3, max_rounds: int = 6, per_round: int = 3,
                 target_solutions: int = 3, explain: bool = True, cegar: bool = True, fallback: bool = True,
                 cegar_budget: int = 40, sql_tool: bool = False, log: Callable[[str], None] = print,
                 on_event: Callable[[dict], None] | None = None, log_prefix: str | None = None):
        assert memory_mode in ("persistent", "session", "off")
        self.llm, self.data, self.log = llm, data or DataLayer(), log
        self.memory_mode, self.max_size, self.max_rounds = memory_mode, max_size, max_rounds
        self.per_round, self.target, self.explain = per_round, target_solutions, explain
        self.cegar, self.fallback, self.cegar_budget = cegar, fallback, cegar_budget
        self.on_event, self.log_prefix = on_event, log_prefix
        self._events: list[dict] = []          # evidence for logs/<scenario>-<run>.events.jsonl (search steps left out)
        self.sql_tool, self._data_notes = sql_tool, "none"
        self.rows = self.data.network_rows()
        self.net = BooleanNetwork.from_rows(self.rows)
        self.verifier = Verifier(self.net)
        self.memory = HMem(self.net, memory_path if memory_mode == "persistent" else None, use_hmem=memory_mode != "off")
        self.run_id = uuid.uuid4().hex[:8]
        self._tokens = 0
        self._llm_calls = 0
        self._providers: set[str] = set()
        self._models: set[str] = set()
        self._t0 = time.perf_counter()

    def _emit(self, kind: str, **data) -> None:
        """Structured progress event for UIs and recordings (never affects the run)."""
        event = {"type": kind, "t": round(time.perf_counter() - self._t0, 2), **data}
        if not kind.startswith("search_"):
            self._events.append(event)
        if self.on_event is not None:
            self.on_event(event)

    # -- LLM plumbing --------------------------------------------------------------------------
    def _ask(self, system: str, user: str, max_tokens: int = 2048, purpose: str = "proposals") -> dict:
        """One JSON reply; a reply cut off by the token limit is retried once with twice the room."""
        for attempt in range(2):
            reply = self.llm.complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                      max_tokens=max_tokens * (attempt + 1))
            self._llm_calls += 1
            self._tokens += reply.prompt_tokens + reply.completion_tokens
            # which provider and which model handled this request (Nightshift reports the routed model)
            provider = getattr(reply, "provider", "")
            model = getattr(reply, "routed_model", "") or getattr(self.llm, "model", "")
            self._providers.add(provider)
            self._models.add(model)
            self._emit("llm_call", purpose=purpose, provider=provider, model=model,
                       latency=getattr(reply, "latency", 0.0), tokens=reply.prompt_tokens + reply.completion_tokens)
            try:
                return extract_json(reply.content)
            except LLMError:
                if attempt == 1 or getattr(reply, "finish_reason", "stop") != "length":
                    raise
        raise LLMError("unreachable")

    # -- one proposal --------------------------------------------------------------------------
    def _check(self, scenario: Scenario, kos: tuple[str, ...], rnd: int, report: RunReport) -> Attempt:
        if self.memory_mode != "off":
            ref = self.memory.refutes(scenario, kos)
            if ref is not None:
                report.memory_refutations += 1
                ce = {k: ref[k] for k in ("kind", "phenotype", "active_genes", "inactive_genes") if k in ref}
                self.memory.remember(scenario, kos, SURVIVES, ce, self.run_id)
                return Attempt(rnd, list(kos), SURVIVES, "memory-replay",
                               "refuted by a stored counterexample, no solver call", ce)
        res = self.verifier.verify(scenario, kos)
        self.memory.record(scenario, kos, res, self.run_id)
        self.memory.remember(scenario, kos, res.verdict, res.counterexample, self.run_id)
        return Attempt(rnd, list(kos), res.verdict, "solver", counterexample=res.counterexample)

    def _explain(self, scenario: Scenario, kos: tuple[str, ...], proof: Verification,
                 baseline: Verification, sol: "Solution", toxic: list[str]) -> dict | None:
        """LLM-worded explanation built only from solver-proven steps, then checked.

        Each chosen step is re-checked against the model's rule, and every gene or node named in the
        wording must belong to the chosen steps. Failures are kept and flagged, not hidden.
        """
        net = self.net
        steps = steps_from_tree(proof.trees[0])
        if not steps:
            return None
        known = knockout_constants(net, scenario, kos)
        origin = {n: "scenario" for n in scenario.fixed} | {n: "knockout" for n in net.nodes_of(kos)}
        for st in steps:
            st["entailed"] = step_entailed(net, st, known)
        base = baseline.counterexample["phenotype"] if baseline.counterexample else "n/a"
        try:
            reply = self._ask(prompts.EXPLAINER_SYSTEM, prompts.EXPLAINER_USER.format(
                description=scenario.description, knockouts=list(kos), baseline=base,
                selectivity=("selective: the resting normal cell survives" if not toxic else
                             f"NOT selective: also kills normal cells in {toxic}"),
                drugs="; ".join(f"{d['gene']}: {d['evidence_level'] or 'unknown'}" for d in sol.drugs),
                steps=prompts.format_steps(steps, origin)), max_tokens=1800, purpose="explanation")
        except LLMError as exc:
            self.log(f"  (explanation skipped: {exc})")
            return None
        by_id = {st["id"]: st for st in steps}
        chosen = []
        for item in reply.get("steps") or []:
            try:
                st = by_id[int(item["id"])]
            except (KeyError, TypeError, ValueError):
                continue
            chosen.append((st, str(item.get("text", ""))))
        allowed = {n for st, _ in chosen for n in [st["node"], *[p for p, _ in st["premises"]]]} | set(known)
        out_steps = []
        for st, text in chosen:
            stray = ungrounded_mentions(net, text, allowed)
            out_steps.append({"id": st["id"], "text": text, "node": st["node"], "value": st["value"],
                              "premises": st["premises"], "entailed": st["entailed"], "stray_mentions": stray,
                              "ok": st["entailed"] and not stray})
        ok = sum(s["ok"] for s in out_steps)
        # The headline is assembled from verified facts only; free LLM prose is limited to the checked steps.
        summary = (f"Knocking out {' + '.join(kos)} forces committed apoptosis (Apoptosis_high=1) in every long-term "
                   f"state of this scenario. " + ("The knockout is selective: a resting normal cell exposed to the "
                                                   "same radiation survives." if not toxic else
                                                   f"It is NOT selective: it also kills normal cells ({', '.join(toxic)}).")
                   + f" The {len(out_steps)} steps below are each checked against the model's update rules.")
        return {"summary": summary, "steps": out_steps,
                "caveats": [str(c) for c in (reply.get("caveats") or [])],
                "steps_ok": ok, "steps_total": len(out_steps),
                "faithful": bool(out_steps) and ok == len(out_steps)}

    def _solution(self, scenario: Scenario, kos: tuple[str, ...], safety: list[Scenario],
                  drugs: dict[str, dict], found_by: str, baseline: Verification) -> Solution:
        toxic = [s.name for s in safety if self.verifier.verify(s, kos).verdict != SAFE]
        proof = self.verifier.verify(scenario, kos)
        sol = Solution(list(kos), found_by, not toxic, toxic,
                       [{"gene": g, **{k: drugs.get(g, {}).get(k, "") for k in
                                       ("druggable", "evidence_level", "example_agents")}} for g in kos],
                       proof.explanation)
        if self.explain and proof.trees:
            sol.explanation = self._explain(scenario, kos, proof, baseline, sol, toxic)
        return sol

    def _proposer_prompt(self, scenario: Scenario, candidates: list[str], drug_rows: list[dict],
                         history: list[str], n: int, memory: str) -> str:
        return prompts.PROPOSER_USER.format(
            sid=scenario.name, description=scenario.description,
            fixed="; ".join(f"{k}={v}" for k, v in scenario.fixed.items()),
            goal="; ".join(f"{k}={v}" for k, v in scenario.goal.items()),
            candidates=", ".join(candidates), max_size=self.max_size,
            rules=prompts.format_rules(self.rows), drugs=prompts.format_drugs(drug_rows, candidates),
            memory=memory, data=self._data_notes, history="\n".join(history) or "none yet", n=n)

    def _explore_data(self, scenario: Scenario, candidates: list[str], report: RunReport) -> str:
        """Let the LLM query the Zetaris data layer with run_sql before it proposes anything (at most two LLM turns)."""
        previous, notes = "", []
        for turn in range(2):
            try:
                reply = self._ask(prompts.SQL_SYSTEM, prompts.SQL_USER.format(
                    sid=scenario.name, description=scenario.description, candidates=", ".join(candidates),
                    schema=schema_text(self.data.client.database), max_queries=2, previous=previous),
                    purpose="sql")
            except LLMError as exc:
                report.notes.append(f"sql tool: {exc}")
                break
            failed = []
            for q in (reply.get("queries") or [])[:2]:
                if not isinstance(q, dict) or not q.get("sql"):
                    continue
                purpose = str(q.get("purpose", "lookup"))[:120]
                res = run_sql(self.data, str(q["sql"]))
                report.sql_calls += 1
                self._emit("sql_call", purpose=purpose, sql=res["sql"], ok=res["ok"], n_rows=len(res["rows"]),
                           rows=res["rows"][:8], error=res["error"], turn=turn + 1)
                self.log(f"    sql [{'ok' if res['ok'] else 'fail'}] {purpose}")
                notes.append(summarise(res, purpose))
                if not res["ok"]:
                    failed.append(f"- {res['sql']}\n  error: {res['error']}")
            if not failed or turn == 1 or self.data.source != "zetaris":
                break
            previous = "Your previous queries failed, fix them:\n" + "\n".join(failed) + "\n"
        return "\n".join(notes) if notes else "none"

    def propose_only(self, scenario_id: str, n: int = 5) -> tuple[list[tuple[str, ...]], bool]:
        """One LLM call and no verification: what the model claims on its own (benchmark baseline)."""
        scenario = Scenario.from_row(self.data.scenario(scenario_id))
        candidates = candidate_genes(self.verifier, scenario)
        canonical = {g.lower(): g for g in candidates}
        prompt = self._proposer_prompt(scenario, candidates, self.data.drug_ranking_join(), [], n,
                                       "No earlier experience with this scenario.")
        reply = self._ask(prompts.PROPOSER_SYSTEM, prompt)
        out = []
        for prop in reply.get("proposals") or []:
            names = prop.get("knockouts") if isinstance(prop, dict) else None
            if isinstance(names, list):
                kos = tuple(sorted({canonical[str(g).lower()] for g in names if str(g).lower() in canonical}))
                if kos and len(kos) <= self.max_size and kos not in out:
                    out.append(kos)
        return out[:n], bool(reply.get("give_up"))

    # -- main loop -----------------------------------------------------------------------------
    def run(self, scenario_id: str) -> RunReport:
        t0 = time.perf_counter()
        calls0 = self.verifier.calls
        scenario = Scenario.from_row(self.data.scenario(scenario_id))
        safety = [Scenario.from_row(r) for r in self.data.scenarios() if r["kind"] == "safety"]
        drug_rows = self.data.drug_ranking_join()
        drugs = {r["gene"]: r for r in drug_rows}
        candidates = candidate_genes(self.verifier, scenario)
        baseline = self.verifier.verify(scenario, [])
        report = RunReport(scenario.name, scenario.description, self.data.source,
                           getattr(self.llm, "model", "?"), self.memory_mode, baseline.verdict)
        self.log(f"[{scenario.name}] {scenario.description}\n  data layer: {self.data.source}; baseline: {baseline.verdict}")
        self._t0 = t0
        self._events = []
        self._emit("start", scenario=scenario.name, description=scenario.description, fixed=dict(scenario.fixed),
                   goal=dict(scenario.goal), candidates=candidates, baseline=baseline.verdict,
                   baseline_counterexample=baseline.counterexample, data_source=self.data.source,
                   model=report.model, max_size=self.max_size, memory_mode=self.memory_mode)
        if baseline.verdict == FORCED:
            report.notes.append("apoptosis is already forced without any knockout")
            return self._finish(report, t0, calls0, None)

        if self.sql_tool:
            self._data_notes = self._explore_data(scenario, candidates, report)
        search = None
        if self.cegar:
            search = CegarSearch(
                self.verifier, scenario, self.max_size, candidates,
                refute=(lambda sc, kos: self.memory.refutes(sc, kos)) if self.memory_mode != "off" else None,
                on_failure=lambda kos, res: self.memory.record(scenario, kos, res, self.run_id),
                on_event=lambda ev: self._emit("search_" + ev["type"], **{k: v for k, v in ev.items() if k != "type"}))

        history: list[str] = []
        tried: set[tuple[str, ...]] = set()
        canonical = {g.lower(): g for g in candidates}
        found: dict[tuple[str, ...], Solution] = {}

        def register(kos: tuple[str, ...], found_by: str) -> None:
            if report.calls_to_first_solution is None:
                report.calls_to_first_solution = self.verifier.calls - calls0
                report.first_solution_found_by = found_by
            minimal = self._minimise(scenario, kos)
            if minimal != kos:
                self.log(f"      shrunk to {list(minimal)}")
                self._emit("shrunk", knockouts=list(kos), minimal=list(minimal))
            if minimal not in found:
                found[minimal] = self._solution(scenario, minimal, safety, drugs, found_by, baseline)
                self._emit("solution", **asdict(found[minimal]))

        def absorb(new, rnd: int, stage: str) -> None:
            for f in new:
                report.attempts.append(Attempt(rnd, list(f.knockouts), FORCED, "cegar", stage))
                self.memory.remember(scenario, f.knockouts, FORCED, None, self.run_id)
                self.log(f"    search found {list(f.knockouts)}")
                register(f.knockouts, "cegar")

        for rnd in range(1, self.max_rounds + 1):
            report.rounds = rnd
            recall = ("No earlier experience with this scenario." if self.memory_mode == "off"
                      else self.memory.recall_text(scenario))
            prompt = self._proposer_prompt(scenario, candidates, drug_rows, history, self.per_round, recall)
            self._emit("round", n=rnd, prompt_chars=len(prompt))
            if self.memory_mode != "off":      # what the official H-MEM engine put into this prompt
                self._emit("memory_recall", round=rnd, **getattr(self.memory, "last_recall", {}))
            reply: dict = {}
            try:
                reply = self._ask(prompts.PROPOSER_SYSTEM, prompt)
            except LLMError as exc:
                report.notes.append(f"round {rnd}: {exc}")
                self.log(f"  round {rnd}: LLM error: {exc}")
                self._emit("llm_error", round=rnd, message=str(exc))
            proposals = reply.get("proposals") or []
            self._emit("llm_reply", round=rnd, give_up=bool(reply.get("give_up")),
                       proposals=[{"knockouts": p.get("knockouts"), "rationale": p.get("rationale", "")}
                                  for p in proposals if isinstance(p, dict)])
            self.log(f"  round {rnd}: {len(proposals)} proposal(s)")
            for prop in proposals[: self.per_round]:
                names = prop.get("knockouts") if isinstance(prop, dict) else None
                if not isinstance(names, list) or not names:
                    continue
                bad = [str(n) for n in names if str(n).lower() not in canonical]
                kos = tuple(sorted({canonical[str(n).lower()] for n in names if str(n).lower() in canonical}))
                idx = len(report.attempts) + 1
                if bad or not kos or len(kos) > self.max_size:
                    why = (f"unknown genes {bad}" if bad else f"needs 1 to {self.max_size} genes")
                    report.attempts.append(Attempt(rnd, list(names), "INVALID", "agent", why))
                    history.append(f"Attempt {idx}: {names} -> INVALID ({why})")
                    self._emit("proposal", round=rnd, knockouts=list(names), verdict="INVALID", via="agent", note=why)
                    continue
                if kos in tried:
                    report.attempts.append(Attempt(rnd, list(kos), "DUPLICATE", "agent", "already tried"))
                    history.append(f"Attempt {idx}: {list(kos)} -> DUPLICATE (already tried, propose something new)")
                    self._emit("proposal", round=rnd, knockouts=list(kos), verdict="DUPLICATE", via="agent",
                               note="already tried")
                    continue
                tried.add(kos)
                att = self._check(scenario, kos, rnd, report)
                report.attempts.append(att)
                history.append(prompts.format_attempt(idx, kos, att.verdict, att.counterexample, att.via))
                self.log(f"    {list(kos)} -> {att.verdict} ({att.via})")
                self._emit("proposal", round=rnd, knockouts=list(kos), verdict=att.verdict, via=att.via,
                           note=att.note, counterexample=att.counterexample,
                           rationale=next((p.get("rationale", "") for p in proposals if isinstance(p, dict)
                                           and sorted(str(x) for x in (p.get("knockouts") or [])) == list(kos)), ""))
                if att.verdict == FORCED:
                    register(kos, "llm")
                elif att.verdict == SURVIVES and att.counterexample and search is not None:
                    search.prioritise(kos, att.counterexample["active_genes"])

            if search is not None and len(found) < self.target:
                absorb(search.advance(self.cegar_budget, want=len(search.solutions) + max(1, self.target - len(found))),
                       rnd, "budgeted")
                history.append(f"Solver-side search after round {rnd}: {search.calls} solver calls so far, "
                               f"{len(search.frontier)} failed sets left to expand, "
                               + (f"working sets found: {[list(s.knockouts) for s in search.solutions]}"
                                  if search.solutions else "no working set yet") + ".")
            self._emit("round_end", n=rnd, found=len(found), solver_calls=self.verifier.calls - calls0)
            if len(found) >= self.target or reply.get("give_up"):
                break

        if search is not None and self.fallback and len(found) < self.target:
            self.log("  completing the counterexample-guided search")
            c0 = search.calls
            absorb(search.advance(None, want=len(search.solutions) + max(1, self.target - len(found))),
                   report.rounds, "completion")
            report.fallback_solver_calls = search.calls - c0
            if not found:
                report.certified_infeasible = search.proved_infeasible
        report.solutions = sorted(found.values(), key=self._rank)
        if search is not None:
            report.cegar_solver_calls, report.cegar_replays = search.calls, search.replays
        if self.memory_mode == "persistent":
            added = self.memory.consolidate(self.llm)
            self.memory.save()
            if added:
                report.notes.append(f"memory: {added} new lesson(s) mined into H-MEM")
            info = self.memory.summary()
            if info["available"]:
                report.notes.append(f"H-MEM: {info['records']} records {info['layers']}, ledger {info['ledger']}, "
                                    f"{info['conflicts_detected']} conflict(s), sleep preview {info['sleep_preview']}")
            else:
                report.notes.append(f"H-MEM engine unavailable ({info['reason']}); only the counterexample cache was used")
        return self._finish(report, t0, calls0, search)

    def _minimise(self, scenario: Scenario, kos: tuple[str, ...]) -> tuple[str, ...]:
        """Smallest forced subset of ``kos`` (the effect is not monotone, so every proper subset is tried)."""
        for size in range(1, len(kos)):
            for sub in itertools.combinations(kos, size):
                if self.verifier.verify(scenario, sub).verdict == FORCED:
                    return self._minimise(scenario, sub)
        return kos

    @staticmethod
    def _rank(sol: Solution):
        drug = sum(EVIDENCE_RANK.get(d["evidence_level"] or "none", 4) for d in sol.drugs)
        return (not sol.selective, len(sol.knockouts), drug, sol.knockouts)

    def _write_logs(self, report: RunReport) -> None:
        """Evidence for judges: the ordered events of the run and the H-MEM audit ledger, as JSONL under logs/."""
        prefix = self.log_prefix or f"{report.scenario}-{self.run_id}"
        write_jsonl(f"{prefix}.events.jsonl", self._events)
        eng = self.memory.engine if self.memory_mode != "off" else None
        if eng is not None:
            try:
                write_jsonl(f"{prefix}.hmem-ledger.jsonl", eng.ledger_all())
            except Exception:       # a log must never break a run
                pass

    def _finish(self, report: RunReport, t0: float, calls0: int, search) -> RunReport:
        report.solver_calls = self.verifier.calls - calls0
        report.llm_calls, report.tokens = self._llm_calls, self._tokens
        if self.memory_mode != "off":
            self._emit("memory_state", **self.memory.summary())
        report.llm_provider = "+".join(sorted(p for p in self._providers if p))
        report.llm_models = sorted(m for m in self._models if m)
        report.seconds = round(time.perf_counter() - t0, 1)
        self._emit("done", report=asdict(report))
        self._write_logs(report)
        return report


def to_markdown(r: RunReport) -> str:
    out = [f"# Ranked knockout experiments: {r.scenario}", "", f"_{r.description}_", ""]
    if r.certified_infeasible:
        out.append("**No knockout set of the allowed size forces apoptosis.** The counterexample-guided search is "
                   "complete up to the size limit and ran out of candidates, so this is a proof, not a failure to "
                   "find one.\n")
    for i, s in enumerate(r.solutions, 1):
        tag = "selective" if s.selective else f"NOT selective (also kills normal cells: {', '.join(s.toxic_in)})"
        out.append(f"## {i}. Knock out {' + '.join(s.knockouts)}  ({tag}; found by {s.found_by})")
        for d in s.drugs:
            out.append(f"- {d['gene']}: druggable={d['druggable'] or 'unknown'}, evidence={d['evidence_level'] or 'unknown'}"
                       + (f" ({d['example_agents']})" if d.get('example_agents') else ""))
        if s.explanation:
            ex = s.explanation
            out += ["", ex["summary"], ""]
            for k, st in enumerate(ex["steps"], 1):
                prem = ", ".join(f"{n}={v}" for n, v in st["premises"])
                mark = "verified" if st["ok"] else ("NOT entailed" if not st["entailed"] else
                                                    "mentions " + ", ".join(st["stray_mentions"]))
                out.append(f"{k}. [{mark}] {st['text']}  ({prem} => {st['node']}={st['value']})")
            out.append("")
            out.append(f"Explanation check: {ex['steps_ok']}/{ex['steps_total']} steps verified against the model rules")
            if ex["caveats"]:
                out += ["", "Caveats: " + "; ".join(ex["caveats"])]
        if s.derivation:
            out += ["", "Solver derivation (why apoptosis holds):", "```", s.derivation, "```"]
        out.append("")
    out += ["---", f"model {r.model} | data layer {r.data_source} | memory {r.memory_mode} | rounds {r.rounds} | "
            f"solver calls {r.solver_calls} (search {r.cegar_solver_calls}, replayed from memory {r.cegar_replays}) | "
            f"LLM calls {r.llm_calls} via {r.llm_provider or 'none'} ({', '.join(r.llm_models) or 'no model'}) | tokens {r.tokens} | {r.seconds}s"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--max-size", type=int, default=3)
    ap.add_argument("--max-rounds", type=int, default=6)
    ap.add_argument("--per-round", type=int, default=3)
    ap.add_argument("--solutions", type=int, default=3)
    ap.add_argument("--memory", choices=("persistent", "session", "off"), default="persistent")
    ap.add_argument("--no-explain", action="store_true")
    args = ap.parse_args()

    try:
        llm: ChatClient = NemotronClient()
    except LLMError as exc:
        print(f"No LLM: {exc}")
        print("Continuing with the symbolic search only.")
        llm = NoLLM(str(exc))
    agent = CEGARAgent(llm, memory_mode=args.memory, max_size=args.max_size,
                       max_rounds=args.max_rounds, per_round=args.per_round, target_solutions=args.solutions,
                       explain=not args.no_explain, sql_tool=True)
    report = agent.run(args.scenario)
    RUNS_DIR.mkdir(exist_ok=True)
    out = RUNS_DIR / f"{report.scenario}-{agent.run_id}.json"
    out.write_text(json.dumps(asdict(report), indent=1), encoding="utf-8")
    print("\n" + to_markdown(report) + f"\n\n(report saved to {out})")


if __name__ == "__main__":
    main()
