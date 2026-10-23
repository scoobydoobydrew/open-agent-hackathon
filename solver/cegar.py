"""Counterexample-guided search for minimal knockout sets (complete, no LLM needed).

Why extending by active genes is complete
-----------------------------------------
Let K fail, and let A be the surviving state the solver returns for K. If a larger set K' only adds genes that are
already inactive in A, then A is still a surviving state of K', so K' fails too. Hence every working superset of K
contains at least one gene that is ACTIVE in A. A minimal solution K* has only failing proper subsets, so walking
from the empty set and extending each failing set by each of its active genes reaches K* (induction on the chain
of subsets of K*). The search therefore finds every minimal solution up to the size limit, and when the frontier
runs dry it has proved that none exists. Memory replay (a stored surviving state that is still stable under a new
set) only skips calls and supplies a valid surviving state, so completeness is kept.

The search is incremental so an LLM can steer it: ``prioritise`` puts the failures of its proposals at the front of
the queue and ``advance`` spends a budget of solver calls.
"""
from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from .verifier import FORCED, SURVIVES, Scenario, Verification, Verifier

Refuter = Callable[[Scenario, tuple[str, ...]], "dict | None"]


@dataclass
class Found:
    knockouts: tuple[str, ...]
    verification: Verification


class CegarSearch:
    def __init__(self, verifier: Verifier, scenario: Scenario, max_size: int = 3,
                 candidates: Sequence[str] | None = None, refute: Refuter | None = None,
                 on_failure: Callable[[tuple[str, ...], Verification], None] | None = None,
                 on_event: Callable[[dict], None] | None = None):
        self.verifier, self.scenario, self.max_size = verifier, scenario, max_size
        self.on_event = on_event
        self.candidates = set(candidates) if candidates is not None else set(verifier.net.knockable_genes())
        self.refute, self.on_failure = refute, on_failure
        self.frontier: deque[tuple[tuple[str, ...], list[str]]] = deque()   # (failing set, its active genes)
        self.seen: set[tuple[str, ...]] = {()}
        self.solutions: list[Found] = []
        self.incomplete = False                  # a verdict was UNKNOWN, so completeness is not guaranteed
        self.calls = 0                           # solver calls made by this search
        self.replays = 0                         # sets refuted from memory without a solver call
        self._started = False
        self._pending: deque[tuple[tuple[str, ...], tuple[str, ...]]] = deque()   # (child, parent)
        self._via = "solver"
        self._announced_end = False

    # -- state -----------------------------------------------------------------------------------
    @property
    def exhausted(self) -> bool:
        return self._started and not self.frontier and not self._pending

    @property
    def proved_infeasible(self) -> bool:
        return self.exhausted and not self.solutions and not self.incomplete

    def _evaluate(self, kos: tuple[str, ...]) -> tuple[str, list[str]]:
        """Verdict and the active genes of a surviving state (empty list when forced)."""
        if self.refute is not None:
            ref = self.refute(self.scenario, kos)
            if ref is not None:
                self.replays += 1
                self._via = "memory"
                return SURVIVES, list(ref["active_genes"])
        self._via = "solver"
        before = self.verifier.calls
        res = self.verifier.verify(self.scenario, kos)
        if res.verdict == FORCED:
            return FORCED, []
        if res.verdict == SURVIVES:
            if self.on_failure is not None and self.verifier.calls > before:
                self.on_failure(kos, res)
            return SURVIVES, list(res.counterexample["active_genes"])
        self.incomplete = True
        return res.verdict, []

    def _is_minimal(self, kos: tuple[str, ...]) -> bool:
        for size in range(0, len(kos)):
            for sub in itertools.combinations(kos, size):
                if self.verifier.verify(self.scenario, sub).verdict == FORCED:
                    return False
        return True

    def _visit(self, kos: tuple[str, ...], parent: tuple[str, ...] | None = None) -> Found | None:
        calls0 = self.verifier.calls
        found: Found | None = None
        try:
            verdict, active = self._evaluate(kos)
            if verdict == FORCED:
                if self._is_minimal(kos) and kos not in {s.knockouts for s in self.solutions}:
                    found = Found(kos, self.verifier.verify(self.scenario, kos))
                    self.solutions.append(found)
            elif verdict == SURVIVES and len(kos) < self.max_size:
                self.frontier.append((kos, active))
            return found
        finally:
            self.calls += self.verifier.calls - calls0
            self._emit("visit", kos=list(kos), parent=None if parent is None else list(parent), verdict=verdict,
                       via=self._via, active=active, solution=found is not None)

    def _emit(self, kind: str, **data) -> None:
        if self.on_event is not None:
            self.on_event({"type": kind, "calls": self.calls, "replays": self.replays,
                           "frontier": len(self.frontier) + len(self._pending),
                           "solutions": len(self.solutions), **data})

    # -- steering --------------------------------------------------------------------------------
    def prioritise(self, kos: Iterable[str], active_genes: Iterable[str]) -> None:
        """Expand this failing set first (used for the failures of LLM proposals)."""
        kos = tuple(sorted(kos))
        if len(kos) < self.max_size:
            self.seen.add(kos)
            self.frontier.appendleft((kos, list(active_genes)))

    def advance(self, call_budget: int | None = None, want: int | None = None) -> list[Found]:
        """Expand the frontier until the budget (solver calls) is spent, ``want`` solutions exist or it is empty."""
        found: list[Found] = []
        spent0 = self.calls
        if not self._started:
            self._started = True
            first = self._visit((), None)
            if first:
                found.append(first)
        while self.frontier or self._pending:
            if call_budget is not None and self.calls - spent0 >= call_budget:
                break
            if want is not None and len(self.solutions) >= want:
                break
            if not self._pending:
                kos, active = self.frontier.popleft()
                for gene in active:
                    if gene in kos or gene not in self.candidates:
                        continue
                    child = tuple(sorted((*kos, gene)))
                    if child not in self.seen:
                        self.seen.add(child)
                        self._pending.append((child, kos))
                continue
            child, parent = self._pending.popleft()
            hit = self._visit(child, parent)
            if hit:
                found.append(hit)
        if self.exhausted and not self._announced_end:
            self._announced_end = True
            self._emit("exhausted", proved_infeasible=self.proved_infeasible)
        return found
