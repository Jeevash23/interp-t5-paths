"""BM2 scoring (PROTOCOL.md, Sections 3, 4, 6, 7).

  python -B score.py confirmation   score results/confirmation/ (checks FREEZE-1 and FREEZE-2 first; written once)
  python -B score.py pilot          self-test on the development records in results/pilot/ (writes scores-selftest/)

Run with AI-06's .venv-stage1 python (numpy and scipy). Reads raw records only; writes, under the split's folder,
scores/SCORES.json, scores/PER-MODEL.csv (every model, condition, mode, strength and readout) and
scores/PRIMARY-TABLE.csv (adapted, full strength, pd_evoked, every model and condition).
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import stats

CODE = Path(__file__).resolve().parent
STUDY = CODE.parent
AI06 = STUDY / "reference/flyvis-first-order"  # release: the reference study's files
STIMULI = ["final_slow", "dev_fast"]
TMS = ["Tm1", "Tm2", "Tm4", "Tm9"]
GROUPS = TMS + ["quad"]
KINDS = ["silence", "cutT5", "cutCT1", "cutT5+CT1", "open"]
MODES = ["adapted", "onset"]
STRENGTHS = {1.0: "s100", 0.5: "s050"}
T5_INDEX = {"a": 4, "b": 5, "c": 6, "d": 7}
READOUTS = ["pd_evoked", "pooled_evoked", "pooled", "pd_peak", "lptc"]
DELTA, DELTAS, ABOLISHED, TOL = 0.2, [0.1, 0.2, 0.3], 0.1, 1e-4
EXCLUDE_REPLICATION = 1e-2
ALPHA = 0.05


# ------------------------------------------------------------------------------------------------------- readouts
def load(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def stimulus(key: str) -> dict:
    manifest = json.loads((AI06 / "03-Data/stage1/stimulus-manifest.json").read_text())
    item = next(x for x in manifest if x["key"] == key)
    with np.load(AI06 / item["path"], allow_pickle=False) as archive:
        return {"angle": archive["angle"].astype(float), "intensity": archive["intensity"].copy(),
                "speed": float(archive["speed"])}


def evoked(record: dict, speed: float) -> np.ndarray:
    """(24, 8): largest rise above the value at the first frame after onset, within AI-06's motion window, floored at 0."""
    trace = record["trace"][:, :, :8].astype(np.float64)
    times = (np.arange(trace.shape[1], dtype=np.float64) + 200) * 0.005 - 1
    end = ((10 * 2.25 / 5.8 + 2.25 / 5.8) - (-10 * 2.25 / 5.8)) / speed
    sel = (times >= 0) & (times <= end)
    with np.errstate(invalid="ignore"):
        return np.maximum(trace[:, sel].max(axis=1) - trace[:, 0], 0.0)


def ratio(a: float, b: float) -> float:
    return float(a / b) if (b > 1e-8 and math.isfinite(a) and math.isfinite(b)) else math.nan


def per_subtype(base: dict, cond: dict, stim: dict) -> dict:
    """Per-subtype ratios (T5a-d) for the readouts that are per subtype, and the opponent contrast."""
    off = np.flatnonzero(stim["intensity"] == 0)
    angles = stim["angle"][off]
    bp, cp = base["peaks"][off].astype(np.float64), cond["peaks"][off].astype(np.float64)
    be, ce = evoked(base, stim["speed"])[off], evoked(cond, stim["speed"])[off]
    out = {r: {} for r in ("pd_evoked", "pooled_evoked", "pooled", "pd_peak")}
    pd_dir = {}
    for letter, r in T5_INDEX.items():
        j = int(np.argmax(be[:, r]))
        out["pd_evoked"][letter] = ratio(ce[j, r], be[j, r])
        out["pooled_evoked"][letter] = ratio(ce[:, r].sum(), be[:, r].sum())
        out["pooled"][letter] = ratio(cp[:, r].sum(), bp[:, r].sum())
        k = int(np.argmax(bp[:, r]))
        pd_dir[letter] = k
        out["pd_peak"][letter] = ratio(cp[k, r], bp[k, r])

    def opposite(j):
        target = (angles[j] + 180.0) % 360.0
        return int(np.argmin(np.abs(((angles - target) + 180.0) % 360.0 - 180.0)))

    lptc = []
    for pref, null in (("a", "b"), ("d", "c")):
        j = pd_dir[pref]
        k = opposite(j)
        rp, rn = T5_INDEX[pref], T5_INDEX[null]
        before = (bp[j, rp] - bp[j, rn]) - (bp[k, rp] - bp[k, rn])
        after = (cp[j, rp] - cp[j, rn]) - (cp[k, rp] - cp[k, rn])
        lptc.append(ratio(after, before))
    out["lptc"] = {"HS": lptc[0], "VS": lptc[1]}
    return out


