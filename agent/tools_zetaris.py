"""Data-layer tool: fetch the network, scenarios and drug annotations from Zetaris with SQL.

Zetaris is reached through the web gateway: log in at /api/auth/login, then run
SELECT statements through /api/proxy/query/sql/start with the bearer token and
organisation id. If the gateway or the tables are unavailable the tool can fall
back to the CSV files in data/, so tests and offline runs keep working; every
result says which source it came from.
"""
from __future__ import annotations

import csv
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .logs import append_jsonl

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TABLE_FILES = {"p53_interactions": "p53_interactions.csv", "phenotypes": "phenotypes.csv",
               "druggability": "druggability.csv"}
_SELECT_ONLY = re.compile(r"^\s*(with|select)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge)\b", re.IGNORECASE)


class ZetarisError(RuntimeError):
    pass


def _short(exc: Exception, limit: int = 110) -> str:
    first = (str(exc).splitlines() or [""])[0]
    return first if len(first) <= limit else first[: limit - 1] + "…"


class ZetarisClient:
    def __init__(self, base_url: str | None = None, user: str | None = None, password: str | None = None,
                 database: str | None = None, timeout: int = 20):
        self.base_url = (base_url or os.getenv("ZETARIS_GATEWAY_URL") or "http://localhost:3000").rstrip("/")
        self.user = user or os.getenv("ZETARIS_USER", "")
        self.password = password or os.getenv("ZETARIS_PASS", "")
        self.database = database or os.getenv("ZETARIS_DB", "open_agent")
        self.timeout = timeout
        self._auth: dict[str, str] | None = None

    def _login(self) -> dict[str, str]:
        if not (self.user and self.password):
            raise ZetarisError("ZETARIS_USER / ZETARIS_PASS are not set")
        try:
            r = requests.post(f"{self.base_url}/api/auth/login",
                              json={"username": self.user, "password": self.password}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ZetarisError(f"cannot reach Zetaris at {self.base_url}: {exc}") from exc
        if r.status_code != 200:
            raise ZetarisError(f"Zetaris login failed (HTTP {r.status_code})")
        body = r.json()
        return {"Authorization": f"Bearer {body['idToken']}", "X-Org-ID": str(body["orgId"])}

    def query(self, sql: str, page_limit: int = 1000) -> list[dict[str, Any]]:
        """Run one read-only statement and return its rows (values arrive as strings)."""
        if not _SELECT_ONLY.match(sql) or _FORBIDDEN.search(sql):
            raise ZetarisError("only read-only SELECT statements are allowed")
        if self._auth is None:
            self._auth = self._login()
        headers = {**self._auth, "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json"}
        try:
            r = requests.post(f"{self.base_url}/api/proxy/query/sql/start", headers=headers,
                              json={"select": sql, "pageLimit": page_limit}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ZetarisError(f"Zetaris query failed: {exc}") from exc
        if r.status_code == 401:
            self._auth = None
        if r.status_code != 200:
            raise ZetarisError(f"Zetaris query error (HTTP {r.status_code}): {r.text[:300]}")
        body = r.json()
        if body.get("totalPages", 1) > 1:
            raise ZetarisError("result spans several pages; narrow the query")
        return body["records"]

    def table(self, name: str) -> str:
        return f"{self.database}.{name}"


class DataLayer:
    """Zetaris first, local CSV as an explicit fallback."""

    def __init__(self, client: ZetarisClient | None = None, allow_fallback: bool = True):
        self.client = client or ZetarisClient()
        self.allow_fallback = allow_fallback
        self.source = "unknown"
        self._down_until = 0.0

    def _q(self, sql: str):
        """Query Zetaris; after a failure skip it for a minute so one outage costs one timeout, not one per query."""
        if os.getenv("SAMPLE_MODE", "").strip().lower() in ("1", "true", "yes", "on"):
            raise ZetarisError("SAMPLE_MODE is on")
        if time.time() < self._down_until:
            raise ZetarisError("Zetaris was unreachable a moment ago")
        t0 = time.perf_counter()
        try:
            rows = self.client.query(sql)
        except ZetarisError as exc:
            self._down_until = time.time() + 60
            append_jsonl("zetaris-calls.jsonl", {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "ok": False, "sql": sql[:400],
                                                 "error": str(exc)[:200], "ms": round((time.perf_counter() - t0) * 1000)})
            raise
        append_jsonl("zetaris-calls.jsonl", {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "ok": True, "sql": sql[:400],
                                             "rows": len(rows), "ms": round((time.perf_counter() - t0) * 1000)})
        return rows

    def _local(self, table: str) -> list[dict[str, str]]:
        with (DATA_DIR / TABLE_FILES[table]).open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def select(self, sql_template: str, table: str) -> list[dict[str, Any]]:
        """Run ``sql_template`` (with {t} for the table) on Zetaris, else read the CSV."""
        try:
            rows = self._q(sql_template.format(t=self.client.table(table)))
            self.source = "zetaris"
            return rows
        except ZetarisError as exc:
            if not self.allow_fallback:
                raise
            self.source = f"local-csv (zetaris unavailable: {_short(exc)})"
            return self._local(table)

    # -- queries the agent uses ---------------------------------------------------------------
    def network_rows(self) -> list[dict[str, Any]]:
        return self.select("SELECT node, gene, role, rule, regulators FROM {t}", "p53_interactions")

    def scenarios(self) -> list[dict[str, Any]]:
        rows = self.select("SELECT * FROM {t} WHERE kind <> 'reference'", "phenotypes")
        return [r for r in rows if r["kind"] != "reference"]

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        safe = re.sub(r"[^A-Za-z0-9_]", "", scenario_id)
        rows = self.select(f"SELECT * FROM {{t}} WHERE scenario_id = '{safe}'", "phenotypes")
        rows = [r for r in rows if r["scenario_id"] == safe]
        if not rows:
            raise KeyError(f"unknown scenario {scenario_id!r}")
        return rows[0]

    def druggability(self) -> list[dict[str, Any]]:
        return self.select("SELECT gene, protein, druggable, example_agents, evidence_level, note FROM {t}",
                           "druggability")

    def drug_ranking_join(self) -> list[dict[str, Any]]:
        """Knockable genes joined with their drug annotation (the join the agent reasons over)."""
        sql = ("SELECT i.gene, d.druggable, d.evidence_level, d.example_agents "
               "FROM (SELECT DISTINCT gene FROM {t} WHERE role = 'internal') i "
               f"LEFT JOIN {self.client.table('druggability')} d ON i.gene = d.gene")
        try:
            rows = self._q(sql.format(t=self.client.table("p53_interactions")))
            self.source = "zetaris"
            return rows
        except ZetarisError as exc:
            if not self.allow_fallback:
                raise
            self.source = f"local-csv (zetaris unavailable: {_short(exc)})"
            drug = {r["gene"]: r for r in self._local("druggability")}
            genes = sorted({r["gene"] for r in self._local("p53_interactions") if r["role"] == "internal"})
            return [{"gene": g, **{k: drug.get(g, {}).get(k, "") for k in
                                   ("druggable", "evidence_level", "example_agents")}} for g in genes]
