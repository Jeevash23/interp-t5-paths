"""BM2 freezes (PROTOCOL.md, Section 10): SHA-256 digests of the frozen files.

  python3 -I freeze.py 1          write FREEZE-1.json (before any confirmation model is loaded)
  python3 -I freeze.py 2          write FREEZE-2.json (scoring scripts, before any confirmation outcome is read)
  python3 -I freeze.py check      every file in both freezes must still match
"""
import hashlib
import json
import sys
import time
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
AI06 = STUDY / "reference/flyvis-first-order"  # release: the reference study's files
P7 = STUDY / "reference/model-vs-fly"  # release: P7's files
sys.path.insert(0, str(STUDY / "tools"))
import release_paths as _release_paths  # noqa: E402  (release: documented changes pass the checks)
SETS = {
    "1": [STUDY / f for f in ("PROTOCOL.md", "AUTHOR-APPROVAL.txt", "SCOOP-CHECK.md", "PILOT-NOTES.md",
                              "code/simulate.py", "code/run.sh", "code/simulate-vs-pilot.diff", "code/pilot_simulate.py",
                              "code/pilot_run.sh", "code/pilot_analyse.py", "code/check_notes.py", "code/inspect_wiring.py",
                              "code/freeze.py", "results/pilot/PILOT-REPORT-adapted.md",
                              "results/pilot/PILOT-REPORT-onset.md", "results/pilot/PILOT-TABLE-adapted.csv",
                              "results/pilot/PILOT-TABLE-onset.csv", "results/pilot/pilot-run.json")]
    + [AI06 / f for f in ("02-Code/stage1/core.py", "02-Code/stage1/common.py", "study/code/revision_common.py",
                          "study/config.json", "03-Data/stage1/model-selection.json",
                          "03-Data/stage1/stimulus-manifest.json")],
    "2": [STUDY / f for f in ("code/score.py", "code/score_p7_table.py")]
    + [P7 / f for f in ("code/common.py", "config.json", "extraction/merged-table.csv",
                        "results/development/settings.json")],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(STUDY.parents[1].resolve())) if not path.is_relative_to(STUDY) \
        else str(path.relative_to(STUDY))


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which in SETS:
        out = STUDY / f"FREEZE-{which}.json"
        if out.exists():
            sys.exit(f"{out.name} exists; freezes are written once")
        record = {"freeze": which, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "files": {rel(p): sha256(p) for p in SETS[which]}}
        out.write_text(json.dumps(record, indent=1) + "\n")
        print(f"{out.name}: {len(record['files'])} files, {record['utc']}; sha256 {sha256(out)}")
    elif which == "check":
        bad = []
        for n in SETS:
            path = STUDY / f"FREEZE-{n}.json"
            if not path.exists():
                continue
            for name, digest in json.loads(path.read_text())["files"].items():
                p = STUDY / name  # release: the keys name the copies under reference/
                if not _release_paths.matches(p, digest, name):
                    bad.append(name)
            print(f"{path.name}: checked")
        if bad:
            sys.exit(f"changed since the freeze: {bad}")
        print("all frozen files match")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
