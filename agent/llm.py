"""LLM access behind a small interface, so the model provider can be swapped.

Meterless Nightshift is the primary provider: it serves one OpenAI-compatible base URL on this machine and routes the
request to the NVIDIA Nemotron model whose key sits in Nightshift's Providers tab, so no NVIDIA key lives in this
project. A direct call to NVIDIA exists only as a labelled fallback for when Nightshift is not running, and
SAMPLE_MODE=true switches every network call off. Every request is appended to a JSONL trace with the model that
actually handled it. Nothing outside this file knows which provider is in use.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests
from dotenv import load_dotenv

from .logs import log_path

load_dotenv()

NIGHTSHIFT_URL = "http://127.0.0.1:8088/v1"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
APP_ID = "verified-knockout-agent"
_EXTENSIONS = ("chat_template_kwargs", "reasoning_effort")     # Nemotron switches; not part of the plain OpenAI schema


class LLMError(RuntimeError):
    pass


def sample_mode() -> bool:
    """SAMPLE_MODE=true: no network call to Zetaris, Nightshift or NVIDIA; the agent runs on the local files and the search."""
    return os.getenv("SAMPLE_MODE", "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class LLMResponse:
    content: str
    reasoning: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"
    provider: str = ""
    routed_model: str = ""             # the model that actually answered, as reported by the provider
    latency: float = 0.0


class ChatClient(Protocol):
    model: str

    def complete(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> LLMResponse: ...


def _find_key(obj, key: str):
    """First value stored under ``key`` anywhere in a nested JSON value."""
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], str):
            return obj[key]
        for v in obj.values():
            hit = _find_key(v, key)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_key(v, key)
            if hit:
                return hit
    return None


def routed_model_of(body: dict) -> str:
    """The model that handled a request, from Nightshift's receipt when present, else the plain ``model`` field."""
    receipt = next((body[k] for k in ("receipt", "meterless", "meterless_response") if isinstance(body.get(k), dict)), {})
    return (_find_key(receipt, "routed_model")
            or _find_key(body.get("winning_route"), "model")
            or _find_key(receipt, "model")
            or (body.get("model") if isinstance(body.get("model"), str) else "")
            or "")


def _token_files() -> list[Path]:
    """Where the runtime's ``proxy-token`` file may be: NIGHTSHIFT_TOKEN_FILE if set, else a few best-effort guesses."""
    explicit = os.getenv("NIGHTSHIFT_TOKEN_FILE", "").strip()
    if explicit:
        return [Path(explicit)]
    home = Path.home()
    guesses = [home / ".meterless" / "proxy-token", home / "Library" / "Application Support" / "Meterless" / "proxy-token"]
    if os.getenv("APPDATA"):
        guesses.insert(0, Path(os.environ["APPDATA"]) / "Meterless" / "proxy-token")
    return guesses


def nightshift_settings() -> tuple[str, str, str]:
    """(base_url, token, app id) of the Nightshift runtime from the environment; the token may be empty."""
    base = (os.getenv("NIGHTSHIFT_BASE_URL") or os.getenv("METERLESS_BASE_URL") or NIGHTSHIFT_URL).strip().rstrip("/")
    token = (os.getenv("NIGHTSHIFT_TOKEN") or os.getenv("METERLESS_API_KEY") or "").strip()
    if not token:
        for f in _token_files():
            try:
                token = f.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if token:
                break
    if token.lower().startswith("your_"):          # a placeholder copied from .env.example is not a token
        token = ""
    return base, token, os.getenv("NIGHTSHIFT_APP", APP_ID).strip() or APP_ID


def _nightshift_headers(token: str, app: str) -> dict:
    return {"Authorization": f"Bearer {token}", "meterless-app": app, "meterless-scope": "user",
            "Content-Type": "application/json"}


_probe_cache: dict[str, tuple[float, str]] = {}


def probe_nightshift(base: str, token: str, app: str, ttl: float = 20.0) -> str:
    """'online' | 'unauthorized' | 'offline', from GET /v1/models (the runtime's own health signal)."""
    now = time.time()
    hit = _probe_cache.get(base + token[-4:])
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        r = requests.get(f"{base}/models", headers=_nightshift_headers(token, app), timeout=3)
        state = "online" if r.status_code == 200 else "unauthorized" if r.status_code in (401, 403) else "offline"
    except requests.RequestException:
        state = "offline"
    _probe_cache[base + token[-4:]] = (now, state)
    return state


def llm_status() -> dict:
    """What the UI shows in its LLM chip: which provider would serve a request now, and why. Never raises."""
    model = os.getenv("NEMOTRON_MODEL", DEFAULT_MODEL)
    if sample_mode():
        return {"available": False, "provider": "sample-mode", "model": model, "state": "sample",
                "note": "SAMPLE_MODE: no LLM calls; recorded replays and the symbolic search still work"}
    base, token, app = nightshift_settings()
    state = probe_nightshift(base, token, app) if token else "not-configured"
    if state == "online":
        return {"available": True, "provider": "nightshift", "model": model, "state": state, "base_url": base,
                "note": "Meterless Nightshift"}
    if os.getenv("NVIDIA_API_KEY", "").strip():
        return {"available": True, "provider": "nvidia-direct", "model": model, "state": state, "fallback": True,
                "note": f"fallback: Nightshift is {state}, calling NVIDIA directly"}
    return {"available": False, "provider": "none", "model": model, "state": state,
            "note": f"Nightshift is {state} and no fallback key is set"}


