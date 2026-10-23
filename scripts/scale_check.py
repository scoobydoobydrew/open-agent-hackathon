"""Scalability probe: load another published .bnet model (PyBoolNet repository format) and run the solver on it.

    python scripts/scale_check.py path/to/grieco_mapk.bnet

Reports free nodes after reduction, attractors (exact when <= 21 free bits) and the guided search. Measured on
grieco_mapk (53 nodes): with EGF or FGFR3 the single strongly connected component has 35-37 nodes, so the exact engine
answers UNKNOWN; a symbolic attractor backend would be needed.
"""
import sys
sys.path.insert(0, ".")
import re, sys, time, math, itertools
sys.path.insert(0, ".")
from solver.boolean_net import BooleanNetwork, NodeSpec, INPUT, INTERNAL, OUTPUT
from solver.verifier import Scenario, Verifier
from solver.cegar import CegarSearch
from solver.attractors import analyze
from solver.knockout_opt import candidate_genes

def load(path, outputs):
    specs = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or line.lower().startswith("targets"): continue
        n, r = (x.strip() for x in line.split(",", 1))
        role = INPUT if r == n else OUTPUT if n in outputs else INTERNAL
        specs.append(NodeSpec(n, n, role, r))
    return BooleanNetwork(specs)

net = load(sys.argv[1], {"Apoptosis", "Proliferation", "Growth_Arrest"})
print("nodes", len(net.order), "inputs", net.inputs, "outputs", net.outputs, "knockable", len(net.knockable_genes()))
v = Verifier(net)
for name, fixed in {"radiation + EGF": dict(DNA_damage=1, EGFR_stimulus=1, FGFR3_stimulus=0, TGFBR_stimulus=0),
                    "radiation + FGFR3": dict(DNA_damage=1, EGFR_stimulus=0, FGFR3_stimulus=1, TGFBR_stimulus=0),
                    "radiation + TGFb": dict(DNA_damage=1, EGFR_stimulus=0, FGFR3_stimulus=0, TGFBR_stimulus=1)}.items():
    fixed = {k: x for k, x in fixed.items() if k in net.specs}
    sc = Scenario(name, fixed, {"Apoptosis": 1})
    t = time.time(); a = analyze(net, dict(fixed))
    print(f"\n[{name}] attractors: complete={a.complete} n={len(a.attractors)} free_bits={len(a.state_nodes)} ({time.time()-t:.2f}s)")
    for at in a.attractors[:4]:
        print("   ", at.kind, at.n_states, {k: at.values[k] for k in ("Apoptosis", "Proliferation", "Growth_Arrest")})
    base = v.verify(sc, [])
    print("   baseline:", base.verdict, "|", base.method)
    cands = candidate_genes(v, sc); total = sum(math.comb(len(cands), k) for k in range(4))
    s = CegarSearch(v, sc, max_size=3, candidates=cands)
    t = time.time(); s.advance()
    print(f"   search size<=3: solutions={[f.knockouts for f in s.solutions][:8]} total={len(s.solutions)} calls={s.calls} vs brute={total} proved_infeasible={s.proved_infeasible} incomplete={s.incomplete} ({time.time()-t:.1f}s)")
