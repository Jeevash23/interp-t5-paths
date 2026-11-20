# Files of P7

P7 is the manuscript's first part, which compared silencing in the FlyVis models with genetic silencing in flies
(released separately). This study re-scores P7's frozen table of fly results with the corrected measurement
(`code/score_p7_table.py`, post hoc), using P7's own matching rules and settings. The files it reads are copied here,
in P7's own layout; `FREEZE-2.json` lists the first four under their paths here.

| File | What it is |
|---|---|
| `code/common.py` | P7's matching of fly results to model readouts, its ensemble rule and agreement measures |
| `config.json` | P7's settings; `ai06_root` names the reference study's copy in this release (see `RELEASE-CHANGES.md`) |
| `extraction/merged-table.csv` | P7's frozen table of fly results |
| `results/development/settings.json` | P7's settings fixed on the development models (the margin and the pooling) |
| `results/confirmation/comparisons.csv` | P7's saved comparisons, which the re-scoring reproduces on P7's measurement (in `data/saved-outputs/reference-study-results.tar.xz`) |
