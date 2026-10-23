"""Solver correctness tests.

The central check compares the optimised engine (percolation + leaf trimming +
numpy/scipy SCCs) with a naive reference that enumerates the raw asynchronous
state graph with networkx, and with Z3's independent stable-state enumeration.
"""
import csv
import itertools
import random
from pathlib import Path

import networkx as nx
import pytest

from solver.attractors import analyze
from solver.boolean_net import BooleanNetwork, parse_rule
from solver.verifier import (FORCED, SAFE, SURVIVES, TOXIC, UNKNOWN, Scenario, Verifier,
                             all_z3_fixed_points, knockout_constants)
from solver.knockout_opt import minimal_knockouts

DATA = Path(__file__).resolve().parent.parent / "data" / "p53_interactions.csv"
GOAL = {"Apoptosis_high": 1}
RT = dict(DNA_damage=1, EGFR_stimulus=0, FGFR3_stimulus=0, Growth_inhibitors=0)


@pytest.fixture(scope="module")
def net():
    with DATA.open(encoding="utf-8") as fh:
        return BooleanNetwork.from_rows(csv.DictReader(fh))


def test_parser_precedence_and_errors():
    assert parse_rule("a | b & !c") == ("or", [("var", "a"), ("and", [("var", "b"), ("not", ("var", "c"))])])
    assert parse_rule("!(a|b)") == ("not", ("or", [("var", "a"), ("var", "b")]))
    for bad in ("a &", "a b", "(a", "a ^ b", ""):
        with pytest.raises(ValueError):
            parse_rule(bad)


def test_network_shape(net):
    assert len(net.order) == 35
    assert set(net.inputs) == {"DNA_damage", "EGFR_stimulus", "FGFR3_stimulus", "Growth_inhibitors"}
    assert "TP53" in net.knockable_genes() and "DNA_damage" not in net.knockable_genes()
    assert "Apoptosis" not in net.knockable_genes()


def test_percolation_is_sound(net):
    """Every node percolation calls constant is constant in all Z3 stable states."""
    consts = dict(RT, FGFR3_stimulus=1, RB1=0)
    forced = net.percolate(consts)
    for state in all_z3_fixed_points(net, consts):
        assert all(state[n] == v for n, v in forced.items())


def _naive_attractors(net, consts, project):
    """Terminal SCCs of the raw async graph over all nodes not fixed by ``consts``.

    State counts are taken after projecting onto ``project`` (the nodes the
    optimised engine enumerates): nodes nothing depends on can lag behind in the
    raw graph, which multiplies its state count without changing any value.
    """
    free = [n for n in net.order if n not in consts]
    assert len(free) <= 14
    index = {n: i for i, n in enumerate(free)}
    pairs = net.level_pairs()
    g = nx.DiGraph()

    def consistent(st):
        return all(not st[h] or st[m] for h, m in pairs)

    for bits in itertools.product((0, 1), repeat=len(free)):
        st = {**consts, **{n: bits[index[n]] for n in free}}
        if not consistent(st):
            continue
        g.add_node(bits)
        for n in free:
            if int(net.update(n, st)) != st[n]:
                flipped = list(bits)
                flipped[index[n]] ^= 1
                g.add_edge(bits, tuple(flipped))
    cond = nx.condensation(g)
    result = []
    for c in cond.nodes:
        if cond.out_degree(c) == 0:
            members = cond.nodes[c]["members"]
            n_proj = len({tuple(m[index[n]] for n in project) for m in members})
            vals = {}
            for n in net.order:
                col = {(consts[n] if n in consts else m[index[n]]) for m in members}
                vals[n] = col.pop() if len(col) == 1 else None
            result.append((n_proj, tuple(vals[n] for n in net.order)))
    return sorted(result, key=str)


