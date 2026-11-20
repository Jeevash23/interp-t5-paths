"""Compare the saved per-subtype values with the independent recheck's (standard library only).

    python3 tools/compare_recheck.py          # after make unpack; exit status 1 on any mismatch

recheck/RECHECK.json was written on 23 October 2026 by a separate script (recheck/recheck.py) that read the raw
simulation records directly and never imported the study's scoring code. For the readouts it recomputed (pd_evoked
and P7's pooled raw-peak ratio, per T5 subtype and stimulus, both applications, the two positive controls and every
full-strength condition), this tool checks that results/confirmation/derived/PER-SUBTYPE.csv, which the release's
score replay reads, holds the same values (relative gap at most 1e-9, the recheck's own tolerance; an undefined ratio
must be undefined in both).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

RELEASE = Path(__file__).resolve().parents[1]
TOL = 1e-9
NAMES = {"pd_evoked": "pd_evoked", "pooled_raw": "pooled"}
STIMULI = ("final_slow", "dev_fast")


def main() -> int:
    table = {}
    with (RELEASE / "results/confirmation/derived/PER-SUBTYPE.csv").open(newline="") as stream:
        for r in csv.DictReader(stream):
            table[(r["mode"], r["model"], r["stimulus"], r["condition"], r["readout"], r["subtype"])] = float(r["value"])
    recheck = json.loads((RELEASE / "recheck/RECHECK.json").read_text())["per_model_subtype_ratios"]
    n, bad = 0, []
    for model, modes in recheck.items():
        for mode, readouts in modes.items():
            for readout, conditions in readouts.items():
                for code, per_stim in conditions.items():
                    for key, subs in zip(STIMULI, per_stim):
                        for letter, theirs in zip("abcd", subs):
                            mine = table[(mode, model, key, code, NAMES[readout], letter)]
                            n += 1
                            if theirs is None or (isinstance(theirs, float) and math.isnan(theirs)):
                                ok = math.isnan(mine)
                            else:
                                ok = math.isfinite(mine) and abs(mine - theirs) / max(1.0, abs(theirs)) <= TOL
                            if not ok:
                                bad.append(f"{model}/{mode}/{key}/{code}/{readout}/T5{letter}: {mine!r} vs {theirs!r}")
    print(f"per-subtype values compared with the independent recheck: {n}, mismatches: {len(bad)}")
    for b in bad[:20]:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
