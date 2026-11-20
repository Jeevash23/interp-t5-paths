"""BM2 secondary, post hoc (PROTOCOL.md, Section 8): re-score P7's frozen fly table with the corrected measurement.

  python -B score_p7_table.py confirmation   (after score.py confirmation; checks the freezes; written once)
  python -B score_p7_table.py pilot          self-test on the development records

P7's code/common.py is imported read-only (python -B) and supplies the matching and ensemble rules: comparisons()
with role "primary", amplitude_value() with P7's frozen settings (weighted pooling, delta 0.2), ensemble(),
agreement_block(). Only amplitude comparisons whose silenced cell is Tm1, Tm2, Tm4 or Tm9, and whose model counterpart is OFF only
(T5; BM2 measures no T4), are kept. Two sets of
per-model values go through the same rules on the same rows: AI-06's saved effects (P7's measurement) and BM2's
corrected per-subtype values (adapted application, pd_evoked); a subtype whose P7 ratio is undefined is left out of
both, so the two pool the same subtypes with P7's weights. P7 is not changed.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
STUDY = CODE.parent
P7 = STUDY / "reference/model-vs-fly"  # release: P7's files
sys.path.insert(0, str(P7 / "code"))
import common as C  # noqa: E402  (P7's rules, read only)
sys.path.insert(0, str(CODE))
import score as S  # noqa: E402  (BM2's readouts)

TMS = ["Tm1", "Tm2", "Tm4", "Tm9"]


def main() -> None:
    split = sys.argv[1] if len(sys.argv) > 1 else ""
    if split == "confirmation":
        S.freeze_check()
        root, run_file, out_dir = STUDY / "results/confirmation", "confirmation-run.json", "scores"
    elif split == "pilot":
        root, run_file, out_dir = STUDY / "results/pilot", "pilot-run.json", "scores-selftest"
    else:
        sys.exit(__doc__)
    out = root / out_dir / "P7-TABLE-RESCORE.json"
    if split == "confirmation" and out.exists():
        sys.exit("already written")
    scores = json.loads((root / out_dir / "SCORES.json").read_text())
    models = [m for m in scores["models"] if m not in scores["excluded_replication"]]
    settings = json.loads((P7 / "results/development/settings.json").read_text())
    delta, pooling = settings["delta"], settings["pooling"]
    effects_split = "confirmation" if split == "confirmation" else "development"
    p7_effects = C.load_effects(effects_split)

    # BM2's corrected per-subtype values, keyed like P7's effects: (model, stimulus, strength, readout, cell).
    stims = {k: S.stimulus(k) for k in S.STIMULI}
    mine = {}
    for model in models:
        for key in S.STIMULI:
            base = S.load(root / "adapted" / model / key / "baseline.npz")
            for s, tag in S.STRENGTHS.items():
                for cell in TMS:
                    rec = S.load(root / "adapted" / model / key / f"{tag}-silence-{cell}.npz")
                    per = S.per_subtype(base, rec, stims[key])["pd_evoked"]
                    for letter, value in per.items():
                        k = (model, key, s, f"T5{letter}", cell)
                        p7 = p7_effects.get(k)
                        # A subtype that P7's rules leave out (its ratio undefined) is left out here too, so both
                        # measurements pool the same subtypes with the same weights (AMENDMENTS.md, 2).
                        keep = p7 is not None and p7["ratio"] is not None and math.isfinite(value)
                        mine[k] = {"ratio": value if keep else None}

    table_path = P7 / "extraction/merged-table.csv"
    every = [c for c in C.comparisons(C.read_table(table_path), ("primary",))
             if c["matched"] and c["measure"] == "amplitude" and c["cell"] in TMS]
    # Only rows whose model counterpart is OFF only (T5): BM2 measures no T4 (AMENDMENTS.md, 2).
    comps = [c for c in every if set(c["sets"]) == {"OFF"}]
    dropped = [c["row_id"] for c in every if set(c["sets"]) != {"OFF"}]
    full, half = C.CONFIG["primary_strength"], C.CONFIG["partial_strength"]
    rows, exp, cat_p7, cat_bm2 = [], [], [], []
    for comp in comps:
        strength = half if comp["strength_class"] == "partial" else full
        v_p7 = [C.amplitude_value(p7_effects, m, comp, strength, pooling) for m in models]
        v_bm2 = [C.amplitude_value(mine, m, comp, strength, pooling) for m in models]
        e_p7, e_bm2 = C.ensemble(v_p7, delta), C.ensemble(v_bm2, delta)
        rows.append({"row_id": comp["row_id"], "source": comp["source"], "cell": comp["cell"],
                     "readout": comp["readout"], "direction": comp["direction"], "experiment": comp["experiment"],
                     "p7_measurement": e_p7["category"], "p7_median": e_p7["median"],
                     "corrected": e_bm2["category"], "corrected_median": e_bm2["median"],
                     "corrected_counts": e_bm2["counts"]})
        if e_p7["category"] is not None and e_bm2["category"] is not None:
            exp.append(comp["experiment"])
            cat_p7.append(e_p7["category"])
            cat_bm2.append(e_bm2["category"])
    reproduce = None
    saved = P7 / "results/confirmation/comparisons.csv"
    if split == "confirmation" and saved.exists():
        with saved.open(newline="") as stream:
            p7rows = {(r["row_id"], r["measure"]): r for r in csv.DictReader(stream)}
        same = [p7rows.get((r["row_id"], "amplitude"), {}).get("model") == r["p7_measurement"] for r in rows]
        reproduce = {"rows": len(rows), "same_category_as_p7_saved": sum(same),
                     "differs": [r["row_id"] for r, ok in zip(rows, same) if not ok]}
    result = {"post_hoc": True, "split": split, "table": str(table_path.relative_to(STUDY.parents[1])),
              "table_sha256": C.sha256(table_path), "settings": settings, "n_models": len(models),
              "n_rows": len(exp), "rows_dropped_not_off_only": dropped, "p7_reproduction": reproduce,
              "p7_measurement": C.agreement_block(exp, cat_p7, C.CATEGORIES),
              "corrected": C.agreement_block(exp, cat_bm2, C.CATEGORIES),
              "rows_changed": [r for r in rows if r["p7_measurement"] != r["corrected"]],
              "rows": rows}
    out.write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(f"{split}: {len(exp)} rows; P7's measurement agree {result['p7_measurement']['agree']}, "
          f"corrected agree {result['corrected']['agree']}; rows changed {len(result['rows_changed'])}")


if __name__ == "__main__":
    main()