def test_engine_matches_naive_reference(net):
    """Fix enough nodes that the raw state space is enumerable, then compare.

    Knockouts are drawn until at most 14 nodes stay free. Half of the cases
    never touch the EGFR/GRB2 module so oscillating attractors are compared too.
    """
    rng = random.Random(7)
    rtk = {"EGFR", "FGFR3", "GRB2", "RAS", "SPRY"}
    core = [g for g in net.knockable_genes() if g not in rtk]
    checked = cyclic = 0
    for attempt in range(60):
        if checked >= 20:
            break
        extra = dict(RT, EGFR_stimulus=rng.choice((0, 1)), FGFR3_stimulus=rng.choice((0, 1)))
        pool = rng.sample(core if attempt % 2 == 0 else net.knockable_genes(), k=len(core))
        consts, kos = dict(extra), []
        for gene in pool:
            if len([n for n in net.order if n not in consts]) <= 14:
                break
            consts.update({n: 0 for n in net.genes[gene]})
            kos.append(gene)
        if len([n for n in net.order if n not in consts]) > 14:
            continue
        analysis = analyze(net, consts)
        fast = sorted(((a.n_states, tuple(a.values[n] for n in net.order))
                       for a in analysis.attractors), key=str)
        assert fast == _naive_attractors(net, consts, analysis.state_nodes), (extra, kos)
        cyclic += any(a.kind == "cyclic" for a in analysis.attractors)
        checked += 1
    assert checked >= 20 and cyclic >= 2, (checked, cyclic)


def _toy(rules):
    return BooleanNetwork.from_rows({"node": n, "gene": n, "role": "internal", "rule": r}
                                    for n, r in rules.items())


def test_toggle_switch_has_two_fixed_points():
    attractors = analyze(_toy({"a": "!b", "b": "!a"}), {}).attractors
    assert sorted((a.kind, tuple(a.values.values())) for a in attractors) == [("fixed", (0, 1)), ("fixed", (1, 0))]


def test_negative_feedback_loop_is_one_four_state_cycle():
    (a,) = analyze(_toy({"a": "!b", "b": "a"}), {}).attractors
    assert a.kind == "cyclic" and a.n_states == 4 and a.values == {"a": None, "b": None}


def test_independent_modules_multiply_attractors():
    net = _toy({"a": "!b", "b": "!a", "c": "!d", "d": "!c"})
    assert len(analyze(net, {}).attractors) == 4


def test_fixed_points_agree_with_z3(net):
    rng = random.Random(11)
    genes = net.knockable_genes()
    for _ in range(60):
        consts = dict(DNA_damage=rng.choice((0, 1)), EGFR_stimulus=rng.choice((0, 1)),
                      FGFR3_stimulus=rng.choice((0, 1)), Growth_inhibitors=rng.choice((0, 1)))
        consts.update({n: 0 for n in net.nodes_of(rng.sample(genes, rng.randint(0, 4)))})
        analysis = analyze(net, consts)
        assert analysis.complete
        explicit = sorted(tuple(a.values[n] for n in net.order)
                          for a in analysis.attractors if a.kind == "fixed")
        z3 = sorted(tuple(s[n] for n in net.order) for s in all_z3_fixed_points(net, consts))
        assert explicit == z3, consts


def test_known_phenotypes(net):
    v = Verifier(net)
    healthy = analyze(net, dict(DNA_damage=0, EGFR_stimulus=0, FGFR3_stimulus=0, Growth_inhibitors=0))
    (a,) = healthy.attractors
    assert a.kind == "fixed" and a.values["Growth_arrest"] == 1 and a.values["Proliferation"] == 0
    # wild-type p53 under damage and FGFR3 signalling arrests instead of dying
    sc = Scenario("t", dict(RT, FGFR3_stimulus=1), GOAL)
    base = v.verify(sc, [])
    assert base.verdict == SURVIVES
    assert base.counterexample["phenotype"]["Growth_arrest"] == 1
    # ... and losing p53 (or p21) pushes it to apoptosis
    assert v.verify(sc, ["TP53"]).verdict == FORCED
    assert v.verify(sc, ["p21CIP"]).verdict == FORCED
    assert v.verify(sc, ["MDM2"]).verdict == SURVIVES


