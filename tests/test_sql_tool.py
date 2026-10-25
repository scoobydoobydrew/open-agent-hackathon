"""The run_sql tool: the LLM writes SELECTs, the tool keeps them read-only and runs them on Zetaris."""
import json

import pytest

from agent.llm import LLMResponse
from agent.main import CEGARAgent
from agent.sql_tool import check_sql, run_sql, schema_text, summarise
from agent.tools_zetaris import DataLayer, ZetarisError

DB = "open_agent"


@pytest.mark.parametrize("sql", [
    "SELECT gene FROM open_agent.druggability WHERE druggable = 'yes'",
    "select d.gene, i.regulators from open_agent.druggability d join open_agent.p53_interactions i on d.gene = i.gene;",
])
def test_good_queries_pass_and_get_a_row_limit(sql):
    checked = check_sql(sql, DB)
    assert checked.lower().rstrip().endswith("limit 40") and not checked.endswith(";")


@pytest.mark.parametrize("sql", [
    "DROP TABLE open_agent.druggability", "SELECT 1; DELETE FROM open_agent.phenotypes",
    "SELECT * FROM open_agent.secret", "SELECT * FROM other_db.druggability", "SELECT 1",
    "SELECT gene FROM open_agent.druggability UNION SELECT node FROM open_agent.p53_interactions",
    "WITH x AS (SELECT 1) SELECT * FROM x", "INSERT INTO open_agent.druggability VALUES (1)",
])
def test_everything_else_is_refused(sql):
    with pytest.raises(ValueError):
        check_sql(sql, DB)


class FakeClient:
    database = DB

    def __init__(self, rows=None, fail=False):
        self.rows, self.fail, self.sent = rows or [], fail, []

    def query(self, sql):
        self.sent.append(sql)
        if self.fail:
            raise ZetarisError("boom")
        return self.rows

    def table(self, name):
        return f"{DB}.{name}"


def layer(client, source="zetaris"):
    d = DataLayer(client=client)
    d.source = source
    return d


def test_run_sql_returns_rows_and_never_raises():
    c = FakeClient(rows=[{"gene": "AKT"}])
    ok = run_sql(layer(c), "SELECT gene FROM open_agent.druggability")
    assert ok["ok"] and ok["rows"] == [{"gene": "AKT"}] and c.sent[0].endswith("LIMIT 40")
    assert not run_sql(layer(c), "DROP TABLE x")["ok"] and len(c.sent) == 1          # refused before reaching Zetaris
    assert "boom" in run_sql(layer(FakeClient(fail=True)), "SELECT gene FROM open_agent.druggability")["error"]
    local = run_sql(layer(c, source="local-csv (x)"), "SELECT gene FROM open_agent.druggability")
    assert not local["ok"] and "no SQL engine" in local["error"]


def test_summaries_are_compact_and_honest_about_failures():
    text = summarise({"ok": True, "rows": [{"gene": f"G{i}", "e": "x"} for i in range(20)], "error": ""}, "what")
    assert "+6 more" in text and "G0 | x" in text
    assert "failed" in summarise({"ok": False, "rows": [], "error": "bad"}, "what")
    assert "druggability" in schema_text(DB)


class SqlLLM:
    """Answers the SQL turn with two queries (one broken, then fixed) and proposals afterwards."""
    model = "scripted"

    def __init__(self):
        self.sql_turns, self.prompts = 0, []

    def complete(self, messages, max_tokens=0, temperature=0.0):
        if messages[0]["content"].startswith("You are a cancer systems-biology agent. Before"):
            self.sql_turns += 1
            q = ("SELECT gene FROM open_agent.druggability WHERE druggable = 'yes'" if self.sql_turns > 1
                 else "SELECT gene FROM open_agent.nope")
            return LLMResponse(json.dumps({"queries": [{"purpose": "find druggable genes", "sql": q}]}))
        self.prompts.append(messages[1]["content"])
        return LLMResponse(json.dumps({"proposals": [], "give_up": True}))


class CsvWithSqlTool(DataLayer):
    """Network, scenarios and drug rows come from the CSV files; only the LLM's own SQL goes to the (fake) Zetaris."""

    def __init__(self, client):
        super().__init__(client=client)
        self.source = "zetaris"

    def select(self, sql_template, table):
        return self._local(table)

    def drug_ranking_join(self):
        drug = {r["gene"]: r for r in self._local("druggability")}
        genes = sorted({r["gene"] for r in self._local("p53_interactions") if r["role"] == "internal"})
        return [{"gene": g, **{k: drug.get(g, {}).get(k, "") for k in ("druggable", "evidence_level", "example_agents")}} for g in genes]


def test_agent_uses_sql_results_in_its_prompt_and_retries_a_failed_query():
    client = FakeClient(rows=[{"gene": "AKT"}, {"gene": "EGFR"}])
    events, llm = [], SqlLLM()
    agent = CEGARAgent(llm, CsvWithSqlTool(client), memory_mode="off", max_rounds=1, explain=False, cegar=False,
                       fallback=False, sql_tool=True, log=lambda _: None, on_event=events.append)
    rep = agent.run("fgfr3_wtp53")
    calls = [e for e in events if e["type"] == "sql_call"]
    assert [c["ok"] for c in calls] == [False, True] and rep.sql_calls == 2 and llm.sql_turns == 2
    assert client.sent == [client.sent[0]] and "druggable" in client.sent[0]       # the failed query never reached Zetaris
    assert "AKT" in llm.prompts[0] and "find druggable genes" in llm.prompts[0]


def test_sql_tool_is_off_by_default_so_benchmarks_stay_comparable():
    llm, client = SqlLLM(), FakeClient()
    CEGARAgent(llm, CsvWithSqlTool(client), memory_mode="off", max_rounds=1, explain=False, cegar=False, fallback=False,
               log=lambda _: None).run("fgfr3_wtp53")
    assert llm.sql_turns == 0 and client.sent == []
