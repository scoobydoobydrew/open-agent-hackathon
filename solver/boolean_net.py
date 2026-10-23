"""Boolean network model: rule parsing, evaluation and Z3 encoding.

Rules use the .bnet operators (``!``, ``&``, ``|``, parentheses) and are parsed
into a small AST, so no rule text is ever passed to ``eval``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

import z3

# AST: ("var", name) | ("const", bool) | ("not", e) | ("and", [e, ...]) | ("or", [e, ...])
Expr = tuple

_TOKEN = re.compile(r"\s*(?:([A-Za-z_][A-Za-z0-9_]*)|([01])|([()!&|]))")

INPUT, INTERNAL, OUTPUT = "input", "internal", "output"


def _tokenize(text: str) -> list[str]:
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"unexpected character {text[pos]!r} in rule {text!r}")
        tokens.append(m.group(m.lastindex))
        pos = m.end()
    return tokens


def parse_rule(text: str) -> Expr:
    tokens = _tokenize(text)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError(f"unexpected end of rule {text!r}")
        pos += 1
        return tokens[pos - 1]

    def parse_or() -> Expr:
        terms = [parse_and()]
        while peek() == "|":
            take()
            terms.append(parse_and())
        return terms[0] if len(terms) == 1 else ("or", terms)

    def parse_and() -> Expr:
        terms = [parse_not()]
        while peek() == "&":
            take()
            terms.append(parse_not())
        return terms[0] if len(terms) == 1 else ("and", terms)

    def parse_not() -> Expr:
        if peek() == "!":
            take()
            return ("not", parse_not())
        return parse_atom()

    def parse_atom() -> Expr:
        tok = peek()
        if tok is None:
            raise ValueError(f"unexpected end of rule {text!r}")
        take()
        if tok == "(":
            inner = parse_or()
            if take() != ")":
                raise ValueError(f"missing ')' in rule {text!r}")
            return inner
        if tok in ("0", "1"):
            return ("const", tok == "1")
        if tok in ")!&|":
            raise ValueError(f"unexpected {tok!r} in rule {text!r}")
        return ("var", tok)

    expr = parse_or()
    if pos != len(tokens):
        raise ValueError(f"trailing tokens in rule {text!r}")
    return expr


def expr_vars(expr: Expr) -> set[str]:
    kind = expr[0]
    if kind == "var":
        return {expr[1]}
    if kind == "const":
        return set()
    if kind == "not":
        return expr_vars(expr[1])
    return set().union(*(expr_vars(e) for e in expr[1]))


def eval_expr(expr: Expr, state: Mapping[str, int | bool]) -> bool:
    kind = expr[0]
    if kind == "var":
        return bool(state[expr[1]])
    if kind == "const":
        return expr[1]
    if kind == "not":
        return not eval_expr(expr[1], state)
    if kind == "and":
        return all(eval_expr(e, state) for e in expr[1])
    return any(eval_expr(e, state) for e in expr[1])


def eval3(expr: Expr, val: Mapping[str, int | None]) -> int | None:
    """Kleene three-valued evaluation; None means undetermined."""
    kind = expr[0]
    if kind == "var":
        return val[expr[1]]
    if kind == "const":
        return int(expr[1])
    if kind == "not":
        x = eval3(expr[1], val)
        return None if x is None else 1 - x
    parts = [eval3(e, val) for e in expr[1]]
    if kind == "and":
        if 0 in parts:
            return 0
        return 1 if all(p == 1 for p in parts) else None
    if 1 in parts:
        return 1
    return 0 if all(p == 0 for p in parts) else None


def expr_to_z3(expr: Expr, env: Mapping[str, z3.BoolRef]) -> z3.BoolRef:
    kind = expr[0]
    if kind == "var":
        return env[expr[1]]
    if kind == "const":
        return z3.BoolVal(expr[1], next(iter(env.values())).ctx)
    if kind == "not":
        return z3.Not(expr_to_z3(expr[1], env))
    args = [expr_to_z3(e, env) for e in expr[1]]
    return z3.And(*args) if kind == "and" else z3.Or(*args)


def expr_to_str(expr: Expr) -> str:
    kind = expr[0]
    if kind == "var":
        return expr[1]
    if kind == "const":
        return "1" if expr[1] else "0"
    if kind == "not":
        return "!" + expr_to_str(expr[1])
    sep = " & " if kind == "and" else " | "
    return "(" + sep.join(expr_to_str(e) for e in expr[1]) + ")"


@dataclass(frozen=True)
class NodeSpec:
    name: str
    gene: str
    role: str
    rule: str


class BooleanNetwork:
    """A Boolean network where every node has one update rule.

    ``gene`` groups the booleanized levels of one gene (``E2F1_medium`` and
    ``E2F1_high`` both belong to ``E2F1``); a knockout acts on whole genes.
    """

    def __init__(self, nodes: Iterable[NodeSpec]):
        self.specs: dict[str, NodeSpec] = {}
        for spec in nodes:
            if spec.name in self.specs:
                raise ValueError(f"duplicate node {spec.name}")
            if spec.role not in (INPUT, INTERNAL, OUTPUT):
                raise ValueError(f"bad role {spec.role!r} for {spec.name}")
            self.specs[spec.name] = spec
        self.order: list[str] = list(self.specs)
        self.rules: dict[str, Expr] = {n: parse_rule(s.rule) for n, s in self.specs.items()}
        for name, rule in self.rules.items():
            unknown = expr_vars(rule) - set(self.specs)
            if unknown:
                raise ValueError(f"rule of {name} uses unknown nodes {sorted(unknown)}")
        self.genes: dict[str, list[str]] = {}
        for spec in self.specs.values():
            self.genes.setdefault(spec.gene, []).append(spec.name)

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping[str, str]]) -> "BooleanNetwork":
        """Build from dict rows with keys node, gene, role, rule (CSV or SQL result)."""
        return cls(NodeSpec(r["node"].strip(), r["gene"].strip(), r["role"].strip(), r["rule"].strip())
                   for r in rows)

    @property
    def inputs(self) -> list[str]:
        return [n for n, s in self.specs.items() if s.role == INPUT]

    @property
    def outputs(self) -> list[str]:
        return [n for n, s in self.specs.items() if s.role == OUTPUT]

    def knockable_genes(self) -> list[str]:
        """Genes that can be knocked out: every node of the gene is internal."""
        return sorted(g for g, nodes in self.genes.items()
                      if all(self.specs[n].role == INTERNAL for n in nodes))

    def nodes_of(self, genes: Iterable[str]) -> list[str]:
        out: list[str] = []
        for g in genes:
            if g not in self.genes:
                raise KeyError(f"unknown gene {g!r}")
            out.extend(self.genes[g])
        return out

    def regulators(self, node: str) -> set[str]:
        return expr_vars(self.rules[node])

    def update(self, node: str, state: Mapping[str, int | bool]) -> bool:
        return eval_expr(self.rules[node], state)

    def to_z3(self, env: Mapping[str, z3.BoolRef]) -> dict[str, z3.BoolRef]:
        return {n: expr_to_z3(r, env) for n, r in self.rules.items()}

    def level_pairs(self) -> list[tuple[str, str]]:
        """(X_high, X_medium) pairs of a booleanized multi-level gene.

        The encoding only makes sense when X_high implies X_medium, so state
        spaces are restricted to states that respect it.
        """
        return [(n, n[: -len("_high")] + "_medium") for n in self.order
                if n.endswith("_high") and n[: -len("_high")] + "_medium" in self.specs]

    def percolate(self, constants: Mapping[str, int]) -> dict[str, int]:
        """Nodes whose value is forced by ``constants`` whatever the other nodes do.

        Three-valued simulation: a node is forced when its rule is decided by
        the already-forced nodes. In every trajectory these nodes freeze after a
        finite time, so all attractors lie inside the returned subspace.
        """
        for n in constants:
            if n not in self.specs:
                raise KeyError(f"unknown node {n!r}")
        val: dict[str, int | None] = {n: None for n in self.order}
        val.update({n: int(v) for n, v in constants.items()})
        changed = True
        while changed:
            changed = False
            for n in self.order:
                if val[n] is None:
                    x = eval3(self.rules[n], val)
                    if x is not None:
                        val[n] = x
                        changed = True
        return {n: v for n, v in val.items() if v is not None}

    def edge_signs(self) -> list[tuple[str, str, str]]:
        """(source, target, sign) derived from the rules by truth-table testing.

        sign is '+' (activates), '-' (inhibits) or '+/-' (context dependent).
        """
        edges = []
        for target in self.order:
            regs = sorted(self.regulators(target))
            for src in regs:
                others = [r for r in regs if r != src]
                pos = neg = False
                for mask in range(1 << len(others)):
                    ctx = {r: bool(mask >> i & 1) for i, r in enumerate(others)}
                    lo = eval_expr(self.rules[target], {**ctx, src: False})
                    hi = eval_expr(self.rules[target], {**ctx, src: True})
                    pos |= hi and not lo
                    neg |= lo and not hi
                if pos or neg:
                    edges.append((src, target, "+/-" if pos and neg else "+" if pos else "-"))
        return edges
