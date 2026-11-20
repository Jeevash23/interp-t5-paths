"""BM2 development pilot (exploratory, not frozen): path-specific cuts onto T5 in the four FlyVis development models.

  code/pilot_run.sh            launches this on the GPU through the portfolio GPU lock, as a systemd unit
  python -B pilot_simulate.py  (CPU if not launched through the lock; slow)

Development models only (000, 001, 004, 005: P7's development set). The 46 confirmation models are never loaded.
AI-06's simulator is imported read-only (python -B); the FlyVis and matplotlib caches point at this folder.
Writes raw records only (readout traces and peaks) under results/pilot/<mode>/; ratios and categories are computed
later by pilot_analyse.py. Existing valid records are kept, so a stopped run resumes.

Two modes. "onset": the condition starts at stimulus onset, after the intact network has adapted to gray (as AI-06
and P7 silence). "adapted": the condition holds from rest, through the 1 s of gray and the 200 pre-onset frames, so
the network has settled with the cut before the stimulus, closer to chronic genetic silencing. (Added after the first
pilot model: with the condition starting at onset, T5 relaxes towards its new resting level inside the response
window, so cutting every input to T5 raised its raw peaks.)

Conditions, for each Tm type in Tm1, Tm2, Tm4, Tm9 and each strength s in 0.5, 1.0 (gain on cut edges = 1 - s):
  silence      the Tm type's release scaled by 1 - s (as in P7)
  cutT5        only the Tm type's edges onto T5a-d scaled
  cutCT1       only the Tm type's edges onto CT1(Lo1) scaled
  cutT5+CT1    both of the above
  open         open loop: every non-T5 cell that feeds T5 is clamped to its intact trajectory, and the Tm type's edges
               onto T5 are scaled, so nothing outside T5 can respond to the loss
The same five for all four Tm types together (the quadruple). Controls: every edge into T5 cut; every non-T5 type
presynaptic to T5 silenced; every excitatory edge into T5 halved. Identity checks: open loop with no cut, and a gain
of 1 on every edge, must reproduce the intact run (normalised gap <= 1e-4, the GPU sums in a varying order).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parent
STUDY = CODE.parent
PORTFOLIO = STUDY.parents[1]
AI06 = STUDY / "reference/flyvis-first-order"  # release: the reference study's files
OUT = STUDY / "results/pilot"
sys.path.insert(0, str(AI06 / "study/code"))
sys.path.insert(0, str(AI06 / "02-Code/stage1"))
import revision_common as ai06  # noqa: E402  (AI-06 paths, stimuli, model list, metrics; read only)
from core import Core, TARGETS  # noqa: E402  (AI-06 batched simulator; its stage1 common sets env vars)
assert Path(sys.modules["common"].__file__).resolve() == (AI06 / "02-Code/stage1/common.py").resolve()

os.environ["MPLCONFIGDIR"] = str(STUDY / ".cache/matplotlib")
os.environ["XDG_CACHE_HOME"] = str(STUDY / ".cache")

DEVELOPMENT = list(ai06.CONFIG["development_models"])
assert sorted(DEVELOPMENT) == ["000", "001", "004", "005"]
TMS = ["Tm1", "Tm2", "Tm4", "Tm9"]
T5 = ["T5a", "T5b", "T5c", "T5d"]
CT1 = "CT1(Lo1)"
EXTRA = ["CT1(Lo1)", "Tm1", "Tm2", "Tm4", "Tm9"]          # central cells kept for diagnostics
STRENGTHS = [0.5, 1.0]
STIMULI = ["final_slow", "dev_fast"]
KINDS = ["silence", "cutT5", "cutCT1", "cutT5+CT1", "open"]
DT = 0.005
GRAY = 200                                                 # steps of uniform gray, as AI-06's Core.gray (1 s)
ONSET = GRAY + 200                                         # stimulus onset in the full sequence
MODES = {"onset": ONSET, "adapted": 0}                     # condition applied at stimulus onset (as P7), or from rest
TOLERANCE = 1e-4
BATCH = int(os.environ.get("BM2_BATCH", ai06.CONFIG["batch_size"]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")
    tmp.replace(path)


def signature() -> str:
    files = [Path(__file__), AI06 / "02-Code/stage1/core.py", AI06 / "02-Code/stage1/common.py",
             AI06 / "study/code/revision_common.py", AI06 / "study/config.json"]
    return hashlib.sha256("\n".join(sha256(p) for p in files).encode()).hexdigest()


def conditions() -> list[dict]:
    out = [{"code": "identity-gain1", "kind": "identity-gain1", "tms": [], "strength": 0.0},
           {"code": "identity-open", "kind": "identity-open", "tms": [], "strength": 0.0},
           {"code": "pc-cut-all-T5-inputs", "kind": "pc-cut-all", "tms": [], "strength": 1.0},
           {"code": "pc-silence-T5-presyn", "kind": "pc-silence-presyn", "tms": [], "strength": 1.0},
           {"code": "pc-half-exc-T5", "kind": "pc-half-exc", "tms": [], "strength": 0.5}]
    for s in STRENGTHS:
        for group in [[t] for t in TMS] + [TMS]:
            name = "+".join(group) if len(group) == 1 else "quad"
            for kind in KINDS:
                out.append({"code": f"s{round(100 * s):03d}-{kind}-{name}", "kind": kind, "tms": group, "strength": s})
    return out


class PathCore(Core):
    """AI-06's Core with per-edge gains and an open-loop clamp. Same Euler arithmetic as Core.step."""

    def setup_paths(self) -> dict:
        import torch
        nt = self.node_names
        src = self.source.cpu().numpy()
        tar = self.target.cpu().numpy()
        self.src_type, self.tar_type = nt[src], nt[tar]
        into_t5 = np.isin(self.tar_type, T5)
        clamp = np.unique(src[into_t5])
        clamp = clamp[~np.isin(nt[clamp], T5)]
        self.clamp_nodes = torch.tensor(clamp, device=self.device, dtype=torch.long)
        central = self.native.connectome.central_cells_index[:]
        self.extra = torch.tensor([int(central[np.flatnonzero(nt[central] == x)[0]]) for x in EXTRA], device=self.device)
        self.presyn_types = sorted(set(self.src_type[into_t5]) - set(T5))
        self.w_np = self.weight.detach().cpu().numpy()
        self.dt_t = torch.tensor(DT, device=self.device, dtype=torch.float32)
        wiring = {}
        for target in T5 + [CT1]:
            sel = self.tar_type == target
            for source in sorted(set(self.src_type[sel])):
                both = sel & (self.src_type == source)
                wiring[f"{source}->{target}"] = {"edges": int(both.sum()), "weight_sum": float(self.w_np[both].sum()),
                                                 "syn_count_sum": float(self.syn_counts[both].sum())}
        return {"clamp_nodes": int(len(clamp)), "clamp_types": sorted(set(nt[clamp])), "t5_presyn_types": self.presyn_types,
                "wiring": wiring}

    def edges(self, sources, targets) -> np.ndarray:
        return np.flatnonzero(np.isin(self.src_type, sources) & np.isin(self.tar_type, targets))

    def plan(self, cond: dict) -> tuple[np.ndarray, np.ndarray | None, bool, dict]:
        """(type attenuation, per-edge gain or None, open loop?, notes) for one condition."""
        atten = np.zeros(self.c, dtype=np.float32)
        gain = None
        s = cond["strength"]
        kind = cond["kind"]
        notes = {}

        def scaled(idx, value):
            g = np.ones(self.e, dtype=np.float32)
            g[idx] = value
            notes["edges_scaled"] = int(len(idx))
            return g

        if kind == "identity-gain1":
            gain = np.ones(self.e, dtype=np.float32)
        elif kind == "identity-open":
            pass
        elif kind == "pc-cut-all":
            gain = scaled(np.flatnonzero(np.isin(self.tar_type, T5)), 0.0)
        elif kind == "pc-silence-presyn":
            for name in self.presyn_types:
                atten[self.names.index(name)] = 1.0
            notes["types_silenced"] = list(self.presyn_types)
        elif kind == "pc-half-exc":
            gain = scaled(np.flatnonzero(np.isin(self.tar_type, T5) & (self.w_np > 0)), 0.5)
        elif kind == "silence":
            for name in cond["tms"]:
                atten[self.names.index(name)] = s
        elif kind == "cutT5" or kind == "open":
            gain = scaled(self.edges(cond["tms"], T5), 1.0 - s)
        elif kind == "cutCT1":
            gain = scaled(self.edges(cond["tms"], [CT1]), 1.0 - s)
        elif kind == "cutT5+CT1":
            gain = scaled(self.edges(cond["tms"], T5 + [CT1]), 1.0 - s)
        else:
            raise ValueError(kind)
        return atten, gain, kind in ("open", "identity-open"), notes

    def pstep(self, v, x, atten, w):
        import torch
        release = torch.relu(v) * (1 - atten[:, self.types])
        edge = release[:, self.source] * w
        current = torch.zeros_like(v).scatter_add(1, self.target[None].expand(v.shape[0], -1), edge)
        external = torch.zeros_like(v)
        external[:, self.input] = x[:, None, :].to(v.dtype)
        velocity = 1 / torch.maximum(self.tau, self.dt_t) * (-v + self.bias + current + external)
        return v + velocity * DT

    def simulate(self, X, atten, w, onset, clamp_traj=None, clamp_rows=None, record=False, keep_from=0):
        """Run from rest (the bias) through X (B,T,hex): the intact network before step `onset`, the condition's
        attenuation atten (B,c) and weights w ((E,) or (B,E)) from `onset` on. clamp_traj (T,24,K) with clamp_rows (B,)
        overwrites the clamp cells after every step (open loop). Returns readouts (B,T-keep_from,13) and, if record,
        the clamp cells (T,B,K)."""
        import torch
        B = X.shape[0]
        v = self.bias[None].expand(B, -1).clone()
        zero = torch.zeros_like(atten)
        outs, rec = [], []
        with torch.no_grad():
            for k in range(X.shape[1]):
                if k >= onset:
                    v = self.pstep(v, X[:, k], atten, w)
                else:
                    v = self.pstep(v, X[:, k], zero, self.weight)
                if clamp_traj is not None:
                    v[:, self.clamp_nodes] = clamp_traj[k][clamp_rows]
                if record:
                    rec.append(v[:, self.clamp_nodes].clone())
                if k >= keep_from:
                    outs.append(torch.cat([v[:, self.readout], v[:, self.extra]], 1)[:, None])
        result = torch.cat(outs, 1)
        if not bool(torch.isfinite(result).all()):
            raise FloatingPointError("nonfinite output")
        return result, (torch.stack(rec, 0) if record else None)