def mean_finite(values) -> float:
    xs = [v for v in values if v is not None and math.isfinite(v)]
    return sum(xs) / len(xs) if xs else math.nan


def category(value: float, delta: float = DELTA) -> str:
    if value is None or not math.isfinite(value):
        return "undefined"
    if value <= ABOLISHED:
        return "abolished"
    if value < 1 - delta:
        return "reduced"
    if value <= 1 + delta:
        return "unchanged"
    return "increased"


def reduced(value: float, delta: float = DELTA) -> bool | None:
    c = category(value, delta)
    return None if c == "undefined" else c in ("reduced", "abolished")


# ------------------------------------------------------------------------------------------------------- statistics
def clopper_pearson(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    low = 0.0 if k == 0 else float(stats.beta.ppf(0.025, k, n - k + 1))
    high = 1.0 if k == n else float(stats.beta.ppf(0.975, k + 1, n - k))
    return [low, high]


def holm(pvalues: dict) -> dict:
    keys = sorted(pvalues, key=lambda k: pvalues[k])
    m, running, out = len(keys), 0.0, {}
    for i, k in enumerate(keys):
        running = max(running, min(1.0, (m - i) * pvalues[k]))
        out[k] = running
    return out


def mcnemar_one_sided(first: list, second: list) -> dict:
    """first = reduced on the corrected measurement, second = reduced on P7's; tests b > c (b: first only)."""
    b = sum(1 for x, y in zip(first, second) if x and not y)
    c = sum(1 for x, y in zip(first, second) if y and not x)
    n = b + c
    p = float(stats.binomtest(b, n, 0.5, alternative="greater").pvalue) if n else 1.0
    return {"n_models": len(first), "reduced_corrected": sum(first), "reduced_p7": sum(second),
            "corrected_only": b, "p7_only": c, "p_one_sided": p}


# ------------------------------------------------------------------------------------------------------- main
def freeze_check() -> None:
    result = subprocess.run([sys.executable, "-I", str(CODE / "freeze.py"), "check"], capture_output=True, text=True)
    if result.returncode != 0 or not (STUDY / "FREEZE-2.json").exists():
        sys.exit("freeze check failed or FREEZE-2.json missing:\n" + result.stdout + result.stderr)


def main() -> None:
    split = sys.argv[1] if len(sys.argv) > 1 else ""
    if split == "confirmation":
        freeze_check()
        root, run_file, out = STUDY / "results/confirmation", "confirmation-run.json", "scores"
        effects_split = "confirmation"
    elif split == "pilot":
        root, run_file, out = STUDY / "results/pilot", "pilot-run.json", "scores-selftest"
        effects_split = "development"
    else:
        sys.exit(__doc__)
    out_dir = root / out
    if split == "confirmation" and (out_dir / "SCORES.json").exists():
        sys.exit("confirmation scores already exist; they are written once")
    run = json.loads((root / run_file).read_text())
    models = sorted(run["models"])
    failed = run.get("failed", {})
    codes = run["conditions"]
    stims = {k: stimulus(k) for k in STIMULI}

    # Per-model, per-condition values: values[(model, mode, code, readout)] = mean over speeds of the subtype mean.
    values, subtype_values, nonfinite, rows = {}, {}, [], []
    for model in models:
        for mode in MODES:
            per = {}
            for key in STIMULI:
                base = load(root / mode / model / key / "baseline.npz")
                for code in codes:
                    meta = json.loads((root / mode / model / key / f"{code}.json").read_text())
                    if meta.get("nonfinite"):
                        nonfinite.append(f"{model}/{mode}/{key}/{code}")
                    rec = load(root / mode / model / key / f"{code}.npz")
                    per[(key, code)] = per_subtype(base, rec, stims[key])
            for code in codes:
                for r in READOUTS:
                    speeds = [mean_finite(per[(key, code)][r].values()) for key in STIMULI]
                    values[(model, mode, code, r)] = mean_finite(speeds)
                    rows.append({"model": model, "mode": mode, "condition": code, "readout": r,
                                 "value": values[(model, mode, code, r)],
                                 **{f"category_delta_{d}": category(values[(model, mode, code, r)], d) for d in DELTAS}})
                for key in STIMULI:
                    subtype_values[(model, mode, code, key)] = per[(key, code)]["pd_evoked"]

    # Replication: onset whole-cell silencing, P7's pooled ratio per subtype, against AI-06's saved effects.
    saved = {}
    with (AI06 / f"study/results/analysis/{effects_split}/effects.csv").open(newline="") as stream:
        for r in csv.DictReader(stream):
            if (r["readout"].startswith("T5") and r["cell"] in TMS and float(r["strength"]) in STRENGTHS
                    and r["model"] in models and r["preferred_amplitude_ratio"] not in ("", "None")):
                saved[(r["model"], r["cell"], float(r["strength"]), r["stimulus"], r["readout"][-1])] = \
                    float(r["preferred_amplitude_ratio"])
    replication = {m: 0.0 for m in models}
    replication_n = {m: 0 for m in models}
    for model in models:
        for key in STIMULI:
            base = load(root / "onset" / model / key / "baseline.npz")
            for s, tag in STRENGTHS.items():
                for cell in TMS:
                    rec = load(root / "onset" / model / key / f"{tag}-silence-{cell}.npz")
                    mine = per_subtype(base, rec, stims[key])["pooled"]
                    for letter in "abcd":
                        k = (model, cell, s, key, letter)
                        if k in saved and math.isfinite(mine[letter]):    # relative gap (AMENDMENTS.md, 1)
                            gap = abs(mine[letter] - saved[k]) / max(1.0, abs(saved[k]))
                            replication[model] = max(replication[model], gap)
                            replication_n[model] += 1

    # Controls and eligibility.
    def v(model, code, readout="pd_evoked", mode="adapted"):
        return values[(model, mode, code, readout)]

    controls = {}
    for model in models:
        cut_all, half_exc = v(model, "pc-cut-all-T5-inputs"), v(model, "pc-half-exc-T5")
        controls[model] = {"cut_all": cut_all, "half_exc": half_exc,
                           "cut_all_pass": math.isfinite(cut_all) and cut_all <= 0.1,
                           "half_exc_pass": math.isfinite(half_exc) and half_exc < 0.8,
                           "replication_worst": replication[model], "replication_values": replication_n[model],
                           "replication_pass": replication[model] <= TOL}
    excluded = sorted(m for m in models if replication[m] > EXCLUDE_REPLICATION)
    control_fail = sorted(m for m in models if m not in excluded
                          and not (controls[m]["cut_all_pass"] and controls[m]["half_exc_pass"]))
    eligible = [m for m in models if m not in excluded and m not in control_fail]

    def patterns(delta, mode="adapted", strength="s100", readout="pd_evoked"):
        """Per-model truth of each hypothesis' pattern (None if a needed value is undefined)."""
        lo, hi = 1 - delta, 1 + delta
        res = {}
        for model in eligible:
            g = lambda kind, name: values[(model, mode, f"{strength}-{kind}-{name}", readout)]
            ok = lambda *xs: all(math.isfinite(x) for x in xs)
            for name in ("Tm1", "Tm9"):
                sil, t5, ct1, both = g("silence", name), g("cutT5", name), g("cutCT1", name), g("cutT5+CT1", name)
                res[(f"H2-{name}", model)] = (t5 < lo and ct1 > hi and abs(both - sil) <= 0.1) if ok(sil, t5, ct1, both) else None
            for name in TMS:
                t5, op = g("cutT5", name), g("open", name)
                res[(f"H3-{name}", model)] = (op < t5 - delta) if ok(t5, op) else None
                sil, both = g("silence", name), g("cutT5+CT1", name)
                res[(f"H4-{name}", model)] = (abs(sil - both) > delta) if ok(sil, both) else None
            quad = g("silence", "quad")
            singles = [g("silence", name) for name in TMS]
            res[("H5", model)] = (quad < lo and all(lo <= x <= hi for x in singles)) if ok(quad, *singles) else None
        return res

    def calls(res):
        names = sorted({k[0] for k in res})
        out, pvals = {}, {}
        for name in names:
            got = [res[(name, m)] for m in eligible if res.get((name, m)) is not None]
            k, n = sum(got), len(got)
            pvals[name] = float(stats.binomtest(k, n, 0.5).pvalue) if n else 1.0
            out[name] = {"holds": k, "n": n, "share": k / n if n else None, "ci95": clopper_pearson(k, n),
                         "p_two_sided": pvals[name]}
        adj = holm(pvals)
        for name in names:
            o = out[name]
            o["p_holm"] = adj[name]
            o["call"] = ("holds in most models" if adj[name] < ALPHA and o["share"] is not None and o["share"] > 0.5
                         else "refuted as the general cause" if adj[name] < ALPHA and o["share"] is not None
                         and o["share"] < 0.5 else "mixed")
        return out

    def h1(delta):
        res = {}
        for name in TMS:
            code = f"s100-silence-{name}"
            pairs = [(reduced(v(m, code), delta), reduced(v(m, code, "pooled", "onset"), delta)) for m in eligible]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
            res[name] = mcnemar_one_sided([a for a, _ in pairs], [b for _, b in pairs])
        adj = holm({n: res[n]["p_one_sided"] for n in ("Tm1", "Tm2", "Tm4")})
        for n in ("Tm1", "Tm2", "Tm4"):
            res[n]["p_holm_secondary"] = adj[n]
        res["Tm9"]["call"] = ("holds" if res["Tm9"]["p_one_sided"] < ALPHA else "not supported")
        return res

    primary_patterns = patterns(DELTA)
    scores = {
        "split": split, "models": models, "n_models": len(models), "failed_checks_in_run": failed,
        "excluded_replication": excluded, "control_fail": control_fail, "eligible": eligible,
        "n_eligible": len(eligible), "nonfinite_records": nonfinite, "controls": controls,
        "H1": {f"delta_{d}": h1(d) for d in DELTAS},
        "H2_H5": {f"delta_{d}": calls(patterns(d)) for d in DELTAS},
        "H2_H5_per_model": {f"{k[0]}|{k[1]}": val for k, val in primary_patterns.items()},
        "secondary_patterns": {f"{mode}|{s}|{r}": calls(patterns(DELTA, mode, s, r))
                               for mode in MODES for s in STRENGTHS.values() for r in READOUTS},
        "runaway_over_100": sorted({f"{m}|{mo}|{c}|{r}" for (m, mo, c, r), x in values.items()
                                    if math.isfinite(x) and x > 100}),
        "category_counts": {},
    }
    for mode in MODES:
        for s in STRENGTHS.values():
            for r in READOUTS:
                for name in GROUPS:
                    for kind in KINDS:
                        code = f"{s}-{kind}-{name}"
                        cats = [category(v(m, code, r, mode)) for m in eligible]
                        scores["category_counts"][f"{mode}|{code}|{r}"] = {c: cats.count(c) for c in
                            ("abolished", "reduced", "unchanged", "increased", "undefined")}
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "PER-MODEL.csv").open("w", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with (out_dir / "PRIMARY-TABLE.csv").open("w", newline="") as stream:
        w = csv.writer(stream)
        w.writerow(["model", "status", "group"] + KINDS + ["silence_p7_measurement"])
        for model in models:
            status = "excluded" if model in excluded else "control_fail" if model in control_fail else "eligible"
            for name in GROUPS:
                w.writerow([model, status, name] + [f"{v(model, f's100-{k}-{name}'):.4f}" for k in KINDS]
                           + [f"{v(model, f's100-silence-{name}', 'pooled', 'onset'):.4f}"])
    (out_dir / "SCORES.json").write_text(json.dumps(scores, indent=1, allow_nan=True) + "\n")
    p = scores["H1"]["delta_0.2"]["Tm9"]
    print(f"{split}: {len(models)} models, {len(eligible)} eligible, {len(excluded)} excluded, "
          f"{len(control_fail)} failed a control; written to {out_dir.relative_to(STUDY)}")
    if split == "pilot":
        print(f"self-test H1 Tm9: {p}")
        for name, o in scores["H2_H5"]["delta_0.2"].items():
            print(f"self-test {name}: {o['holds']}/{o['n']} {o['call']}")


if __name__ == "__main__":
    main()
