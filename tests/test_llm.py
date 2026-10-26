"""The LLM client against a fake Meterless Nightshift (a local HTTP server): contract, routing, fallback, SAMPLE_MODE."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import agent.llm as llm
from agent.llm import LLMError, NemotronClient, NoLLM, llm_status, routed_model_of

TOKEN = "test-runtime-token"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


class FakeNightshift:
    """Answers GET /v1/models and POST /v1/chat/completions like the runtime; records what it received."""

    def __init__(self, reject_extensions: bool = False, receipt: bool = True, models: list[str] | None = None):
        self.models = models or ["meterless/auto", MODEL]
        self.requests: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _auth(self) -> bool:
                return self.headers.get("Authorization") == f"Bearer {TOKEN}"

            def _send(self, code: int, body: dict) -> None:
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("meterless-route", "nvidia-lightning")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):  # noqa: N802
                if not self._auth():
                    return self._send(401, {"error": "unauthorized"})
                self._send(200, {"data": [{"id": m} for m in outer.models]})

            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
                if not self._auth():
                    return self._send(401, {"error": "unauthorized"})
                if outer_reject and "reasoning_effort" in body:
                    return self._send(400, {"error": "unknown parameter reasoning_effort"})
                reply = {"id": "x", "model": "meterless/auto",
                         "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 12, "completion_tokens": 5}}
                if receipt:
                    reply["receipt"] = {"routed_model": MODEL, "race_width": 1}
                self._send(200, reply)

        outer_reject = reject_extensions
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("NIGHTSHIFT_BASE_URL", "NIGHTSHIFT_TOKEN", "NIGHTSHIFT_APP", "METERLESS_API_KEY", "METERLESS_BASE_URL",
                "METERLESS_TOKEN", "METERLESS_RUNTIME_TOKEN", "NIGHTSHIFT_CONNECT_LINK", "LOCALAPPDATA", "NVIDIA_API_KEY", "SAMPLE_MODE", "NEMOTRON_MODEL", "NEMOTRON_THINKING", "LLM_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NIGHTSHIFT_TOKEN_FILE", str(tmp_path / "no-such-token"))
    llm._probe_cache.clear()
    yield
    llm._probe_cache.clear()


@pytest.fixture
def nightshift():
    srv = FakeNightshift()
    yield srv
    srv.close()


def configure(monkeypatch, srv):
    monkeypatch.setenv("NIGHTSHIFT_BASE_URL", srv.url)
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", TOKEN)


def test_nightshift_is_the_primary_provider_and_follows_its_contract(monkeypatch, nightshift, tmp_path):
    configure(monkeypatch, nightshift)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-should-not-be-used")           # present, but Nightshift is online
    trace = tmp_path / "trace.jsonl"
    client = NemotronClient(trace_path=trace)
    assert client.provider == "nightshift" and not client.fallback
    reply = client.complete([{"role": "user", "content": "SECRET PROMPT TEXT"}])
    assert reply.content == '{"ok": true}' and reply.provider == "nightshift"
    assert reply.routed_model == MODEL                                           # from the receipt, not the "meterless/auto" alias
    req = nightshift.requests[0]
    assert req["path"] == "/v1/chat/completions"
    assert req["headers"]["Authorization"] == f"Bearer {TOKEN}"                 # the runtime token, never the NVIDIA key
    assert req["headers"]["meterless-app"] == "verified-knockout-agent" and req["headers"]["meterless-scope"] == "user"
    assert req["body"]["model"] == MODEL and req["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert req["body"]["reasoning_effort"] == "none"
    # the trace says which model handled the request and contains neither prompts nor secrets
    line = trace.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["provider"] == "nightshift" and rec["routed_model"] == MODEL and rec["prompt_tokens"] == 12
    assert rec["meterless_headers"] == {"meterless-route": "nvidia-lightning"}
    assert "SECRET PROMPT TEXT" not in line and TOKEN not in line and "nvapi" not in line


def test_routed_model_falls_back_to_the_plain_model_field():
    assert routed_model_of({"model": "plain-model"}) == "plain-model"
    assert routed_model_of({"model": "meterless/auto", "winning_route": {"model": "nvidia/x"}}) == "nvidia/x"
    assert routed_model_of({"meterless": {"receipt": {"routed_model": "nvidia/y"}}, "model": "m"}) == "nvidia/y"
    assert routed_model_of({}) == ""


def test_extensions_the_runtime_rejects_are_dropped_and_the_request_retried(monkeypatch, tmp_path):
    srv = FakeNightshift(reject_extensions=True)
    try:
        configure(monkeypatch, srv)
        reply = NemotronClient(trace_path=None).complete([{"role": "user", "content": "hi"}])
        assert reply.content and len(srv.requests) == 2
        assert "reasoning_effort" not in srv.requests[1]["body"] and "chat_template_kwargs" not in srv.requests[1]["body"]
    finally:
        srv.close()


def test_wrong_token_without_fallback_says_how_to_fix_it(monkeypatch, nightshift):
    monkeypatch.setenv("NIGHTSHIFT_BASE_URL", nightshift.url)
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", "wrong")
    with pytest.raises(LLMError, match="unauthorized.*NIGHTSHIFT_TOKEN"):
        NemotronClient(trace_path=None)


def test_nvidia_direct_is_only_a_labelled_fallback(monkeypatch):
    monkeypatch.setenv("NIGHTSHIFT_BASE_URL", "http://127.0.0.1:9/v1")           # nothing listens there
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", TOKEN)
    with pytest.raises(LLMError, match="offline"):
        NemotronClient(trace_path=None)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    client = NemotronClient(trace_path=None)
    assert client.provider == "nvidia-direct" and client.fallback and "offline" in client.note
    assert "nvidia.com" in client.base_url and "reasoning_effort" not in client._headers()
    status = llm_status()
    assert status["available"] and status["provider"] == "nvidia-direct" and status["fallback"]


def test_status_reports_nightshift_when_online(monkeypatch, nightshift):
    configure(monkeypatch, nightshift)
    status = llm_status()
    assert status["available"] and status["provider"] == "nightshift" and status["model"] == MODEL


def test_explicit_arguments_win_over_the_environment(monkeypatch, nightshift):
    configure(monkeypatch, nightshift)
    client = NemotronClient(api_key="explicit", trace_path=None)
    assert client.provider == "nvidia-direct" and client.api_key == "explicit"


def test_sample_mode_disables_every_llm_and_data_network_call(monkeypatch, nightshift):
    configure(monkeypatch, nightshift)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    with pytest.raises(LLMError, match="SAMPLE_MODE"):
        NemotronClient(trace_path=None)
    status = llm_status()
    assert not status["available"] and status["provider"] == "sample-mode"
    assert nightshift.requests == []
    from agent.tools_zetaris import DataLayer
    layer = DataLayer()
    assert layer.network_rows() and layer.source.startswith("local-csv")
    with pytest.raises(LLMError, match="no LLM"):
        NoLLM("no LLM here").complete([])


def test_agent_reports_which_model_handled_each_request(monkeypatch, nightshift, tmp_path):
    """End to end: the agent's events and report carry the provider and the routed model of every LLM request."""
    from agent.main import CEGARAgent
    configure(monkeypatch, nightshift)
    client = NemotronClient(trace_path=tmp_path / "t.jsonl")
    events: list[dict] = []
    agent = CEGARAgent(client, memory_mode="off", max_rounds=1, per_round=1, explain=False, log=lambda _: None,
                       on_event=events.append)
    report = agent.run("fgfr3_wtp53")
    calls = [e for e in events if e["type"] == "llm_call"]
    assert calls and all(c["provider"] == "nightshift" and c["model"] == MODEL for c in calls)
    assert report.llm_provider == "nightshift" and report.llm_models == [MODEL]


