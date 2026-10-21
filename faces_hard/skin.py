"""Measured skin tone (ITA angle) of each face, from the face pixels. Light numpy work, runs on the Mac.

    python faces_hard/skin.py        # writes faces_hard/skin.json for every portrait that passed the face check

Method: take the middle of the YuNet face box (middle 60% of width, rows 25% to 85% of height); keep pixels that are
skin-coloured (YCbCr: Cb 75-128, Cr 131-175), which drops hair, eyes, sunglasses and most masks and hats; convert to CIE L*a*b*
(sRGB, D65); keep the lit skin (pixels between the 60th and 90th L* percentile: the first version, a plain median, read shadowed
side-lit faces far too dark); ITA = atan2(median L* - 50, median b*) in degrees. Needs at least 150 skin pixels, else None.
Buckets (this project's, built from the usual Chardon ITA bands): light = ITA > 41, medium = 10 < ITA <= 41, dark = ITA <= 10
(the usual 'brown' and 'dark' bands together). ITA depends on the lighting as well as the skin (inferred), so it is a measure of
the pixels, not of the person the picture is meant to show.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
CHARDON = [(55, "very light"), (41, "light"), (28, "intermediate"), (10, "tan"), (-30, "brown")]


def bucket(ita):
    if ita is None:
        return None
    return "light" if ita > 41 else "medium" if ita > 10 else "dark"


def chardon(ita):
    if ita is None:
        return None
    for lim, name in CHARDON:
        if ita > lim:
            return name
    return "dark"


def _lab(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return 116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])


def ita(img, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    a = np.asarray(img.convert("RGB"))[int(y0 + 0.25 * h):int(y0 + 0.85 * h), int(x0 + 0.2 * w):int(x0 + 0.8 * w)].reshape(-1, 3).astype(float)
    if len(a) == 0:
        return {"ita": None, "n_skin_px": 0}
    r, g, b = a[:, 0], a[:, 1], a[:, 2]
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    m = (cb >= 75) & (cb <= 128) & (cr >= 131) & (cr <= 175)
    if m.sum() < 150:
        return {"ita": None, "n_skin_px": int(m.sum())}
    L, _, B = _lab(a[m])
    lo, hi = np.percentile(L, [60, 90])  # lit skin: drops shadow side, glasses frames, beard shade and bright highlights
    k = (L >= lo) & (L <= hi)
    Lm, Bm = float(np.median(L[k])), float(np.median(B[k]))
    return {"ita": round(float(np.degrees(np.arctan2(Lm - 50, Bm))), 1), "n_skin_px": int(m.sum()), "L": round(Lm, 1), "b": round(Bm, 1),
            "ita_all_skin_median": round(float(np.degrees(np.arctan2(np.median(L) - 50, np.median(B)))), 1)}


def main(meta_name="images_meta.json", out_name="skin.json"):
    meta = json.loads((HERE / meta_name).read_text())
    out = {}
    for it in meta["items"]:
        if it["kind"] == "bg" or not it["ok"]:
            continue
        r = ita(Image.open(HERE / "images_raw" / f"i{it['index']:03d}.png"), it["face_box"])
        r["bucket"], r["chardon"] = bucket(r["ita"]), chardon(r["ita"])
        out[str(it["index"])] = r
    (HERE / out_name).write_text(json.dumps(out, indent=1))
    from collections import Counter
    print(len(out), "faces;", dict(Counter(v["bucket"] for v in out.values())))
    print("by prompt word:")
    sp = {s["index"]: s for s in meta["specs"]}
    for w in sorted({s["attrs"]["skin_word"] for s in meta["specs"] if s["kind"] != "bg"}):
        c = Counter(v["bucket"] for k, v in out.items() if sp[int(k)]["attrs"]["skin_word"] == w)
        print(" ", w, dict(c))


if __name__ == "__main__":
    main()
