"""The counterexample-guided search must agree with exhaustive enumeration (completeness) and cost less."""
import csv
import json
from pathlib import Path

import pytest

from agent.memory import HMem
from solver.boolean_net import BooleanNetwork
from solver.cegar import CegarSearch
from solver.knockout_opt import candidate_genes
from solver.verifier import Scenario, Verifier

ROOT = Path(__file__).resolve().parent.parent
TRUTH = json.loads((ROOT / "benchmark" / "ground_truth.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def net():
    with (ROOT / "data" / "p53_interactions.csv").open(encoding="utf-8") as fh:
        return BooleanNetwork.from_rows(csv.DictReader(fh))


@pytest.fixture(scope="module")
def scenarios():
    with (ROOT / "data" / "phenotypes.csv").open(encoding="utf-8") as fh:
        return {r["scenario_id"]: Scenario.from_row(r) for r in csv.DictReader(fh)}


@pytest.mark.parametrize("sid", ["fgfr3_wtp53", "egf_tp53null", "egf_wtp53", "growthinh_only"])
def test_search_matches_exhaustive_ground_truth(net, scenarios, sid):
    truth = TRUTH[sid]
    ver, sc = Verifier(net), scenarios[sid]
    search = CegarSearch(ver, sc, max_size=truth["max_size_searched"], candidates=candidate_genes(ver, sc))
    search.advance()
    expected = sorted(tuple(sorted(e["knockouts"])) for e in truth["minimal_sets"])
    assert sorted(f.knockouts for f in search.solutions) == expected
    assert search.exhausted and search.proved_infeasible == (not expected)
    assert search.calls < truth["sets_evaluated"]


def test_memory_replay_keeps_the_result_and_saves_calls(net, scenarios):
    sid = "egf_wtp53"
    truth, sc = TRUTH[sid], scenarios[sid]
    plain = CegarSearch(Verifier(net), sc, max_size=3)
    plain.advance()
    ver, mem = Verifier(net), HMem(net, None)
    # a second search seeded with what the first one learned
    first = CegarSearch(ver, sc, max_size=3, refute=mem.refutes, on_failure=lambda k, r: mem.record(sc, k, r))
    first.advance()
    again = CegarSearch(Verifier(net), sc, max_size=3, refute=mem.refutes)
    again.advance()
    expected = sorted(tuple(sorted(e["knockouts"])) for e in truth["minimal_sets"])
    assert sorted(f.knockouts for f in again.solutions) == expected
    assert again.replays > 0 and again.calls < plain.calls


def test_budget_stops_the_search_and_it_can_resume(net, scenarios):
    sc = scenarios["egf_wtp53"]
    search = CegarSearch(Verifier(net), sc, max_size=3)
    search.advance(call_budget=20)
    assert not search.exhausted and 20 <= search.calls < 60
    search.advance()
    assert search.exhausted and len(search.solutions) == 3
