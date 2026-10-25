"""Local web UI for the verified knockout agent (standard library only).

    python ui/server.py            # then open http://localhost:8765

Everything the page shows comes from the real solver and agent: nothing is mocked.
  GET  /api/meta                   network graph, scenarios, drug table, replays, benchmark summary
  POST /api/verify                 verdict, attractors, counterexample, proof steps for one knockout set
  GET  /api/search  (SSE)          the counterexample-guided search, event by event
  GET  /api/agent   (SSE)          a live LLM + solver run (needs NVIDIA_API_KEY)
  GET  /api/replay?name=...        a recorded agent run (works offline)
"""
from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.llm import LLMError, NemotronClient  # noqa: E402
from agent.main import CEGARAgent  # noqa: E402
from agent.memory import HMem  # noqa: E402
from agent.tools_zetaris import DataLayer  # noqa: E402
from agent.zetaris_heal import heal  # noqa: E402
from solver.attractors import analyze  # noqa: E402
from solver.boolean_net import INPUT, OUTPUT, BooleanNetwork  # noqa: E402
from solver.cegar import CegarSearch  # noqa: E402
from solver.explain import step_entailed, steps_from_tree  # noqa: E402
from solver.knockout_opt import candidate_genes  # noqa: E402
from solver.verifier import SAFE, Scenario, Verifier, knockout_constants  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
REPLAYS = Path(__file__).resolve().parent / "replays"
BENCH = ROOT / "benchmark"
GOAL = {"Apoptosis_high": 1}


class _Abort(Exception):
    pass


