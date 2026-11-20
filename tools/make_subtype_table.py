"""Write the per-subtype values of every confirmation record (added for the code release, post hoc).

    python tools/make_subtype_table.py [STUDY_DIR [OUTPUT_CSV]]

For every model, application, stimulus and condition in results/confirmation/confirmation-run.json, this applies the
frozen scoring code's own readout function (code/score.py, per_subtype) to the condition's record and the intact
record, and writes each per-subtype value to results/confirmation/derived/PER-SUBTYPE.csv (values written with
Python's repr, so they read back exactly). It needs the raw simulation records (the time traces), which the release
does not ship; a rerun of the simulation (make rerun) recreates them. The release's copy of the table was written
from the original records; tools/replay_scores.py reruns the frozen scoring from it.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

STUDY = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "code"))
import score as S  # noqa: E402  (the frozen readouts; nothing is changed)

ROOT = STUDY / "results/confirmation"
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "derived/PER-SUBTYPE.csv"


def main() -> None:
    run = json.loads((ROOT / "confirmation-run.json").read_text())
    stims = {k: S.stimulus(k) for k in S.STIMULI}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("w", newline="") as stream:
        w = csv.writer(stream, lineterminator="\n")
        w.writerow(["mode", "model", "stimulus", "condition", "readout", "subtype", "value"])
        for model in sorted(run["models"]):
            for mode in S.MODES:
                for key in S.STIMULI:
                    base = S.load(ROOT / mode / model / key / "baseline.npz")
                    for code in run["conditions"]:
                        per = S.per_subtype(base, S.load(ROOT / mode / model / key / f"{code}.npz"), stims[key])
                        for readout in S.READOUTS:
                            for sub, value in per[readout].items():
                                w.writerow([mode, model, key, code, readout, sub, repr(float(value))])
                                n += 1
    print(f"{OUT}: {n} values")


if __name__ == "__main__":
    main()
