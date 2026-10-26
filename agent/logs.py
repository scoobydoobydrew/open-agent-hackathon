"""JSONL evidence written to ``logs/``: how the agent reached its output, request by request.

Files (all append-only JSONL, no prompts and no secrets):
  logs/llm-trace.jsonl                       one line per LLM request: provider, requested and routed model, latency, tokens
  logs/hmem-retrieval.jsonl                  one line per H-MEM retrieval: query, strategy, ranked memories, what was injected
  logs/<scenario>-<run>.events.jsonl         every proposal, verdict, SQL call, search milestone and LLM request of one run
  logs/<scenario>-<run>.hmem-ledger.jsonl    the H-MEM audit ledger as it stood at the end of that run

``AGENT_LOG_DIR`` moves the directory; ``AGENT_LOG_DIR=off`` disables logging (benchmarks and tests use this).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent


def log_dir() -> Path | None:
    raw = os.getenv("AGENT_LOG_DIR", "").strip()
    if raw.lower() == "off":
        return None
    return Path(raw) if raw else ROOT / "logs"


def log_path(name: str) -> Path | None:
    d = log_dir()
    return None if d is None else d / name


def append_jsonl(name: str, record: dict[str, Any]) -> None:
    """Append one record; a log must never break a run, so failures are swallowed."""
    path = log_path(name)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def write_jsonl(name: str, records: Iterable[dict[str, Any]]) -> Path | None:
    """Replace a log file with ``records`` (used for the per-run files, which are written once at the end of a run)."""
    path = log_path(name)
    if path is None:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError:
        return None
    return path