class State:
    """Loaded once; every request reads from it."""

    def __init__(self) -> None:
        self.data = DataLayer()
        self.rows = self.data.network_rows()
        self.net = BooleanNetwork.from_rows(self.rows)
        self.scenarios = {r["scenario_id"]: r for r in self.data.scenarios()}
        self.drugs = {r["gene"]: r for r in self.data.drug_ranking_join()}
        self.safety = [Scenario.from_row(r) for r in self.scenarios.values() if r["kind"] == "safety"]
        self.truth = {}
        gt = BENCH / "ground_truth.json"
        if gt.exists():
            self.truth = json.loads(gt.read_text(encoding="utf-8"))
        self.verifier = Verifier(self.net)
        self.lock = threading.Lock()
        self.graph = self._graph()
        self._retried = time.time()

    def reconnect(self, force: bool = False) -> str:
        """Retry Zetaris when the data layer fell back to local CSV (it goes down whenever Docker restarts)."""
        if self.data.source == "zetaris" or (not force and time.time() - self._retried < 30):
            return self.data.source
        self._retried = time.time()
        fresh = DataLayer()
        fresh.network_rows()
        if fresh.source == "zetaris":
            self.data = fresh
            self.scenarios = {r["scenario_id"]: r for r in fresh.scenarios()}
            self.drugs = {r["gene"]: r for r in fresh.drug_ranking_join()}
        return self.data.source

    # -- gene level graph ----------------------------------------------------------------------
    def _graph(self) -> dict:
        net = self.net
        genes = []
        for gene, nodes in net.genes.items():
            roles = {net.specs[n].role for n in nodes}
            kind = "input" if roles == {INPUT} else "output" if roles == {OUTPUT} else "gene"
            ordered = sorted(nodes, key=lambda n: (n.endswith("_high"), n))
            drug = self.drugs.get(gene, {})
            genes.append({"id": gene, "kind": kind, "nodes": ordered, "rules": {n: net.specs[n].rule for n in ordered},
                          "knockable": gene in net.knockable_genes(),
                          "druggable": drug.get("druggable", ""), "evidence": drug.get("evidence_level", ""),
                          "agents": drug.get("example_agents", "")})
        edges: dict[tuple[str, str], set[str]] = {}
        for src, dst, sign in net.edge_signs():
            a, b = net.specs[src].gene, net.specs[dst].gene
            if a != b:
                edges.setdefault((a, b), set()).add(sign)
        out_edges = [{"source": a, "target": b, "sign": "+/-" if len(s) > 1 or "+/-" in s else next(iter(s))}
                     for (a, b), s in sorted(edges.items())]
        # depth = distance from the inputs, used to lay the picture out left to right
        depth = {g["id"]: 0 for g in genes if g["kind"] == "input"}
        frontier = list(depth)
        while frontier:
            nxt = []
            for cur in frontier:
                for e in out_edges:
                    if e["source"] == cur and e["target"] not in depth:
                        depth[e["target"]] = depth[cur] + 1
                        nxt.append(e["target"])
            frontier = nxt
        top = max(depth.values(), default=1)
        for g in genes:
            g["depth"] = top + 1 if g["kind"] == "output" else depth.get(g["id"], 1)
        return {"genes": genes, "edges": out_edges, "max_depth": top + 1}

    # -- scenarios -----------------------------------------------------------------------------
    def scenario(self, sid: str, fixed: dict | None = None) -> Scenario:
        if fixed is not None:
            name = "custom:" + ";".join(f"{k}={v}" for k, v in sorted(fixed.items()))
            return Scenario(name, {k: int(v) for k, v in fixed.items()}, GOAL, "target", "Custom scenario")
        return Scenario.from_row(self.scenarios[sid])

    def replay_names(self) -> list[str]:
        return sorted(p.stem for p in REPLAYS.glob("*.json")) if REPLAYS.exists() else []

    def benchmark(self) -> dict | None:
        path = BENCH / "results-nemotron-lightning.json"
        if not path.exists():
            return None
        import importlib
        mod = importlib.import_module("benchmark.run_benchmark")
        results = json.loads(path.read_text(encoding="utf-8"))
        return {"model": "nvidia/nemotron-3.5-lightning-30b-a3b",
                "arms": {arm: mod.aggregate(rows) for arm, rows in results.items() if rows},
                "per_scenario": {arm: {sid: mod.aggregate([r for r in rows if r["scenario"] == sid])
                                       for sid in sorted({r["scenario"] for r in rows})}
                                 for arm, rows in results.items() if rows}}

    def meta(self) -> dict:
        solutions = {sid: [{"knockouts": e["knockouts"], "selective": e["selective"]} for e in t["minimal_sets"]]
                     for sid, t in self.truth.items()}
        scenarios = []
        for sid, r in self.scenarios.items():
            sc = Scenario.from_row(r)
            scenarios.append({"id": sid, "kind": r["kind"], "description": r["description"], "fixed": dict(sc.fixed),
                              "baseline": r["baseline_verdict"], "baseline_phenotype": r["baseline_phenotype"],
                              "max_size": self.truth.get(sid, {}).get("max_size_searched", 3)})
        return {"graph": self.graph, "scenarios": scenarios, "known_solutions": solutions,
                "replays": self.replay_names(), "data_source": self.data.source,
                "llm": {"available": bool(os.getenv("NVIDIA_API_KEY")),
                        "model": os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")},
                "benchmark": self.benchmark()}

    # -- verify --------------------------------------------------------------------------------
    def verify(self, sid: str, fixed: dict | None, kos: list[str]) -> dict:
        net = self.net
        sc = self.scenario(sid, fixed)
        kos = [g for g in kos if g in net.knockable_genes()]
        with self.lock:
            res = self.verifier.verify(sc, kos)
            safety = [{"scenario": s.name, "verdict": self.verifier.verify(s, kos).verdict} for s in self.safety]
        consts = knockout_constants(net, sc, kos)
        analysis = analyze(net, consts)
        attractors = [{"kind": a.kind, "n_states": a.n_states, "values": a.values,
                       "samples": a.samples[:1]} for a in analysis.attractors] if analysis.complete else []
        out = {"scenario": sc.name, "knockouts": kos, "verdict": res.verdict, "method": res.method,
               "elapsed_ms": res.elapsed_ms, "attractors": attractors, "complete": analysis.complete,
               "counterexample": res.counterexample, "derivation": res.explanation,
               "selective": all(s["verdict"] == SAFE for s in safety), "safety": safety,
               "forced_nodes": analysis.constants, "steps": []}
        if res.trees:
            known = knockout_constants(net, sc, kos)
            origin = {n: "scenario" for n in sc.fixed} | {n: "knockout" for n in net.nodes_of(kos)}
            for st in steps_from_tree(res.trees[0], limit=60):
                st["entailed"] = step_entailed(net, st, known)
                st["premises"] = [[n, v, origin.get(n, "")] for n, v in st["premises"]]
                out["steps"].append(st)
        return out


STATE: State | None = None
HEAL = {"running": False, "last": ""}


def start_heal() -> bool:
    """Bring Zetaris back in the background (Docker restarts break its driver container); no-op if already running."""
    if HEAL["running"] or os.getenv("ZETARIS_AUTOHEAL", "1") == "0":
        return False
    HEAL["running"], HEAL["last"] = True, "starting"

    def work() -> None:
        try:
            HEAL["last"] = heal(log=lambda m: HEAL.update(last=m))
            state().reconnect(force=True)
        except Exception as exc:  # keep the UI alive whatever Docker does
            HEAL["last"] = f"error: {exc}"
        finally:
            HEAL["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return True


def state() -> State:
    global STATE
    if STATE is None:
        STATE = State()
    return STATE


class Handler(BaseHTTPRequestHandler):
    server_version = "KnockoutUI/1.0"

    def log_message(self, fmt, *args):  # quiet
        pass

    # -- helpers -------------------------------------------------------------------------------
    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC / rel).resolve()
        if STATIC.resolve() not in target.parents and target != STATIC.resolve() or not target.is_file():
            self._json({"error": "not found"}, 404)
            return
        body = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix == ".js":
            ctype = "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _stream(self, worker) -> None:
        """Run ``worker(emit)`` in a thread and relay its events as server-sent events."""
        q: queue.Queue = queue.Queue()
        stop = threading.Event()

        def emit(ev: dict) -> None:
            if stop.is_set():
                raise _Abort()
            q.put(ev)

        def run() -> None:
            try:
                worker(emit)
            except _Abort:
                pass
            except Exception as exc:  # surface problems in the page instead of hanging
                q.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
            finally:
                q.put(None)

        threading.Thread(target=run, daemon=True).start()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                try:
                    ev = q.get(timeout=10)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                if ev is None:
                    break
                self.wfile.write(b"data: " + json.dumps(ev, default=str).encode("utf-8") + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            stop.set()

    # -- routes --------------------------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == "/api/meta":
                state().reconnect()
                return self._json(state().meta())
            if url.path == "/api/reconnect":
                if state().data.source != "zetaris":
                    start_heal()
                return self._json({"data_source": state().data.source, "healing": HEAL["running"], "last": HEAL["last"]})
            if url.path == "/api/replay":
                name = Path(qs.get("name", "")).name
                path = REPLAYS / f"{name}.json"
                if not path.is_file():
                    return self._json({"error": "unknown replay"}, 404)
                return self._json(json.loads(path.read_text(encoding="utf-8")))
            if url.path == "/api/search":
                return self._stream(lambda emit: self._search(qs, emit))
            if url.path == "/api/agent":
                return self._stream(lambda emit: self._agent(qs, emit))
            if url.path.startswith("/api/"):
                return self._json({"error": "not found"}, 404)
            return self._static(url.path)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        if url.path == "/api/verify":
            try:
                return self._json(state().verify(body.get("scenario", ""), body.get("fixed"), body.get("knockouts", [])))
            except KeyError:
                return self._json({"error": "unknown scenario"}, 404)
        return self._json({"error": "not found"}, 404)

    # -- streaming workers ---------------------------------------------------------------------
    def _search(self, qs: dict, emit) -> None:
        st = state()
        fixed = json.loads(qs["fixed"]) if qs.get("fixed") else None
        sc = st.scenario(qs.get("scenario", ""), fixed)
        max_size = int(qs.get("max_size") or st.truth.get(sc.name, {}).get("max_size_searched", 3))
        verifier = Verifier(st.net)
        cands = candidate_genes(verifier, sc)
        mem = HMem(st.net, None) if qs.get("memory") == "1" else None
        total = sum(math.comb(len(cands), k) for k in range(max_size + 1))
        emit({"type": "init", "scenario": sc.name, "max_size": max_size, "candidates": cands,
              "brute_force_sets": total, "memory": mem is not None})
        search = CegarSearch(verifier, sc, max_size, cands,
                             refute=(lambda s, k: mem.refutes(s, k)) if mem else None,
                             on_failure=(lambda k, r: mem.record(sc, k, r)) if mem else None,
                             on_event=emit)
        t0 = time.perf_counter()
        search.advance()
        emit({"type": "done", "calls": search.calls, "replays": search.replays, "seconds": round(time.perf_counter() - t0, 2),
              "proved_infeasible": search.proved_infeasible, "brute_force_sets": total,
              "solutions": [list(f.knockouts) for f in search.solutions]})

    def _agent(self, qs: dict, emit) -> None:
        st = state()
        try:
            llm = NemotronClient()
        except LLMError as exc:
            emit({"type": "error", "message": str(exc)})
            return
        target = len(st.truth.get(qs.get("scenario", ""), {}).get("minimal_sets", [])) or 3
        agent = CEGARAgent(llm, st.data, memory_mode="session", max_size=int(qs.get("max_size") or 3),
                           max_rounds=int(qs.get("rounds") or 5), per_round=3, target_solutions=min(target, 3),
                           explain=qs.get("explain", "1") == "1", sql_tool=True, log=lambda _: None, on_event=emit)
        agent.run(qs["scenario"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    state()  # fail early and warm up
    if state().data.source != "zetaris":
        start_heal()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"UI on http://{args.host}:{args.port}  (data layer: {state().data.source})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
