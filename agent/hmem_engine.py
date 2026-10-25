"""Python client for the official H-MEM reference implementation (vendored unmodified in hmem/reference).

The engine runs as a Node child process behind hmem/bridge.ts. Every call forwards to the reference services
(store, retrieval, ledger, conflicts, sleep, dreaming, mining), so the spec behaviour is the reference's, not a port.
The built bridge (hmem/dist/bridge.mjs: the unmodified reference plus our JSON bridge) is committed, so a clean clone
needs only Node.js. ``cd hmem/reference && npm install`` is needed just to rebuild it or to run the official conformance suite.
"""
from __future__ import annotations

import atexit
import itertools
import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

HMEM_DIR = Path(__file__).resolve().parent.parent / "hmem"
BUNDLE = HMEM_DIR / "dist" / "bridge.mjs"
ESBUILD = HMEM_DIR / "reference" / "node_modules" / "esbuild" / "bin" / "esbuild"   # JS launcher: same on every OS


class HMemUnavailable(RuntimeError):
    """Node or the reference dependencies are missing; callers degrade gracefully."""


def build_bundle(out: Path = BUNDLE) -> Path:
    """Bundle bridge.ts with the vendored reference using esbuild (needs ``npm install`` in hmem/reference)."""
    if not shutil.which("node"):
        raise HMemUnavailable("Node.js is not installed (needed for the official H-MEM reference implementation)")
    if not ESBUILD.exists():
        raise HMemUnavailable("run `npm install` in hmem/reference first")
    out.parent.mkdir(exist_ok=True)
    done = subprocess.run(["node", str(ESBUILD), "hmem/bridge.ts", "--bundle", "--platform=node", "--format=esm",
                           f"--outfile={out}", "--log-level=error"], capture_output=True, text=True, cwd=HMEM_DIR.parent)
    if done.returncode != 0:
        raise HMemUnavailable(f"could not build the H-MEM bridge: {done.stderr[:300]}")
    return out


def ensure_bundle() -> Path:
    """The committed bundle is used as it is; it is rebuilt only when esbuild is installed and a source is newer."""
    if BUNDLE.exists() and not ESBUILD.exists():
        if not shutil.which("node"):
            raise HMemUnavailable("Node.js is not installed (needed for the official H-MEM reference implementation)")
        return BUNDLE
    sources = [HMEM_DIR / "bridge.ts", *(HMEM_DIR / "reference" / "src").glob("*.ts")]
    if BUNDLE.exists() and BUNDLE.stat().st_mtime >= max(p.stat().st_mtime for p in sources):
        return BUNDLE
    return build_bundle()


class HMemEngine:
    """One H-MEM instance. ``persist_dir`` keeps state.json and the append-only ledger.jsonl between runs."""

    def __init__(self, persist_dir: str | Path | None = None, actor: str = "agent"):
        self.persist_dir = str(persist_dir) if persist_dir else "-"
        self.actor = actor
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._ids = itertools.count(1)

    # -- process ---------------------------------------------------------------------------------
    def _start(self) -> subprocess.Popen:
        bundle = ensure_bundle()
        proc = subprocess.Popen(["node", str(bundle), self.persist_dir, self.actor], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        atexit.register(self.close)
        return proc

    def call(self, method: str, **params: Any) -> Any:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._proc = self._start()
            rid = next(self._ids)
            self._proc.stdin.write(json.dumps({"id": rid, "method": method, "params": params}) + "\n")
            self._proc.stdin.flush()
            while True:
                line = self._proc.stdout.readline()
                if not line:
                    raise HMemUnavailable("the H-MEM process ended unexpectedly")
                msg = json.loads(line)
                if msg.get("id") != rid:
                    continue
                if "error" in msg:
                    raise ValueError(msg["error"])
                return msg["result"]

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc and proc.poll() is None:
            try:
                proc.stdin.close()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    # -- the H-MEM surface (names follow the spec's services) -------------------------------------
    def add(self, content: str, source: str, **fields: Any) -> dict:
        return self.call("add", content=content, source=source, **fields)

    def get(self, memory_id: str) -> dict | None:
        return self.call("get", id=memory_id)

    def all(self) -> list[dict]:
        return self.call("all")

    def query(self, query: str, top_n: int | None = None, threshold: float | None = None) -> dict:
        opts = {k: v for k, v in (("topN", top_n), ("threshold", threshold)) if v is not None}
        return self.call("query", query=query, opts=opts)

    def feedback(self, memory_id: str, kind: str) -> dict:
        if kind not in ("helpful", "not_helpful", "wrong"):
            raise ValueError(f"unknown feedback kind {kind!r}")
        return self.call("feedback", id=memory_id, kind=kind)

    def mine(self, event: str, text: str) -> list[dict]:
        return self.call("mine", event=event, text=text)

    def history(self, memory_id: str) -> list[dict]:
        return self.call("ledger_history", id=memory_id)

    def ledger_stats(self) -> dict:
        return self.call("ledger_stats")

    def scan_conflicts(self) -> list[dict]:
        return self.call("conflicts_scan")

    def auto_resolve(self, conflict: dict) -> str:
        return self.call("conflicts_auto_resolve", conflict=conflict)

    def sleep_preview(self) -> dict:
        return self.call("sleep_preview")

    def sleep_execute(self, preview: dict | None = None) -> dict:
        return self.call("sleep_execute", preview=preview)

    def sleep_restore(self, backup_id: str) -> None:
        self.call("sleep_restore", backupId=backup_id)

    def dream(self) -> list[dict]:
        return self.call("dream")

    def dream_pending(self) -> list[dict]:
        return self.call("dream_pending")

    def dream_approve(self, proposal_id: str) -> dict | None:
        return self.call("dream_approve", id=proposal_id)

    def dream_reject(self, proposal_id: str) -> None:
        self.call("dream_reject", id=proposal_id)
