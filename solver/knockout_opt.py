"""Exhaustive search for minimal knockout sets (ground truth and baseline).

Sets are tried by increasing size; a set containing an already verified
solution is skipped, so every returned set is minimal. This is the exact
reference the LLM agent is benchmarked against.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .verifier import FORCED, SAFE, Scenario, Verifier


@dataclass
class SearchResult:
    scenario: str
    max_size: int
    solutions: list[tuple[str, ...]] = field(default_factory=list)
    evaluated: int = 0
    pruned: int = 0
    seconds: float = 0.0


def candidate_genes(verifier: Verifier, scenario: Scenario) -> list[str]:
    """Knockable genes that actually change something in this scenario."""
    net = verifier.net
    out = []
    for gene in net.knockable_genes():
        nodes = net.genes[gene]
        if all(scenario.fixed.get(n) == 0 for n in nodes):
            continue                      # already lost in this background
        out.append(gene)
    return out


def minimal_knockouts(verifier: Verifier, scenario: Scenario, max_size: int = 3,
                      candidates: Sequence[str] | None = None) -> SearchResult:
    genes = list(candidates) if candidates is not None else candidate_genes(verifier, scenario)
    result = SearchResult(scenario.name, max_size)
    t0 = time.perf_counter()
    for size in range(0, max_size + 1):
        for combo in itertools.combinations(genes, size):
            if any(set(sol) <= set(combo) for sol in result.solutions):
                result.pruned += 1
                continue
            result.evaluated += 1
            if verifier.verify(scenario, combo).verdict == FORCED:
                result.solutions.append(combo)
    result.seconds = round(time.perf_counter() - t0, 2)
    return result


def is_safe(verifier: Verifier, safety: Iterable[Scenario], knockouts: Iterable[str]) -> bool:
    kos = tuple(knockouts)
    return all(verifier.verify(s, kos).verdict == SAFE for s in safety)
