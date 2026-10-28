"""Public-repo hygiene: remove private paths and planted test values from tracked text files (results, logs, spike outputs).
Replaces the home-directory path with '.', and any planted personal value from the test keys with '[made-up value]'.
Dry run by default; pass --apply to write. The keys themselves (testset/faces/faces_hard key.json) are left alone."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = {".md", ".json", ".txt", ".jsonl", ".log"}
KEYS = ("testset/key.json", "faces/key.json", "faces_hard/key.json")
values = set()
for k in KEYS:
    for e in json.loads((ROOT / k).read_text())["images"]:
        for s in e["spans"]:
            if s["kind"] == "personal" and s["pii_type"] != "face" and len(s["text"]) >= 8:
                values.add(s["text"])
files = [ROOT / f for f in subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
         if f and (ROOT / f).suffix in TEXT and not f.endswith(KEYS) and not f.startswith("tests/") and (ROOT / f).exists()]
apply = "--apply" in sys.argv
pat = re.compile("|".join(re.escape(v) for v in sorted(values, key=len, reverse=True)), re.I)
n_paths = n_vals = changed = 0
for f in files:
    t = f.read_text(errors="ignore")
    new = re.sub(r"/home/[A-Za-z0-9_.-]+/Projects/active/picture-guard", ".", t)
    new = re.sub(r"/home/[A-Za-z0-9_.-]+/", "~/", new)
    new = new.replace("Documents/Projects/private-project", "(events folder)")
    n_paths += t != new
    new2 = pat.sub("[made-up value]", new)
    n_vals += new2 != new
    if new2 != t:
        changed += 1
        if apply:
            f.write_text(new2)
print(f"{len(files)} files; paths scrubbed in {n_paths}; planted values scrubbed in {n_vals}; changed {changed}{'' if apply else ' (dry run)'}")
