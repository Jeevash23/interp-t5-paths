# Files of the reference study

The study runs the simulator of a reference study of the same 50 FlyVis models (exact and first-order silencing of
each cell type, released separately), and its replication check compares with that study's saved results. The files
the code reads or imports are copied here, in the reference study's own layout. `FREEZE-1.json` lists the simulator
and its inputs under their paths here.

| File | What it is | Read by |
|---|---|---|
| `02-Code/stage1/core.py`, `02-Code/stage1/common.py`, `study/code/revision_common.py`, `study/config.json` | The batched FlyVis simulator, its settings, and the helpers for paths, stimuli and readouts | the simulator |
| `03-Data/stage1/stimulus-dev_fast.npz`, `stimulus-final_slow.npz`, `stimulus-manifest.json` | The two moving-edge stimuli and their manifest | the simulator and the scoring |
| `03-Data/stage1/model-selection.json`, `network-structure.json` | The 50 models with the SHA-256 of every checkpoint, and the network's cell types | the simulator |
| `study/results/analysis/development/effects.csv`, `.../confirmation/effects.csv` | Exact silencing of every cell type in the 4 development and 46 confirmation models | the replication checks of the simulator and the scoring, and P7's matching |
| `study/results/runs/<model>/{final_slow,dev_fast}/baseline.npz` | The intact network's responses of the 50 models at the two stimuli | P7's weighted pooling and the simulator's identity check |
| `03-Data/biology-key.csv`, `01-Papers/sources/flyvis/LICENSE` | The reference study's key of experimental results, and the flyvis package's MIT licence | shipped as in P7's release |

The analysis tables and the intact-network records are packed in `data/saved-outputs/reference-study-results.tar.xz`, and `make unpack` restores
them here. One file differs from the reference study's copy: `02-Code/stage1/common.py` sets the `TIMEZONE` variable,
which flyvis uses only for the time stamps of its log messages, to UTC (see `RELEASE-CHANGES.md`).
