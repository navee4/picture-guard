"""Self-check for the harder face set. Fails loudly (non-zero exit) on any miss.

    python faces_hard/check.py     # needs faces_hard/images, faces_hard/images_raw, faces_hard/key.json

Proves: 80 pictures, 20 per type, 60 dev / 20 hold-out (15 / 5 per type); face counts per type (1, 1, 2-5, 1-4); every face box inside its
picture, at least 8 px a side, and no two face boxes in one picture overlap; every picture has a label span; every face has a measured
skin tone; the dark bucket holds at least a quarter of all faces; file and source SHA-256 match the key; two fresh composes give
identical SHA-256 and equal the key; face regions are not blank.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate import SEED, build, encode  # noqa: E402

errors = []
key = json.loads((HERE / "key.json").read_text())
E = key["images"]
c = Counter((e["type"], e["split"]) for e in E)
for t in ("side_view", "accessory", "group", "scene"):
    if c[(t, "dev")] != 15 or c[(t, "holdout")] != 5:
        errors.append(f"{t}: dev/holdout {c[(t, 'dev')]}/{c[(t, 'holdout')]} != 15/5")
if len(E) != 80 or sum(e["split"] == "dev" for e in E) != 60:
    errors.append("need 80 pictures, 60 dev")
allfaces = []
for e in E:
    p = HERE / "images" / e["file"]
    if hashlib.sha256(p.read_bytes()).hexdigest() != key["sha256"][e["file"]]:
        errors.append(f"{e['file']}: file differs from key SHA-256")
    im = Image.open(p)
    if im.size != (e["width"], e["height"]):
        errors.append(f"{e['file']}: size {im.size} != key")
    faces = [s for s in e["spans"] if s["pii_type"] == "face"]
    lo, hi = {"side_view": (1, 1), "accessory": (1, 1), "group": (2, 5), "scene": (1, 4)}[e["type"]]
    if not lo <= len(faces) <= hi:
        errors.append(f"{e['file']}: {len(faces)} faces, expected {lo}-{hi}")
    if not any(s["text"] == "SYNTHETIC TEST DATA" for s in e["spans"]):
        errors.append(f"{e['file']}: no label span")
    a = np.asarray(im.convert("L"), dtype=float)
    for i, s in enumerate(faces):
        x0, y0, x1, y1 = s["box"]
        if not (0 <= x0 < x1 <= e["width"] and 0 <= y0 < y1 <= e["height"]):
            errors.append(f"{e['file']}: box {s['box']} outside picture"); continue
        if min(x1 - x0, y1 - y0) < 8:
            errors.append(f"{e['file']}: face box under 8 px {s['box']}")
        if a[y0:y1, x0:x1].std() < 4:
            errors.append(f"{e['file']}: face region looks blank {s['box']}")
        if s.get("ita") is None or s.get("skin_bucket") not in ("light", "medium", "dark"):
            errors.append(f"{e['file']}: face without measured skin tone")
        for o in faces[i + 1:]:
            if not (x1 <= o["box"][0] or o["box"][2] <= x0 or y1 <= o["box"][1] or o["box"][3] <= y0):
                errors.append(f"{e['file']}: two face boxes overlap")
        allfaces.append(s)
bk = Counter(f["skin_bucket"] for f in allfaces)
if bk["dark"] < 0.25 * len(allfaces):
    errors.append(f"dark bucket {bk['dark']} of {len(allfaces)} is under a quarter")
for name, sha in key["source_sha256"].items():
    if hashlib.sha256((HERE / "images_raw" / name).read_bytes()).hexdigest() != sha:
        errors.append(f"{name}: source image differs from key")
meta = json.loads((HERE / "images_meta.json").read_text())
skin = json.loads((HERE / "skin.json").read_text())
runs = []
for _ in range(2):
    runs.append({n: hashlib.sha256(encode(img, fmt, q)).hexdigest() for n, img, fmt, q, _e in build(SEED, meta=meta, skin=skin)})
if runs[0] != runs[1]:
    errors.append("two composes differ")
if runs[0] != key["sha256"]:
    errors.append("fresh compose differs from key")
print(f"{len(E)} pictures, counts {dict(c)}, faces {len(allfaces)}, measured skin buckets {dict(bk)}")
if errors:
    print("FAILED:\n" + "\n".join(errors[:40])); sys.exit(1)
print("OK: all checks passed")
