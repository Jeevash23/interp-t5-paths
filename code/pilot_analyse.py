"""BM2 development pilot: readouts, categories and hypothesis indicators from the raw pilot records (exploratory).

  python -B pilot_analyse.py [onset|adapted ...]   (AI-06's .venv-stage1 python; numpy only; both modes by default)
Reads results/pilot/<mode>/ and writes PILOT-REPORT-<mode>.md, PILOT-TABLE-<mode>.csv and PILOT-SUMMARY-<mode>.json
in results/pilot/. If the first-version records are kept in results/pilot-v1/ (onset only), the onset records are
compared with them.

Three readouts of T5's OFF response, each a ratio of silenced or cut to intact, averaged over the two stimulus speeds:
  pooled   P7's preferred-polarity amplitude ratio: summed peaks over the 12 OFF-edge directions, mean over T5a-d
  pd_peak  the central T5's peak at its preferred direction (argmax of the intact OFF peaks), mean over T5a-d
           (the readout of Ryan's Paper 11, closest to single-T5 recordings)
  lptc     an opponent tangential-cell-like contrast: for HS-like, L(theta) = T5a(theta) - T5b(theta), contrast =
           L(PD of T5a) - L(opposite direction); VS-like the same with T5d and T5c; mean of the two
  pd_evoked, pooled_evoked   as pd_peak and pooled, but on the evoked peak: the largest rise of the voltage above
           its value at stimulus onset (0 if it never rises). Added after the first pilot model showed that the raw
           peaks rise when every input to T5 is cut, because T5 then sits at its resting bias.
Categories as in P7: abolished <= 0.1, reduced < 1 - delta, unchanged within +-delta, increased > 1 + delta (delta 0.2).
Every number in PILOT-REPORT.md is written by this script from the saved records.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parent
STUDY = CODE.parent
PORTFOLIO = STUDY.parents[1]
AI06 = STUDY / "reference/flyvis-first-order"  # release: the reference study's files
OUT = STUDY / "results/pilot"
MODELS = ["000", "001", "004", "005"]
STIMULI = ["final_slow", "dev_fast"]
TMS = ["Tm1", "Tm2", "Tm4", "Tm9"]
KINDS = ["silence", "cutT5", "cutCT1", "cutT5+CT1", "open"]
STRENGTHS = [1.0, 0.5]
DELTA, ABOLISHED = 0.2, 0.1
T5_INDEX = {"a": 4, "b": 5, "c": 6, "d": 7}
READOUTS = ["pd_peak", "pooled", "lptc", "pd_evoked", "pooled_evoked"]


def load(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def stimulus(key: str) -> dict:
    manifest = json.loads((AI06 / "03-Data/stage1/stimulus-manifest.json").read_text())
    item = next(x for x in manifest if x["key"] == key)
    with np.load(AI06 / item["path"], allow_pickle=False) as archive:
        return {"angle": archive["angle"].astype(float), "intensity": archive["intensity"].copy(),
                "speed": float(archive["speed"])}


def category(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "undefined"
    if value <= ABOLISHED:
        return "abolished"
    if value < 1 - DELTA:
        return "reduced"
    if value <= 1 + DELTA:
        return "unchanged"
    return "increased"


def evoked(record: dict, speed: float) -> np.ndarray:
    """(24, 8): largest rise above the value at stimulus onset within AI-06's motion window."""
    trace = record["trace"][:, :, :8].astype(np.float64)
    T = trace.shape[1]
    times = (np.arange(T, dtype=np.float64) + 200) * 0.005 - 1
    end = ((10 * 2.25 / 5.8 + 2.25 / 5.8) - (-10 * 2.25 / 5.8)) / speed
    sel = (times >= 0) & (times <= end)
    return np.maximum(trace[:, sel].max(axis=1) - trace[:, 0], 0.0)


