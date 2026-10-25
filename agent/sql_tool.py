"""run_sql: the tool the LLM uses to ask the Zetaris data layer questions.

The model decides which SELECT statements it needs; this module checks them (read-only, only our three tables, one
statement, a row limit) and runs them through the Zetaris REST gateway. The agent never answers data questions from
memory: what it knows about druggability or regulators in a run comes from these results.
"""
from __future__ import annotations

import re
from typing import Any

from .tools_zetaris import DataLayer, ZetarisError

TABLES = ("p53_interactions", "druggability", "phenotypes")
ROW_LIMIT = 40
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|call|exec|union)\b", re.I)
_SOURCES = re.compile(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.I)
_LIMIT = re.compile(r"\blimit\s+\d+\s*$", re.I)


def schema_text(db: str) -> str:
    return (f"Database {db} (Spark SQL, read-only). Use the full names below.\n"
            f"- {db}.p53_interactions(node, gene, role, rule, regulators): the 35 Boolean update rules of the model. "
            "role is input|internal|output; regulators looks like 'TP53+;MDM2-' (+ activates, - inhibits)\n"
            f"- {db}.druggability(gene, protein, druggable, example_agents, evidence_level, note): druggable is "
            "yes|limited|indirect|no; evidence_level is approved|approved_other_indication|clinical|preclinical|none\n"
            f"- {db}.phenotypes(scenario_id, kind, description, fixed_nodes, goal, baseline_verdict, baseline_phenotype, source): "
            "scenario definitions and what the unperturbed cell does (no solutions)")


def check_sql(sql: str, db: str) -> str:
    """Return the statement ready to run, or raise ValueError saying what is wrong."""
    text = sql.strip().rstrip(";").strip()
    if ";" in text:
        raise ValueError("only one statement is allowed")
    if not re.match(r"select\b", text, re.I) or _FORBIDDEN.search(text):
        raise ValueError("only plain SELECT statements are allowed")
    allowed = {f"{db}.{t}".lower() for t in TABLES}
    sources = _SOURCES.findall(text)
    if not sources:
        raise ValueError("the query must read from one of the tables")
    for src in sources:
        if src.lower() not in allowed:
            raise ValueError(f"unknown table {src!r}; use one of: " + ", ".join(sorted(allowed)))
    return text if _LIMIT.search(text) else f"{text} LIMIT {ROW_LIMIT}"


def run_sql(layer: DataLayer, sql: str) -> dict[str, Any]:
    """{'ok': bool, 'sql': str, 'rows': [...], 'error': str}. Never raises."""
    db = layer.client.database
    try:
        checked = check_sql(sql, db)
    except ValueError as exc:
        return {"ok": False, "sql": sql, "rows": [], "error": str(exc)}
    if layer.source != "zetaris":
        return {"ok": False, "sql": checked, "rows": [], "error": "the data layer is the local CSV fallback, which has no SQL engine"}
    try:
        return {"ok": True, "sql": checked, "rows": layer._q(checked), "error": ""}
    except ZetarisError as exc:
        return {"ok": False, "sql": checked, "rows": [], "error": str(exc)[:200]}


def summarise(result: dict[str, Any], purpose: str, max_rows: int = 14) -> str:
    if not result["ok"]:
        return f"- {purpose}: query failed ({result['error']})"
    rows = result["rows"]
    if not rows:
        return f"- {purpose}: no rows"
    cols = list(rows[0])
    lines = [" | ".join(str(r.get(c, ""))[:60] for c in cols) for r in rows[:max_rows]]
    more = f" (+{len(rows) - max_rows} more)" if len(rows) > max_rows else ""
    return f"- {purpose} [{', '.join(cols)}]{more}:\n  " + "\n  ".join(lines)