class NemotronClient:
    """Nemotron through Meterless Nightshift (primary) or NVIDIA directly (labelled fallback)."""

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None, timeout: int = 180, retries: int = 3,
                 thinking: bool | None = None, trace_path: Path | None | str = "default"):
        if sample_mode():
            raise LLMError("SAMPLE_MODE is on: LLM calls are disabled")
        self.model = model or os.getenv("NEMOTRON_MODEL", DEFAULT_MODEL)
        self.timeout, self.retries = timeout, retries
        # None disables the trace; the default is logs/llm-trace.jsonl (AGENT_LOG_DIR moves or switches it off)
        self.trace_path = log_path("llm-trace.jsonl") if trace_path == "default" else trace_path
        self.fallback, self.note = False, ""
        self.calls: list[dict] = []
        self._lock = threading.Lock()
        # Measured on this model: with thinking on, a 5k-character prompt still had no answer after
        # 16000 tokens (268 s). Thinking off answers in about 2 s, so it is the default.
        self.thinking = (os.getenv("NEMOTRON_THINKING", "0") == "1") if thinking is None else thinking
        if api_key is not None or base_url is not None:                      # explicit arguments always win
            self.provider, self.api_key = "nvidia-direct", api_key or os.getenv("NVIDIA_API_KEY", "").strip()
            self.base_url = (base_url or NVIDIA_URL).rstrip("/")
            self.app = APP_ID
        else:
            ns_base, ns_token, self.app = nightshift_settings()
            state = probe_nightshift(ns_base, ns_token, self.app) if ns_token else "not-configured"
            nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
            if state == "online":
                self.provider, self.api_key, self.base_url = "nightshift", ns_token, ns_base
            elif nvidia_key:
                self.provider, self.api_key = "nvidia-direct", nvidia_key
                self.base_url = os.getenv("LLM_BASE_URL", NVIDIA_URL).rstrip("/")
                self.fallback, self.note = True, f"Nightshift is {state}; calling NVIDIA directly (fallback)"
            else:
                raise LLMError(f"Meterless Nightshift is {state} at {ns_base} and no NVIDIA_API_KEY fallback is set. "
                               "Start Nightshift, add the NVIDIA key in its Providers tab and put its runtime token in "
                               ".env as NIGHTSHIFT_TOKEN (or run with SAMPLE_MODE=true).")
        if not self.api_key:
            raise LLMError("no API key for the LLM provider")

    # -- one request ---------------------------------------------------------------------------
    def _headers(self) -> dict:
        if self.provider == "nightshift":
            return _nightshift_headers(self.api_key, self.app)
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _trace(self, rec: dict) -> None:
        with self._lock:
            self.calls.append(rec)
            if self.trace_path is None:
                return
            try:
                self.trace_path.parent.mkdir(parents=True, exist_ok=True)
                with self.trace_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except OSError:
                pass                                              # a trace must never break a run

    def complete(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
                   "chat_template_kwargs": {"enable_thinking": self.thinking}}
        if not self.thinking and self.provider == "nightshift":
            payload["reasoning_effort"] = "none"
        headers = self._headers()
        last = ""
        for attempt in range(self.retries):
            t0 = time.perf_counter()
            try:
                r = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last = str(exc)
            else:
                latency = time.perf_counter() - t0
                if r.status_code == 200:
                    body = r.json()
                    choice = body["choices"][0]
                    msg = choice["message"]
                    usage = body.get("usage", {})
                    finish = choice.get("finish_reason") or "stop"
                    content = msg.get("content") or ""
                    routed = routed_model_of(body) or self.model
                    self._trace({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "provider": self.provider,
                                 "fallback": self.fallback, "requested_model": self.model, "routed_model": routed,
                                 "latency_s": round(latency, 2), "prompt_tokens": usage.get("prompt_tokens", 0),
                                 "completion_tokens": usage.get("completion_tokens", 0), "finish_reason": finish,
                                 "meterless_headers": {k: v for k, v in r.headers.items() if k.lower().startswith("meterless")}})
                    if not content and finish == "length":
                        raise LLMError(f"reply cut off by the {max_tokens}-token limit before any answer "
                                       "(the model spent it on thinking)")
                    return LLMResponse(content, msg.get("reasoning_content") or "", usage.get("prompt_tokens", 0),
                                       usage.get("completion_tokens", 0), finish, self.provider, routed, round(latency, 2))
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code == 400 and any(k in payload for k in _EXTENSIONS):
                    for k in _EXTENSIONS:                                # endpoint rejects the extensions: retry plainly
                        payload.pop(k, None)
                    continue
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(2 ** attempt)
        self._trace({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "provider": self.provider, "fallback": self.fallback,
                     "requested_model": self.model, "error": last[:200]})
        raise LLMError(f"LLM request failed: {last}")


class NoLLM:
    """Stand-in when no provider is reachable or SAMPLE_MODE is on: every call fails fast, so the agent's complete
    symbolic search finishes the job on its own (it needs no LLM) and the report says that no LLM was used."""
    model = "none"
    provider = "none"

    def __init__(self, reason: str = "no LLM provider available"):
        self.reason = reason

    def complete(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> LLMResponse:
        raise LLMError(self.reason)


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parse the JSON object in a model reply, tolerating code fences and surrounding prose."""
    cleaned = re.sub(r"```(?:json)?", "", text)
    for candidate in (cleaned.strip(), *(m.group(0) for m in [_JSON_OBJECT.search(cleaned)] if m)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise LLMError(f"no JSON object in model reply: {text[:200]!r}")
