"""Verification of knockout sets against a scenario.

A *target* scenario is satisfied (verdict FORCED) when every attractor of the
perturbed network satisfies the goal (default: Apoptosis_high = 1 on every
state of every attractor). A *safety* scenario is satisfied (SAFE) when no
attractor visits a goal state, used to flag knockouts that would kill a normal
cell.

Two engines cooperate:
  * Z3 asks "is there a stable state that violates the goal?". SAT gives an
    instant, concrete counterexample; it is also the independent check used in
    the tests.
  * The explicit-state engine in attractors.py enumerates all attractors of the
    reduced network (including oscillating ones) and decides the rest exactly.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Iterable, Mapping

import z3

from .attractors import Attractor, analyze
from .boolean_net import BooleanNetwork, eval_expr
from .explain import justify, render

FORCED, SURVIVES, UNKNOWN, SAFE, TOXIC = "FORCED", "SURVIVES", "UNKNOWN", "SAFE", "TOXIC"
READOUTS = ("Apoptosis_high", "Apoptosis_medium", "Proliferation", "Growth_arrest")


def parse_assignments(text: str) -> dict[str, int]:
    """'A=1;B=0' -> {'A': 1, 'B': 0} (empty string gives {})."""
    out: dict[str, int] = {}
    for part in filter(None, (p.strip() for p in text.split(";"))):
        name, value = part.split("=")
        if value.strip() not in ("0", "1"):
            raise ValueError(f"bad value in assignment {part!r}")
        out[name.strip()] = int(value)
    return out


@dataclass(frozen=True)
class Scenario:
    name: str
    fixed: Mapping[str, int]             # stimuli and background lesions
    goal: Mapping[str, int]              # e.g. {"Apoptosis_high": 1}
    kind: str = "target"                 # "target" or "safety"
    description: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, str]) -> "Scenario":
        return cls(row["scenario_id"].strip(), parse_assignments(row["fixed_nodes"]),
                   parse_assignments(row["goal"]), row.get("kind", "target").strip(),
                   row.get("description", "").strip())


@dataclass
class Verification:
    scenario: str
    knockouts: tuple[str, ...]
    verdict: str
    method: str
    n_attractors: int | None = None
    counterexample: dict | None = None
    attractors: list[dict] = field(default_factory=list)
    explanation: str = ""
    trees: list[dict] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def knockout_constants(net: BooleanNetwork, scenario: Scenario, knockouts: Iterable[str]) -> dict[str, int]:
    consts = dict(scenario.fixed)
    for node in net.nodes_of(knockouts):
        consts[node] = 0                 # an intervention overrides a background lesion
    return consts


def _origins(net: BooleanNetwork, scenario: Scenario, knockouts: Iterable[str]) -> dict[str, str]:
    origin = {n: "scenario" for n in scenario.fixed}
    origin.update({n: "knockout" for n in net.nodes_of(knockouts)})
    return origin


_local = threading.local()


def _z3_context() -> z3.Context:
    """One Z3 context per thread: the default global context is not thread-safe."""
    ctx = getattr(_local, "ctx", None)
    if ctx is None:
        ctx = _local.ctx = z3.Context()
    return ctx


def _domain_clauses(net: BooleanNetwork, env: Mapping[str, z3.BoolRef]) -> list[z3.BoolRef]:
    return [z3.Implies(env[hi], env[med]) for hi, med in net.level_pairs()]


def z3_fixed_point(net: BooleanNetwork, constants: Mapping[str, int],
                   require: Mapping[str, int] | None = None,
                   violate: Mapping[str, int] | None = None,
                   timeout_ms: int = 5000) -> dict[str, int] | None | str:
    """A stable state satisfying ``require`` (all) and violating ``violate`` (any one).

    Returns the state, None if no such state exists (UNSAT) or "timeout".
    """
    ctx = _z3_context()
    env = {n: z3.Bool(n, ctx) for n in net.order}
    rules = net.to_z3(env)
    solver = z3.Solver(ctx=ctx)
    solver.set(timeout=timeout_ms)
    for n in net.order:
        solver.add(env[n] == (z3.BoolVal(bool(constants[n]), ctx) if n in constants else rules[n]))
    solver.add(*_domain_clauses(net, env))
    for n, v in (require or {}).items():
        solver.add(env[n] == bool(v))
    if violate:
        solver.add(z3.Or(*[env[n] != bool(v) for n, v in violate.items()]))
    res = solver.check()
    if res == z3.unsat:
        return None
    if res != z3.sat:
        return "timeout"
    model = solver.model()
    state = {n: int(z3.is_true(model.eval(env[n], model_completion=True))) for n in net.order}
    assert all(eval_expr(net.rules[n], state) == bool(state[n]) for n in net.order if n not in constants)
    return state


def all_z3_fixed_points(net: BooleanNetwork, constants: Mapping[str, int], limit: int = 200) -> list[dict[str, int]]:
    """Enumerate every stable state (used to cross-check the explicit engine)."""
    ctx = _z3_context()
    env = {n: z3.Bool(n, ctx) for n in net.order}
    rules = net.to_z3(env)
    solver = z3.Solver(ctx=ctx)
    for n in net.order:
        solver.add(env[n] == (z3.BoolVal(bool(constants[n]), ctx) if n in constants else rules[n]))
    solver.add(*_domain_clauses(net, env))
    found: list[dict[str, int]] = []
    while len(found) < limit and solver.check() == z3.sat:
        model = solver.model()
        state = {n: int(z3.is_true(model.eval(env[n], model_completion=True))) for n in net.order}
        found.append(state)
        solver.add(z3.Or(*[env[n] != bool(state[n]) for n in net.order]))
    return found


def _phenotype(values: Mapping[str, int | None]) -> dict[str, int | str]:
    return {k: ("oscillates" if values[k] is None else values[k]) for k in READOUTS if k in values}


def _meets_goal(values: Mapping[str, int | None], goal: Mapping[str, int]) -> bool:
    return all(values[n] == v for n, v in goal.items())


def _touches_goal(values: Mapping[str, int | None], goal: Mapping[str, int]) -> bool:
    return any(values[n] is None or values[n] == v for n, v in goal.items())


def _activity(net: BooleanNetwork, values: Mapping[str, int | None]) -> tuple[list[str], list[str]]:
    """Knockable genes that are active (some node on or oscillating) vs inactive in an attractor."""
    active, inactive = [], []
    for gene in net.knockable_genes():
        off = all(values[n] == 0 for n in net.genes[gene])
        (inactive if off else active).append(gene)
    return active, inactive


def _summarise(a: Attractor, ok: bool) -> dict:
    return {"kind": a.kind, "n_states": a.n_states, "phenotype": _phenotype(a.values),
            "oscillating_nodes": sorted(n for n, v in a.values.items() if v is None),
            "values": dict(a.values), "goal_satisfied": ok}


class Verifier:
    """Verifies knockout sets for one network and caches the results."""

    def __init__(self, net: BooleanNetwork):
        self.net = net
        self.calls = 0                   # solver invocations (cache misses)
        self._cache: dict[tuple, Verification] = {}

    def verify(self, scenario: Scenario, knockouts: Iterable[str]) -> Verification:
        kos = tuple(sorted(set(knockouts)))
        key = (scenario.name, kos)
        if key not in self._cache:
            self.calls += 1
            t0 = time.perf_counter()
            result = self._verify(scenario, kos)
            result.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            self._cache[key] = result
        return self._cache[key]

    def _verify(self, scenario: Scenario, kos: tuple[str, ...]) -> Verification:
        net = self.net
        consts = knockout_constants(net, scenario, kos)
        origin = _origins(net, scenario, kos)
        target = scenario.kind == "target"
        res = Verification(scenario.name, kos, UNKNOWN, "")

        # 1. Z3: a stable state that already breaks the property?
        if target:
            hit = z3_fixed_point(net, consts, violate=scenario.goal)
        else:
            hit = z3_fixed_point(net, consts, require=scenario.goal)
        if isinstance(hit, dict):
            res.verdict, res.method = (SURVIVES if target else TOXIC), "z3-stable-state"
            active, inactive = _activity(net, hit)
            res.counterexample = {
                "kind": "stable_state",
                "phenotype": {k: hit[k] for k in READOUTS if k in hit},
                "active_nodes": sorted(n for n in net.order if hit[n] and n not in net.outputs),
                "active_genes": active,
                "inactive_genes": inactive,
                "state": hit,
                "values": dict(hit),
                "why_goal_fails": render(justify(net, next(iter(scenario.goal)), hit, origin)) if target else "",
            }
            return res

        # 2. exact attractor analysis (also finds oscillating attractors)
        analysis = analyze(net, consts)
        if not analysis.complete:
            res.method = f"z3-only ({analysis.reason})"
            res.explanation = ("No stable state violates the property, but oscillating attractors "
                               "could not be excluded.")
            return res

        res.method = "exact-attractors+z3"
        res.n_attractors = len(analysis.attractors)
        ok_flags = []
        for a in analysis.attractors:
            ok = _meets_goal(a.values, scenario.goal) if target else not _touches_goal(a.values, scenario.goal)
            ok_flags.append(ok)
            res.attractors.append(_summarise(a, ok))

        if all(ok_flags):
            res.verdict = FORCED if target else SAFE
            goal_node = next(iter(scenario.goal))
            if target:
                res.trees = [justify(net, goal_node, a.samples[0], origin) for a in analysis.attractors[:3]]
                res.explanation = "\n\n".join(
                    f"Attractor {i + 1} ({a.kind}, {a.n_states} state(s)):\n" + render(tree)
                    for i, (a, tree) in enumerate(zip(analysis.attractors, res.trees)))
            return res

        bad = analysis.attractors[ok_flags.index(False)]
        res.verdict = SURVIVES if target else TOXIC
        active, inactive = _activity(net, bad.values)
        res.counterexample = {
            "kind": "stable_state" if bad.kind == "fixed" else "oscillating_attractor",
            "phenotype": _phenotype(bad.values),
            "active_nodes": sorted(n for n, v in bad.values.items() if v == 1 and n not in net.outputs),
            "oscillating_nodes": sorted(n for n, v in bad.values.items() if v is None),
            "active_genes": active,
            "inactive_genes": inactive,
            "n_states": bad.n_states,
            "values": dict(bad.values),
        }
        if bad.kind == "fixed":
            res.counterexample["state"] = bad.samples[0]
        if target and bad.kind == "fixed":
            res.counterexample["why_goal_fails"] = render(
                justify(net, next(iter(scenario.goal)), bad.samples[0], origin))
        return res


def stable_under(net: BooleanNetwork, state: Mapping[str, int], constants: Mapping[str, int]) -> bool:
    """Is ``state`` a stable state of the network with ``constants`` held fixed?

    This replays a stored counterexample against a new proposal: the check costs
    microseconds and needs no solver call.
    """
    for n, v in constants.items():
        if state[n] != v:
            return False
    return all(eval_expr(net.rules[n], state) == bool(state[n]) for n in net.order if n not in constants)
