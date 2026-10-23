"""Derivation trees: why does a node hold its value in a given stable state?

A justification keeps only the literals that are needed for the value (one false
conjunct for a false AND, one true disjunct for a true OR, ...), so the result
reads as a cause chain back to interventions and inputs instead of a dump of the
whole state.
"""
from __future__ import annotations

import re
from typing import Mapping

from .boolean_net import BooleanNetwork, Expr, eval3, eval_expr

_MAX_DEPTH = 8


def _literals(expr: Expr, want: bool, state: Mapping[str, int]) -> list[tuple[str, int]]:
    """Smallest set of (node, value) literals of ``state`` that makes expr evaluate to ``want``."""
    kind = expr[0]
    if kind == "var":
        return [(expr[1], int(state[expr[1]]))]
    if kind == "const":
        return []
    if kind == "not":
        return _literals(expr[1], not want, state)

    parts = expr[1]
    needs_all = (kind == "and") == want          # AND true, or OR false
    if needs_all:
        out: list[tuple[str, int]] = []
        for e in parts:
            for lit in _literals(e, want if kind == "and" else False, state):
                if lit not in out:
                    out.append(lit)
        return out
    witness = [e for e in parts if eval_expr(e, state) == want]
    options = [_literals(e, want, state) for e in witness]
    return min(options, key=len) if options else []


def justify(net: BooleanNetwork, node: str, state: Mapping[str, int],
            origin: Mapping[str, str], depth: int = 0, explained: set[str] | None = None) -> dict:
    """Nested dict {node, value, origin?, because: [...]} explaining ``node`` in ``state``.

    ``origin`` maps nodes to what fixed them from outside ('knockout' or
    'scenario'); those are leaves of the derivation. Each node is expanded only
    the first time it appears; later mentions point back to it, so feedback
    loops and shared causes do not blow the tree up.
    """
    explained = set() if explained is None else explained
    value = int(state[node])
    tree: dict = {"node": node, "value": value}
    if node in origin:
        tree["origin"] = origin[node]
        return tree
    if node in explained:
        tree["note"] = "see above"
        return tree
    explained.add(node)
    if depth >= _MAX_DEPTH:
        tree["note"] = "chain cut here"
        return tree
    tree["rule"] = net.specs[node].rule
    lits = _literals(net.rules[node], bool(value), state)
    tree["because"] = [justify(net, n, state, origin, depth + 1, explained) for n, _ in lits]
    return tree


def render(tree: dict, indent: int = 0) -> str:
    pad = "  " * indent
    head = f"{pad}{tree['node']} = {tree['value']}"
    if "origin" in tree:
        head += f"  [{tree['origin']}]"
    if "note" in tree:
        head += f"  ({tree['note']})"
    lines = [head]
    for child in tree.get("because", []):
        lines.append(render(child, indent + 1))
    return "\n".join(lines)


def steps_from_tree(tree: dict, limit: int = 30) -> list[dict]:
    """Flatten a derivation into numbered steps, causes before effects.

    Each step reads: premises (node=value literals) => node=value, by the node's rule.
    """
    steps: list[dict] = []

    def walk(t: dict) -> None:
        for child in t.get("because", []):
            walk(child)
        if t.get("because"):
            steps.append({"id": len(steps) + 1, "node": t["node"], "value": t["value"],
                          "premises": [(c["node"], c["value"]) for c in t["because"]], "rule": t["rule"]})

    walk(tree)
    return steps[:limit]


def step_entailed(net: BooleanNetwork, step: Mapping, known: Mapping[str, int]) -> bool:
    """Do the premises (plus the experiment's fixed nodes) force the conclusion through its rule?"""
    val: dict[str, int | None] = {n: None for n in net.order}
    val.update(known)
    val.update(dict(step["premises"]))
    return eval3(net.rules[step["node"]], val) == step["value"]


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def ungrounded_mentions(net: BooleanNetwork, text: str, allowed: set[str]) -> list[str]:
    """Node or gene names used in ``text`` that are not covered by the selected derivation steps."""
    known = set(net.order) | set(net.genes)
    gene_of = {n: net.specs[n].gene for n in net.order}
    cover = set(allowed) | {gene_of[n] for n in allowed if n in gene_of}
    return sorted({w for w in _WORD.findall(text) if w in known and w not in cover})
