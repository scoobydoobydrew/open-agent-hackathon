"""Convert data/source/remy_tumorigenesis.bnet into data/p53_interactions.csv.

The CSV is the table that gets ingested into Zetaris. Edge signs are derived
from the rules (truth-table test), not typed by hand.

Source model: Remy et al., Cancer Research 2015 (booleanized with GINsim,
Didier et al. 2011), as distributed in the PyBoolNet model repository.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from solver.boolean_net import INPUT, INTERNAL, OUTPUT, BooleanNetwork, NodeSpec  # noqa: E402

OUTPUT_NODES = {"Apoptosis_medium", "Apoptosis_high", "Growth_arrest", "Proliferation"}
LEVEL_SUFFIX = re.compile(r"^(.*)_(medium|high)$")


def read_bnet(path: Path) -> list[tuple[str, str]]:
    rules = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower().startswith("targets"):
            continue
        name, rule = (part.strip() for part in line.split(",", 1))
        rules.append((name, rule))
    return rules


def build() -> BooleanNetwork:
    specs = []
    for name, rule in read_bnet(ROOT / "data" / "source" / "remy_tumorigenesis.bnet"):
        if rule == name:
            role = INPUT
        elif name in OUTPUT_NODES:
            role = OUTPUT
        else:
            role = INTERNAL
        m = LEVEL_SUFFIX.match(name)
        gene = m.group(1) if m else name
        specs.append(NodeSpec(name, gene, role, rule))
    net = BooleanNetwork(specs)
    for name in net.order:
        if net.specs[name].role != OUTPUT:
            leaked = net.regulators(name) & OUTPUT_NODES
            assert not leaked, f"{name} depends on output nodes {leaked}"
    return net


def main() -> None:
    net = build()
    signs: dict[str, list[str]] = {}
    for src, dst, sign in net.edge_signs():
        signs.setdefault(dst, []).append(f"{src}{sign}")
    out = ROOT / "data" / "p53_interactions.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["node", "gene", "role", "rule", "regulators"])
        for n in net.order:
            s = net.specs[n]
            w.writerow([s.name, s.gene, s.role, s.rule, ";".join(signs.get(n, []))])
    print(f"wrote {out.relative_to(ROOT)}: {len(net.order)} nodes, "
          f"{len(net.knockable_genes())} knockable genes")


if __name__ == "__main__":
    main()
