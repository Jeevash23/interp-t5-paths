# BM2 report: T5's robustness to Tm silencing in the FlyVis models is largely a matter of how it is measured

24 October 2026. Confirmation run on the 46 confirmation models, under `PROTOCOL.md` (Freeze 1, 05:37 UTC on 23 October) with the scoring scripts frozen before any outcome was read (Freeze 2, 05:41 UTC) and two amendments made before Freeze 2 (`AMENDMENTS.md`). Every number below comes from `results/confirmation/scores/` and is checked by `check_report.py`. An independent recheck, written from the protocol's definitions with the standard library only and without the scoring code, recomputed the controls, H1, H2–H5 and the primary category counts from the raw records and matched them all (`recheck/RECHECK.md`); it did not cover the replication check, the δ sensitivity, half strength, the secondary readouts or the re-scoring of P7's table.

## 1. Question

In the FlyVis models (Lappalainen et al. 2024), silencing any one of T5's four OFF inputs (Tm1, Tm2, Tm4, Tm9) has been reported to leave T5's OFF responses unchanged (P7; Ryan's Paper 11), whereas flies lose OFF responses (Serbe et al. 2016; Braun, Borst and Meier 2023). The development pilot (`PILOT-NOTES.md`) found that P7's measurement, silencing switched on at stimulus onset and read from raw rectified peaks, fails a basic control. BM2 asked whether a measurement that passes it (silencing held from rest, the central T5's evoked response at its preferred direction) changes the result, and, where T5 is still robust, which of four causes accounts for it.

## 2. What was done

Each Tm type, and all four together, was silenced and, separately, had its connections onto T5 cut, its connections onto CT1's lobula compartment cut, both cut, or its direct input removed with every other input to T5 clamped to its intact trajectory (open loop). Every condition was run at full and half strength, held from rest (adapted, primary) and switched on at stimulus onset (as in P7), on two edge speeds, in all 46 models. The local GPU took about 13 minutes per model.

**Checks.** All 46 models passed the identity checks: this simulator reproduces AI-06's simulator and saved records, and the two identity conditions reproduce the intact run (worst normalised gap 8.2e-07, limit 1e-4). Whole-cell silencing at onset on P7's readout reproduces AI-06's saved confirmation effects, which are P7's input (worst relative gap 2.7e-06). No simulation gave non-finite values.

**Positive controls.** Cutting every edge into T5 abolished the evoked response in all 46 models. Halving every excitatory edge into T5 did not reduce it below 0.8 in 6 models (014, 020, 021, 028, 034, 035). As the protocol requires, these are reported and left out of H1–H5, which therefore rest on 40 models.

## 3. Primary A: the measurement (H1)

| Tm type | Reduced, P7's measurement | Reduced, corrected | Reduced only when corrected | Reduced only on P7's | One-sided p |
|---|---|---|---|---|---|
| Tm9 (primary) | 14 | 26 | 15 | 3 | 0.0038 |
| Tm1 | 13 | 32 | 20 | 1 | < 0.0001 (Holm) |
| Tm2 | 11 | 28 | 19 | 2 | 0.0002 (Holm) |
| Tm4 | 9 | 11 | 6 | 4 | 0.38 (Holm) |

Counts are of the 40 eligible models; "reduced" includes abolished.

**H1 holds.** Silencing Tm9 reduces T5's response in 26 of 40 models on the corrected measurement, against 14 on P7's (exact one-sided McNemar test, p = 0.0038). The result keeps its direction at δ = 0.1 (30 against 17, p = 0.0005) and δ = 0.3 (19 against 9, p = 0.011). Tm1 and Tm2 move the same way, more strongly. Tm4 does not: T5 stays unchanged in most models either way.

Both parts of the correction contribute. For Tm9, the evoked readout with silencing switched on at onset gives 19 reduced models, and P7's raw readout with silencing held from rest gives 16; together they give 26.

## 4. Primary B: what accounts for the effects (H2–H5)

| Pattern | Models (of 40) | 95% interval | Call |
|---|---|---|---|
| H2, opposing direct and CT1 routes, Tm1 | 0 | 0.00–0.09 | refuted as the general cause |
| H2, Tm9 | 5 | 0.04–0.27 | refuted as the general cause |
| H3, compensation through T5's feedback, Tm1 / Tm2 / Tm4 / Tm9 | 4 / 0 / 2 / 2 | all upper bounds ≤ 0.24 | refuted as the general cause |
| H4, other routes from the Tm cell, Tm1 | 30 | 0.59–0.87 | holds in most models |
| H4, Tm2 | 23 | 0.41–0.73 | mixed |
| H4, Tm4 | 14 | 0.21–0.52 | mixed |
| H4, Tm9 | 8 | 0.09–0.36 | refuted as the general cause |
| H5, redundancy among the four | 2 | 0.01–0.17 | refuted as the general cause |

(Holm-adjusted exact binomial tests against one half, across the 11 calls.)

- **Tm9 acts through its direct connections.** Cutting only Tm9's edges onto T5 reduces T5 in 24 of 40 models, close to the 26 for silencing, and silencing differs from cutting both routes by more than 0.2 in only 8.
- **Tm1 acts mostly through other routes.** Silencing Tm1 reduces T5 in 32 models, but cutting its edges onto T5 does so in only 12, and cutting its edges onto both T5 and CT1 in 10. In 30 models silencing and the two cuts differ by more than 0.2. Which routes carry the effect was not tested.
- **The candidate explanations for robustness do not hold generally.** Opposing routes (H2), feedback compensation (H3) and redundancy (H5) each hold in at most 5 of 40 models. Removing all four Tm inputs to T5 at once reduces T5 in 40 of 40 models, but so do most single inputs once measured properly; the four are not redundant in the sense Ryan's Paper 11 proposed.

## 5. Secondary, post hoc: P7's fly table re-scored

P7's frozen table was re-scored with P7's own rules and ensemble (Section 8 of the protocol), on the 12 amplitude rows whose model counterpart is OFF only; all 12 are Serbe et al.'s tangential-cell results, and all are "reduced" in the flies. With P7's measurement, the script reproduces P7's saved category for 12 of 12 rows. The ensemble agrees with the flies on 0 of 12 rows with P7's measurement and on 9 of 12 with the corrected one. The three rows that still disagree are Tm4's, which stay unchanged (ensemble medians 0.93, 0.96 and 0.96). Cohen's κ is 0 for both, because every fly category in these rows is the same; the agreement counts carry the information. This analysis uses all 46 models, including the 6 that failed a control, because the frozen script for it applies only the replication rule.

## 6. Secondary results

- **Half strength:** silencing Tm9 reduces T5 in 18 of 40 models, Tm1 in 28 and Tm4 in 3.
- **Other readouts:** on the opponent tangential-cell-like contrast, H4 holds in most models for Tm1 (30 of 39) and Tm2 (28 of 39); H2, H3 and H5 are refuted as general causes on every readout and in both application modes.
- **Runaway values:** ratios above 100 occur only in the control that silences every type presynaptic to T5, in 3 models (014, 015, 034).

## 7. Reading

The OFF-pathway mismatch that P7 reported, models unchanged where flies are reduced, is for Tm1, Tm2 and Tm9 mostly a property of the measurement. P7's raw rectified peaks track where T5's voltage sits rather than how far the stimulus moves it, and switching silencing on at onset lets T5 drift inside the response window. Measured as fly recordings measure it, the change from baseline under chronic silencing, most models lose T5's OFF response when Tm1, Tm2 or Tm9 is silenced, as flies do. Tm4 remains a genuine miss. Tm1 now reduces T5 in most models, whereas Braun et al. report Tm1 silencing leaves T5 itself unchanged; that difference is not scored here. The mechanisms differ by input: Tm9 through its direct connections, Tm1 through routes outside its direct and CT1 connections.

## 8. Limits

- The corrected measurement and the application mode were chosen on the four development models (disclosed in the protocol); the 46 confirmation models were not seen before the freeze.
- 6 of 46 models failed the halved-excitation control and are outside H1–H5.
- The re-scoring of P7's table is post hoc and rests on 12 rows from one paper. P7's ON-pathway rows, and rows reporting both polarities, were not re-scored, because BM2 measures no T4.
- "Other routes" (H4) is a residual: it says the effect does not travel through the Tm cell's direct and CT1 connections, not which connections carry it.
- The fly comparison is categorical. Model voltages and fly calcium or voltage are compared only as reduced, unchanged or increased.

## 9. Departures and interruptions, all dated

- **Amendments 1 and 2** (before Freeze 2, from the self-test on development records): a relative replication gap; the same subtypes and OFF-only rows in the P7 re-score.
- **Interruptions:** the local machine shut down at 16:32 UTC on 23 October after 42 models; the run resumed at 17:42 UTC, was paused at the author's request at about 17:50 UTC for other GPU work, and resumed at 18:25 UTC. Saved records were kept; nothing was re-run because of its result. The run finished at 19:34 UTC.

## 10. Files

`PROTOCOL.md`, `AUTHOR-APPROVAL.txt`, `AMENDMENTS.md`, `FREEZE-1.json`, `FREEZE-2.json`; raw records in `results/confirmation/` (adapted and onset); scores in `results/confirmation/scores/SCORES.json`, `PER-MODEL.csv`, `PRIMARY-TABLE.csv` and `P7-TABLE-RESCORE.json`; development pilot in `results/pilot/`, `results/pilot-v1/` and `PILOT-NOTES.md`; independent recheck in `recheck/`.
