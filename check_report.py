"""Check every number in REPORT.md against the saved outputs (standard library only).

  python3 -I check_report.py

Each check recomputes a value from results/confirmation/ and asserts that the exact text the report prints for it
appears in REPORT.md. It also lists any number in the report that no check covers.
"""
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent
SC = STUDY / "results/confirmation/scores"
report = (STUDY / "REPORT.md").read_text()
s = json.loads((SC / "SCORES.json").read_text())
p7 = json.loads((SC / "P7-TABLE-RESCORE.json").read_text())
run = json.loads((STUDY / "results/confirmation/confirmation-run.json").read_text())
cc = s["category_counts"]
checks, failures, covered = [], [], set()


def red(key):
    c = cc[key]
    return c["abolished"] + c["reduced"]


def expect(text, value, label):
    checks.append(label)
    if str(value) != text:
        failures.append(f"{label}: computed {value!r}, report text {text!r}")
    elif text not in report:
        failures.append(f"{label}: {text!r} not found in REPORT.md")
    covered.add(text)


def p(x):
    return "< 0.0001" if x < 0.0001 else f"{x:.4f}" if x < 0.01 else f"{x:.3f}" if x < 0.1 else f"{x:.2f}"


# Counts and checks.
expect("46", len(run["models"]), "models run")
expect("40", s["n_eligible"], "eligible")
expect("6", len(s["control_fail"]), "control failures")
expect("014, 020, 021, 028, 034, 035", ", ".join(s["control_fail"]), "control-failure models")
worst = max(v for r in run["models"].values() for c in r["checks"].values() for v in c.values())
expect("8.2e-07", f"{worst:.1e}", "worst identity gap")
expect("2.7e-06", f"{max(c['replication_worst'] for c in s['controls'].values()):.1e}", "worst replication gap")
expect("46", sum(c["cut_all_pass"] for c in s["controls"].values()), "cut-all control passes")
expect("0", len(s["nonfinite_records"]), "non-finite records")
# H1 table.
h1 = s["H1"]["delta_0.2"]
for tm in ("Tm9", "Tm1", "Tm2", "Tm4"):
    row = h1[tm]
    pv = p(row["p_one_sided"]) if tm == "Tm9" else p(row["p_holm_secondary"])
    pv_text = pv if tm == "Tm9" else f"{pv} (Holm)"
    line = (f"| {tm}{' (primary)' if tm == 'Tm9' else ''} | {row['reduced_p7']} | {row['reduced_corrected']} | "
            f"{row['corrected_only']} | {row['p7_only']} | {pv_text} |")
    expect(line, line, f"H1 row {tm}")
    if line not in report:
        failures.append(f"H1 row {tm}: {line!r} not in report")
expect("p = 0.0038", f"p = {p(h1['Tm9']['p_one_sided'])}", "H1 p")
for d, text in (("0.1", "30 against 17, p = 0.0005"), ("0.3", "19 against 9, p = 0.011")):
    r = s["H1"][f"delta_{d}"]["Tm9"]
    expect(text, f"{r['reduced_corrected']} against {r['reduced_p7']}, p = {p(r['p_one_sided'])}", f"H1 delta {d}")
expect("19", red("onset|s100-silence-Tm9|pd_evoked"), "onset evoked Tm9")
expect("16", red("adapted|s100-silence-Tm9|pooled"), "adapted raw Tm9")
# H2-H5 table.
hh = s["H2_H5"]["delta_0.2"]


def ci(name):
    a, b = hh[name]["ci95"]
    return f"{a:.2f}–{b:.2f}"


for name, label in (("H2-Tm1", "H2, opposing direct and CT1 routes, Tm1"), ("H2-Tm9", "H2, Tm9"),
                    ("H4-Tm1", "H4, other routes from the Tm cell, Tm1"), ("H4-Tm2", "H4, Tm2"),
                    ("H4-Tm4", "H4, Tm4"), ("H4-Tm9", "H4, Tm9"), ("H5", "H5, redundancy among the four")):
    line = f"| {label} | {hh[name]['holds']} | {ci(name)} | {hh[name]['call']} |"
    expect(line, line, f"row {name}")
    if line not in report:
        failures.append(f"row {name}: {line!r} not in report")
