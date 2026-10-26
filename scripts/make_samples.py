"""Run the agent on sample inputs and keep readable outputs and traces under logs/samples/.

    python scripts/make_samples.py --replays             # also refresh the UI's offline replays from the same runs
    python scripts/make_samples.py                       # three scenarios, LLM through Nightshift (or the labelled fallback)
    SAMPLE_MODE=true python scripts/make_samples.py      # no LLM, no network: symbolic search on the local files only

Per scenario it writes <id>.md (the report), <id>.events.jsonl (every proposal, verdict, SQL call and LLM request in
order), <id>.hmem-ledger.jsonl (the H-MEM audit ledger of the run), <id>.llm-trace.jsonl (one line per LLM request:
provider, requested and routed model, latency, tokens; no prompts and no keys), and hmem-retrieval.jsonl (what the memory
engine retrieved and injected before each proposal round).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.llm import ChatClient, LLMError, NemotronClient, NoLLM  # noqa: E402
from agent.main import CEGARAgent, to_markdown  # noqa: E402
from ui.record_replays import save_replay, target_solutions  # noqa: E402

DEFAULT = ["fgfr3_wtp53", "egf_tp53null", "growthinh_only"]
OUT = ROOT / "logs" / "samples"


def run_one(sid: str, out: Path, max_size: int, rounds: int, replays: bool) -> None:
    os.environ["AGENT_LOG_DIR"] = str(out)                      # events, H-MEM ledger and retrieval log land next to the report
    trace = out / f"{sid}.llm-trace.jsonl"
    trace.unlink(missing_ok=True)
    try:
        llm: ChatClient = NemotronClient(trace_path=trace)
    except LLMError as exc:
        print(f"  no LLM ({exc}); running the symbolic search only")
        llm = NoLLM(str(exc))
    events: list[dict] = []
    agent = CEGARAgent(llm, memory_mode="session", max_size=4 if sid == "growthinh_only" else max_size, max_rounds=rounds,
                       per_round=3, target_solutions=target_solutions(sid), explain=True, sql_tool=True, log=lambda _: None,
                       log_prefix=sid, on_event=events.append)
    t0 = time.time()
    report = agent.run(sid)
    (out / f"{sid}.md").write_text(to_markdown(report) + "\n", encoding="utf-8")
    if replays:
        save_replay(sid, llm, events, time.time() - t0)
    print(f"  {sid}: {len(report.solutions)} solution(s), {report.solver_calls} solver calls, "
          f"{report.llm_calls} LLM calls via {report.llm_provider or 'none'} {report.llm_models}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenarios", nargs="*", default=DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--max-size", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--replays", action="store_true", help="also write ui/replays/<id>.json from the same runs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "hmem-retrieval.jsonl").unlink(missing_ok=True)
    for sid in args.scenarios:
        run_one(sid, args.out, args.max_size, args.rounds, args.replays)
    print("written to", args.out)


if __name__ == "__main__":
    main()
