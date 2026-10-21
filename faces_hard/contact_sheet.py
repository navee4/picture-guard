"""Contact sheet of 16 faces from the PG-3 set (seeded pick), each labelled with its prompt words AND its measured skin tone.

    python faces_hard/contact_sheet.py OUT.png
4 side views, 4 accessories, 8 from groups/scenes (source portraits used in the set); measured buckets rotated dark/medium/light.
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

H = Path(__file__).resolve().parent
key = json.loads((H / "key.json").read_text())
meta = json.loads((H / "images_meta.json").read_text())
items = {i["index"]: i for i in meta["items"]}
faces = {}
for e in key["images"]:
    for s in e["spans"]:
        if s["pii_type"] == "face":
            faces[s["portrait_index"]] = (e["type"], s)
rng = random.Random(20261022)
chosen = []
for types, n in ((("side_view",), 4), (("accessory",), 4), (("group", "scene"), 8)):
    pool = sorted(i for i, (t, s) in faces.items() if t in types)
    rng.shuffle(pool)
    want = ["dark", "medium", "light", "dark", "medium", "light", "dark", "medium"][:n]
    for b in want:
        c = next((i for i in pool if faces[i][1]["skin_bucket"] == b and i not in chosen), None) or next(i for i in pool if i not in chosen)
        chosen.append(c)
W, LH = 330, 84
sheet = Image.new("RGB", (W * 4, (W + LH) * 4), "white")
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
for k, i in enumerate(chosen):
    t, s = faces[i]
    im = Image.open(H / "images_raw" / f"i{i:03d}.png").convert("RGB")
    x0, y0, x1, y1 = items[i]["face_box"]
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 0.75
    L, T = min(max(0, cx - r), im.width - 2 * r), min(max(0, cy - r), im.height - 2 * r)
    im = im.crop((int(L), int(T), int(L + 2 * r), int(T + 2 * r))).resize((W, W))
    x, y = (k % 4) * W, (k // 4) * (W + LH)
    sheet.paste(im, (x, y))
    pw = s["prompt_words"]
    d.text((x + 6, y + W + 3), f"#{k + 1} {t}: {pw['gender_word']}, {pw['age'].replace('in their ', '')}", fill="black", font=f)
    d.text((x + 6, y + W + 22), f"prompt: {s['prompt_skin_word']}", fill="black", font=f)
    d.text((x + 6, y + W + 41), f"MEASURED: {s['skin_bucket']} (ITA {s['ita']}, {s['skin_chardon']})", fill=(170, 0, 0), font=f)
    d.text((x + 6, y + W + 60), pw["view_or_accessory"][:46], fill=(90, 90, 90), font=f)
sheet.save(sys.argv[1])
print(sys.argv[1], chosen)