def valid(path: Path, sig: str) -> bool:
    if not path.exists() or not path.with_suffix(".json").exists():
        return False
    meta = json.loads(path.with_suffix(".json").read_text())
    return meta.get("sha256") == sha256(path) and meta.get("simulation_signature") == sig


def write_record(path: Path, arrays: dict, meta: dict, sig: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".npz.tmp")
    with tmp.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    tmp.replace(path)
    save_json(path.with_suffix(".json"), {**meta, "sha256": sha256(path), "simulation_signature": sig, "utc": utc_now()})


def arrays_of(trace: np.ndarray, stim: dict) -> dict:
    main = ai06.independent_metrics(trace[:, :, :8], stim)
    extra_vals = trace[:, ai06.window(trace.shape[1], float(stim["speed"])), 8:].astype(np.float64)
    return {"trace": trace.astype(np.float32), "peaks": main["peaks"], "dsi": main["dsi"], "all_dsi": main["all_dsi"],
            "denominator": main["denominator"], "extra_peaks": np.maximum(extra_vals, 0).max(axis=1),
            "extra_mean": extra_vals.mean(axis=1)}


def run_model(model: str, device: str, sig: str, conds: list[dict]) -> dict:
    import torch
    started = time.perf_counter()
    model_folder = AI06 / f"03-Data/flyvis-root/results/flow/0000/{model}"
    expected = next(item["checkpoint_sha256"] for item in ai06.SELECTION["models"] if item["model"] == model)
    if sha256(model_folder / "best_chkpt") != expected:
        raise RuntimeError(f"checkpoint changed: {model}")
    core = PathCore(model, device)
    info = core.setup_paths()
    save_json(OUT / "wiring" / f"{model}.json", {"model": model, **info})
    gray = core.gray()
    report = {"model": model, "checks": {}, "conditions": 0, "clamp_nodes": info["clamp_nodes"]}
    for key in STIMULI:
        stim = ai06.stimulus(key)
        if sha256(AI06 / ai06.STIMULI[key]["path"]) != ai06.STIMULI[key]["sha256"]:
            raise RuntimeError(f"stimulus changed: {key}")
        frames = stim["stimulus"]
        if frames.ndim == 4:
            frames = frames[:, :, 0]
        n_frames = ai06.causal_frames(key)
        warm = torch.as_tensor(frames[:, :200], device=device, dtype=torch.float32)
        causal = torch.as_tensor(frames[:, 200:200 + n_frames], device=device, dtype=torch.float32)
        # The full sequence: 1 s of uniform gray (AI-06's Core.gray), the 200 pre-onset frames, then the causal frames.
        X = torch.cat([torch.full((24, GRAY, warm.shape[2]), 0.5, device=device), warm, causal], 1)
        _, state, _ = core.run(frames[:, :200], state=gray.expand(24, -1).clone())
        zero = torch.zeros((24, core.c), device=device)
        # Intact run with this code from rest, recording the clamp cells; checked against Core.run and AI-06's record.
        intact, rec = core.simulate(X, zero, core.weight, onset=len(X[0]), record=True, keep_from=ONSET)
        native, _, _ = core.run(causal, state=state.detach().clone(), start=0)
        scale = float(intact[:, :, :8].abs().max())
        exact_gap = float((intact[:, :, :8] - native).abs().max()) / scale
        base = arrays_of(intact.cpu().numpy(), stim)
        with np.load(AI06 / "study/results/runs" / model / key / "baseline.npz", allow_pickle=False) as saved:
            saved_peaks = saved["peaks"]
        record_gap = float(np.max(np.abs(base["peaks"] - saved_peaks)) / max(float(np.max(saved_peaks)), 1e-8))
        report["checks"][key] = {"pstep_vs_core_max_abs": exact_gap, "baseline_vs_ai06_record": record_gap}
        if exact_gap > TOLERANCE or record_gap > TOLERANCE:
            raise RuntimeError(f"baseline check failed: {model} {key} {exact_gap:.2e} {record_gap:.2e}")
        del native, state
        for mode, onset in MODES.items():
            dest = OUT / mode / model / key
            if not valid(dest / "baseline.npz", sig):
                write_record(dest / "baseline.npz", base, {"model": model, "stimulus": key, "kind": "baseline",
                                                           "mode": mode}, sig)
            pending = [c for c in conds if not valid(dest / (c["code"] + ".npz"), sig)]
            for is_open in (False, True):
                group = [c for c in pending if (c["kind"] in ("open", "identity-open")) == is_open]
                queue = [(ci, t) for ci in range(len(group)) for t in range(24)]
                partial = {}
                plans = {}
                for begin in range(0, len(queue), BATCH):
                    jobs = queue[begin:begin + BATCH]
                    idx = [t for _, t in jobs]
                    atten = torch.zeros((len(jobs), core.c), device=device)
                    needs_gain = False
                    for ci in {ci for ci, _ in jobs}:
                        if ci not in plans:
                            plans[ci] = core.plan(group[ci])
                        needs_gain |= plans[ci][1] is not None
                    w = core.weight
                    if needs_gain:
                        w = core.weight[None].repeat(len(jobs), 1)
                    for row, (ci, _) in enumerate(jobs):
                        a, g, _, _ = plans[ci]
                        atten[row] = torch.as_tensor(a, device=device)
                        if g is not None:
                            w[row] = core.weight * torch.as_tensor(g, device=device)
                    rows = torch.as_tensor(idx, device=device) if is_open else None
                    t0 = time.perf_counter()
                    out, _ = core.simulate(X[idx], atten, w, onset=onset, clamp_traj=rec if is_open else None,
                                           clamp_rows=rows, keep_from=ONSET)
                    if device == "cuda":
                        torch.cuda.synchronize()
                    wall = time.perf_counter() - t0
                    bank = out.cpu().numpy()
                    del out, w
                    for row, (ci, t) in enumerate(jobs):
                        r = partial.setdefault(ci, [np.empty((24, n_frames, 13), np.float32), set(), 0.0])
                        r[0][t] = bank[row]
                        r[1].add(t)
                        r[2] += wall / len(jobs)
                        if len(r[1]) == 24:
                            cond = group[ci]
                            arrays, _, seconds = partial.pop(ci)
                            notes = plans.pop(ci)[3]
                            write_record(dest / (cond["code"] + ".npz"), arrays_of(arrays, stim),
                                         {"model": model, "stimulus": key, "mode": mode, **cond, **notes,
                                          "wall_seconds": seconds}, sig)
                            report["conditions"] += 1
                if partial:
                    raise RuntimeError("incomplete trajectory assembly")
            # Identity checks must reproduce the intact traces (up to GPU summation order: normalised gap <= 1e-4).
            for code in ("identity-gain1", "identity-open"):
                with np.load(dest / f"{code}.npz", allow_pickle=False) as rec_i:
                    gap = float(np.max(np.abs(rec_i["trace"][:, :, :8] - base["trace"][:, :, :8]))) / scale
                report["checks"][key][f"{mode}:{code}"] = gap
                if gap > TOLERANCE:
                    raise RuntimeError(f"identity check failed: {model} {key} {mode} {code} {gap:.2e}")
        del rec, intact, X
        if device == "cuda":
            torch.cuda.empty_cache()
    report["seconds"] = time.perf_counter() - started
    return report


