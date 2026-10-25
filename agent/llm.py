"""LLM access behind a small interface, so the model provider can be swapped.

NemotronClient talks to NVIDIA's OpenAI-compatible endpoint directly over REST.
The Meta submission adds another client with the same ``complete`` signature;
nothing outside this file knows which provider is in use.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    content: str
    reasoning: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"


class ChatClient(Protocol):
    model: str

    def complete(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> LLMResponse: ...


class NemotronClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None, timeout: int = 180, retries: int = 3,
                 thinking: bool | None = None):
        # The hackathon's runtime credits are served by Meterless as an OpenAI-compatible endpoint; without those
        # variables the agent calls NVIDIA's endpoint directly. Explicit arguments always win.
        meterless = (os.getenv("METERLESS_API_KEY", "").strip(), os.getenv("METERLESS_BASE_URL", "").strip())
        use_meterless = api_key is None and base_url is None and all(meterless)
        self.provider = "meterless" if use_meterless else "nvidia"
        self.api_key = api_key or (meterless[0] if use_meterless else os.getenv("NVIDIA_API_KEY", "").strip())
        self.model = model or os.getenv("NEMOTRON_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or (meterless[1] if use_meterless else os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL))).rstrip("/")
        self.timeout = timeout
        self.retries = retries
        # Measured on this model: with thinking on, a 5k-character prompt still had no answer after
        # 16000 tokens (268 s). Thinking off answers in about 2 s, so it is the default.
        self.thinking = (os.getenv("NEMOTRON_THINKING", "0") == "1") if thinking is None else thinking
        if not self.api_key:
            raise LLMError("NVIDIA_API_KEY (or METERLESS_API_KEY and METERLESS_BASE_URL) is not set")

    def complete(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature,
                   "chat_template_kwargs": {"enable_thinking": self.thinking}}
        if self.provider != "nvidia":
            payload.pop("chat_template_kwargs")          # not part of the plain OpenAI schema; added back if accepted
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last = ""
        for attempt in range(self.retries):
            try:
                r = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload,
                                  timeout=self.timeout)
            except requests.RequestException as exc:
                last = str(exc)
            else:
                if r.status_code == 200:
                    body = r.json()
                    msg = body["choices"][0]["message"]
                    usage = body.get("usage", {})
                    finish = body["choices"][0].get("finish_reason") or "stop"
                    content = msg.get("content") or ""
                    if not content and finish == "length":
                        raise LLMError(f"reply cut off by the {max_tokens}-token limit before any answer "
                                       "(the model spent it on thinking)")
                    return LLMResponse(content, msg.get("reasoning_content") or "",
                                       usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), finish)
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code == 400 and "chat_template_kwargs" in payload:
                    payload.pop("chat_template_kwargs")        # endpoint rejects the extension: retry plainly
                    continue
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(2 ** attempt)
        raise LLMError(f"LLM request failed: {last}")


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
