# BM2 independent recheck

**Result: pass.** 5,813 values compared with the saved scores, 0 mismatches.

Run on 23 October 2026 (19:41 UTC) by a separate session, as PROTOCOL.md Section 7 requires. The script is `recheck/recheck.py` (standard library only, Python 3.14, run under a memory limit with `python3 -I`); its output is `recheck/RECHECK.json`. BM2's scoring code (`code/score.py`, `code/score_p7_table.py`, `code/pilot_analyse.py`) was not read or imported. The definitions came from PROTOCOL.md Sections 3, 4 and 6, AMENDMENTS.md and the recheck brief. The script ran in two steps. `compute` read only the raw records and AI-06's stimulus files and wrote its numbers to RECHECK.json. Only after that did `compare` open `results/confirmation/scores/`.

## What was recomputed

- **Inputs.** All 46 models in `confirmation-run.json` (no failed runs; the model folders on disk match the list). For each model, application (adapted, onset) and stimulus (`final_slow`, `dev_fast`), the script read the intact run, the two identity conditions, the two positive controls and all 25 full-strength conditions. It parsed the `.npy` members (`trace`, `peaks`) directly from the `.npz` zips. It did not read the per-record `.json` files.
- **Stimuli.** From AI-06's stimulus files it read only `angle`, `intensity` and `speed`, not the large `stimulus` array. Both files match the SHA-256 digests in AI-06's manifest. The 12 OFF trajectories are the even indices 0–22 (directions 0–330 degrees in steps of 30). The motion window ends at 1.71506 s for `final_slow` (speed 4.75) and 0.42877 s for `dev_fast` (speed 19.0), which agrees with the manifest's values to within 4e-16. The window covers frames 0–343 of 344 and frames 0–85 of 86.
- **Record checks.** The saved `peaks` matched the maximum of the rectified trace over the motion window exactly (gap 0 over 264,960 values). No record had non-finite values and none was missing. No stimulus was left without a defined subtype ratio. As an informational check of my own design, the identity conditions differ from the intact run by at most 8.0e-7, measured as the largest absolute gap divided by the largest absolute intact value. This is not the protocol's normalised gap.
- **Readouts.** pd_evoked (primary) and P7's pooled raw-peak ratio, per T5 subtype and stimulus, then averaged over the defined subtypes and the two stimuli. Both readouts were computed for both applications on every full-strength condition and both controls.
- **Scores.** The positive controls and eligibility; H1 for all four Tm types (counts, discordant pairs, exact one-sided binomial p, and Holm adjustment across Tm1, Tm2 and Tm4); H2–H5 per model and in total (counts, share, Clopper–Pearson 95% interval, exact two-sided binomial p, Holm adjustment across the 11 calls, and the call); category counts at δ = 0.2.

## Results (δ = 0.2)

**Controls.** Every edge into T5 cut gives 0 in all 46 models. Six models fail the halved-excitation control (it must be below 0.8): 014 (0.887), 020 (0.835), 021 (2.069), 028 (3.900), 034 (0.929) and 035 (0.937). This leaves 40 eligible models.

**H1** (40 models each; reduced on the corrected measurement versus reduced on P7's measurement):

| Tm | corrected | P7 | corrected only | P7 only | one-sided p |
|---|---|---|---|---|---|
| Tm1 | 32 | 13 | 20 | 1 | 1.05e-5 (Holm 3.15e-5) |
| Tm2 | 28 | 11 | 19 | 2 | 1.11e-4 (Holm 2.21e-4) |
| Tm4 | 11 | 9 | 6 | 4 | 0.377 (Holm 0.377) |
| Tm9 | 26 | 14 | 15 | 3 | 0.00377 (primary; holds) |

**H2–H5** (models in which the pattern holds, out of 40):

| Call | holds | Holm p | call |
|---|---|---|---|
| H2-Tm1 | 0 | 2.0e-11 | refuted as the general cause |
| H2-Tm9 | 5 | 6.9e-6 | refuted as the general cause |
| H3-Tm1 | 4 | 1.1e-6 | refuted as the general cause |
| H3-Tm2 | 0 | 2.0e-11 | refuted as the general cause |
| H3-Tm4 | 2 | 1.3e-8 | refuted as the general cause |
| H3-Tm9 | 2 | 1.3e-8 | refuted as the general cause |
| H4-Tm1 | 30 | 0.0067 | holds in most models |
| H4-Tm2 | 23 | 0.43 | mixed |
| H4-Tm4 | 14 | 0.16 | mixed |
| H4-Tm9 | 8 | 7.3e-4 | refuted as the general cause |
| H5 | 2 | 1.3e-8 | refuted as the general cause |

**Categories, adapted, pd_evoked, full-strength silencing** (abolished / reduced / unchanged / increased, 40 models): Tm1 9/23/7/1, Tm2 8/20/10/2, Tm4 1/10/23/6, Tm9 5/21/11/3, quadruple 21/18/1/0.

No value used in any decision lies within 1e-6 of a threshold, so the counts do not depend on rounding at a boundary.

## Comparison with the saved scores

The saved files compared were `SCORES.json` (SHA-256 `714debfa…f416`) and `PER-MODEL.csv` (SHA-256 `85d6101c…8fd1`). Counts, model lists, pass flags and calls had to agree exactly. Ratios and p-values had to agree to within |a − b| / max(1, |b|) ≤ 1e-9.

- `control_fail`, `eligible` (40) and `nonfinite_records` (none): match.
- The per-model control values and pass flags for all 46 models: match. The largest gap is 0.
- H1 at δ = 0.2 for all four Tm types (`n_models`, `reduced_corrected`, `reduced_p7`, `corrected_only`, `p7_only`, `p_one_sided`, `p_holm_secondary`), and the Tm9 call "holds": match.
- H2–H5 at δ = 0.2 for all 11 calls (`holds`, `n`, `share`, `ci95`, `p_two_sided`, `p_holm`, `call`): match. The largest relative gap is 2.2e-16. The 440 per-model outcomes in `H2_H5_per_model` also match.
- `category_counts`: all 100 full-strength keys for both applications and both readouts (`pd_evoked`; `pooled` is P7's raw-peak ratio) match, including the five primary `adapted|s100-silence-*|pd_evoked` keys.
- `PER-MODEL.csv`: all 4,968 model values for the two readouts (46 models × 2 applications × 27 conditions × 2 readouts) agree exactly (largest gap 0), and so do their δ = 0.2 categories.

**Mismatches: none.**

## Not rechecked

- The replication check against AI-06's saved effects (Section 6). The brief left it out.
- The sensitivity analyses at δ = 0.1 and 0.3.
- The half-strength (s050) conditions.
- The secondary readouts pooled_evoked, pd_peak and lptc.
- `secondary_patterns`, `runaway_over_100`, and the post hoc re-scoring of P7's fly table (`P7-TABLE-RESCORE.json`).
