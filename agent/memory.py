"""Agent memory: the official H-MEM engine plus a solver-specific counterexample cache.

H-MEM (Meterless spec, AGENTS.md) is implemented by the vendored, unmodified reference in ``hmem/reference`` and reached
through ``agent/hmem_engine.py``. The agent's knowledge goes through its services:

  mining      an LLM-mined lessons list (strict JSON array, tolerant parsing, model-free fallback) -> records
  store       every verified proposal and solution becomes a record with the mandatory source, confidence, provenance
  retrieval   the canonical hybrid ranking and the domain-grouped reinjection block that goes into the next prompt
  feedback    helpful / not_helpful / wrong with the exact deltas, driven by whether a recalled fact held up
  ledger      append-only audit of every create / read / feedback (and sleep, dream, conflict actions)
  conflicts / sleep / dreaming   exposed with the spec's approval boundary: dreams are never approved automatically

``HMem`` keeps one extra structure that is NOT part of the H-MEM spec: the counterexample cache ("refuters"). A stored
surviving state is replayed against new proposals; if it is still stable the proposal is refuted without a solver
call. That is a sound, domain-specific accelerator for the search, kept apart from the memory records on purpose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterable

from solver.boolean_net import BooleanNetwork
from solver.verifier import FORCED, SURVIVES, Scenario, Verification, knockout_constants, stable_under

from .hmem_engine import HMemEngine, HMemUnavailable
from .hmem_prompts import MAX_ITEMS, MINING_PLAN_COMPLETION, MINING_SYSTEM, parse_strict_json_array
from .llm import ChatClient, LLMError

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "memory" / "hmem.json"
PROJECT_TAG = "project:p53-knockout"
FACT_SOURCE = "solver:z3+exact-attractors"
LESSON_SOURCE = "llm:lesson-miner"


def network_hash(net: BooleanNetwork) -> str:
    text = "\n".join(f"{n}:{net.specs[n].rule}" for n in net.order)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _scenario_key(scenario: Scenario) -> str:
    return scenario.name + "|" + ";".join(f"{k}={v}" for k, v in sorted(scenario.fixed.items()))


_WORDS = {"DNA_damage": "radiation", "EGFR_stimulus": "EGF signal", "FGFR3_stimulus": "FGFR3 signal",
          "Growth_inhibitors": "growth inhibitors"}


def _conditions(scenario: Scenario) -> str:
    """Conditions in words, not digits: H-MEM's conflict heuristic reads differing numbers as contradictions."""
    parts = [_WORDS[k] for k in _WORDS if scenario.fixed.get(k) == 1]
    lesions = [f"{k} lost" if v == 0 else f"{k} constitutively active" for k, v in sorted(scenario.fixed.items()) if k not in _WORDS]
    return ", ".join(parts + lesions) or "no stimulus"


