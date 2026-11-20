"""Development only: list the edge types into T5a-d and into/out of CT1 in one FlyVis model (no simulation)."""
import sys, os
from pathlib import Path
from collections import defaultdict
AI06 = Path(__file__).resolve().parents[1] / "reference/flyvis-first-order"  # release: the reference study's files
sys.path.insert(0, str(AI06 / "study/code")); sys.path.insert(0, str(AI06 / "02-Code/stage1"))
from core import Core
here = Path(__file__).resolve().parent.parent
os.environ["MPLCONFIGDIR"] = str(here / ".cache/matplotlib"); os.environ["XDG_CACHE_HOME"] = str(here / ".cache")
import numpy as np
c = Core(sys.argv[1] if len(sys.argv) > 1 else "000", "cpu")
src = c.source.numpy(); tar = c.target.numpy(); nt = c.node_names
w = c.weight.numpy(); sc = c.syn_counts
print("nodes", c.n, "edges", c.e, "types", c.c)
print("CT1-like types:", [x for x in c.names if "CT1" in x])
agg = defaultdict(lambda: [0, 0.0, 0.0])
for i in range(len(src)):
    a, b = nt[src[i]], nt[tar[i]]
    if b.startswith("T5") or "CT1" in b or ("CT1" in a and b.startswith("T5")) or a.startswith("T5"):
        r = agg[(a, b)]; r[0] += 1; r[1] += float(sc[i]); r[2] += float(w[i])
def show(pred, title):
    print("\n" + title)
    for (a, b), (n, s, ws) in sorted(agg.items(), key=lambda kv: (kv[0][1], -abs(kv[1][2]))):
        if pred(a, b): print(f"  {a:>10} -> {b:<10} edges {n:6d}  syn {s:9.1f}  weight_sum {ws:+.4f}")
show(lambda a, b: b == "T5a", "into T5a (per-edge weights are signed: sign x strength x count)")
show(lambda a, b: "CT1" in b, "into CT1 compartments")
show(lambda a, b: a.startswith("T5"), "out of T5 (all subtypes)")
