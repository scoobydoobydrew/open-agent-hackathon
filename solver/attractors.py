"""Exact attractor analysis of a Boolean network under asynchronous updates.

Constants (scenario + knockouts) are percolated first, nodes that nothing
depends on are evaluated on demand instead of being enumerated, and the
remaining state space is searched explicitly: attractors are the terminal
strongly connected components of the asynchronous state transition graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import reduce
from typing import Mapping

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .boolean_net import BooleanNetwork, Expr

MAX_STATE_BITS = 21
SAMPLE_STATES = 3


@dataclass
class Attractor:
    kind: str                        # "fixed" or "cyclic"
    n_states: int                    # states of the enumerated nodes (derived leaves excluded)
    values: dict[str, int | None]    # 0/1 when constant on the attractor, None if it varies
    samples: list[dict[str, int]]    # a few full states of the attractor


@dataclass
class AttractorAnalysis:
    complete: bool
    constants: dict[str, int]        # forced nodes (given constants and percolated ones)
    state_nodes: list[str]           # nodes that were enumerated
    attractors: list[Attractor] = field(default_factory=list)
    reason: str = ""


def _eval_np(expr: Expr, env: Mapping[str, object]):
    kind = expr[0]
    if kind == "var":
        return env[expr[1]]
    if kind == "const":
        return np.bool_(expr[1])
    if kind == "not":
        return np.logical_not(_eval_np(expr[1], env))
    args = [_eval_np(e, env) for e in expr[1]]
    return reduce(np.logical_and if kind == "and" else np.logical_or, args)


def _trim_leaves(net: BooleanNetwork, free: list[str]) -> tuple[list[str], list[str]]:
    """Split free nodes into enumerated ones and derived leaves.

    A leaf has no dependents and no self-regulation, so its value is a function
    of the rest and does not need a state bit. Returned ``derived`` lists leaves
    in the order they must be evaluated.
    """
    state = list(free)
    removed: list[str] = []
    changed = True
    while changed:
        changed = False
        dependents = {n: False for n in state}
        for m in state:
            for r in net.regulators(m):
                if r != m and r in dependents:
                    dependents[r] = True
        for n in list(state):
            if not dependents[n] and n not in net.regulators(n):
                state.remove(n)
                removed.append(n)
                changed = True
    return state, removed[::-1]


def analyze(net: BooleanNetwork, constants: Mapping[str, int],
            max_bits: int = MAX_STATE_BITS) -> AttractorAnalysis:
    forced = net.percolate(constants)
    free = [n for n in net.order if n not in forced]
    state_nodes, derived = _trim_leaves(net, free)
    n = len(state_nodes)
    if n > max_bits:
        return AttractorAnalysis(False, forced, state_nodes,
                                 reason=f"{n} free nodes after reduction (limit {max_bits})")

    size = 1 << n
    idx = np.arange(size, dtype=np.int64)
    bits = {nm: ((idx >> i) & 1).astype(bool) for i, nm in enumerate(state_nodes)}
    env: dict[str, object] = {nm: np.bool_(v) for nm, v in forced.items()}
    env.update(bits)

    domain = np.ones(size, dtype=bool)
    for hi, med in net.level_pairs():
        domain &= np.logical_or(np.logical_not(env.get(hi, np.bool_(0))), env.get(med, np.bool_(1)))

    src_parts, dst_parts = [], []
    for i, nm in enumerate(state_nodes):
        unstable = np.logical_xor(_eval_np(net.rules[nm], env), bits[nm]) & domain
        s = np.nonzero(unstable)[0]
        src_parts.append(s)
        dst_parts.append(s ^ (1 << i))
    src = np.concatenate(src_parts) if src_parts else np.empty(0, dtype=np.int64)
    dst = np.concatenate(dst_parts) if dst_parts else np.empty(0, dtype=np.int64)
    if len(src) and not domain[dst].all():
        return AttractorAnalysis(False, forced, state_nodes,
                                 reason="level-consistent states are not closed under updates")

    graph = csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(size, size))
    n_comp, labels = connected_components(graph, directed=True, connection="strong")
    non_terminal = np.zeros(n_comp, dtype=bool)
    crossing = labels[src] != labels[dst]
    non_terminal[labels[src[crossing]]] = True

    in_attractor = domain & ~non_terminal[labels]
    ids = np.nonzero(in_attractor)[0]
    order = np.argsort(labels[ids], kind="stable")
    ids = ids[order]
    boundaries = np.nonzero(np.diff(labels[ids]))[0] + 1 if len(ids) else np.empty(0, dtype=np.int64)
    groups = np.split(ids, boundaries) if len(ids) else []

    attractors = [_describe(net, g, state_nodes, forced, derived) for g in groups]
    attractors.sort(key=lambda a: (a.kind != "fixed", a.n_states))
    return AttractorAnalysis(True, forced, state_nodes, attractors)


def _describe(net: BooleanNetwork, states: np.ndarray, state_nodes: list[str],
              forced: Mapping[str, int], derived: list[str]) -> Attractor:
    env: dict[str, object] = {nm: np.bool_(v) for nm, v in forced.items()}
    for i, nm in enumerate(state_nodes):
        env[nm] = ((states >> i) & 1).astype(bool)
    for nm in derived:
        env[nm] = np.broadcast_to(_eval_np(net.rules[nm], env), states.shape)

    values: dict[str, int | None] = {}
    for nm in net.order:
        col = env[nm]
        if np.ndim(col) == 0:
            values[nm] = int(col)
        else:
            col = np.asarray(col)
            values[nm] = int(col[0]) if (col == col[0]).all() else None
    samples = []
    for k in range(min(SAMPLE_STATES, len(states))):
        samples.append({nm: int(np.asarray(env[nm]).reshape(-1)[k] if np.ndim(env[nm]) else env[nm])
                        for nm in net.order})
    return Attractor("fixed" if len(states) == 1 else "cyclic", len(states), values, samples)