class HMem:
    def __init__(self, net: BooleanNetwork, path: str | os.PathLike | None = DEFAULT_PATH, use_hmem: bool = True):
        self.net = net
        self.path = Path(path) if path else None
        self.hash = network_hash(net)
        # solver-specific counterexample cache (not H-MEM)
        self.episodes: list[dict] = []
        self.lessons: list[dict] = []            # kept for compatibility; advisory lessons now live in H-MEM
        self._load()
        # official H-MEM engine
        self.use_hmem = use_hmem
        self.engine_error: str | None = None
        self._engine: HMemEngine | None = None
        self._engine_dir = (self.path.parent / "hmem-engine" / self.hash) if self.path else None
        self._index: dict[str, dict] = {}        # fact key -> {id, verdict}
        self._retrieved: set[str] = set()        # fact keys recalled in this session (for the feedback loop)
        self._load_index()

    # -- engine access ---------------------------------------------------------------------------
    @property
    def engine(self) -> HMemEngine | None:
        if not self.use_hmem or self.engine_error:
            return None
        if self._engine is None:
            try:
                self._engine = HMemEngine(self._engine_dir, actor="agent")
                self._engine.call("ping")
            except HMemUnavailable as exc:
                self.engine_error, self._engine = str(exc), None
        return self._engine

    def close(self) -> None:
        if self._engine:
            self._engine.close()

    # -- persistence (cache + fact index) --------------------------------------------------------
    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if data.get("network_hash") != self.hash:
            return                       # learned on a different model: ignore it
        self.episodes = data.get("episodes", [])

    def _load_index(self) -> None:
        f = self._engine_dir / "index.json" if self._engine_dir else None
        if f and f.exists():
            try:
                self._index = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._index = {}

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"network_hash": self.hash, "episodes": self.episodes}, indent=1), encoding="utf-8")
        tmp.replace(self.path)
        if self._engine_dir:
            self._engine_dir.mkdir(parents=True, exist_ok=True)
            (self._engine_dir / "index.json").write_text(json.dumps(self._index), encoding="utf-8")

    # -- counterexample cache (solver-specific) --------------------------------------------------
    def record(self, scenario: Scenario, knockouts: Iterable[str], result: Verification, run_id: str = "") -> None:
        ep = {"t": int(time.time()), "run": run_id, "scenario": scenario.name, "key": _scenario_key(scenario),
              "knockouts": sorted(knockouts), "verdict": result.verdict}
        ce = result.counterexample
        if ce:
            ep["phenotype"] = ce["phenotype"]
            ep["kind"] = ce["kind"]
            ep["active_genes"] = ce["active_genes"]
            ep["inactive_genes"] = ce["inactive_genes"]
            if "state" in ce:
                ep["state"] = ce["state"]
        self.episodes.append(ep)

    def refutes(self, scenario: Scenario, knockouts: Iterable[str]) -> dict | None:
        """An earlier counterexample that still defeats ``knockouts``, or None."""
        key, kos = _scenario_key(scenario), set(knockouts)
        consts = knockout_constants(self.net, scenario, kos)
        for ep in reversed(self.episodes):
            if ep["key"] != key or ep["verdict"] != SURVIVES:
                continue
            state = ep.get("state")
            if state is not None:
                if stable_under(self.net, state, consts):
                    return ep
            elif set(ep["knockouts"]) <= kos and (kos - set(ep["knockouts"])) <= set(ep.get("inactive_genes", ())):
                return ep                # oscillating attractor: extra genes were already off in it
        return None

    def dead_additions(self, scenario: Scenario, knockouts: Iterable[str]) -> list[str]:
        """Genes that provably cannot rescue ``knockouts`` (already inactive in a surviving state)."""
        key, kos = _scenario_key(scenario), sorted(knockouts)
        dead: set[str] | None = None
        for ep in self.episodes:
            if ep["key"] == key and ep["verdict"] == SURVIVES and ep["knockouts"] == kos:
                gone = set(ep.get("inactive_genes", ()))
                dead = gone if dead is None else dead & gone
        return sorted(dead or ())

    # -- H-MEM: store + feedback loop ------------------------------------------------------------
    @staticmethod
    def _fact_key(scenario: Scenario, kos: Iterable[str]) -> str:
        return _scenario_key(scenario) + "#" + ",".join(sorted(kos))

    def remember(self, scenario: Scenario, knockouts: Iterable[str], verdict: str, counterexample: dict | None = None,
                 run_id: str = "") -> str | None:
        """Store a verified outcome as an H-MEM record, or give feedback if the same fact was recalled earlier.

        Returns the record id, or None when H-MEM is unavailable or the verdict is not a verified one.
        """
        eng = self.engine
        if eng is None or verdict not in (FORCED, SURVIVES):
            return None
        kos = sorted(knockouts)
        key = self._fact_key(scenario, kos)
        known = self._index.get(key)
        if known:
            if key in self._retrieved:   # the recalled fact met reality again: close the loop
                eng.feedback(known["id"], "helpful" if known["verdict"] == verdict else "wrong")
                self._retrieved.discard(key)
            return known["id"]
        who = "+".join(kos) if kos else "no knockout"
        base = f"In scenario {scenario.name} ({_conditions(scenario)}), knocking out {who}"
        if verdict == FORCED:
            content = f"{base} forces apoptosis in every long-term state (exact solver proof)."
        else:
            alive = ", ".join((counterexample or {}).get("active_genes", [])[:12])
            content = f"{base} does not force apoptosis: the cell survives in a state that keeps {alive or 'other genes'} active."
        rec = eng.add(content, FACT_SOURCE, type="factual", layer="working", confidence=0.9,
                      tags=[PROJECT_TAG, f"scenario:{scenario.name}", f"verdict:{verdict.lower()}", *[f"gene:{g}" for g in kos]],
                      provenance={"origin": "plan_completion", "learnedAt": int(time.time() * 1000),
                                  "label": "verified by the exact attractor solver", "refs": [run_id] if run_id else []})
        self._index[key] = {"id": rec["id"], "verdict": verdict}
        return rec["id"]

    def recall_text(self, scenario: Scenario) -> str:
        """Reinjection block for the next prompt: the official ranking and the domain-grouped context format."""
        eng = self.engine
        fallback = "No earlier experience with this scenario."
        if eng is None:
            return fallback
        q = f"In scenario {scenario.name} ({_conditions(scenario)}), knocking out genes forces apoptosis? {scenario.description}"
        res = eng.query(q, top_n=6, threshold=0.2)
        if not res["memories"]:
            return fallback
        by_id = {v["id"]: k for k, v in self._index.items()}
        self._retrieved |= {by_id[m["memory"]["id"]] for m in res["memories"] if m["memory"]["id"] in by_id}
        return res["context"] + f"\n(retrieval: {res['trace']['retrievalReason']}; strategy {res['trace']['strategy']})"

    # -- H-MEM: mining -----------------------------------------------------------------------------
    def consolidate(self, llm: ChatClient, window: int = 12) -> int:
        """Mine reusable lessons from recent failures (spec 4.1) and store them as short-term records."""
        eng = self.engine
        fails = [e for e in self.episodes if e["verdict"] == SURVIVES][-window:]
        if eng is None or len(fails) < 3:
            return 0
        lines = [f"- conditions [{e['key'].split('|', 1)[1]}]; knockout {e['knockouts'] or 'none'}; surviving state keeps "
                 f"{', '.join(e.get('active_genes', [])[:10]) or 'n/a'} active" for e in fails]
        try:
            reply = llm.complete([{"role": "system", "content": MINING_SYSTEM},
                                  {"role": "user", "content": MINING_PLAN_COMPLETION.format(evidence="\n".join(lines), max_items=MAX_ITEMS)}],
                                 max_tokens=1500)
            items = parse_strict_json_array(reply.content)
        except LLMError:
            items = []
        if not items:                    # no-model fallback (4.3): keep a concise direct summary instead of dropping it
            items = [f"Recent verified failures kept these genes active: {', '.join(sorted({g for e in fails for g in e.get('active_genes', [])})[:12])}."]
        existing = {m["content"] for m in eng.all()}
        added = 0
        for text in items:
            if text not in existing:
                eng.add(text, LESSON_SOURCE, type="general", layer="short_term", confidence=0.5, tags=[PROJECT_TAG, "advisory"],
                        provenance={"origin": "model_response", "learnedAt": int(time.time() * 1000), "label": "LLM-mined lesson"})
                added += 1
        return added

    # -- H-MEM: maintenance, always preview-first with an approval boundary for dreams ---------------
    def summary(self, scan: bool = False) -> dict:
        """Memory health. Conflict scanning is on demand: every scan writes ``conflict_detected`` ledger entries."""
        eng = self.engine
        if eng is None:
            return {"available": False, "reason": self.engine_error or "disabled"}
        recs = eng.all()
        layers: dict[str, int] = {}
        for r in recs:
            layers[r["layer"]] = layers.get(r["layer"], 0) + 1
        pre = eng.sleep_preview()
        return {"available": True, "records": len(recs), "layers": layers, "ledger": eng.ledger_stats(),
                "conflicts_detected": len(eng.scan_conflicts() if scan else eng.call("conflicts_queue")),
                "sleep_preview": {"consolidate": len(pre["toConsolidate"]), "archive": len(pre["toArchive"]), "synthesize": len(pre["toSynthesize"])}}

    def dream(self) -> list[dict]:
        """Dream proposals for human review. Nothing becomes durable until ``approve_dream`` is called."""
        eng = self.engine
        return eng.dream() if eng else []

    def approve_dream(self, proposal_id: str) -> dict | None:
        eng = self.engine
        return eng.dream_approve(proposal_id) if eng else None

    # -- prompt text for the legacy UI/tests --------------------------------------------------------
    def known_verdict(self, scenario: Scenario, knockouts: Iterable[str]) -> str | None:
        key, kos = _scenario_key(scenario), sorted(knockouts)
        for ep in reversed(self.episodes):
            if ep["key"] == key and ep["knockouts"] == kos and ep["verdict"] in (FORCED, SURVIVES):
                return ep["verdict"]
        return None