def readouts(base: dict, cond: dict, stim: dict) -> dict:
    off = np.flatnonzero(stim["intensity"] == 0)
    angles = stim["angle"][off]
    bp, cp = base["peaks"][off], cond["peaks"][off]          # (12 directions, 8 readouts)
    be, ce = evoked(base, float(stim["speed"]))[off], evoked(cond, float(stim["speed"]))[off]
    pooled_e, pd_e = [], []
    for letter, r in T5_INDEX.items():
        denom = be[:, r].sum()
        pooled_e.append(ce[:, r].sum() / denom if denom > 1e-8 else math.nan)
        j = int(np.argmax(be[:, r]))
        pd_e.append(ce[j, r] / be[j, r] if be[j, r] > 1e-8 else math.nan)
    pooled, pd_peak, pd_dir = [], [], {}
    for letter, r in T5_INDEX.items():
        denom = bp[:, r].sum()
        pooled.append(cp[:, r].sum() / denom if denom > 1e-8 else math.nan)
        j = int(np.argmax(bp[:, r]))
        pd_dir[letter] = j
        pd_peak.append(cp[j, r] / bp[j, r] if bp[j, r] > 1e-8 else math.nan)

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
        lptc.append(after / before if before > 1e-8 else math.nan)
    dsi = [cond["dsi"][r] / base["dsi"][r] if base["dsi"][r] > 1e-8 else math.nan for r in T5_INDEX.values()]
    return {"pooled": float(np.nanmean(pooled)), "pd_peak": float(np.nanmean(pd_peak)), "lptc": float(np.nanmean(lptc)),
            "pd_evoked": float(np.nanmean(pd_e)), "pooled_evoked": float(np.nanmean(pooled_e)),
            "dsi_ratio": float(np.nanmean(dsi)), "per_subtype_pooled": [float(x) for x in pooled],
            "per_subtype_pd_peak": [float(x) for x in pd_peak]}


def main() -> None:
    import sys
    for mode in sys.argv[1:] or ["onset", "adapted"]:
        analyse(mode)


