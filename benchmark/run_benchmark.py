"""Benchmark: does the solver loop beat the LLM on its own, and what does each part contribute?

Arms
  brute_force      exhaustive enumeration up to the ground-truth size (exact reference, no search guidance)
  llm_only         one LLM call, no verification: what the model claims without a solver
  llm_feedback     LLM + solver verification + counterexample feedback, no guided search
  symbolic_cegar   NO LLM: the counterexample-guided search alone (complete, proves infeasibility)
  llm_cegar        LLM proposals steer the counterexample-guided search
  ours_full        llm_cegar + checked explanations (the system as shipped)

Ground truth (benchmark/ground_truth.json) comes from the exhaustive solver, so every claim is scored against a
proof, not an opinion. The model is selectable (--model), which is how the same suite runs with other providers.

    python benchmark/run_benchmark.py --repeats 3 --workers 4
"""
from __future__ import annotations

import argparse
import os
import concurrent.futures as cf
import json
import random
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AGENT_LOG_DIR", "off")          # thousands of agent runs: no per-run evidence files
from agent.llm import LLMResponse, NemotronClient  # noqa: E402
from agent.main import CEGARAgent  # noqa: E402
from agent.tools_zetaris import DataLayer  # noqa: E402
from solver.boolean_net import BooleanNetwork  # noqa: E402
from solver.knockout_opt import minimal_knockouts  # noqa: E402
from solver.verifier import FORCED, Scenario, Verifier  # noqa: E402

ARMS = ["brute_force", "llm_only", "llm_feedback", "symbolic_cegar", "llm_cegar", "ours_full"]
OUT = ROOT / "benchmark"


class NullProposer:
    """No LLM at all: every round yields no proposals, so only the guided search works."""
    model = "none (symbolic only)"

    def complete(self, messages, max_tokens=0, temperature=0.0):
        return LLMResponse(json.dumps({"proposals": [], "give_up": False}))


def scenario_obj(data: DataLayer, sid: str) -> Scenario:
    return Scenario.from_row(data.scenario(sid))


def run_one(arm: str, sid: str, truth: dict, model: str | None, seed: int) -> dict:
    gt = {tuple(sorted(e["knockouts"])) for e in truth["minimal_sets"]}
    feasible = bool(gt)
    max_size = truth["max_size_searched"]
    data = DataLayer()
    t0 = time.perf_counter()
    res: dict = {"arm": arm, "scenario": sid, "seed": seed, "feasible": feasible, "found": [], "solver_calls": 0,
                 "llm_calls": 0, "tokens": 0, "claimed_wrong": 0, "claimed_total": 0, "certified_infeasible": None,
                 "first_attempt": None, "repair_calls": 0, "explained": None}
    quiet = lambda _: None  # noqa: E731
    common = dict(memory_mode="session", max_size=max_size, target_solutions=max(len(gt), 1), log=quiet)

    if arm == "brute_force":
        ver = Verifier(BooleanNetwork.from_rows(data.network_rows()))
        out = minimal_knockouts(ver, scenario_obj(data, sid), max_size=max_size)
        res.update(found=[list(s) for s in out.solutions], solver_calls=ver.calls,
                   certified_infeasible=not out.solutions)
    elif arm == "llm_only":
        agent = CEGARAgent(NemotronClient(model=model), data, explain=False, **{**common, "memory_mode": "off"})
        proposals, gave_up = agent.propose_only(sid, n=5)
        oracle = Verifier(agent.net)
        sc = scenario_obj(data, sid)
        good = [p for p in proposals if oracle.verify(sc, p).verdict == FORCED]
        res.update(found=[list(p) for p in good if p in gt], claimed_total=len(proposals),
                   claimed_wrong=len(proposals) - len(good), llm_calls=agent._llm_calls, tokens=agent._tokens)
        res["valid_but_not_minimal"] = len([p for p in good if p not in gt])
        res["gave_up"] = gave_up
    else:
        llm = NullProposer() if arm == "symbolic_cegar" else NemotronClient(model=model)
        kw = dict(common, explain=(arm == "ours_full"), cegar=arm != "llm_feedback",
                  fallback=arm in ("symbolic_cegar", "llm_cegar", "ours_full"), max_rounds=8)
        agent = CEGARAgent(llm, data, **kw)
        rep = agent.run(sid)
        res.update(found=[s.knockouts for s in rep.solutions], llm_found=[s.knockouts for s in rep.solutions if s.found_by == "llm"],
                   solver_calls=rep.solver_calls, llm_calls=rep.llm_calls, tokens=rep.tokens,
                   certified_infeasible=rep.certified_infeasible, first_attempt=rep.calls_to_first_solution,
                   memory_refutations=rep.memory_refutations + rep.cegar_replays, notes=rep.notes)
        if arm == "ours_full":
            exps = [s.explanation for s in rep.solutions if s.explanation]
            res["explained"] = {"steps_ok": sum(e["steps_ok"] for e in exps), "steps_total": sum(e["steps_total"] for e in exps),
                                "faithful": sum(e["faithful"] for e in exps), "n": len(exps)}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    got = {tuple(sorted(s)) for s in res["found"]}
    res["recall"] = (len(got & gt) / len(gt)) if feasible else None
    res["solved"] = bool(got & gt) if feasible else None
    return res


