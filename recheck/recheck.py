#!/usr/bin/env python3
"""Independent recheck of BM2's confirmation scores (standard library only).

Written without reading BM2's scoring code (code/score.py, code/score_p7_table.py,
code/pilot_analyse.py). Definitions are taken from PROTOCOL.md (Sections 3, 4, 6)
and AMENDMENTS.md, as restated in the recheck brief.

Usage, from the study folder:
    python3 -I recheck/recheck.py compute   # raw records -> recheck/RECHECK.json
    python3 -I recheck/recheck.py compare   # adds a comparison with SCORES.json

The compute step never opens results/confirmation/scores/.
"""

import array
import ast
import datetime
import hashlib
import json
import math
import os
import struct
import sys
import zipfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
CONF = os.path.join(STUDY, "results", "confirmation")
AI06 = os.path.join(STUDY, "reference", "flyvis-first-order")  # release: the reference study's files
OUT = os.path.join(HERE, "RECHECK.json")
SCORES = os.path.join(CONF, "scores", "SCORES.json")

MODES = ("adapted", "onset")
STIMULI = ("final_slow", "dev_fast")
TMS = ("Tm1", "Tm2", "Tm4", "Tm9")
GROUPS = TMS + ("quad",)
KINDS = ("silence", "cutT5", "cutCT1", "cutT5+CT1", "open")
CONTROLS = ("pc-cut-all-T5-inputs", "pc-half-exc-T5")
IDENTITY = ("identity-gain1", "identity-open")
S100 = tuple("s100-%s-%s" % (k, g) for g in GROUPS for k in KINDS)
CONDITIONS = CONTROLS + S100
READOUTS = ("pd_evoked", "pooled_raw")
T5_COLS = (4, 5, 6, 7)          # T5a, T5b, T5c, T5d
T5_NAMES = ("T5a", "T5b", "T5c", "T5d")
N_PEAK_COLS = 8
EPS = 1e-8
DELTA = 0.2
LO, HI, ABOL = 1.0 - DELTA, 1.0 + DELTA, 0.1   # 0.8, 1.2, 0.1

NPY_DTYPES = {"<f4": ("f", 4), "<f8": ("d", 8), "<i8": ("q", 8), "<i4": ("i", 4)}


# ---------------------------------------------------------------- .npy parsing

def parse_npy(raw):
    """Parse one .npy byte string into (shape, flat array.array)."""
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("not an .npy member")
    major = raw[6]
    if major == 1:
        hlen = struct.unpack("<H", raw[8:10])[0]
        start = 10
    elif major in (2, 3):
        hlen = struct.unpack("<I", raw[8:12])[0]
        start = 12
    else:
        raise ValueError("unknown .npy version %d" % major)
    header = ast.literal_eval(raw[start:start + hlen].decode("latin1"))
    if header["fortran_order"]:
        raise ValueError("Fortran-ordered array not supported")
    code, size = NPY_DTYPES[header["descr"]]
    arr = array.array(code)
    if arr.itemsize != size:
        raise ValueError("platform item size mismatch for %s" % code)
    arr.frombytes(raw[start + hlen:])
    if sys.byteorder != "little":
        arr.byteswap()
    shape = tuple(header["shape"])
    n = 1
    for s in shape:
        n *= s
    if len(arr) != n:
        raise ValueError("size mismatch: %d values for shape %s" % (len(arr), shape))
    return shape, arr


def read_members(path, names):
    out = {}
    with zipfile.ZipFile(path) as zf:
        for name in names:
            out[name] = parse_npy(zf.read(name + ".npy"))
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------ stimulus metadata

