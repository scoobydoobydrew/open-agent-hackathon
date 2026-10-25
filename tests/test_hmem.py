"""H-MEM: the vendored engine is the official one, it passes the official conformance suite, and the agent really uses it."""
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agent.hmem_engine import BUNDLE, ESBUILD, HMemEngine, HMemUnavailable, build_bundle, ensure_bundle
from agent.memory import HMem
from solver.boolean_net import BooleanNetwork
from solver.verifier import FORCED, SURVIVES, Scenario, Verifier

ROOT = Path(__file__).resolve().parent.parent
HM = ROOT / "hmem"
# The built bridge is committed, so the engine tests need only Node; the official suite and the rebuild need `npm install`.
pytestmark = pytest.mark.skipif(not shutil.which("node") or not BUNDLE.exists(), reason="needs Node.js")
needs_npm = pytest.mark.skipif(not (HM / "reference" / "node_modules").exists(),
                               reason="needs `npm install` in hmem/reference")


@pytest.fixture(scope="module")
def net():
    with (ROOT / "data" / "p53_interactions.csv").open(encoding="utf-8") as fh:
        return BooleanNetwork.from_rows(csv.DictReader(fh))


@pytest.fixture(scope="module")
def scenario():
    with (ROOT / "data" / "phenotypes.csv").open(encoding="utf-8") as fh:
        return Scenario.from_row(next(r for r in csv.DictReader(fh) if r["scenario_id"] == "fgfr3_wtp53"))