def aggregate(rows: list[dict]) -> dict:
    feas = [r for r in rows if r["feasible"]]
    infeas = [r for r in rows if not r["feasible"]]
    mean = lambda xs: round(statistics.mean(xs), 2) if xs else None  # noqa: E731
    out = {
        "runs": len(rows),
        "solved_rate": mean([r["solved"] for r in feas]),
        "recall": mean([r["recall"] for r in feas]),
        "solver_calls": mean([r["solver_calls"] for r in rows]),
        "calls_to_first": mean([r["first_attempt"] for r in rows if r.get("first_attempt") is not None]),
        "llm_calls": mean([r["llm_calls"] for r in rows]),
        "seconds": mean([r["seconds"] for r in rows]),
        "tokens": mean([r["tokens"] for r in rows]),
    }
    claims = sum(r["claimed_total"] for r in rows)
    if claims:
        out["wrong_claim_rate"] = round(sum(r["claimed_wrong"] for r in rows) / claims, 2)
    if infeas:
        if rows[0]["arm"] == "llm_only":
            out["infeasible_hallucinated"] = mean([r["claimed_total"] > 0 for r in infeas])
        else:
            out["infeasible_proved"] = mean([bool(r["certified_infeasible"]) for r in infeas])
    ex = [r["explained"] for r in rows if r.get("explained")]
    if ex:
        out["explanation_steps_verified"] = round(sum(e["steps_ok"] for e in ex) / max(1, sum(e["steps_total"] for e in ex)), 3)
        out["explanations_fully_faithful"] = round(sum(e["faithful"] for e in ex) / max(1, sum(e["n"] for e in ex)), 3)
    return out


def markdown(model: str, results: dict[str, list[dict]]) -> str:
    cols = ["solved_rate", "recall", "solver_calls", "calls_to_first", "llm_calls", "seconds", "wrong_claim_rate",
            "infeasible_proved", "infeasible_hallucinated", "explanation_steps_verified"]
    lines = [f"# Benchmark results ({model})", "",
             "Scored against exhaustive-solver ground truth. `solved_rate`/`recall` are over feasible scenarios; "
             "`infeasible_*` over the scenario with no solution.", "",
             "| arm | runs | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for arm, rows in results.items():
        agg = aggregate(rows)
        lines.append(f"| {arm} | {agg['runs']} | " + " | ".join("" if agg.get(c) is None else str(agg[c]) for c in cols) + " |")
    lines += ["", "## Per scenario (mean over repeats)", "", "| scenario | arm | solved | recall | solver calls | LLM calls | s |",
              "|---|---|---|---|---|---|---|"]
    for arm, rows in results.items():
        for sid in sorted({r["scenario"] for r in rows}):
            sub = [r for r in rows if r["scenario"] == sid]
            a = aggregate(sub)
            lines.append(f"| {sid} | {arm} | {a['solved_rate'] if a['solved_rate'] is not None else 'n/a'} | "
                         f"{a['recall'] if a['recall'] is not None else 'n/a'} | {a['solver_calls']} | {a['llm_calls']} | {a['seconds']} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=ARMS, choices=ARMS)
    ap.add_argument("--scenarios", nargs="*")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default=None)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    truth = json.loads((OUT / "ground_truth.json").read_text(encoding="utf-8"))
    sids = args.scenarios or list(truth)
    model = args.model or NemotronClient().model
    jobs = []
    for arm in args.arms:
        reps = 1 if arm == "brute_force" else args.repeats
        for sid in sids:
            for k in range(reps):
                jobs.append((arm, sid, truth[sid], args.model, k))
    print(f"{len(jobs)} runs, model {model}", flush=True)
    results: dict[str, list[dict]] = {a: [] for a in args.arms}
    pooled = [j for j in jobs if j[0] != "brute_force"]
    serial = [j for j in jobs if j[0] == "brute_force"]      # timed alone: parallel threads would distort seconds
    done = 0

    def record(job, fut_result=None, error=None):
        nonlocal done
        done += 1
        arm, sid = job[0], job[1]
        if error is not None:
            print(f"[{done}/{len(jobs)}] {arm} {sid} FAILED: {error}", flush=True)
            return
        results[arm].append(fut_result)
        print(f"[{done}/{len(jobs)}] {arm:14s} {sid:16s} solved={fut_result['solved']} recall={fut_result['recall']} "
              f"solver={fut_result['solver_calls']} llm={fut_result['llm_calls']} {fut_result['seconds']}s", flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(run_one, *j): j for j in pooled}
        for fut in cf.as_completed(futs):
            try:
                record(futs[fut], fut.result())
            except Exception as exc:  # one failed run must not hide the others
                record(futs[fut], error=exc)
    for j in serial:
        try:
            record(j, run_one(*j))
        except Exception as exc:
            record(j, error=exc)
    stamp = args.tag or re.sub(r"[^A-Za-z0-9]+", "-", model).strip("-")
    (OUT / f"results-{stamp}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    md = markdown(model, {a: r for a, r in results.items() if r})
    (OUT / f"RESULTS-{stamp}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