def load_stimuli():
    with open(os.path.join(AI06, "03-Data", "stage1", "stimulus-manifest.json")) as f:
        manifest = json.load(f)
    by_key = {e["key"]: e for e in manifest}
    info = {}
    for key in STIMULI:
        entry = by_key[key]
        path = os.path.join(AI06, entry["path"])
        m = read_members(path, ("angle", "intensity", "speed"))
        angle = list(m["angle"][1])
        intensity = list(m["intensity"][1])
        speed = float(m["speed"][1][0])
        off = [j for j, v in enumerate(intensity) if v == 0]
        end = ((10 * 2.25 / 5.8 + 2.25 / 5.8) - (-10 * 2.25 / 5.8)) / speed
        sha = sha256_file(path)
        info[key] = {
            "path": entry["path"],
            "sha256": sha,
            "sha256_matches_manifest": sha == entry.get("sha256"),
            "speed": speed,
            "motion_window_end_s": end,
            "manifest_motion_window_end_s": entry.get("motion_window_end_s"),
            "off_trajectories": off,
            "off_angles": [angle[j] for j in off],
            "n_on": sum(1 for v in intensity if v == 1),
        }
    return info


def window_bounds(T, end):
    idx = [i for i in range(T) if 0 <= (i + 200) * 0.005 - 1 <= end]
    if not idx:
        raise ValueError("empty motion window")
    if idx != list(range(idx[0], idx[-1] + 1)):
        raise ValueError("non-contiguous motion window")
    return idx[0], idx[-1]


# ------------------------------------------------------------- record readouts

def record_path(mode, model, stim, code):
    return os.path.join(CONF, mode, model, stim, code + ".npz")


def read_record(mode, model, stim, code, stiminfo, windows, stats):
    """Return evoked responses, saved peaks and trace-derived peaks for one record."""
    m = read_members(record_path(mode, model, stim, code), ("trace", "peaks"))
    shape, tr = m["trace"]
    pshape, pk = m["peaks"]
    n_traj, T, nc = shape
    if n_traj != 24 or nc != 13 or pshape != (24, N_PEAK_COLS):
        raise ValueError("unexpected shapes %s %s in %s/%s/%s/%s"
                         % (shape, pshape, mode, model, stim, code))
    key = (stim, T)
    if key not in windows:
        windows[key] = window_bounds(T, stiminfo[stim]["motion_window_end_s"])
    i0, i1 = windows[key]
    off = stiminfo[stim]["off_trajectories"]
    evoked = {}
    nonfinite = False
    for x in T5_COLS:
        d = {}
        for j in off:
            base = j * T * nc + x
            seg = tr[base + i0 * nc: base + i1 * nc + 1: nc]
            first = tr[base]
            if not math.isfinite(sum(seg) + first):
                d[j] = None
                nonfinite = True
                continue
            top = max(seg)
            v = top - first
            d[j] = v if v > 0.0 else 0.0
            # consistency of the saved peaks with the trace
            derived = top if top > 0.0 else 0.0
            saved = pk[j * N_PEAK_COLS + x]
            if math.isfinite(saved):
                gap = abs(saved - derived)
                if gap > stats["peaks_max_abs_gap"]:
                    stats["peaks_max_abs_gap"] = gap
                    stats["peaks_max_abs_gap_at"] = [mode, model, stim, code, j, x]
            stats["peaks_checked"] += 1
        evoked[x] = d
    if nonfinite:
        stats["nonfinite_records"].append([mode, model, stim, code])
    return {"evoked": evoked, "peaks": pk, "trace": tr, "T": T, "window": (i0, i1)}


def identity_gap(base_tr, cond_tr, T, window):
    """Largest |cond - base| over columns 0-7 and the window, over largest |base|."""
    i0, i1 = window
    num = 0.0
    den = 0.0
    nc = 13
    for j in range(24):
        for x in range(8):
            b0 = j * T * nc + x
            sb = base_tr[b0 + i0 * nc: b0 + i1 * nc + 1: nc]
            sc = cond_tr[b0 + i0 * nc: b0 + i1 * nc + 1: nc]
            for u, v in zip(sb, sc):
                g = abs(u - v)
                if g > num:
                    num = g
                a = abs(u)
                if a > den:
                    den = a
    return num / den if den > 0 else None


def pd_ratios(base, cond, off):
    """pd_evoked ratio per T5 subtype (None when undefined)."""
    out = []
    for x in T5_COLS:
        b = base["evoked"][x]
        vals = [b[j] for j in off]
        if any(v is None for v in vals):
            out.append(None)
            continue
        k = max(range(len(off)), key=lambda i: vals[i])   # first maximum, as argmax
        p = off[k]
        den = b[p]
        num = cond["evoked"][x][p]
        if den <= EPS or num is None:
            out.append(None)
        else:
            out.append(num / den)
    return out