def test_vendored_reference_is_unmodified():
    manifest = json.loads((HM / "UPSTREAM.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "Apache-2.0" and len(manifest["commit"]) == 40
    for rel, digest in manifest["sha256"].items():
        assert hashlib.sha256((HM / rel).read_bytes()).hexdigest() == digest, f"{rel} differs from upstream"


@needs_npm
def test_official_conformance_suite_is_green():
    runner = HM / "conformance" / "runner.ts"
    tsx = HM / "reference" / "node_modules" / "tsx" / "dist" / "cli.mjs"
    out = subprocess.run(["node", str(tsx), str(runner)], capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stdout[-1500:] + out.stderr[-500:]
    assert "13/13 checks passed" in out.stdout


@needs_npm
def test_committed_bundle_is_exactly_what_the_vendored_sources_build(tmp_path):
    """The bridge the agent runs is the unmodified reference plus our bridge.ts, not something else."""
    rebuilt = build_bundle(tmp_path / "bridge.mjs")
    assert rebuilt.read_bytes() == BUNDLE.read_bytes()


# -- the engine behind the Python client follows the spec -----------------------------------------------------------
def test_record_without_source_is_rejected_by_construction():
    e = HMemEngine()
    with pytest.raises(ValueError, match="no source"):
        e.add("a fact with no source", source="")
    assert e.add("a fact with a source", source="test")["source"] == "test"


def test_feedback_uses_the_exact_deltas_and_the_ledger_records_it():
    e = HMemEngine()
    m = e.add("feedback target", source="t", confidence=0.7)
    assert e.feedback(m["id"], "helpful")["confidence"] == pytest.approx(0.75)
    assert e.feedback(m["id"], "not_helpful")["confidence"] == pytest.approx(0.72)
    wrong = e.feedback(m["id"], "wrong")
    assert wrong["confidence"] == pytest.approx(0.52) and "review" in wrong["tags"]
    assert [h["action"] for h in e.history(m["id"])] == ["create", "feedback", "feedback", "feedback"]
    with pytest.raises(ValueError):
        e.feedback(m["id"], "fantastic")


def test_retrieval_returns_the_spec_reinjection_block():
    e = HMemEngine()
    e.add("Python services use PostgreSQL for the database", source="t", tags=["tech:python"])
    res = e.query("which database do python services use")
    assert res["context"].startswith("[MEMORY CONTEXT]") and res["context"].endswith("[/MEMORY CONTEXT]")
    assert res["trace"]["strategy"] in ("minimal", "personal", "comprehensive") and res["memories"]


def test_sleep_preview_never_mutates_and_dreams_need_approval():
    e = HMemEngine()
    for text in ("I prefer short answers in the morning", "I prefer concise summaries in the morning"):
        e.add(text, source="t", type="preference")
    before = sorted(m["id"] for m in e.all())
    e.sleep_preview()
    assert sorted(m["id"] for m in e.all()) == before
    proposals = e.dream()
    assert proposals and len(e.all()) == len(before)             # nothing materialises before approval
    created = e.dream_approve(proposals[0]["id"])
    assert created is None or (created["layer"] == "long_term" and created["derivedFrom"])


def test_state_and_ledger_persist_between_processes(tmp_path):
    a = HMemEngine(tmp_path)
    rec = a.add("persistent fact about p53", source="t")
    a.close()
    b = HMemEngine(tmp_path)
    assert [m["id"] for m in b.all()] == [rec["id"]]
    assert [h["action"] for h in b.history(rec["id"])] == ["create"]
    assert (tmp_path / "ledger.jsonl").exists()


# -- the agent's memory uses the engine -------------------------------------------------------------------------------
def test_facts_are_stored_recalled_and_graded(net, scenario, tmp_path):
    ver = Verifier(net)
    path = tmp_path / "hmem.json"
    mem = HMem(net, path)
    res = ver.verify(scenario, ["MDM2"])
    assert res.verdict == SURVIVES
    rid = mem.remember(scenario, ["MDM2"], res.verdict, res.counterexample, "run1")
    assert rid and mem.remember(scenario, ["TP53"], FORCED, None, "run1")
    rec = next(m for m in mem.engine.all() if m["id"] == rid)
    assert rec["source"] == "solver:z3+exact-attractors" and rec["provenance"]["origin"] == "plan_completion"
    assert rec["confidence"] == 0.9 and "scenario:fgfr3_wtp53" in rec["tags"]
    mem.save(); mem.close()

    again = HMem(net, path)                                         # a new session recalls what the last one learned
    text = again.recall_text(scenario)
    assert "[MEMORY CONTEXT]" in text and "MDM2" in text
    # the recalled fact meets reality again: a correct prediction earns +0.05, a wrong one -0.20
    again.remember(scenario, ["MDM2"], SURVIVES, None, "run2")
    assert next(m for m in again.engine.all() if m["id"] == rid)["confidence"] == pytest.approx(0.95)
    again.recall_text(scenario)
    again.remember(scenario, ["MDM2"], FORCED, None, "run3")
    wrong = next(m for m in again.engine.all() if m["id"] == rid)
    assert wrong["confidence"] == pytest.approx(0.75) and "review" in wrong["tags"]
    again.close()


def test_every_fact_has_source_provenance_and_a_ledger_trail(net, scenario):
    mem = HMem(net, None)
    rid = mem.remember(scenario, ["RB1"], SURVIVES, {"active_genes": ["TP53"]}, "r")
    assert [h["action"] for h in mem.engine.history(rid)] == ["create"]
    info = mem.summary()
    assert info["available"] and info["records"] == 1 and info["ledger"]["create"] == 1


def test_lesson_mining_follows_the_spec_and_falls_back_without_a_model(net, scenario):
    from agent.hmem_prompts import parse_strict_json_array
    assert parse_strict_json_array('```json\n["a lesson that is long enough to keep", "short"]\n```') == ["a lesson that is long enough to keep"]
    assert parse_strict_json_array("not json at all") == []

    class Broken:
        model = "x"

        def complete(self, *a, **k):
            from agent.llm import LLMError
            raise LLMError("down")

    ver, mem = Verifier(net), HMem(net, None)
    for g in ("MDM2", "AKT", "ATM"):
        res = ver.verify(scenario, [g])
        mem.record(scenario, [g], res)
    assert mem.consolidate(Broken()) == 1                         # model-free path keeps a direct summary
    assert any(m["source"] == "llm:lesson-miner" and m["layer"] == "short_term" for m in mem.engine.all())


def test_agent_runs_without_the_engine_and_says_so(net, scenario, monkeypatch):
    monkeypatch.setattr("agent.hmem_engine.ensure_bundle", lambda: (_ for _ in ()).throw(HMemUnavailable("no node")))
    mem = HMem(net, None)
    assert mem.engine is None and mem.remember(scenario, ["TP53"], FORCED) is None
    assert mem.recall_text(scenario) == "No earlier experience with this scenario."
    assert mem.summary() == {"available": False, "reason": "no node"}