def _cli() -> None:
    """python -m agent.memory status | ledger | sleep [--execute] | dream [--approve-all]"""
    ap = argparse.ArgumentParser(description=_cli.__doc__)
    ap.add_argument("command", choices=["status", "ledger", "sleep", "dream"])
    ap.add_argument("--execute", action="store_true", help="sleep: actually run it (default is preview only)")
    ap.add_argument("--approve-all", action="store_true", help="dream: approve every proposal (human decision)")
    args = ap.parse_args()
    from .tools_zetaris import DataLayer
    net = BooleanNetwork.from_rows(DataLayer().network_rows())
    mem = HMem(net)
    if mem.engine is None:
        raise SystemExit(f"H-MEM engine unavailable: {mem.engine_error}")
    eng = mem.engine
    if args.command == "status":
        print(json.dumps(mem.summary(scan=True), indent=1))
    elif args.command == "ledger":
        print(json.dumps(eng.ledger_stats(), indent=1))
    elif args.command == "sleep":
        pre = eng.sleep_preview()
        print("preview:", {k: len(v) for k, v in pre.items()})
        if args.execute:
            print("report:", json.dumps(eng.sleep_execute(pre), indent=1))
    else:
        props = mem.dream()
        for p in props:
            print(f"[{p['type']}] {p['id']}: {p['content']}")
            if args.approve_all:
                print("  approved ->", (mem.approve_dream(p["id"]) or {}).get("id"))
        if not props:
            print("no dream proposals (needs at least two related memories)")
    mem.close()


if __name__ == "__main__":
    _cli()
