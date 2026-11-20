# Why T5 keeps its OFF responses when its inputs are silenced in the FlyVis models

Code and results for the later study (Section 5) of the preprint *Silencing in the FlyVis models matches fly experiments for Mi1 and Mi9, and the OFF-pathway mismatch depends largely on the measurement*, by Richard Jeevash (link to be added when it is posted).

This repository holds the code, study records and saved outputs of the later study (Section 5) behind it; the saved
outputs and the frozen protocols are attached to its v1.0 release (see [Release files](#release-files)). Every
score of the study is reproduced on a CPU in under a minute, without a model or network: the frozen scoring code is
rerun from the saved per-subtype readouts and its output is compared with the saved scores byte for byte.

## Release files

The saved outputs and the frozen protocols are not in this repository's files; they are attached to its v1.0 release:

| File | Size | Contents |
|---|---|---|
| `per-run-outputs.tar.gz` | 21.9 MB | The saved outputs: the 2 compressed archives in `data/saved-outputs/`, which `make unpack` places in the study folders and checks file by file |
| `frozen-protocols.tar.gz` | 10 kB | The studies' protocols, predictions, amendments, approvals and freeze records (7 files), at their places in the folder, where the checks read them |
| `SHA256SUMS` | | Checksums of the two archives |

Download the three files into an empty folder, check them there, and unpack them into this one:

```sh
sha256sum -c SHA256SUMS
tar -xzf per-run-outputs.tar.gz -C /path/to/interp-t5-paths
tar -xzf frozen-protocols.tar.gz -C /path/to/interp-t5-paths
```

After unpacking, `sha256sum -c SHA256SUMS` in this folder checks every file that its `SHA256SUMS` lists, the
unpacked attachments included, and the checks below run as described.

## What the study asks

The manuscript's first part found that, in the 50 released FlyVis models, silencing any one of T5's four OFF inputs
(Tm1, Tm2, Tm4 and Tm9) mostly leaves T5's OFF responses unchanged, whereas flies lose them (Serbe et al. 2016). This
later study asked two questions. First, whether that result depends on the measurement: the first part switched the
silencing on at stimulus onset and read raw rectified peaks, a measurement that fails a basic control on the
development models (cutting every input to T5 raises the raw peaks). The corrected measurement holds the silencing
from rest and reads the central T5's evoked response at its preferred direction (H1). Second, where T5 stays robust,
which of four causes accounts for it: opposing direct and CT1 routes (H2), compensation through T5's own feedback (H3),
other routes from the silenced cell (H4) or redundancy among the four inputs (H5). Each Tm type, and all four
together, was silenced and, separately, had its connections onto T5 cut, its connections onto CT1's lobula
compartment cut, both cut, or its direct input removed with every other input to T5 clamped to its intact trajectory
(open loop), at full and half strength, in both applications, on two edge speeds, in the 46 confirmation models.

In the 40 models that passed both positive controls, silencing Tm9 reduced T5's response in 26 on the corrected
measurement against 14 on the first part's (exact one-sided McNemar test, p = 0.0038); Tm1 and Tm2 moved the same way
and Tm4 did not. H2, H3 and H5 were refuted as general causes, and H4 held in most models for Tm1 only. Re-scored post
hoc with the first part's own rules, the 12 fly results on the OFF side go from 0 to 9 agreements. `REPORT.md` gives
the results in full.

## The study

- **Pilot.** A development pilot on the four development models (`PILOT-NOTES.md`; the reports and tables in
  `results/pilot/` and the first version in `results/pilot-v1/`) chose the measurement. A search for prior work was
  made before the protocol and again on the day of the freeze (`SCOOP-CHECK.md`).
- **Protocol.** The draft (`PROTOCOL-DRAFT.md`), the author's choices on it (`AUTHOR-APPROVAL.txt`) and the protocol
  (`PROTOCOL.md`).
- **Freezes.** `FREEZE-1.json` (05:37 UTC on 23 October 2026) hashed the protocol, the simulator, the pilot's
  outputs and the companion studies' files the simulator reads, before any confirmation model was run.
  `FREEZE-2.json` (05:41 UTC) hashed the scoring scripts and P7's files they read, before any confirmation outcome was
  read. Two amendments were made between the freezes (`AMENDMENTS.md`, hashed in `AMENDMENTS-1-2.sha256`).
- **Run and scoring.** The 46 confirmation models were simulated (`code/run.sh`, `code/simulate.py`) and scored by the
  frozen scripts (`code/score.py`, `code/score_p7_table.py`). A separate script written from the protocol's
  definitions, with Python's standard library only and without the scoring code, recomputed the controls, H1, H2–H5
  and the primary category counts from the raw records and matched every one (`recheck/`). `check_report.py` checks
  every number in `REPORT.md` against the saved scores.

The freezes are local hash records written by the study code, not public preregistrations. Times in the records are
UTC. The study's working name was BM2; "P7" is the manuscript's first part, and "AI-06" the reference study whose
simulator and saved results it uses (both released separately).

## What is in this folder

| Path | Contents |
|---|---|
| `PROTOCOL*.md`, `AUTHOR-APPROVAL.txt`, `AMENDMENTS*`, `FREEZE-*.json`, `SCOOP-CHECK.md`, `PILOT-NOTES.md`, `REPORT.md` | The study records (above) and the written report |
| `code/` | The simulator and its run script (`simulate.py`, `run.sh`), the pilot's simulator, analysis and run script, the scoring (`score.py`) and the re-scoring of P7's fly table (`score_p7_table.py`), the freeze records (`freeze.py`), the check of the pilot notes, a wiring listing, the difference between the pilot's simulator and the frozen one (`simulate-vs-pilot.diff`), and the GPU lock helper |
| `check_report.py` | Checks every number in `REPORT.md` against the saved scores |
| `recheck/` | The independent recheck (`recheck.py`) and its report (`RECHECK.md`); its output, `RECHECK.json`, is in the saved outputs |
| `results/` | After `make unpack`: the confirmation run's record, every simulation record's metadata, the wiring summaries, the scores, the per-subtype readouts, and the pilot's reports, tables and self-test scores |
| `reference/flyvis-first-order/`, `reference/model-vs-fly/` | The files of the reference study and of P7 that the code reads or imports (see their READMEs) |
| `data/saved-outputs/` | Saved outputs as compressed archives (see its README) (attached to the release: `per-run-outputs.tar.gz`) |
| `tools/` | Unpacking, freeze checking, the replay of the scoring, the comparison with the recheck, and the table and comparison for a rerun of the simulation |
| `requirements.txt`, `ENVIRONMENT.md` | The exact environment, and how to obtain the FlyVis models |
| `RELEASE-CHANGES.md`, `release-changes.json` | Every file that differs from the original project, with the original's SHA-256 |

## Install

```sh
make setup        # .venv with CPython 3.12.14 and the pinned packages (see ENVIRONMENT.md)
```

This downloads the packages in `requirements.txt`, including PyTorch's CUDA 12.4 build and its CUDA libraries (several
GB). The quick check needs only NumPy and SciPy; `ENVIRONMENT.md` gives a small route. Pass `PYTHON=/path/to/python`
to any `make` target to use another environment.

## Quick check (CPU, under a minute, no model, no network)

First unpack the two release attachments into this folder (see [Release files](#release-files)): the checks read
the saved outputs and the freeze records they contain.

```sh
make quick-check
```

It unpacks the saved outputs (checking every SHA-256), then:

1. checks both freeze records against this folder (`tools/check_freezes.py`, and the study's own `code/freeze.py
   check`): each frozen file is unchanged or changed for the release in a documented way (`RELEASE-CHANGES.md`);
2. reruns the frozen scoring, `code/score.py` and `code/score_p7_table.py` unchanged, in a temporary folder, with the
   raw records answered from the saved per-subtype readouts, and compares the four score files they write with the
   saved ones byte for byte (`tools/replay_scores.py`);
3. compares the per-subtype readouts with the values the independent recheck computed from the raw records
   (`tools/compare_recheck.py`);
4. checks every number in `REPORT.md` against the saved scores (`check_report.py`) and every number in
   `PILOT-NOTES.md` against the pilot's reports (`code/check_notes.py`).

Expected output (abridged):

```
FREEZE-1.json: 24 files: 13 changed for the release (documented), 11 unchanged
FREEZE-2.json: 6 files: 3 changed for the release (documented), 3 unchanged
total: 16 changed for the release (documented), 14 unchanged
all frozen files match
confirmation: 46 models, 40 eligible, 0 excluded, 6 failed a control; written to results/confirmation/scores
confirmation: 12 rows; P7's measurement agree 0, corrected agree 9; rows changed 9
SCORES.json: identical
PER-MODEL.csv: identical
PRIMARY-TABLE.csv: identical
P7-TABLE-RESCORE.json: identical
replay of the frozen scoring: all four saved score files reproduced
per-subtype values compared with the independent recheck: 39744, mismatches: 0
49 checks; 0 failures
34 numbers in PILOT-NOTES.md; 34 found in the reports
```

## The raw records and a rerun

The simulation wrote about 10,300 raw records (each condition's T5 and diagnostic traces and peaks, 2.5 GB). They are
not included. Each record's metadata file (included) gives the record's SHA-256. The scores depend on the records
only through one function of the frozen scoring code, `per_subtype` in `code/score.py` (each T5 subtype's readouts
for a condition against the intact network). `results/confirmation/derived/PER-SUBTYPE.csv` holds that function's
output for every confirmation record. It was added for this release, written from the original records by
`tools/make_subtype_table.py`, and it is what the quick check replays the scoring from; the independent recheck, which
read the raw records with its own code, agrees with it.

To simulate models again and compare them with the saved values:

```sh
make flyvis-models                                   # the 50 released models, from the FlyVis authors
make rerun COPY=../t5-rerun MODELS="002 003"         # any of the 46 confirmation models
```

`make rerun` copies this folder without its saved results, runs the simulator through `code/run.sh` (GPU lock, write
audit) for the given models, reads the new records with the frozen `per_subtype` and compares every value with the
saved table (`tools/compare_rerun.py`, relative gap at most 1e-4, the protocol's identity tolerance). The study ran on
one 6 GB NVIDIA GPU (CUDA 12.4) at about 13 minutes per model, so all 46 take about 10 hours. The simulator checks
each model as it runs: the identity conditions must reproduce the intact run, and whole-cell silencing at onset must
reproduce the reference study's saved effects. Without the GPU lock helper the simulator runs on the CPU (much
slower; not timed). Tested for this release with `MODELS=002` on the same GPU: 775 s, identity checks within 2.4e-07,
3,960 per-subtype values compared, worst relative gap 1.2e-05, no failures.

## What is not included

- The raw simulation records of the confirmation run and the pilot (time traces, 2.5 GB and 0.3 GB); see above.
- The FlyVis models and the files the flyvis package builds (`make flyvis-models`), and the companion studies' other
  files (their own releases hold them).
- The run logs and the study's working status notes.

## Licence

MIT (`LICENSE`), covering the code and the study's records and saved outputs. The FlyVis package's licence is
included under `reference/flyvis-first-order/`; the FlyVis models and package are distributed under their own
licences.

## Study codes

The records and code name the studies by the codes they had while the work was done. Each code that occurs here,
and where that study is released:

| Code | Released in |
|---|---|
| AI-06 | `interp-flyvis-first-order` |
| AI-11 | `interp-model-vs-fly` |

## Use of AI assistants

As the preprint states:

> Language-model assistants were used throughout this work, under the author's direction, to help design the
> studies, to write and run the code for the experiments and analyses, to draft and revise the text and to check
> the references against their online records. All reported results come from the saved study outputs, and the
> numbers in the text were generated from those outputs or checked against them.

## Citation

Please cite the preprint (the link will be added here when it is posted) and, for the code and results, this
repository; [CITATION.cff](CITATION.cff) has the details.

```bibtex
@software{interp_t5_paths_2026,
  author  = {Jeevash, Richard},
  title   = {{Why T5 keeps its OFF responses when its inputs are silenced in the FlyVis models: code and results of the later study}},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/Jeevash23/interp-t5-paths}
}
```
