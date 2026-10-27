"""Day 7 experiment helper: run the readers once per dev picture and keep the words (git-ignored cache) so matching ideas can be tried offline.
    .venv/bin/python tools/cache_passes.py --set testset --type chat [--shard i/n]"""
import argparse
import json
import pickle
from pathlib import Path

from PIL import Image

from picture_guard import ocr

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--set", default="testset")
ap.add_argument("--type", default=None)
ap.add_argument("--shard", default="0/1")
a = ap.parse_args()
i, n = (int(x) for x in a.shard.split("/"))
key = json.loads((ROOT / a.set / "key.json").read_text())
ents = [e for e in key["images"] if e["split"] == "dev" and (a.type is None or e["type"] == a.type)]
out = ROOT / "results" / "pg10" / "debug" / f"passes-{a.set}"
out.mkdir(parents=True, exist_ok=True)
for k, e in enumerate(ents):
    if k % n != i:
        continue
    f = out / f"{e['file']}.pkl"
    if f.exists():
        continue
    im = Image.open(ROOT / a.set / "images" / e["file"]).convert("RGB")
    passes = ocr.read_passes(im, cleanups=ocr.DEFAULT_CLEANUPS + ("dig",))
    pickle.dump({p: [(w.text, w.conf, w.box, w.line) for w in ws] for p, ws in passes.items()}, open(f, "wb"))