def pooled_ratios(base, cond, off):
    """P7's pooled raw-peak ratio per T5 subtype (None when undefined)."""
    out = []
    for x in T5_COLS:
        num = sum(cond["peaks"][j * N_PEAK_COLS + x] for j in off)
        den = sum(base["peaks"][j * N_PEAK_COLS + x] for j in off)
        if not (math.isfinite(num) and math.isfinite(den)) or den <= EPS:
            out.append(None)
        else:
            out.append(num / den)
    return out


def combine(per_stim, stats, label):
    """Mean over the two stimuli of the mean over defined subtype ratios."""
    means = []
    for rs in per_stim:
        d = [r for r in rs if r is not None]
        if d:
            means.append(sum(d) / len(d))
        else:
            stats["stimulus_with_no_defined_subtype"].append(label)
    return sum(means) / len(means) if means else None


# ------------------------------------------------------------------ statistics

def binom_upper_tail(b, n):
    """P(X >= b) for X ~ Binomial(n, 1/2), exact."""
    if n == 0:
        return 1.0
    return float(Fraction(sum(math.comb(n, k) for k in range(b, n + 1)), 2 ** n))


def binom_two_sided(k, n):
    """Exact two-sided binomial test against 1/2 (sum of outcomes no more likely than k)."""
    if n == 0:
        return 1.0
    ck = math.comb(n, k)
    return float(Fraction(sum(math.comb(n, i) for i in range(n + 1)
                              if math.comb(n, i) <= ck), 2 ** n))


def holm(pvals):
    """Holm step-down adjustment; pvals is a dict name -> p."""
    names = sorted(pvals, key=lambda k: pvals[k])
    m = len(names)
    out = {}
    running = 0.0
    for i, name in enumerate(names):
        adj = min(1.0, (m - i) * pvals[name])
        running = max(running, adj)
        out[name] = running
    return out


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, alpha=0.05):
    if n == 0:
        return [0.0, 1.0]

    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    # lower: P(X >= k | p) = alpha/2, increasing in p
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) >= alpha / 2)
    # upper: P(X <= k | p) = alpha/2, decreasing in p
    upper = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) <= alpha / 2)
    return [lower, upper]


def category(v):
    if v is None:
        return "undefined"
    if v <= ABOL:
        return "abolished"
    if v < LO:
        return "reduced"
    if v <= HI:
        return "unchanged"
    return "increased"


# --------------------------------------------------------------------- compute

