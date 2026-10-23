"""Memory-mining prompt (AGENTS.md section 4.1): an event-specific extraction prompt, a strict JSON array of memory
strings, tolerant parsing and validation. Only the ``plan_completion`` event is used here: the agent finishes a plan
(a search for knockouts) and the miner distils reusable lessons from it.
"""
from __future__ import annotations

import json
import re

MIN_LENGTH = 20
MAX_ITEMS = 5

MINING_SYSTEM = (
    "You are the background memory miner of a research agent that searches for gene knockouts. "
    "You only receive verified results from an exact solver. Extract short, reusable, factual lessons that would help "
    "choose better knockouts next time. State only what the evidence supports. "
    "Reply with a strict JSON array of strings and nothing else."
)

MINING_PLAN_COMPLETION = """A plan has just been completed. Verified results (newest last):

{evidence}

Extract at most {max_items} reusable lessons. Each lesson is one self-contained sentence that names the genes and the
conditions it applies to. Reply with exactly this format: ["lesson one", "lesson two"]"""


def parse_strict_json_array(text: str) -> list[str]:
    """Tolerant parse: strip markdown fences, find the first array, keep valid strings only."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    candidates = [cleaned]
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            value = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            return [v.strip() for v in value if isinstance(v, str) and len(v.strip()) >= MIN_LENGTH][:MAX_ITEMS]
    return []