def test_connect_link_supplies_base_url_key_and_app_name(monkeypatch):
    monkeypatch.setenv("NIGHTSHIFT_CONNECT_LINK", "http://192.168.1.20:8088/connect#k=link-key&m=nvidia%2Fx&n=my-app")
    base, token, app = llm.nightshift_settings()
    assert (base, token, app) == ("http://192.168.1.20:8088/v1", "link-key", "my-app")
    assert llm.parse_connect_link("not a link") == {}


def test_meterless_token_variable_is_read_like_the_ns_tool_does(monkeypatch):
    monkeypatch.setenv("METERLESS_TOKEN", "from-ns-variable")
    assert llm.nightshift_settings()[1] == "from-ns-variable"
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", "explicit-wins")
    assert llm.nightshift_settings()[1] == "explicit-wins"


def test_token_is_read_from_the_runtimes_own_file_on_windows(monkeypatch, tmp_path):
    state = tmp_path / "ai.meterless.runtime"
    state.mkdir()
    (state / "proxy-token").write_text("file-token\n", encoding="utf-8")
    monkeypatch.delenv("NIGHTSHIFT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert llm.nightshift_settings()[1] == "file-token"


def test_model_id_is_taken_from_the_list_the_runtime_serves(monkeypatch):
    llm._model_cache.clear()
    srv = FakeNightshift(models=["meterless/auto", "nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-lightning-30b-a3b-fp8"])
    try:
        configure(monkeypatch, srv)
        client = NemotronClient(trace_path=None)
        assert client.model == "nvidia/nemotron-3.5-lightning-30b-a3b-fp8" and "does not list" in client.note
        assert client.complete([{"role": "user", "content": "hi"}]).content
        assert srv.requests[0]["body"]["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b-fp8"
        monkeypatch.setenv("NEMOTRON_MODEL", "meterless/auto")                     # an explicit choice is never replaced
        assert NemotronClient(trace_path=None).model == "meterless/auto"
    finally:
        llm._model_cache.clear()
        srv.close()


def test_runtime_token_variable_used_by_other_hackathon_projects_is_accepted(monkeypatch):
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "runtime-var")
    assert llm.nightshift_settings()[1] == "runtime-var"
