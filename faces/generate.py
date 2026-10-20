"""Compose the 75-picture face set from the AI portraits (faces/portraits/, made by modal_faces.py) and write faces/key.json.

    python faces/generate.py            # light CPU work only (PIL); no model runs here

50 ID-style cards (one photo-like AI face each) + 25 chat screenshots (a small round profile photo beside the
other person's messages). Split 55 dev / 20 hold-out from the seed. Face boxes come from the YuNet detector run on
the portrait, mapped through the crop and resize. Text on the pictures is made up (PG-1 value generator) and is not keyed.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "testset"))  # read-only use of PG-1 helpers (fonts, fake values)
import spec  # noqa: E402
from draw import FAMILIES, font  # noqa: E402
from values import ID_ISSUERS, NATIONALITIES, Person  # noqa: E402

SEED = spec.SEED
HOLDOUT = {"id_card": 13, "chat": 7}
RED, INK, GREY = (190, 30, 30), (25, 25, 30), (90, 90, 100)
CHAT_PLAIN = ["Running a bit late, see you at the cafe at six", "Did you get the tickets for Saturday?", "Haha that was brilliant",
              "Can you bring the blue folder tomorrow?", "Thanks so much, speak soon", "Just leaving work now",
              "What time does the film start?", "Sounds good to me", "I will call you after lunch", "Look at this photo from today"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def crop_around(face, margin, aspect, size=1024):
    """Crop box (x0,y0,x1,y1) of the portrait around the face, face fills 1/margin of the longer side, kept inside the portrait."""
    fx, fy = (face[0] + face[2]) / 2, (face[1] + face[3]) / 2
    side = max(face[2] - face[0], face[3] - face[1]) * margin
    w, h = (side * aspect, side) if aspect < 1 else (side, side / aspect)
    w, h = min(w, size), min(h, size)
    x0 = min(max(0, fx - w / 2), size - w)
    y0 = min(max(0, fy - h / 2), size - h)
    return (x0, y0, x0 + w, y0 + h)


def place_photo(portrait, face, margin, dest, circle=False):
    """Paste the cropped portrait into dest=(x0,y0,x1,y1) on the picture. Returns the face box in picture pixels (clipped to dest)."""
    pw, ph = dest[2] - dest[0], dest[3] - dest[1]
    cb = crop_around(face, margin, pw / ph)
    tile = portrait.crop(tuple(round(v) for v in cb)).resize((pw, ph), Image.LANCZOS)
    sx, sy = pw / (cb[2] - cb[0]), ph / (cb[3] - cb[1])
    box = [dest[0] + (face[0] - cb[0]) * sx, dest[1] + (face[1] - cb[1]) * sy, dest[0] + (face[2] - cb[0]) * sx, dest[1] + (face[3] - cb[1]) * sy]
    box = [max(dest[0], box[0]), max(dest[1], box[1]), min(dest[2], box[2]), min(dest[3], box[3])]
    return tile, [round(v) for v in box]


def text(d, xy, s, fam, size, fill, bold=False):
    f = font(FAMILIES[fam][1 if bold else 0], size)
    d.text(xy, s, font=f, fill=fill)
    return f.getlength(s)


def make_card(rng, portrait, face, fam):
    img = Image.new("RGB", (1000, 640), (176, 160, 138))
    d = ImageDraw.Draw(img)
    p = Person(rng, rng.randint(0, 2**31 - 1))
    issuer = rng.choice(ID_ISSUERS)
    tint = rng.choice([(214, 232, 240), (232, 240, 214), (240, 226, 214), (226, 214, 240)])
    d.rounded_rectangle((40, 40, 960, 560), radius=26, fill=tint, outline=(80, 80, 90), width=3)
    d.rounded_rectangle((40, 40, 960, 110), radius=26, fill=(60, 80, 120))
    d.rectangle((40, 80, 960, 110), fill=(60, 80, 120))
    text(d, (70, 52), issuer, fam, 28, (255, 255, 255), True)
    pw, ph = rng.choice([(170, 210), (240, 300), (300, 380)])
    margin = rng.choice([1.25, 1.8, 2.6])
    dest = (70, 135, 70 + pw, 135 + ph)
    d.rectangle((dest[0] - 3, dest[1] - 3, dest[2] + 3, dest[3] + 3), fill=(205, 215, 225), outline=(90, 90, 100))
    tile, box = place_photo(portrait, face, margin, dest)
    img.paste(tile, dest[:2])
    x = dest[2] + 40
    y = 135
    for label, val in (("Surname", p.last.upper()), ("Given names", p.first), ("Date of birth", p.dob), ("ID number", p.id_number)):
        text(d, (x, y), label, fam, 13, GREY)
        text(d, (x, y + 17), val, fam, 20, INK, True)
        y += 58
    text(d, (x, y), "Nationality", fam, 13, GREY)
    text(d, (x, y + 17), NATIONALITIES[issuer], fam, 20, INK, True)
    lab = "SYNTHETIC TEST DATA"
    f = font(FAMILIES[fam][1], 15)
    lw = f.getlength(lab)
    lx, ly = 500 - lw / 2, 590
    d.text((lx, ly), lab, font=f, fill=RED)
    lbox = [round(v) for v in d.textbbox((lx, ly), lab, font=f)]
    return img, [box], lbox, {"face_px": [pw, ph], "margin": margin}


def make_chat(rng, portrait, face, fam, scale_name):
    dark = rng.random() < 0.4
    bg, bar = ((18, 20, 28), (32, 36, 52)) if dark else ((240, 242, 247), (255, 255, 255))
    fg, sub = ((235, 235, 240), (150, 155, 170)) if dark else ((25, 25, 30), (110, 110, 120))
    mine, theirs = ((46, 110, 220), (48, 52, 70)) if dark else ((60, 130, 240), (255, 255, 255))
    img = Image.new("RGB", (600, 1000), bg)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 600, 90), fill=bar)
    p = Person(rng, rng.randint(0, 2**31 - 1))
    text(d, (20, 12), rng.choice(["Chatterly", "Pingwell", "Hullo!", "Nestbird"]), fam, 15, sub)
    text(d, (20, 12 + 20), p.name, fam, 20, fg, True)
    diam = {"tiny": 36, "small": 52, "medium": 72}[scale_name]
    margin = rng.choice([1.3, 1.9])
    boxes = []
    y = 115
    f = font(FAMILIES[fam][0], 17)
    n_msgs = rng.randint(7, 9)
    msgs = rng.sample(CHAT_PLAIN, n_msgs)
    n_in = 0
    for i, m in enumerate(msgs):
        incoming = i % 2 == 1 or i == 0
        words, lines, cur = m.split(), [], ""
        maxw = 400 - (diam + 10 if incoming else 0)
        for w in words:
            t = (cur + " " + w).strip()
            if f.getlength(t) <= maxw:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        lh = 23
        bw = max(f.getlength(l) for l in lines) + 30
        bh = lh * len(lines) + 18
        if incoming:
            ax, ay = 14, y + max(0, (bh - diam) // 2)
            dest = (ax, ay, ax + diam, ay + diam)
            tile, box = place_photo(portrait, face, margin, dest)
            mask = Image.new("L", (diam, diam), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, diam - 1, diam - 1), fill=255)
            img.paste(tile, dest[:2], mask)
            boxes.append(box)
            n_in += 1
            x0 = ax + diam + 10
        else:
            x0 = 600 - 20 - bw
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), radius=18, fill=theirs if incoming else mine)
        tc = fg if incoming else (255, 255, 255)
        for k, l in enumerate(lines):
            d.text((x0 + 15, y + 9 + k * lh), l, font=f, fill=tc)
        y += max(bh, diam if incoming else 0) + 22
    lab = "SYNTHETIC TEST DATA"
    fb = font(FAMILIES[fam][1], 15)
    lw = fb.getlength(lab)
    lx, ly = 300 - lw / 2, 965
    d.text((lx, ly), lab, font=fb, fill=RED)
    lbox = [round(v) for v in d.textbbox((lx, ly), lab, font=fb)]
    return img, boxes, lbox, {"avatar_px": diam, "margin": margin, "faces": n_in}


def build(seed=SEED, portraits_dir=HERE / "portraits", meta=None):
    """Yield (name, type, split, PIL image, key entry-without-sha, jpeg/png settings). Fully determined by seed + portraits."""
    meta = meta or json.loads((HERE / "portraits_meta.json").read_text())
    por = {p["index"]: p for p in meta["portraits"]}
    sp = {s["index"]: s for s in meta["specs"]}
    rng0 = random.Random(seed + 7)
    hold = {"id_card": set(rng0.sample(range(50), HOLDOUT["id_card"])), "chat": set(rng0.sample(range(25), HOLDOUT["chat"]))}
    out = []
    for idx in range(75):
        typ, j = ("id_card", idx) if idx < 50 else ("chat", idx - 50)
        rng = random.Random(seed * 1000 + idx)
        fam = rng.choice(sorted(FAMILIES))
        portrait = Image.open(portraits_dir / f"p{idx:03d}.png").convert("RGB")
        face = por[idx]["face_box"]
        if typ == "id_card":
            img, boxes, lbox, info = make_card(rng, portrait, face, fam)
        else:
            img, boxes, lbox, info = make_chat(rng, portrait, face, fam, ["tiny", "small", "medium"][j % 3])
        tags = [f"font:{fam}"] + [f"{k}:{v}" for k, v in info.items() if k != "faces"]
        a = sp[idx]["attrs"]
        tags += [f"light:{a['light']}", f"angle:{a['angle']}", "glasses" if a["glasses"] else "no_glasses"]
        blur = rng.choice([0.8, 1.2, 1.6]) if rng.random() < 0.25 else 0
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(blur)); tags.append(f"blur:{blur}")
        fmt = "png" if rng.random() < 0.3 else "jpg"
        q = rng.choice([40, 60, 80, 95]) if fmt == "jpg" else None
        tags.append(fmt + (f"_q{q}" if q else ""))
        fa = max(((b[2] - b[0]) * (b[3] - b[1])) for b in boxes) / (img.width * img.height)
        tags.append("face_size:" + ("tiny" if fa < 0.002 else "small" if fa < 0.01 else "medium" if fa < 0.03 else "large"))
        spans = [{"text": "", "kind": "personal", "pii_type": "face", "box": b} for b in boxes]
        spans.append({"text": "SYNTHETIC TEST DATA", "kind": "other", "pii_type": None, "box": lbox})
        name = f"{typ}_{j:03d}.{fmt}"
        split = "holdout" if j in hold[typ] else "dev"
        entry = {"file": name, "type": typ, "split": split, "variety": tags, "width": img.width, "height": img.height,
                 "portrait_index": idx, "face_attrs": a, "spans": spans}
        out.append((name, img, fmt, q, entry))
    return out


def encode(img, fmt, q):
    import io
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, "PNG", compress_level=6)
    else:
        img.save(buf, "JPEG", quality=q, subsampling=2)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "images"))
    ap.add_argument("--key", default=str(HERE / "key.json"))
    a = ap.parse_args()
    meta = json.loads((HERE / "portraits_meta.json").read_text())
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    entries, digests = [], {}
    for name, img, fmt, q, entry in build(SEED, meta=meta):
        data = encode(img, fmt, q)
        (out / name).write_bytes(data)
        digests[name] = sha(data)
        entries.append(entry)
    key = {"seed": SEED, "note": "SYNTHETIC TEST DATA. AI-made faces of people who do not exist. Boxes [x0,y0,x1,y1] in pixels; "
           "face boxes come from the YuNet detector run on each portrait; skin/age words are PROMPT attributes, not measured. "
           "Text drawn on the pictures is made up and not keyed.",
           "image_model": meta["model"], "detector": meta["detector"], "yunet_sha256": meta["yunet_sha256"],
           "portrait_sha256": {f"p{p['index']:03d}.png": p["sha256"] for p in meta["portraits"]},
           "images": entries, "sha256": digests}
    Path(a.key).write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(entries)} pictures to {out} and {a.key}")


if __name__ == "__main__":
    main()
