"""Self-check for the face set. Fails loudly (non-zero exit) on any miss.

    python faces/check.py      # needs faces/images, faces/portraits, faces/key.json

Proves: counts by type/split; every face box inside its picture and >= 12 px; a label span per picture;
the files on disk match the key's SHA-256; the portraits match the key's SHA-256; two fresh composes
from the portraits give identical SHA-256 and equal the key; the face region is not blank.
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
want = {("id_card", "dev"): 37, ("id_card", "holdout"): 13, ("chat", "dev"): 18, ("chat", "holdout"): 7}
if dict(c) != want:
    errors.append(f"counts {dict(c)} != {want}")
if len(E) != 75 or sum(e["split"] == "dev" for e in E) != 55:
    errors.append("need 75 pictures, 55 dev")
for e in E:
    p = HERE / "images" / e["file"]
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() != key["sha256"][e["file"]]:
        errors.append(f"{e['file']}: file differs from key SHA-256")
    im = Image.open(p)
    if im.size != (e["width"], e["height"]):
        errors.append(f"{e['file']}: size {im.size} != key")
    faces = [s for s in e["spans"] if s["pii_type"] == "face"]
    if not faces:
        errors.append(f"{e['file']}: no face span")
    if not any(s["text"] == "SYNTHETIC TEST DATA" for s in e["spans"]):
        errors.append(f"{e['file']}: no label span")
    a = np.asarray(im.convert("L"), dtype=float)
    for s in e["spans"]:
        x0, y0, x1, y1 = s["box"]
        if not (0 <= x0 < x1 <= e["width"] and 0 <= y0 < y1 <= e["height"]):
            errors.append(f"{e['file']}: box {s['box']} outside picture"); continue
        if s["pii_type"] == "face":
            if min(x1 - x0, y1 - y0) < 12:
                errors.append(f"{e['file']}: face box under 12 px {s['box']}")
            if a[y0:y1, x0:x1].std() < 8:
                errors.append(f"{e['file']}: face region looks blank")
    if e["type"] == "chat" and len(faces) < 2:
        errors.append(f"{e['file']}: chat picture needs several faces, has {len(faces)}")
for name, sha in key["portrait_sha256"].items():
    if hashlib.sha256((HERE / "portraits" / name).read_bytes()).hexdigest() != sha:
        errors.append(f"{name}: portrait differs from key")
meta = json.loads((HERE / "portraits_meta.json").read_text())
runs = []
for _ in range(2):
    runs.append({n: hashlib.sha256(encode(img, fmt, q)).hexdigest() for n, img, fmt, q, _e in build(SEED, meta=meta)})
if runs[0] != runs[1]:
    errors.append("two composes differ")
if runs[0] != key["sha256"]:
    errors.append("fresh compose differs from key")
print(f"{len(E)} pictures, counts {dict(c)}, faces {sum(len([s for s in e['spans'] if s['pii_type']=='face']) for e in E)}")
if errors:
    print("FAILED:\n" + "\n".join(errors[:40])); sys.exit(1)
print("OK: all checks passed")
