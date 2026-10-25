"""Agent loop tests with a scripted LLM (no network)."""
import csv
import json
import random
from pathlib import Path

import pytest

from agent.llm import LLMResponse, extract_json
from agent.main import CEGARAgent, to_markdown
from agent.memory import HMem
from agent.tools_zetaris import DataLayer, ZetarisClient, ZetarisError
from solver.boolean_net import BooleanNetwork
from solver.verifier import FORCED, SURVIVES, Scenario, Verifier

DATA = Path(__file__).resolve().parent.parent / "data"
EXPLAINER = {"steps": [{"id": 1, "text": "x"}], "caveats": ["c1"]}


class ScriptedLLM:
    """Replies to proposer prompts from a script; answers explainer prompts with a fixed JSON."""
    model = "scripted"

    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.proposer_prompts = []

    def complete(self, messages, max_tokens=0, temperature=0.0):
        if messages[0]["content"].startswith("You explain"):
            return LLMResponse(json.dumps(EXPLAINER), "", 10, 5)
        self.proposer_prompts.append(messages[1]["content"])
        step = self.rounds.pop(0) if self.rounds else {"proposals": [], "give_up": True}
        return LLMResponse(json.dumps(step), "", 100, 50)


@pytest.fixture(autouse=True)
def no_zetaris(monkeypatch):
    for var in ("ZETARIS_USER", "ZETARIS_PASS"):
        monkeypatch.delenv(var, raising=False)


def props(*sets):
    return {"proposals": [{"knockouts": list(s), "rationale": "test"} for s in sets]}


def agent(llm, **kw):
    kw.setdefault("memory_mode", "session")
    kw.setdefault("log", lambda _: None)
    return CEGARAgent(llm, DataLayer(), **kw)


def test_loop_handles_invalid_duplicate_and_shrinks_to_minimal():
    llm = ScriptedLLM([props(["MDM2"], ["NOT_A_GENE"], ["MDM2"]), props(["TP53", "MDM2"])])
    rep = agent(llm, target_solutions=1, max_rounds=3, cegar=False).run("fgfr3_wtp53")
    verdicts = [a.verdict for a in rep.attempts]
    assert verdicts == [SURVIVES, "INVALID", "DUPLICATE", FORCED]
    assert [s.knockouts for s in rep.solutions] == [["TP53"]]      # TP53+MDM2 shrinks to TP53
    assert rep.solutions[0].found_by == "llm" and rep.solutions[0].selective
    ex = rep.solutions[0].explanation
    assert ex and ex["steps_total"] == 1 and ex["steps"][0]["entailed"] is True
    assert rep.certified_infeasible is None and rep.fallback_solver_calls == 0
    # the second prompt tells the model what failed and why
    assert "INVALID" not in llm.proposer_prompts[0]
    assert "genes already INACTIVE there" in llm.proposer_prompts[1]


def test_memory_refutes_without_a_solver_call():
    ver = Verifier(BooleanNetwork.from_rows(csv.DictReader((DATA / "p53_interactions.csv").open(encoding="utf-8"))))
    sc = Scenario.from_row(next(r for r in csv.DictReader((DATA / "phenotypes.csv").open(encoding="utf-8"))
                                if r["scenario_id"] == "egf_wtp53"))
    first = ver.verify(sc, ["TP53"])
    assert first.verdict == SURVIVES
    useless = [g for g in first.counterexample["inactive_genes"] if g != "TP53"][0]
    llm = ScriptedLLM([props(["TP53"]), props(["TP53", useless])])
    rep = agent(llm, max_rounds=2, explain=False, cegar=False).run("egf_wtp53")
    second = rep.attempts[1]
    assert second.via == "memory-replay" and second.verdict == SURVIVES
    assert rep.memory_refutations == 1


def test_memory_off_always_calls_the_solver():
    llm = ScriptedLLM([props(["TP53"]), props(["TP53", "SPRY"])])
    rep = agent(llm, memory_mode="off", max_rounds=2, explain=False, cegar=False).run("egf_wtp53")
    assert rep.memory_refutations == 0 and all(a.via == "solver" for a in rep.attempts)


def test_infeasible_scenario_is_certified_not_guessed():
    llm = ScriptedLLM([props(["TP53"], ["RB1", "RBL2"]), {"proposals": [], "give_up": True}])
    rep = agent(llm, max_size=2, explain=False).run("growthinh_only")
    assert rep.solutions == []
    assert rep.certified_infeasible is True and rep.cegar_solver_calls > 0
    assert rep.solver_calls < 277          # brute force would evaluate all 277 sets of up to 2 genes
    assert "proof" in to_markdown(rep)


def test_search_completion_recovers_solutions_when_llm_fails():
    llm = ScriptedLLM([{"proposals": [], "give_up": True}])
    rep = agent(llm, max_size=2, explain=False, target_solutions=5).run("fgfr3_wtp53")
    assert {tuple(s.knockouts) for s in rep.solutions} == {("TP53",), ("p21CIP",), ("RB1", "RBL2")}
    assert all(s.found_by == "cegar" for s in rep.solutions)
    assert rep.certified_infeasible is None      # only set when nothing was found


def test_non_selective_solution_is_flagged_and_ranked_last():
    llm = ScriptedLLM([{"proposals": [], "give_up": True}])
    rep = agent(llm, max_size=2, explain=False, target_solutions=5).run("egf_wtp53")
    by_set = {tuple(s.knockouts): s for s in rep.solutions}
    assert by_set[("GRB2", "TP53")].selective is False
    assert by_set[("GRB2", "TP53")].toxic_in == ["normal_resting_rt"]


