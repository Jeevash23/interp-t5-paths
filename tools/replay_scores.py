"""Rerun the frozen scoring from the saved per-subtype values and compare with the saved scores.

    python tools/replay_scores.py          # after make unpack; exit status 1 on any difference

The study's scoring (code/score.py) reads the raw simulation records (time traces, 2.5 GB), which this release does
not ship. Every score it writes is computed from one function of those records, per_subtype (the readouts of each T5
subtype for one condition against the intact network), and the release ships that function's output for every
record (results/confirmation/derived/PER-SUBTYPE.csv, written from the original records by
tools/make_subtype_table.py). This tool runs the frozen code/score.py and code/score_p7_table.py unchanged in a
scratch folder, with their record loader and per_subtype answered from that table, and compares what they write
with the saved results/confirmation/scores/ byte for byte. The one field that names a folder (the "table" path in
P7-TABLE-RESCORE.json) is compared after setting it to the saved value. The freeze check that score.py runs first is
covered by make check-freezes and is skipped here.
"""
from __future__ import annotations

import csv
import filecmp
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

RELEASE = Path(__file__).resolve().parents[1]
SAVED = RELEASE / "results/confirmation"
OUTPUTS = ["SCORES.json", "PER-MODEL.csv", "PRIMARY-TABLE.csv", "P7-TABLE-RESCORE.json"]


def table() -> dict:
    out = {}
    with (SAVED / "derived/PER-SUBTYPE.csv").open(newline="") as stream:
        for r in csv.DictReader(stream):
            per = out.setdefault((r["mode"], r["model"], r["stimulus"], r["condition"]), {})
            per.setdefault(r["readout"], {})[r["subtype"]] = float(r["value"])
    return out


def main() -> int:
    values = table()
    with tempfile.TemporaryDirectory(prefix="replay-") as tmp:
        study = Path(tmp) / "study"
        (study / "results").mkdir(parents=True)
        shutil.copytree(RELEASE / "code", study / "code")
        (study / "reference").symlink_to(RELEASE / "reference")
        shutil.copytree(SAVED, study / "results/confirmation", ignore=shutil.ignore_patterns("scores", "derived"))
        sys.path.insert(0, str(study / "code"))
        sys.dont_write_bytecode = True
        import score as S
        S.STUDY = study
        S.freeze_check = lambda: None
        S.load = lambda path: {"record": Path(path)}

        def per_subtype(base, rec, stim):
            p = rec["record"]
            return values[(p.parents[2].name, p.parents[1].name, p.parent.name, p.stem)]
        S.per_subtype = per_subtype
        import score_p7_table as T
        T.STUDY = study
        argv = sys.argv
        try:
            sys.argv = ["score.py", "confirmation"]
            S.main()
            T.main()
        finally:
            sys.argv = argv
        new = study / "results/confirmation/scores"
        failures = []
        for name in OUTPUTS:
            a, b = new / name, SAVED / "scores" / name
            if name == "P7-TABLE-RESCORE.json":
                x, y = json.loads(a.read_text()), json.loads(b.read_text())
                x["table"] = y["table"]
                same = json.dumps(x, sort_keys=True) == json.dumps(y, sort_keys=True)
            else:
                same = filecmp.cmp(a, b, shallow=False)
            print(f"{name}: {'identical' if same else 'DIFFERS'}")
            if not same:
                failures.append(name)
    print("replay of the frozen scoring: " + ("FAILED for " + ", ".join(failures) if failures else
                                              "all four saved score files reproduced"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
