"""The UI server: real solver behind HTTP, event streams, replays, path safety."""
import json
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from ui.server import Handler, state


@pytest.fixture(scope="module")
def base():
    state()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def events(url, **params):
    out = []
    with requests.get(url, params=params, stream=True, timeout=120) as r:
        assert r.headers["Content-Type"].startswith("text/event-stream")
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


def test_meta_describes_graph_scenarios_and_replays(base):
    m = requests.get(f"{base}/api/meta", timeout=60).json()
    genes = {g["id"]: g for g in m["graph"]["genes"]}
    assert len(genes) == 30 and genes["TP53"]["knockable"] and genes["DNA_damage"]["kind"] == "input"
    assert genes["Apoptosis"]["kind"] == "output" and genes["p21CIP"]["rules"]["p21CIP"]
    assert all(e["source"] in genes and e["target"] in genes and e["source"] != e["target"] for e in m["graph"]["edges"])
    assert {s["id"] for s in m["scenarios"] if s["kind"] == "target"} >= {"fgfr3_wtp53", "growthinh_only"}
    assert m["known_solutions"]["growthinh_only"] == []
    assert "llm" in m and "data_source" in m


def test_verify_returns_a_checked_proof_for_a_working_knockout(base):
    r = requests.post(f"{base}/api/verify", json={"scenario": "fgfr3_wtp53", "knockouts": ["TP53"]}, timeout=60).json()
    assert r["verdict"] == "FORCED" and r["selective"] is True
    assert r["attractors"] and r["attractors"][0]["values"]["Apoptosis_high"] == 1
    assert r["steps"] and all(s["entailed"] for s in r["steps"])
    assert any(p[2] == "knockout" for s in r["steps"] for p in s["premises"])


def test_verify_returns_a_counterexample_for_a_failing_knockout(base):
    r = requests.post(f"{base}/api/verify", json={"scenario": "fgfr3_wtp53", "knockouts": ["MDM2"]}, timeout=60).json()
    ce = r["counterexample"]
    assert r["verdict"] == "SURVIVES" and ce["active_genes"] and "MDM2" in ce["inactive_genes"]
    assert ce["values"]["Apoptosis_high"] != 1


def test_custom_inputs_are_a_different_scenario(base):
    fixed = {"DNA_damage": 0, "EGFR_stimulus": 0, "FGFR3_stimulus": 1, "Growth_inhibitors": 0}
    r = requests.post(f"{base}/api/verify", json={"scenario": "x", "fixed": fixed, "knockouts": ["TP53"]}, timeout=60).json()
    assert r["verdict"] == "SURVIVES" and r["scenario"].startswith("custom:")   # no radiation, no apoptosis


def test_unknown_scenario_and_non_knockable_genes(base):
    assert requests.post(f"{base}/api/verify", json={"scenario": "nope", "knockouts": []}, timeout=30).status_code == 404
    r = requests.post(f"{base}/api/verify", json={"scenario": "fgfr3_wtp53", "knockouts": ["DNA_damage", "Apoptosis"]}, timeout=60).json()
    assert r["knockouts"] == []                                              # inputs and outputs cannot be knocked out


def test_search_stream_finds_every_minimal_set_with_few_calls(base):
    evs = events(f"{base}/api/search", scenario="fgfr3_wtp53", max_size=3)
    assert evs[0]["type"] == "init" and evs[-1]["type"] == "done"
    done = evs[-1]
    assert sorted(map(tuple, done["solutions"])) == [("RB1", "RBL2"), ("TP53",), ("p21CIP",)]
    assert done["calls"] < done["brute_force_sets"] / 3 and done["proved_infeasible"] is False
    visits = [e for e in evs if e["type"] == "visit"]
    assert visits[0]["kos"] == [] and visits[0]["parent"] is None
    assert all(v["parent"] is not None for v in visits[1:])


def test_search_stream_proves_impossibility(base):
    evs = events(f"{base}/api/search", scenario="growthinh_only", max_size=3)
    assert evs[-1]["type"] == "done" and evs[-1]["proved_infeasible"] is True and evs[-1]["solutions"] == []
    assert any(e["type"] == "exhausted" for e in evs)


def test_memory_replay_option_changes_the_cost_not_the_answer(base):
    plain = events(f"{base}/api/search", scenario="fgfr3_rb1loss", max_size=3)[-1]
    mem = events(f"{base}/api/search", scenario="fgfr3_rb1loss", max_size=3, memory="1")[-1]
    assert sorted(map(tuple, plain["solutions"])) == sorted(map(tuple, mem["solutions"]))
    assert mem["calls"] <= plain["calls"]


def test_replays_are_real_recordings(base):
    names = requests.get(f"{base}/api/meta", timeout=60).json()["replays"]
    if not names:
        pytest.skip("no recordings yet (python ui/record_replays.py)")
    rec = requests.get(f"{base}/api/replay", params={"name": names[0]}, timeout=30).json()
    types = [e["type"] for e in rec["events"]]
    assert types[0] == "start" and types[-1] == "done" and "proposal" in types


def test_paths_cannot_escape_the_static_folder(base):
    assert requests.get(f"{base}/", timeout=10).status_code == 200
    assert requests.get(f"{base}/js/app.js", timeout=10).headers["Content-Type"].startswith("application/javascript")
    for bad in ("/../server.py", "/..%2fserver.py", "/js/../../server.py"):
        assert requests.get(f"{base}{bad}", timeout=10).status_code == 404
    assert requests.get(f"{base}/api/replay", params={"name": "../../.env"}, timeout=10).status_code == 404


# -- the programmatic interface: a judge can drive the agent without the UI ---------------------------------------
def test_health_reports_the_services(base):
    h = requests.get(f"{base}/health", timeout=60).json()
    assert h["status"] == "ok" and "provider" in h["llm"] and "data_source" in h


def test_run_endpoint_returns_a_report_without_the_ui(base):
    r = requests.post(f"{base}/run", json={"scenario": "growthinh_only", "max_size": 2, "rounds": 1, "llm": False}, timeout=180)
    assert r.status_code == 200
    body = r.json()
    assert body["report"]["certified_infeasible"] is True and body["report"]["solutions"] == []
    assert "No knockout set of the allowed size forces apoptosis" in body["markdown"]


def test_run_endpoint_rejects_bad_input_and_caps_the_work(base):
    bad = requests.post(f"{base}/run", json={"scenario": "nope"}, timeout=60)
    assert bad.status_code == 400 and "unknown scenario" in bad.json()["error"]
    assert requests.post(f"{base}/run", json={"scenario": "fgfr3_wtp53", "max_size": "x"}, timeout=60).status_code == 400
    from agent.api import MAX_SIZE, _bounded
    assert _bounded({"max_size": 99}, "max_size", 3, MAX_SIZE) == MAX_SIZE


def test_committed_examples_are_what_the_endpoint_returns_in_sample_mode(monkeypatch):
    import json as _json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    monkeypatch.setenv("SAMPLE_MODE", "true")
    from agent.api import run_payload
    for i in (1, 3):
        payload = _json.loads((root / "input_examples" / f"example_{i}.json").read_text(encoding="utf-8"))
        want = _json.loads((root / "output_examples" / f"example_{i}.json").read_text(encoding="utf-8"))["report"]
        got = run_payload(payload)["report"]
        assert got["solutions"] == want["solutions"] and got["certified_infeasible"] == want["certified_infeasible"]
