"""Record real agent runs so the UI can replay them offline (no API key, no cost, same events).

    python ui/record_replays.py fgfr3_wtp53 egf_wtp53 growthinh_only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.llm import NemotronClient  # noqa: E402
from agent.main import CEGARAgent  # noqa: E402
from agent.tools_zetaris import DataLayer  # noqa: E402

OUT = Path(__file__).resolve().parent / "replays"
DEFAULT = ["fgfr3_wtp53", "egf_wtp53", "egf_tp53null", "growthinh_only"]


def target_solutions(sid: str) -> int:
    truth = json.loads((ROOT / "benchmark" / "ground_truth.json").read_text(encoding="utf-8"))
    return min(len(truth.get(sid, {}).get("minimal_sets", [])) or 3, 3)


def save_replay(sid: str, llm, events: list[dict], seconds: float) -> Path:
    """Write the events of a real run in the form the UI's Replay button plays offline."""
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{sid}.json"
    path.write_text(json.dumps({"scenario": sid, "model": getattr(llm, "model", ""), "provider": getattr(llm, "provider", ""),
                                "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(seconds, 1),
                                "events": events}, default=str), encoding="utf-8")
    return path


def record(sid: str, rounds: int, max_size: int) -> Path:
    events: list[dict] = []
    llm = NemotronClient()
    agent = CEGARAgent(llm, DataLayer(), memory_mode="session", max_size=max_size, max_rounds=rounds, per_round=3,
                       target_solutions=target_solutions(sid), explain=True, sql_tool=True, log=lambda _: None,
                       on_event=events.append)
    t0 = time.time()
    agent.run(sid)
    return save_replay(sid, llm, events, time.time() - t0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenarios", nargs="*", default=DEFAULT)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--max-size", type=int, default=3)
    args = ap.parse_args()
    for sid in args.scenarios:
        path = record(sid, args.rounds, 4 if sid == "growthinh_only" else args.max_size)
        print(f"recorded {sid}: {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)", flush=True)


if __name__ == "__main__":
    main()