h3 = " / ".join(str(hh[f"H3-{t}"]["holds"]) for t in ("Tm1", "Tm2", "Tm4", "Tm9"))
expect("4 / 0 / 2 / 2", h3, "H3 counts")
expect("0.24", f"{max(hh[f'H3-{t}']['ci95'][1] for t in ('Tm1', 'Tm2', 'Tm4', 'Tm9')):.2f}", "H3 upper bound")
assert all(hh[f"H3-{t}"]["call"] == "refuted as the general cause" for t in ("Tm1", "Tm2", "Tm4", "Tm9"))
# Mechanism sentences.
expect("24", red("adapted|s100-cutT5-Tm9|pd_evoked"), "Tm9 direct cut")
expect("26", red("adapted|s100-silence-Tm9|pd_evoked"), "Tm9 silence")
expect("8", hh["H4-Tm9"]["holds"], "H4 Tm9")
expect("32", red("adapted|s100-silence-Tm1|pd_evoked"), "Tm1 silence")
expect("12", red("adapted|s100-cutT5-Tm1|pd_evoked"), "Tm1 direct cut")
expect("10", red("adapted|s100-cutT5+CT1-Tm1|pd_evoked"), "Tm1 both cuts")
expect("30", hh["H4-Tm1"]["holds"], "H4 Tm1")
expect("5", max(hh[n]["holds"] for n in hh if not n.startswith("H4")), "most for H2/H3/H5")
expect("40 of 40", f"{red('adapted|s100-cutT5-quad|pd_evoked')} of {s['n_eligible']}", "quad direct cut")
# P7 re-score.
expect("12", p7["n_rows"], "re-score rows")
expect("12 of 12", f"{p7['p7_reproduction']['same_category_as_p7_saved']} of {p7['p7_reproduction']['rows']}",
       "reproduction")
assert all(r["experiment"] == "reduced" and r["source"].startswith("Serbe") for r in p7["rows"])
expect("0 of 12", f"{p7['p7_measurement']['agree']} of {p7['n_rows']}", "P7 agreement")
expect("9 of 12", f"{p7['corrected']['agree']} of {p7['n_rows']}", "corrected agreement")
still = [r for r in p7["rows"] if r["corrected"] != r["experiment"]]
assert {r["cell"] for r in still} == {"Tm4"} and all(r["corrected"] == "unchanged" for r in still)
expect("0.93, 0.96 and 0.96", ", ".join(f"{r['corrected_median']:.2f}" for r in still[:2]) + f" and "
       f"{still[2]['corrected_median']:.2f}", "Tm4 medians")
assert p7["p7_measurement"]["kappa"] == 0 and p7["corrected"]["kappa"] == 0
expect("46", p7["n_models"], "re-score models")
# Secondary.
expect("18", red("adapted|s050-silence-Tm9|pd_evoked"), "half Tm9")
expect("28", red("adapted|s050-silence-Tm1|pd_evoked"), "half Tm1")
expect("3", red("adapted|s050-silence-Tm4|pd_evoked"), "half Tm4")
lp = s["secondary_patterns"]["adapted|s100|lptc"]
expect("30 of 39", f"{lp['H4-Tm1']['holds']} of {lp['H4-Tm1']['n']}", "lptc H4 Tm1")
expect("28 of 39", f"{lp['H4-Tm2']['holds']} of {lp['H4-Tm2']['n']}", "lptc H4 Tm2")
assert lp["H4-Tm1"]["call"] == lp["H4-Tm2"]["call"] == "holds in most models"
bad = [(k, n) for k, v in s["secondary_patterns"].items() for n, o in v.items()
       if n.split("-")[0] in ("H2", "H3", "H5") and o["call"] != "refuted as the general cause"]
if bad:
    failures.append(f"'H2, H3 and H5 refuted on every readout and mode' is false for {bad}")
runaway = s["runaway_over_100"]
assert all("pc-silence-T5-presyn" in r for r in runaway)
expect("014, 015, 034", ", ".join(sorted({r.split("|")[0] for r in runaway})), "runaway models")
expect("3", len({r.split("|")[0] for r in runaway}), "runaway model count")
expect("19:34", run["finished_utc"][11:16], "finish time")

# Numbers in the report that no check covers (structural ones are listed for a reader to judge).
nums = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?:e-?\d+)?(?![\w])", report))
inside = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?:e-?\d+)?(?![\w])", " ".join(covered)))
print(f"{len(checks)} checks; {len(failures)} failures")
print("numbers not covered by a check (dates, times, settings, section numbers):",
      ", ".join(sorted(nums - inside, key=lambda x: float(x))))
if failures:
    print("\n".join(failures))
    sys.exit(1)