def analyse(mode: str) -> None:
    root = OUT / mode
    stims = {k: stimulus(k) for k in STIMULI}
    rows, values = [], {}
    run = json.loads((OUT / "pilot-run.json").read_text())
    models = [m for m in MODELS if m in run["models"]]
    codes = run["conditions"]
    for model in models:
        for key in STIMULI:
            base = load(root / model / key / "baseline.npz")
            for code in codes:
                meta = json.loads((root / model / key / f"{code}.json").read_text())
                r = readouts(base, load(root / model / key / f"{code}.npz"), stims[key])
                values[(model, key, code)] = r
                rows.append({"model": model, "stimulus": key, "condition": code, "kind": meta["kind"],
                             "tms": "+".join(meta["tms"]), "strength": meta["strength"],
                             **{k: r[k] for k in READOUTS + ["dsi_ratio"]}})
    with (OUT / f"PILOT-TABLE-{mode}.csv").open("w", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def v(model, code, readout):
        xs = [values[(model, k, code)][readout] for k in STIMULI]
        xs = [x for x in xs if math.isfinite(x)]
        return sum(xs) / len(xs) if xs else math.nan

    def fmt(x):
        return "n/a" if not math.isfinite(x) else f"{x:.2f}"

    mode_text = {"onset": "the condition starts at stimulus onset, after the intact network has adapted (as P7)",
                 "adapted": "the condition holds from rest, so the network settles with it before the stimulus"}[mode]
    lines = [f"# BM2 development pilot, {mode} mode: path cuts onto T5 in the four development models", "",
             f"Mode: {mode_text}.", "",
             f"Written by `code/pilot_analyse.py` from `results/pilot/` (run started {run['started_utc']}, "
             f"finished {run.get('finished_utc', 'not finished')}). **Development models only; exploratory; not a test.** "
             "Values are ratios of the cut or silenced response to the intact one, averaged over the two speeds "
             "(27.55 and 110.2 degrees per second). Categories: abolished <= 0.1, reduced < 0.8, unchanged 0.8-1.2, "
             "increased > 1.2.", ""]
    checks = {m: run["models"][m]["checks"] for m in models}
    worst = max(x for c in checks.values() for s in c.values() for x in s.values())
    lines += ["## Checks", "",
              f"- Worst normalised gap over all checks (this code against AI-06's simulator and saved records, and the "
              f"two identity conditions in both modes): {worst:.1e} (limit 1e-4)."]
    v1 = STUDY / "results/pilot-v1"
    if mode == "onset" and v1.exists():
        gaps = []
        for model in models:
            for key in STIMULI:
                for code in codes:
                    old = v1 / model / key / f"{code}.npz"
                    if old.exists():
                        a, b = load(old)["peaks"], load(root / model / key / f"{code}.npz")["peaks"]
                        gaps.append(float(np.max(np.abs(a - b)) / max(float(np.max(np.abs(a))), 1e-8)))
        lines.append(f"- Against the first-version records (condition at onset, warm-up by AI-06's own code): "
                     f"{len(gaps)} records compared, worst normalised peak gap {max(gaps):.1e}.")
    if mode == "onset":
        # Whole-cell silencing at onset on P7's readout must equal AI-06's saved development effects (P7's input).
        saved = {}
        with (AI06 / "study/results/analysis/development/effects.csv").open(newline="") as stream:
            for r in csv.DictReader(stream):
                if (r["readout"].startswith("T5") and r["cell"] in TMS and float(r["strength"]) in STRENGTHS
                        and r["preferred_amplitude_ratio"] not in ("", "None")):
                    saved.setdefault((r["model"], r["cell"], float(r["strength"]), r["stimulus"]), []).append(
                        float(r["preferred_amplitude_ratio"]))
        gaps = []
        for (model, cell, s, key), ratios in saved.items():
            if model in models and key in STIMULI and len(ratios) == 4:
                mine = values[(model, key, f"s{round(100 * s):03d}-silence-{cell}")]["pooled"]
                gaps.append(abs(mine - sum(ratios) / 4))
        lines.append(f"- Whole-cell silencing on P7's pooled readout against AI-06's saved development effects "
                     f"(P7's input): {len(gaps)} model-cell-strength-speed values compared, worst absolute gap "
                     f"{max(gaps):.1e}.")
    lines.append("")
    for name, code in (("every edge into T5 cut", "pc-cut-all-T5-inputs"),
                       ("every non-T5 type presynaptic to T5 silenced", "pc-silence-T5-presyn"),
                       ("every excitatory edge into T5 halved", "pc-half-exc-T5"),
                       ("Tm9's edges onto T5 halved", "s050-cutT5-Tm9")):
        cells = ", ".join(f"{m}: " + " / ".join(f"{fmt(v(m, code, r))} ({category(v(m, code, r))})" for r in READOUTS)
                          for m in models)
        lines.append(f"- Control, {name} ({' / '.join(READOUTS)}): {cells}.")
    lines.append("")
    for s in STRENGTHS:
        tag = f"s{round(100 * s):03d}"
        for readout in READOUTS:
            lines += [f"## {readout} readout, strength {s}", "",
                      "| Model | Tm | " + " | ".join(KINDS) + " |", "|---|---|" + "---|" * len(KINDS)]
            for model in models:
                for name in TMS + ["quad"]:
                    cells = [f"{fmt(v(model, f'{tag}-{k}-{name}', readout))}" for k in KINDS]
                    lines.append(f"| {model} | {name} | " + " | ".join(cells) + " |")
            lines.append("")
    # Hypothesis indicators (strength 1.0, each readout), descriptive only.
    lines += ["## Indicators (strength 1.0; descriptive, development only)", ""]
    summary = {}
    for readout in READOUTS:
        lines.append(f"**{readout}:**")
        for model in models:
            parts = []
            for name in TMS:
                sil, t5, ct1, both, op = (v(model, f"s100-{k}-{name}", readout) for k in KINDS)
                additive = 1 + (t5 - 1) + (ct1 - 1)
                summary[(readout, model, name)] = {"silence": sil, "cutT5": t5, "cutCT1": ct1, "cutT5+CT1": both,
                                                   "open": op, "additive_cuts": additive}
                flags = []
                if t5 < 1 - DELTA and ct1 > 1 + DELTA:
                    flags.append("opposing routes" + (", together = silencing" if abs(both - sil) <= 0.1 else ""))
                if op < t5 - DELTA:
                    flags.append("T5 feedback compensates")
                if abs(sil - both) > DELTA:
                    flags.append("other routes matter")
                parts.append(f"{name} silence {fmt(sil)}, direct cut {fmt(t5)}, CT1 cut {fmt(ct1)}, both {fmt(both)} "
                             f"(additive {fmt(additive)}), open loop {fmt(op)}" + (f" [{'; '.join(flags)}]" if flags else ""))
            quad = v(model, "s100-silence-quad", readout)
            singles = [category(v(model, f"s100-silence-{t}", readout)) for t in TMS]
            red = quad < 1 - DELTA and all(c == "unchanged" for c in singles)
            parts.append(f"quadruple silence {fmt(quad)} ({category(quad)}); singles {', '.join(singles)}"
                         + (" [redundancy pattern]" if red else ""))
            lines.append(f"- {model}: " + "; ".join(parts) + ".")
        lines.append("")
    if mode == "adapted":
        onset_root = OUT / "onset"
        lines += ["## Whole-cell silencing at full strength: P7's measurement against the adapted, evoked one", "",
                  "P7's measurement: silencing switched on at stimulus onset, pooled raw-peak ratio. Here: silencing "
                  "held from rest, central preferred-direction evoked ratio (and the opponent contrast).", "",
                  "| Model | Tm | P7-style (onset, pooled) | adapted, pd_evoked | adapted, lptc |", "|---|---|---|---|---|"]
        for model in models:
            for name in TMS + ["quad"]:
                code = f"s100-silence-{name}"
                p7 = []
                for key in STIMULI:
                    b0 = load(onset_root / model / key / "baseline.npz")
                    p7.append(readouts(b0, load(onset_root / model / key / f"{code}.npz"), stims[key])["pooled"])
                p7v = sum(p7) / len(p7)
                pe, lp = v(model, code, "pd_evoked"), v(model, code, "lptc")
                lines.append(f"| {model} | {name} | {fmt(p7v)} ({category(p7v)}) | {fmt(pe)} ({category(pe)}) | "
                             f"{fmt(lp)} ({category(lp)}) |")
        lines.append("")
    lines += ["## Wiring of the development models (summed signed weights, from the checkpoints)", "",
              "| Model | " + " | ".join(f"{t}->T5 (a-d)" for t in TMS) + " | Tm1->CT1 | Tm9->CT1 | CT1->T5 (a-d) |",
              "|---|" + "---|" * (len(TMS) + 3)]
    for model in models:
        wiring = json.loads((OUT / "wiring" / f"{model}.json").read_text())["wiring"]

        def ws(src, tgts):
            return sum(wiring.get(f"{src}->{t}", {"weight_sum": 0.0})["weight_sum"] for t in tgts)
        t5s = ["T5a", "T5b", "T5c", "T5d"]
        cells = [f"{ws(t, t5s):+.0f}" for t in TMS] + [f"{ws('Tm1', ['CT1(Lo1)']):+.0f}", f"{ws('Tm9', ['CT1(Lo1)']):+.0f}",
                                                         f"{ws('CT1(Lo1)', t5s):+.0f}"]
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    lines.append("")
    (OUT / f"PILOT-REPORT-{mode}.md").write_text("\n".join(lines) + "\n")
    (OUT / f"PILOT-SUMMARY-{mode}.json").write_text(json.dumps(
        {"|".join(k): val for k, val in summary.items()}, indent=1, allow_nan=True) + "\n")
    print(f"{mode}: {len(rows)} rows; report written")


if __name__ == "__main__":
    main()
