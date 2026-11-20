"""Check that every decimal number in PILOT-NOTES.md appears in the script-written pilot reports.

  python3 -I check_notes.py      (standard library only)
"""
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
notes = (STUDY / "PILOT-NOTES.md").read_text()
reports = "\n".join((STUDY / "results/pilot" / f"PILOT-REPORT-{m}.md").read_text() for m in ("adapted", "onset"))
pattern = re.compile(r"(?<![\w.])-?\d+\.\d+(?:e-?\d+)?(?!\w)(?!\.\d)")
found = set(pattern.findall(reports))
numbers = pattern.findall(notes)
missing = [n for n in numbers if n not in found]
print(f"{len(numbers)} numbers in PILOT-NOTES.md; {len(numbers) - len(missing)} found in the reports")
if missing:
    print("not found:", ", ".join(missing))
    sys.exit(1)
