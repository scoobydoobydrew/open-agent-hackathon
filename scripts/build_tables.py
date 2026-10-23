"""Build data/phenotypes.csv and benchmark/ground_truth.json from the solver.

phenotypes.csv (ingested into Zetaris) holds scenario definitions and what the
unperturbed network does. It deliberately contains NO solutions: the agent has
to find them. The exhaustive answers go to benchmark/ground_truth.json, which
only the benchmark reads.

    python scripts/build_tables.py            # scenarios up to size 3 (about 3 min)
    python scripts/build_tables.py --quick    # baselines only, no exhaustive search
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from solver.boolean_net import BooleanNetwork  # noqa: E402
from solver.knockout_opt import minimal_knockouts  # noqa: E402
from solver.verifier import Scenario, Verifier  # noqa: E402

SOURCE = "exact attractor analysis of the Remy et al. 2015 rules"
GOAL = "Apoptosis_high=1"


def inputs(damage=0, egf=0, fgfr3=0, inhib=0, **lesions):
    fixed = f"DNA_damage={damage};EGFR_stimulus={egf};FGFR3_stimulus={fgfr3};Growth_inhibitors={inhib}"
    return fixed + "".join(f";{g}={v}" for g, v in lesions.items())


# (id, kind, description, fixed_nodes, max_size)
SCENARIOS = [
    ("fgfr3_wtp53", "target", "FGFR3-driven tumour with wild-type p53 after radiation", inputs(1, fgfr3=1), 3),
    ("egf_wtp53", "target", "EGF-driven tumour with wild-type p53 after radiation", inputs(1, egf=1), 3),
    ("egf_growthinh", "target", "EGF-driven tumour in an anti-growth (TGF-beta like) environment after radiation",
     inputs(1, egf=1, inhib=1), 3),
    ("fgfr3_growthinh", "target", "FGFR3-driven tumour in an anti-growth environment after radiation",
     inputs(1, fgfr3=1, inhib=1), 3),
    ("egf_tp53null", "target", "EGF-driven tumour that has lost TP53, after radiation", inputs(1, egf=1, TP53=0), 3),
    ("egf_mdm2amp", "target", "EGF-driven tumour with MDM2 amplification, after radiation", inputs(1, egf=1, MDM2=1), 3),
    ("fgfr3_rb1loss", "target", "FGFR3-driven tumour that has lost RB1, after radiation", inputs(1, fgfr3=1, RB1=0), 3),
    ("growthinh_only", "target", "Quiescent anti-growth tissue with no mitogenic signal, after radiation",
     inputs(1, inhib=1), 4),
    ("normal_resting_rt", "safety", "Resting normal cell exposed to the same radiation (must not undergo apoptosis)",
     inputs(1), 0),
    ("normal_resting", "safety", "Resting normal cell without radiation (must not undergo apoptosis)", inputs(0), 0),
    ("ref_healthy_resting", "reference", "Healthy resting cell, no stimulus, no damage", inputs(0), 0),
    ("ref_healthy_fgfr3", "reference", "Healthy cell with FGFR3 growth signal, no damage", inputs(0, fgfr3=1), 0),
    ("ref_wt_radiation", "reference", "Wild-type cell, no growth signal, radiation", inputs(1), 0),
]


def parse(fixed: str) -> dict[str, int]:
    return {k: int(v) for k, v in (p.split("=") for p in fixed.split(";"))}


def describe(verification) -> str:
    atts = verification.attractors
    if not atts:
        ce = verification.counterexample
        return "stable state: " + ";".join(f"{k}={v}" for k, v in ce["phenotype"].items()) if ce else ""
    parts = []
    for a in atts:
        ph = ";".join(f"{k}={v}" for k, v in a["phenotype"].items())
        parts.append(f"{a['kind']}({a['n_states']}): {ph}")
    return " | ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    with (ROOT / "data" / "p53_interactions.csv").open(encoding="utf-8") as fh:
        net = BooleanNetwork.from_rows(csv.DictReader(fh))
    verifier = Verifier(net)
    goal = {"Apoptosis_high": 1}

    safety = [Scenario(i, parse(f), goal, "safety") for i, k, _, f, _ in SCENARIOS if k == "safety"]
    rows, truth = [], {}
    for sid, kind, desc, fixed, max_size in SCENARIOS:
        sc = Scenario(sid, parse(fixed), goal, kind if kind != "reference" else "target", desc)
        base = verifier.verify(sc, [])
        verdict = base.verdict
        rows.append([sid, kind, desc, fixed, GOAL if kind != "reference" else "", verdict,
                     describe(base), SOURCE])
        if kind == "target" and not args.quick:
            res = minimal_knockouts(verifier, sc, max_size=max_size)
            entries = []
            for sol in res.solutions:
                tox = [s.name for s in safety if verifier.verify(s, sol).verdict != "SAFE"]
                entries.append({"knockouts": list(sol), "selective": not tox, "toxic_in": tox})
            truth[sid] = {"baseline": verdict, "max_size_searched": max_size,
                          "sets_evaluated": res.evaluated, "seconds": res.seconds, "minimal_sets": entries}
            print(f"{sid}: {len(entries)} minimal set(s) up to size {max_size} ({res.seconds}s)", flush=True)

    out = ROOT / "data" / "phenotypes.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "kind", "description", "fixed_nodes", "goal",
                    "baseline_verdict", "baseline_phenotype", "source"])
        w.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} scenarios)")
    if truth:
        gt = ROOT / "benchmark" / "ground_truth.json"
        gt.parent.mkdir(exist_ok=True)
        gt.write_text(json.dumps(truth, indent=2), encoding="utf-8")
        print(f"wrote {gt.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
