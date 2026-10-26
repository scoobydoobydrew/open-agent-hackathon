"""Rewrite input_examples/ and output_examples/: three request payloads and the reports `POST /run` returns for them.

    python scripts/make_examples.py

The examples are produced in SAMPLE_MODE with the LLM off, so they are reproducible on any machine without an account:
the solutions and proofs come from the solver and the complete search.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["SAMPLE_MODE"] = "true"
os.environ["AGENT_LOG_DIR"] = "off"
sys.path.insert(0, str(ROOT))

from agent.api import run_payload  # noqa: E402

INPUTS = [
    {"scenario": "fgfr3_wtp53", "max_size": 3, "rounds": 4, "solutions": 3, "llm": False},
    {"scenario": "egf_tp53null", "max_size": 3, "rounds": 4, "solutions": 3, "llm": False},
    {"scenario": "growthinh_only", "max_size": 3, "rounds": 4, "solutions": 3, "llm": False},
]


def main() -> None:
    (ROOT / "input_examples").mkdir(exist_ok=True)
    (ROOT / "output_examples").mkdir(exist_ok=True)
    for i, payload in enumerate(INPUTS, start=1):
        (ROOT / "input_examples" / f"example_{i}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        out = run_payload(payload)
        rep = out["report"]
        rep["seconds"] = 0.0                                   # timing differs per machine; keep the files stable
        (ROOT / "output_examples" / f"example_{i}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"example_{i}: {payload['scenario']} -> {len(rep['solutions'])} solution(s), "
              f"{rep['solver_calls']} solver calls, infeasible proved: {rep['certified_infeasible']}")


if __name__ == "__main__":
    main()
