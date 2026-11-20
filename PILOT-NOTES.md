# BM2 development pilot: what it shows (22–23 October 2026)

**Development models only (000, 001, 004, 005); exploratory; not a test.** The full tables are written by `code/pilot_analyse.py` in `results/pilot/PILOT-REPORT-adapted.md` and `PILOT-REPORT-onset.md`. Every number below appears in those reports; `code/check_notes.py` checks this. Values are ratios of the silenced or cut response to the intact one, averaged over the two speeds and over T5a–d.

## What was run

Each Tm type (Tm1, Tm2, Tm4, Tm9) and all four together, at full and half strength, five ways: silence the cell; cut only its edges onto T5; cut only its edges onto CT1(Lo1); both cuts; open loop (every non-T5 cell that feeds T5 clamped to its intact trajectory, direct edges cut). Each condition was applied two ways: at stimulus onset, as P7 and AI-06 silence ("onset"), and held from rest so the network settles before the stimulus ("adapted", closer to chronic genetic silencing). Plus three positive controls and two identity checks, on both stimulus speeds. Local machine GPU, about 13 minutes per model; $0; no downloads.

## Checks

- This code reproduces AI-06's simulator and saved baseline records, and both identity conditions reproduce the intact run (worst normalised gap 3.2e-07 against a limit of 1e-4).
- Whole-cell silencing at onset, read with P7's pooled ratio, reproduces AI-06's saved development effects, which are P7's input (worst absolute gap 1.4e-07 over 40 values).
- The second version's onset mode reproduces the first version (440 records, worst normalised peak gap 3.6e-07).
- Write audit: 0 files changed under AI-06.

## 1. The raw-peak readouts fail the basic positive control

Cutting every edge into T5 should abolish its response. On the evoked readout under adapted application it does, in all four models (0.00). On the raw-peak readouts it does not: P7's pooled ratio becomes 2.43, 1.53, 423.49 and 3.07 in models 000, 001, 004 and 005. With no input, T5 sits at its resting bias, and that level is above the peaks it reaches in the intact network. The raw peaks measure where T5's voltage is, not how much the stimulus moves it. Calcium and voltage recordings in flies report the change from baseline, which the evoked readout follows.

Halving every excitatory edge into T5 reduces the evoked response in all four models (0.36, 0.49, 0.54, 0.69), so the evoked readout registers a known reduction too.

Switching the condition on at stimulus onset adds a second problem: T5 drifts towards its new resting level inside the response window. In model 004, silencing Tm1 reads 4.66 on the evoked readout at onset and 0.51 when adapted.

## 2. Measured properly, T5 is not uniformly robust

Whole-cell silencing at full strength (table "P7's measurement against the adapted, evoked one" in the adapted report):
- **Model 000, Tm9:** P7's measurement gives 0.83 (unchanged); adapted and evoked gives 0.16 (reduced), which is the direction flies show.
- **Model 004, Tm1:** P7's measurement gives 385.85 (a runaway rise of the resting level); adapted and evoked gives 0.51 (reduced).
- **Elsewhere the two agree or both say unchanged**, and some models still show rises that flies do not (model 001: Tm2 1.60, Tm9 1.27).

So part of the models' apparent robustness may come from the measurement, not the models. Four models cannot say how much; the 46 confirmation models can.

## 3. The causes differ from model to model (adapted, evoked readout, full strength)

- **000, two opposing routes from Tm9.** Cutting Tm9's direct edges onto T5 nearly abolishes the response (0.09); cutting its edges onto CT1 raises it (1.41); both cuts together (0.20) match silencing (0.16).
- **001, compensation through T5's own feedback.** With the rest of the network clamped (open loop), removing Tm9's direct input drops T5 to 0.45, against 0.88 with the network free. For all four Tm types the figures are 0.32 and 0.63.
- **004, a strong direct Tm1 input.** The direct cut alone (0.55) matches silencing (0.51). Tm2 acts through other routes: silencing it gives 0.47 while cutting its T5 and CT1 edges leaves T5 at 1.04.
- **005, Tm9 through CT1.** Cutting Tm9's edges onto CT1 lowers the evoked response (0.64) about as much as silencing (0.60), mainly because T5's resting level rises.

No model shows the clean redundancy pattern (all four together collapse T5 while every single silencing leaves it unchanged).

## What this means for the protocol

- The primary readout should be the evoked one, with conditions held from rest. The raw-peak readouts stay as secondary, for continuity with P7 and Ryan's Paper 11. These choices were made on the development models, which is what they are for; the protocol says so.
- The hypotheses are revised to keep four questions apart: opposing direct and CT1 routes; compensation through T5's feedback; other routes from the Tm cell; redundancy. A fifth question is now central: whether P7's measurement and the corrected one give different categories in the confirmation models.
- Results must be reported per model; an ensemble median would hide four different mechanisms.

## For the author

This bears on P7, which is frozen and was not touched. P7 used the onset application and the raw-peak pooled ratio, both inherited from AI-06. In two of the four development models, a corrected measurement moves a T5 result from "unchanged" or a runaway rise to "reduced". Whether this changes P7's confirmation results is unknown until the 46 models are run. If it does, it affects P7's OFF-pathway conclusion and the comparison with Ryan's Paper 11, which reads the central T5's peak (whether raw or measured from baseline has not been checked). AI-06 and P6 use the same raw-peak convention; whether it matters there has not been checked.
