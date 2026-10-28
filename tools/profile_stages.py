"""Mean seconds per stage on 20 dev pictures (5 per type), replay of saved model answers (the GPU wait is NOT included: replay answers at once).
Usage: [PG_OCR_WORKERS=1] python tools/profile_stages.py  -> prints one JSON line"""
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from picture_guard.evaluate import SETS, _replay_guard
from picture_guard.pipeline import protect

base = SETS["testset"]
key = json.loads((base / "key.json").read_text())
entries = []
for t in ("payslip", "letter", "id_card", "chat"):
    entries += [e for e in key["images"] if e["split"] == "dev" and e["type"] == t][:5]
sc = Path(tempfile.mkdtemp())
(sc / "debug").mkdir()
src = Path("results/pg11/final/debug/boxes-testset.jsonl")
(sc / "debug" / src.name).write_text(src.read_text())
guard = _replay_guard("testset", entries, base, sc, "profile")
guard.offline = True
acc, tot = defaultdict(float), 0.0
with guard as g:
    for e in entries:
        r = protect(base / "images" / e["file"], sc / "s.png", sc / "r.json", guard=g, options={"fallback": "zoom"})
        for s in r["stages"]:
            acc[s["name"]] += s["seconds"]
        tot += r["total_seconds"]
n = len(entries)
print(json.dumps({"workers": __import__("os").environ.get("PG_OCR_WORKERS", "auto"), "pictures": n, "mean_total": round(tot / n, 2), **{k: round(v / n, 2) for k, v in acc.items() if v / n >= 0.005}}))