def compute():
    with open(os.path.join(CONF, "confirmation-run.json")) as f:
        run = json.load(f)
    models = list(run["models"])
    stiminfo = load_stimuli()
    windows = {}
    stats = {
        "peaks_max_abs_gap": 0.0,
        "peaks_max_abs_gap_at": None,
        "peaks_checked": 0,
        "nonfinite_records": [],
        "stimulus_with_no_defined_subtype": [],
        "missing_records": [],
    }
    identity = {}
    # values[model][mode][readout][condition] = model value
    values = {}
    stim_means = {}
    subtype = {}
    for mi, model in enumerate(models):
        values[model] = {mode: {r: {} for r in READOUTS} for mode in MODES}
        stim_means[model] = {mode: {r: {} for r in READOUTS} for mode in MODES}
        subtype[model] = {mode: {r: {} for r in READOUTS} for mode in MODES}
        for mode in MODES:
            per = {r: {c: [] for c in CONDITIONS} for r in READOUTS}
            for stim in STIMULI:
                off = stiminfo[stim]["off_trajectories"]
                base = read_record(mode, model, stim, "baseline", stiminfo, windows, stats)
                for code in IDENTITY:
                    rec = read_record(mode, model, stim, code, stiminfo, windows, stats)
                    identity["%s|%s|%s|%s" % (mode, model, stim, code)] = identity_gap(
                        base["trace"], rec["trace"], base["T"], base["window"])
                for code in CONDITIONS:
                    if not os.path.exists(record_path(mode, model, stim, code)):
                        stats["missing_records"].append([mode, model, stim, code])
                        per["pd_evoked"][code].append([None] * 4)
                        per["pooled_raw"][code].append([None] * 4)
                        continue
                    rec = read_record(mode, model, stim, code, stiminfo, windows, stats)
                    per["pd_evoked"][code].append(pd_ratios(base, rec, off))
                    per["pooled_raw"][code].append(pooled_ratios(base, rec, off))
            for r in READOUTS:
                for code in CONDITIONS:
                    label = "%s|%s|%s|%s" % (mode, model, r, code)
                    values[model][mode][r][code] = combine(per[r][code], stats, label)
                    stim_means[model][mode][r][code] = [
                        (sum(x for x in rs if x is not None) / sum(1 for x in rs if x is not None))
                        if any(x is not None for x in rs) else None
                        for rs in per[r][code]]
                    subtype[model][mode][r][code] = per[r][code]
        print("model %s done (%d/%d)" % (model, mi + 1, len(models)), file=sys.stderr, flush=True)

    def v(model, mode, readout, code):
        return values[model][mode][readout][code]

    near = []

    def note_near(label, value, thresholds):
        if value is None:
            return
        for t in thresholds:
            if abs(value - t) < 1e-6:
                near.append({"what": label, "value": value, "threshold": t})

    # 1. positive controls
    control_fail = []
    control_detail = {}
    for model in models:
        a = v(model, "adapted", "pd_evoked", "pc-cut-all-T5-inputs")
        h = v(model, "adapted", "pd_evoked", "pc-half-exc-T5")
        note_near("%s cut-all" % model, a, (ABOL,))
        note_near("%s half-exc" % model, h, (LO,))
        ok_a = a is not None and a <= ABOL
        ok_h = h is not None and h < LO
        control_detail[model] = {"pc-cut-all-T5-inputs": a, "pc-half-exc-T5": h,
                                 "cut_all_ok": ok_a, "half_exc_ok": ok_h}
        if not (ok_a and ok_h):
            control_fail.append(model)
    eligible = [m for m in models if m not in control_fail]

    # 2. H1
    h1 = {}
    for tm in TMS:
        code = "s100-silence-" + tm
        rc = rp = b = c = 0
        n_used = 0
        skipped = []
        per_model = {}
        for model in eligible:
            x = v(model, "adapted", "pd_evoked", code)
            y = v(model, "onset", "pooled_raw", code)
            note_near("%s H1 corrected %s" % (model, tm), x, (LO,))
            note_near("%s H1 p7 %s" % (model, tm), y, (LO,))
            if x is None or y is None:
                skipped.append(model)
                continue
            n_used += 1
            red_c = x < LO
            red_p = y < LO
            rc += red_c
            rp += red_p
            b += red_c and not red_p
            c += red_p and not red_c
            per_model[model] = {"corrected": x, "p7": y,
                                "reduced_corrected": red_c, "reduced_p7": red_p}
        h1[tm] = {"n": n_used, "reduced_corrected": rc, "reduced_p7": rp,
                  "corrected_only": b, "p7_only": c,
                  "p_one_sided": binom_upper_tail(b, b + c),
                  "skipped_undefined": skipped, "per_model": per_model}
    holm_h1 = holm({tm: h1[tm]["p_one_sided"] for tm in ("Tm1", "Tm2", "Tm4")})
    for tm in holm_h1:
        h1[tm]["p_holm_secondary"] = holm_h1[tm]

    # 3. H2-H5
    def s(model, kind, group):
        return v(model, "adapted", "pd_evoked", "s100-%s-%s" % (kind, group))

    patterns = {}
    for tm in ("Tm1", "Tm9"):
        def h2(model, tm=tm):
            d, ct, both, sil = (s(model, "cutT5", tm), s(model, "cutCT1", tm),
                                s(model, "cutT5+CT1", tm), s(model, "silence", tm))
            if None in (d, ct, both, sil):
                return None
            note_near("%s H2 %s direct" % (model, tm), d, (LO,))
            note_near("%s H2 %s ct1" % (model, tm), ct, (HI,))
            note_near("%s H2 %s |both-sil|" % (model, tm), abs(both - sil), (DELTA / 2,))
            return d < LO and ct > HI and abs(both - sil) <= DELTA / 2
        patterns["H2-" + tm] = h2
    for tm in TMS:
        def h3(model, tm=tm):
            o, d = s(model, "open", tm), s(model, "cutT5", tm)
            if None in (o, d):
                return None
            note_near("%s H3 %s d-o" % (model, tm), d - o, (DELTA,))
            return o < d - DELTA
        patterns["H3-" + tm] = h3
    for tm in TMS:
        def h4(model, tm=tm):
            sil, both = s(model, "silence", tm), s(model, "cutT5+CT1", tm)
            if None in (sil, both):
                return None
            note_near("%s H4 %s |sil-both|" % (model, tm), abs(sil - both), (DELTA,))
            return abs(sil - both) > DELTA
        patterns["H4-" + tm] = h4

    def h5(model):
        q = s(model, "silence", "quad")
        singles = [s(model, "silence", tm) for tm in TMS]
        if q is None or None in singles:
            return None
        note_near("%s H5 quad" % model, q, (LO,))
        for x in singles:
            note_near("%s H5 single" % model, x, (LO, HI))
        return q < LO and all(LO <= x <= HI for x in singles)
    patterns["H5"] = h5

    h2h5 = {}
    for name, fn in patterns.items():
        res = {m: fn(m) for m in eligible}
        used = [m for m in eligible if res[m] is not None]
        k = sum(1 for m in used if res[m])
        n = len(used)
        h2h5[name] = {"holds": k, "n": n, "share": (k / n) if n else None,
                      "p_two_sided": binom_two_sided(k, n),
                      "clopper_pearson_95": clopper_pearson(k, n),
                      "models_holding": [m for m in used if res[m]],
                      "skipped_undefined": [m for m in eligible if res[m] is None]}
    adj = holm({k: h2h5[k]["p_two_sided"] for k in h2h5})
    for name in h2h5:
        h2h5[name]["p_holm"] = adj[name]
        share = h2h5[name]["share"]
        if adj[name] < 0.05 and share is not None and share > 0.5:
            verdict = "holds in most models"
        elif adj[name] < 0.05 and share is not None and share < 0.5:
            verdict = "refuted as the general cause"
        else:
            verdict = "mixed"
        h2h5[name]["verdict"] = verdict

    # 4. category counts over eligible models (all s100 conditions and controls,
    # both modes and both readouts; the brief's primary set is adapted|s100-silence-*|pd_evoked)
    cats = {}
    for mode in MODES:
        for code in CONDITIONS:
            for r in READOUTS:
                cnt = {"abolished": 0, "reduced": 0, "unchanged": 0, "increased": 0,
                       "undefined": 0}
                for model in eligible:
                    cnt[category(v(model, mode, r, code))] += 1
                cats["%s|%s|%s" % (mode, code, r)] = cnt

    on_disk = sorted(os.listdir(os.path.join(CONF, "adapted")))
    result = {
        "what": "Independent standard-library recheck of BM2 confirmation scores",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "inputs": {
            "confirmation_run_sha256": sha256_file(os.path.join(CONF, "confirmation-run.json")),
            "n_models_listed": len(models),
            "run_failed": run.get("failed"),
            "models_on_disk_match_run_list": on_disk == sorted(models),
        },
        "stimuli": stiminfo,
        "motion_windows": {"%s|T=%d" % k: list(w) for k, w in sorted(windows.items())},
        "record_checks": {
            "saved_peaks_vs_trace_max_abs_gap": stats["peaks_max_abs_gap"],
            "saved_peaks_vs_trace_worst_at": stats["peaks_max_abs_gap_at"],
            "peak_values_checked": stats["peaks_checked"],
            "nonfinite_records": stats["nonfinite_records"],
            "missing_records": stats["missing_records"],
            "stimulus_with_no_defined_subtype": stats["stimulus_with_no_defined_subtype"],
            "identity_max_normalised_gap": max(g for g in identity.values() if g is not None),
            "identity_gap_definition": "max |condition - intact| over T4a-T5d, all 24 trajectories, "
                                       "motion window, divided by max |intact| (informational)",
        },
        "replication_check": "not rechecked (outside the brief)",
        "models": models,
        "control_fail": control_fail,
        "control_detail": control_detail,
        "eligible": eligible,
        "n_eligible": len(eligible),
        "H1": {"delta_0.2": h1},
        "H2_H5": {"delta_0.2": h2h5},
        "category_counts": cats,
        "near_threshold_values": near,
        "per_model_values": values,
        "per_model_stimulus_means": stim_means,
        "per_model_subtype_ratios_order": "[stimulus final_slow, dev_fast][T5a, T5b, T5c, T5d]",
        "per_model_subtype_ratios": subtype,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1, sort_keys=False)
    print("wrote %s" % OUT, file=sys.stderr)


