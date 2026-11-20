"""Compare a rerun of the simulation with the saved per-subtype values.

    python tools/compare_rerun.py COPY MODEL [MODEL ...]      (make rerun runs it)

COPY is a copy of this release in which code/simulate.py has written new raw records for the given confirmation
models. For every application, stimulus and condition of each model, this applies the frozen readout function
(code/score.py, per_subtype) to the new records and compares the result with the saved
results/confirmation/derived/PER-SUBTYPE.csv, which was written by the same function from the original records.
The GPU sums in a varying order, so values pass when their relative gap is at most 1e-4 (the protocol's identity
tolerance); an undefined ratio must be undefined in both. Exit status 1 on any failure.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

RELEASE = Path(__file__).resolve().parents[1]
TOL = 1e-4


def main() -> int:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    copy, models = Path(sys.argv[1]).resolve(), sys.argv[2:]
    sys.path.insert(0, str(copy / "code"))
    sys.dont_write_bytecode = True
    import score as S
    saved = {}
    with (RELEASE / "results/confirmation/derived/PER-SUBTYPE.csv").open(newline="") as stream:
        for r in csv.DictReader(stream):
            if r["model"] in models:
                saved[(r["mode"], r["model"], r["stimulus"], r["condition"], r["readout"], r["subtype"])] = float(r["value"])
    codes = json.loads((RELEASE / "results/confirmation/confirmation-run.json").read_text())["conditions"]
    root = copy / "results/confirmation"
    stims = {k: S.stimulus(k) for k in S.STIMULI}
    n, worst, bad = 0, 0.0, []
    for model in models:
        for mode in S.MODES:
            for key in S.STIMULI:
                base = S.load(root / mode / model / key / "baseline.npz")
                for code in codes:
                    per = S.per_subtype(base, S.load(root / mode / model / key / f"{code}.npz"), stims[key])
                    for readout in S.READOUTS:
                        for sub, value in per[readout].items():
                            theirs = saved[(mode, model, key, code, readout, sub)]
                            n += 1
                            if math.isnan(theirs) or math.isnan(value):
                                ok = math.isnan(theirs) and math.isnan(value)
                            else:
                                gap = abs(value - theirs) / max(1.0, abs(theirs))
                                worst = max(worst, gap)
                                ok = gap <= TOL
                            if not ok:
                                bad.append(f"{model}/{mode}/{key}/{code}/{readout}/{sub}: {value!r} vs {theirs!r}")
    print(f"rerun of models {', '.join(models)}: {n} per-subtype values compared with the saved ones; worst relative "
          f"gap {worst:.1e} (limit {TOL:.0e}); failures {len(bad)}")
    for b in bad[:20]:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
