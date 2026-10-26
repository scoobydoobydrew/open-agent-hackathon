"""Check the connection to Meterless Nightshift, step by step, without printing any secret.

    python scripts/check_nightshift.py

It reports whether the runtime answers, whether the token is accepted, which Nemotron models it serves, and then sends one
tiny chat request and prints which model handled it. The output (safe to paste into a chat) names the response fields
and headers but never their secret values.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.llm import (DEFAULT_MODEL, _nightshift_headers, _token_files, nightshift_settings,  # noqa: E402
                       probe_nightshift, routed_model_of)


def main() -> int:
    base, token, app = nightshift_settings()
    print(f"base url      : {base}")
    print(f"app id        : {app}")
    print(f"token         : {'found' if token else 'MISSING'}")
    if not token:
        print("\nNo token. Put NIGHTSHIFT_TOKEN=... in .env, or point NIGHTSHIFT_TOKEN_FILE at Nightshift's proxy-token file.")
        print("Files looked at:", ", ".join(str(p) for p in _token_files()))
        return 1
    state = probe_nightshift(base, token, app, ttl=0)
    print(f"GET /models   : {state}")
    if state != "online":
        print({"offline": "\nNightshift is not answering. Start it and check the port in its settings (default 8088).",
               "unauthorized": "\nThe runtime rejected the token. Copy the current token (it can be rotated) and note that the placeholder 'rt-local' is refused."}[state])
        return 1
    headers = _nightshift_headers(token, app)
    ids = [m.get("id", "") for m in requests.get(f"{base}/models", headers=headers, timeout=10).json().get("data", [])]
    nemo = [i for i in ids if "nemotron" in i.lower()]
    print(f"models served : {len(ids)} ({len(nemo)} Nemotron)")
    for i in nemo[:12]:
        print("   ", i)
    model = DEFAULT_MODEL
    if nemo and model not in ids:
        print(f"\nNote: the default model {model} is not in the list; set NEMOTRON_MODEL to one of the ids above.")
    t0 = time.perf_counter()
    r = requests.post(f"{base}/chat/completions", headers=headers, timeout=120, json={
        "model": model, "max_tokens": 40, "temperature": 0,
        "messages": [{"role": "user", "content": "Reply with the single word: ready"}]})
    dt = time.perf_counter() - t0
    print(f"POST /chat/completions: HTTP {r.status_code} in {dt:.1f}s")
    if r.status_code != 200:
        print("   ", r.text[:300])
        return 1
    body = r.json()
    print("reply         :", (body["choices"][0]["message"].get("content") or "").strip()[:80])
    print("handled by    :", routed_model_of(body) or "(not reported)")
    print("response keys :", sorted(body.keys()))
    print("meterless-* headers:", sorted(k for k in r.headers if k.lower().startswith("meterless")) or "none")
    print("\nNightshift works. The agent will use it as its primary provider.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