# --------------------------------------------------------------------- compare
# Written after the compute step had saved its numbers to RECHECK.json.

RATIO_TOL = 1e-9   # on |a - b| / max(1, |b|)
READOUT_NAME_IN_SCORES = {"pd_evoked": "pd_evoked", "pooled_raw": "pooled"}


def rel_gap(a, b):
    if a is None or b is None:
        return None if a is None and b is None else float("inf")
    return abs(a - b) / max(1.0, abs(b))


def compare():
    with open(OUT) as f:
        mine = json.load(f)
    with open(SCORES) as f:
        theirs = json.load(f)
    items = []        # every compared value
    mismatches = []

    def check(label, my, their, kind):
        if kind == "exact":
            ok = my == their
            gap = None
        else:
            gap = rel_gap(my, their)
            ok = gap is not None and gap <= RATIO_TOL if not (my is None and their is None) else True
        row = {"what": label, "recheck": my, "saved": their, "match": ok}
        if gap is not None:
            row["rel_gap"] = gap
        items.append(row)
        if not ok:
            mismatches.append(row)

    # models, exclusions and eligibility
    check("models", mine["models"], theirs["models"], "exact")
    check("control_fail", sorted(mine["control_fail"]), sorted(theirs["control_fail"]), "exact")
    check("eligible", sorted(mine["eligible"]), sorted(theirs["eligible"]), "exact")
    check("n_eligible", mine["n_eligible"], theirs["n_eligible"], "exact")
    check("nonfinite_records", mine["record_checks"]["nonfinite_records"],
          theirs.get("nonfinite_records"), "exact")

    # per-model control values
    for model, det in mine["control_detail"].items():
        sv = theirs["controls"][model]
        check("controls|%s|cut_all" % model, det["pc-cut-all-T5-inputs"], sv["cut_all"], "ratio")
        check("controls|%s|half_exc" % model, det["pc-half-exc-T5"], sv["half_exc"], "ratio")
        check("controls|%s|cut_all_pass" % model, det["cut_all_ok"], sv["cut_all_pass"], "exact")
        check("controls|%s|half_exc_pass" % model, det["half_exc_ok"], sv["half_exc_pass"], "exact")

    # H1
    for tm in TMS:
        m = mine["H1"]["delta_0.2"][tm]
        s = theirs["H1"]["delta_0.2"][tm]
        check("H1|%s|n_models" % tm, m["n"], s.get("n_models"), "exact")
        for k in ("reduced_corrected", "reduced_p7", "corrected_only", "p7_only"):
            check("H1|%s|%s" % (tm, k), m[k], s.get(k), "exact")
        check("H1|%s|p_one_sided" % tm, m["p_one_sided"], s.get("p_one_sided"), "ratio")
        if "call" in s:   # primary test (Tm9): holds if p < 0.05 and b > c
            my_call = ("holds" if m["p_one_sided"] < 0.05
                       and m["corrected_only"] > m["p7_only"] else "not held")
            check("H1|%s|call" % tm, my_call, s["call"], "exact")
        if "p_holm_secondary" in s or "p_holm_secondary" in m:
            check("H1|%s|p_holm_secondary" % tm, m.get("p_holm_secondary"),
                  s.get("p_holm_secondary"), "ratio")

    # H2-H5
    for name, m in mine["H2_H5"]["delta_0.2"].items():
        s = theirs["H2_H5"]["delta_0.2"][name]
        check("H2_H5|%s|holds" % name, m["holds"], s.get("holds"), "exact")
        check("H2_H5|%s|n" % name, m["n"], s.get("n"), "exact")
        check("H2_H5|%s|share" % name, m["share"], s.get("share"), "ratio")
        check("H2_H5|%s|p_two_sided" % name, m["p_two_sided"], s.get("p_two_sided"), "ratio")
        check("H2_H5|%s|p_holm" % name, m["p_holm"], s.get("p_holm"), "ratio")
        for i, side in enumerate(("lower", "upper")):
            check("H2_H5|%s|ci95_%s" % (name, side), m["clopper_pearson_95"][i],
                  s.get("ci95", [None, None])[i], "ratio")
        check("H2_H5|%s|call" % name, m["verdict"], s.get("call"), "exact")
        holding = set(m["models_holding"])
        for model in mine["eligible"]:
            key = "%s|%s" % (name, model)
            if key in theirs.get("H2_H5_per_model", {}):
                check("H2_H5_per_model|" + key, model in holding,
                      theirs["H2_H5_per_model"][key], "exact")

    # category counts (s100 conditions, both modes, pd_evoked and P7's pooled raw readout)
    for key, cnt in mine["category_counts"].items():
        mode, code, readout = key.split("|")
        skey = "%s|%s|%s" % (mode, code, READOUT_NAME_IN_SCORES[readout])
        if skey in theirs["category_counts"]:
            check("category_counts|" + skey, cnt, theirs["category_counts"][skey], "exact")

    # per-model values in PER-MODEL.csv (the saved ratio table behind the scores)
    import csv
    per_model_gap = {"compared": 0, "max_rel_gap": 0.0, "worst": None,
                     "category_mismatches": []}
    with open(os.path.join(CONF, "scores", "PER-MODEL.csv"), newline="") as f:
        for row in csv.DictReader(f):
            mode, code, readout = row["mode"], row["condition"], row["readout"]
            mine_r = {v: k for k, v in READOUT_NAME_IN_SCORES.items()}.get(readout)
            if mine_r is None or code not in CONDITIONS:
                continue
            my = mine["per_model_values"][row["model"]][mode][mine_r][code]
            their = float(row["value"]) if row["value"] not in ("", "nan", "None") else None
            gap = rel_gap(my, their)
            per_model_gap["compared"] += 1
            if gap is None:
                continue
            if gap > per_model_gap["max_rel_gap"]:
                per_model_gap["max_rel_gap"] = gap
                per_model_gap["worst"] = [row["model"], mode, code, readout, my, their]
            if gap > RATIO_TOL:
                mismatches.append({"what": "PER-MODEL|%s|%s|%s|%s" % (row["model"], mode, code, readout),
                                   "recheck": my, "saved": their, "rel_gap": gap, "match": False})
            if category(my) != row["category_delta_0.2"]:
                per_model_gap["category_mismatches"].append(
                    [row["model"], mode, code, readout, my, category(my), row["category_delta_0.2"]])
    if per_model_gap["category_mismatches"]:
        mismatches.append({"what": "PER-MODEL categories", "match": False,
                           "detail": per_model_gap["category_mismatches"]})

    mine["comparison"] = {
        "saved_scores": os.path.relpath(SCORES, STUDY),
        "saved_scores_sha256": sha256_file(SCORES),
        "per_model_csv_sha256": sha256_file(os.path.join(CONF, "scores", "PER-MODEL.csv")),
        "tolerance": "counts, lists, flags and calls exact; ratios and p-values "
                     "|a - b| / max(1, |b|) <= %g" % RATIO_TOL,
        "n_compared": len(items) + per_model_gap["compared"],
        "n_mismatches": len(mismatches),
        "verdict": "pass" if not mismatches else "fail",
        "per_model_csv": per_model_gap,
        "mismatches": mismatches,
        "items": items,
    }
    with open(OUT, "w") as f:
        json.dump(mine, f, indent=1)
    print("compared %d values, %d mismatches -> %s"
          % (mine["comparison"]["n_compared"], len(mismatches),
             mine["comparison"]["verdict"]), file=sys.stderr)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "compute"
    if step == "compute":
        compute()
    elif step == "compare":
        compare()
    else:
        raise SystemExit("usage: recheck.py compute|compare")