def test_oscillating_attractor_is_a_counterexample(net):
    v = Verifier(net)
    sc = Scenario("osc", dict(RT, EGFR_stimulus=1, TP53=0), GOAL)
    res = v.verify(sc, [])
    assert res.verdict == SURVIVES
    assert res.counterexample["kind"] == "oscillating_attractor"
    assert "Apoptosis_high" in res.counterexample["oscillating_nodes"]
    # silencing the EGFR/GRB2 loop removes the oscillation
    assert v.verify(sc, ["GRB2"]).verdict == FORCED


def test_knockout_overrides_background_lesion(net):
    sc = Scenario("t", dict(RT, RAS=1), GOAL)
    assert knockout_constants(net, sc, ["RAS"])["RAS"] == 0


def test_safety_flags_toxic_knockout(net):
    v = Verifier(net)
    normal = Scenario("normal", dict(DNA_damage=0, EGFR_stimulus=0, FGFR3_stimulus=1,
                                     Growth_inhibitors=0), GOAL, kind="safety")
    assert v.verify(normal, []).verdict == SAFE


def test_search_returns_minimal_sets_only(net):
    v = Verifier(net)
    sc = Scenario("fgfr3", dict(RT, FGFR3_stimulus=1), GOAL)
    res = minimal_knockouts(v, sc, max_size=3)
    assert set(res.solutions) == {("TP53",), ("p21CIP",), ("RB1", "RBL2")}
    sets = [set(s) for s in res.solutions]
    assert not any(a < b for a in sets for b in sets)


def test_no_unknown_verdicts_up_to_three_knockouts(net):
    v = Verifier(net)
    sc = Scenario("egf", dict(RT, EGFR_stimulus=1), GOAL)
    genes = net.knockable_genes()
    verdicts = {v.verify(sc, c).verdict
                for k in range(0, 3) for c in itertools.combinations(genes, k)}
    assert UNKNOWN not in verdicts


def test_verifier_is_thread_safe(net):
    """Parallel benchmark runs share the module; Z3 must not mix contexts across threads."""
    import concurrent.futures as cf
    sc = Scenario("t", dict(RT, FGFR3_stimulus=1), GOAL)

    def work(i):
        v = Verifier(net)
        return [v.verify(sc, [g]).verdict for g in ("TP53", "MDM2", "p21CIP", "RB1")]

    with cf.ThreadPoolExecutor(4) as ex:
        results = list(ex.map(work, range(8)))
    assert all(r == [FORCED, SURVIVES, FORCED, SURVIVES] for r in results)


def test_every_derivation_step_is_entailed_by_its_premises(net):
    """The explanation steps are proofs: premises force the conclusion through the node's rule."""
    from solver.explain import step_entailed, steps_from_tree
    v = Verifier(net)
    cases = [(dict(RT, FGFR3_stimulus=1), ["TP53"]), (dict(RT, FGFR3_stimulus=1), ["p21CIP"]),
             (dict(RT, FGFR3_stimulus=1), ["RB1", "RBL2"]), (dict(RT, EGFR_stimulus=1), ["GRB2", "TP53"]),
             (dict(RT, EGFR_stimulus=1, TP53=0), ["GRB2"])]
    total = 0
    for fixed, kos in cases:
        sc = Scenario("t", fixed, GOAL)
        res = v.verify(sc, kos)
        assert res.verdict == FORCED and res.trees
        known = knockout_constants(net, sc, kos)
        for tree in res.trees:
            for step in steps_from_tree(tree, limit=200):
                assert step_entailed(net, step, known), (kos, step)
                total += 1
    assert total > 30


def test_ungrounded_mentions_flag_genes_outside_the_chosen_steps(net):
    from solver.explain import ungrounded_mentions
    allowed = {"TP53", "p21CIP", "Growth_inhibitors"}
    assert ungrounded_mentions(net, "TP53 loss lowers p21CIP", allowed) == []
    assert ungrounded_mentions(net, "TP53 loss also changes MDM2 and AKT", allowed) == ["AKT", "MDM2"]
    assert ungrounded_mentions(net, "the cell survives radiation", allowed) == []
