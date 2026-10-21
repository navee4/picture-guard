"""Merge the first run (images_meta_run1.json: specs 0-233) and the light-skin top-up (images_meta_extra.json: specs 234-273)
into images_meta.json. Run once after the top-up:  python faces_hard/merge_meta.py"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
a = json.loads((H / "images_meta_run1.json").read_text())
b = json.loads((H / "images_meta_extra.json").read_text())
assert a["yunet_sha256"] == b["yunet_sha256"] and a["model"] == b["model"]
a["specs"] = a["specs"] + b["specs"]
a["items"] = sorted(a["items"] + b["items"], key=lambda d: d["index"])
a["note"] = "merged: run 1 = specs 0-233, top-up = specs 234-273 (light and medium skin words, added after the first skin-tone measurement)"
(H / "images_meta.json").write_text(json.dumps(a, indent=1))
print(len(a["specs"]), "specs,", len(a["items"]), "items")
