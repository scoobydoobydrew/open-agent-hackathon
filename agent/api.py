"""A programmatic entry point: one JSON payload in, one JSON report out (no UI needed).

    POST /run   {"scenario": "fgfr3_wtp53", "max_size": 3, "rounds": 4, "solutions": 3, "explain": true, "llm": true}

``llm: false`` (or SAMPLE_MODE, or no reachable provider) runs the symbolic search alone, which finds the same answers.
Limits are capped so that one request cannot run away: size <= 4, rounds <= 6, solutions <= 5.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .llm import ChatClient, LLMError, NemotronClient, NoLLM
from .main import CEGARAgent, to_markdown
from .tools_zetaris import DataLayer

MAX_SIZE, MAX_ROUNDS, MAX_SOLUTIONS = 4, 6, 5


def scenario_ids(data: DataLayer | None = None) -> list[str]:
    return sorted(r["scenario_id"] for r in (data or DataLayer()).scenarios() if r["kind"] != "safety")


def _bounded(payload: dict, key: str, default: int, cap: int) -> int:
    try:
        return max(1, min(int(payload.get(key, default)), cap))
    except (TypeError, ValueError):
        raise ValueError(f"{key!r} must be a whole number") from None


def run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the agent on one scenario and return ``{"report": ..., "markdown": ...}``; raises ValueError on bad input."""
    if not isinstance(payload, dict):
        raise ValueError("the payload must be a JSON object")
    data = DataLayer()
    valid = scenario_ids(data)
    sid = payload.get("scenario")
    if sid not in valid:
        raise ValueError(f"unknown scenario {sid!r}; choose one of {valid}")
    llm: ChatClient
    if payload.get("llm", True):
        try:
            llm = NemotronClient()
        except LLMError as exc:
            llm = NoLLM(str(exc))
    else:
        llm = NoLLM("llm disabled in the request")
    agent = CEGARAgent(llm, data, memory_mode="session", max_size=_bounded(payload, "max_size", 3, MAX_SIZE),
                       max_rounds=_bounded(payload, "rounds", 4, MAX_ROUNDS), per_round=3,
                       target_solutions=_bounded(payload, "solutions", 3, MAX_SOLUTIONS),
                       explain=bool(payload.get("explain", True)), sql_tool=True, log=lambda _: None)
    report = agent.run(sid)
    return {"report": asdict(report), "markdown": to_markdown(report)}