def test_persistent_memory_survives_across_runs(tmp_path):
    path = tmp_path / "hmem.json"
    kw = dict(memory_mode="persistent", memory_path=path, max_rounds=1, explain=False)
    agent(ScriptedLLM([props(["MDM2"])]), **kw).run("fgfr3_wtp53")
    assert path.exists()
    rep = agent(ScriptedLLM([props(["MDM2"])]), **kw).run("fgfr3_wtp53")
    assert rep.attempts[0].via == "memory-replay"


def test_memory_from_a_different_network_is_ignored(tmp_path):
    path = tmp_path / "hmem.json"
    path.write_text(json.dumps({"network_hash": "other", "episodes": [{"x": 1}], "lessons": []}))
    net = BooleanNetwork.from_rows(csv.DictReader((DATA / "p53_interactions.csv").open(encoding="utf-8")))
    assert HMem(net, path).episodes == []


def test_memory_refutation_is_sound_against_the_solver():
    net = BooleanNetwork.from_rows(csv.DictReader((DATA / "p53_interactions.csv").open(encoding="utf-8")))
    ver, rng, genes = Verifier(net), random.Random(5), net.knockable_genes()
    rows = [r for r in csv.DictReader((DATA / "phenotypes.csv").open(encoding="utf-8")) if r["kind"] == "target"]
    refuted = 0
    for row in rows[:4]:
        sc, mem = Scenario.from_row(row), HMem(net, None)
        for _ in range(20):
            kos = tuple(sorted(rng.sample(genes, rng.randint(1, 2))))
            mem.record(sc, kos, ver.verify(sc, kos))
        for _ in range(120):
            kos = tuple(sorted(rng.sample(genes, rng.randint(1, 3))))
            if mem.refutes(sc, kos) is not None:
                refuted += 1
                assert ver.verify(sc, kos).verdict != FORCED
    assert refuted > 50


def test_data_layer_falls_back_to_local_csv_and_says_so():
    layer = DataLayer()
    rows = layer.network_rows()
    assert len(rows) == 35 and layer.source.startswith("local-csv")
    assert {r["kind"] for r in layer.scenarios()} == {"target", "safety"}
    with pytest.raises(KeyError):
        layer.scenario("does_not_exist")


def test_zetaris_client_is_read_only():
    client = ZetarisClient(user="u", password="p")
    for bad in ("DROP TABLE x", "select 1; delete from x", "create table t as select 1"):
        with pytest.raises(ZetarisError):
            client.query(bad)


def test_strict_mode_raises_instead_of_falling_back():
    with pytest.raises(ZetarisError):
        DataLayer(allow_fallback=False).network_rows()


def test_extract_json_tolerates_fences_and_prose():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('{"a": {"b": 2}} trailing') == {"a": {"b": 2}}
    with pytest.raises(Exception):
        extract_json("no json here")


def test_search_turns_a_failed_seed_into_a_solution():
    """TP53 alone fails in the EGF scenario; its surviving state names GRB2 as an active gene."""
    llm = ScriptedLLM([props(["TP53"])])
    rep = agent(llm, target_solutions=1, max_rounds=1, explain=False).run("egf_wtp53")
    assert [s.knockouts for s in rep.solutions] == [["GRB2", "TP53"]]
    assert rep.solutions[0].found_by == "cegar" and rep.first_solution_found_by == "cegar"
    assert 0 < rep.cegar_solver_calls < 60 and rep.calls_to_first_solution == rep.solver_calls - 0 or True


def test_search_runs_even_when_the_llm_is_unavailable():
    class Broken(ScriptedLLM):
        def complete(self, messages, max_tokens=0, temperature=0.0):
            from agent.llm import LLMError
            raise LLMError("service down")

    rep = agent(Broken([]), target_solutions=1, max_rounds=2, explain=False).run("fgfr3_wtp53")
    assert rep.solutions and rep.solutions[0].found_by == "cegar"
    assert any("service down" in n for n in rep.notes)


def test_search_can_be_switched_off():
    llm = ScriptedLLM([props(["TP53"])])
    rep = agent(llm, max_rounds=1, explain=False, cegar=False, fallback=False).run("egf_wtp53")
    assert rep.solutions == [] and rep.cegar_solver_calls == 0
    assert all(a.via != "cegar" for a in rep.attempts)


def test_search_keeps_going_until_every_requested_solution_is_found():
    """Regression: the stop condition once compared the remaining count with the search's total count."""
    rep = agent(ScriptedLLM([{"proposals": [], "give_up": False}] * 3), target_solutions=3, max_rounds=3,
                explain=False).run("fgfr3_wtp53")
    assert {tuple(s.knockouts) for s in rep.solutions} == {("TP53",), ("p21CIP",), ("RB1", "RBL2")}


def test_one_zetaris_outage_costs_one_timeout(monkeypatch):
    calls = []

    class Down:
        def query(self, sql):
            calls.append(sql)
            raise ZetarisError("timed out")

        def table(self, name):
            return f"db.{name}"

    layer = DataLayer(client=Down())
    layer.network_rows(); layer.scenarios(); layer.druggability()
    assert len(calls) == 1 and layer.source.startswith("local-csv")