def environment(device: str) -> dict:
    import torch
    import flyvis
    info = {"python": platform.python_version(), "torch": torch.__version__, "flyvis": getattr(flyvis, "__version__", "?"),
            "numpy": np.__version__, "platform": platform.platform(), "device": device}
    if device == "cuda":
        info.update(gpu=torch.cuda.get_device_name(0), cuda=torch.version.cuda)
    return info


def configure(device: str):
    import torch
    torch.set_num_threads(ai06.CONFIG["cpu_threads"])
    torch.set_num_interop_threads(ai06.CONFIG["cpu_threads"])
    if device == "cuda":
        os.fstat(int(os.environ["AI09_GPU_LOCK_FD"]))
        torch.cuda.set_per_process_memory_fraction(ai06.CONFIG["max_gpu_memory_fraction"])
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False


def main() -> None:
    device = "cuda" if os.environ.get("AI09_GPU_LOCK_FD") else "cpu"
    models = sys.argv[1:] or DEVELOPMENT
    if any(m not in DEVELOPMENT for m in models):
        sys.exit("development models only (000, 001, 004, 005)")
    configure(device)
    sig = signature()
    conds = conditions()
    log = {"phase": "pilot", "started_utc": utc_now(), "simulation_signature": sig, "environment": environment(device),
           "conditions": [c["code"] for c in conds], "stimuli": STIMULI, "batch": BATCH, "models": {}}
    for model in models:
        report = run_model(model, device, sig, conds)
        log["models"][model] = report
        save_json(OUT / "pilot-run.json", log)
        print(f"pilot: model {model} done in {report['seconds']:.1f} s; new conditions {report['conditions']}; "
              f"checks {json.dumps(report['checks'])}", flush=True)
    log["finished_utc"] = utc_now()
    save_json(OUT / "pilot-run.json", log)
    print("pilot: complete")


if __name__ == "__main__":
    main()
