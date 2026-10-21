"""PG-3: compose the 80 harder face pictures and faces_hard/key.json. Light PIL work on the Mac. Fully determined by SEED,
faces_hard/images_meta.json, faces_hard/skin.json and the portraits in faces_hard/images_raw/.

    python faces_hard/generate.py

Types (20 each; 15 dev / 5 hold-out each, 60 / 20 in all):
  side_view  single portrait, side view or strong three-quarter view (face box: YuNet on the portrait, moved by the placement)
  accessory  single portrait with sunglasses, hat or face mask (same box method)
  group      2 to 5 head-and-shoulders cut-outs placed in an empty room (face box: YuNet box on the source portrait, moved and
             scaled by our own placement, so it is exact to about 1 px)
  scene      1 to 4 small far-away cut-outs placed in an empty everyday place (same box method)
Cut-outs are made with ellipses (head, shoulders, neck) and a soft edge, not a segmentation model, so they look pasted-in.
Skin tone per face is the MEASURED ITA from faces_hard/skin.py; selection balances the measured light / medium / dark buckets.
"""
import argparse
import hashlib
import io
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import skin as skinmod  # noqa: E402
from spec import SEED  # noqa: E402

LABEL = "SYNTHETIC TEST DATA"
N_PER_TYPE, N_HOLD = 20, 5
GROUP_SIZES = [2] * 5 + [3] * 5 + [4] * 5 + [5] * 5
SCENE_SIZES = [1] * 7 + [2] * 6 + [3] * 4 + [4] * 3
FONT = "/System/Library/Fonts/Helvetica.ttc"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pick(cands, n, rng, skin):
    """Round-robin over the measured buckets (dark first) so the set is spread fairly; seeded."""
    by = {"dark": [], "medium": [], "light": []}
    for i in sorted(cands):
        by[skin[str(i)]["bucket"]].append(i)
    for v in by.values():
        rng.shuffle(v)
    out = []
    while len(out) < n and any(by.values()):
        for b in ("dark", "medium", "light"):
            if by[b] and len(out) < n:
                out.append(by[b].pop())
    return out


def head_cutout(portrait, fb, scale):
    """Head-and-shoulders crop of a portrait with a soft elliptical alpha. Returns (RGBA image, crop origin, scale)."""
    x0, y0, x1, y1 = fb
    fw, fh = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    W, H = portrait.size
    cl, ct = max(0, int(cx - 1.9 * fw)), max(0, int(y0 - 1.1 * fh))
    cr, cb = min(W, int(cx + 1.9 * fw)), min(H, int(y1 + 2.0 * fh))
    a = Image.new("L", (cr - cl, cb - ct), 0)
    d = ImageDraw.Draw(a)
    hc = (y0 + y1) / 2 - 0.18 * fh
    d.ellipse([cx - 0.8 * fw - cl, hc - 1.0 * fh - ct, cx + 0.8 * fw - cl, hc + 1.0 * fh - ct], fill=255)
    d.rectangle([cx - 0.45 * fw - cl, y1 - 0.3 * fh - ct, cx + 0.45 * fw - cl, y1 + 1.6 * fh - ct], fill=255)
    sc = y1 + 1.55 * fh
    d.ellipse([cx - 1.85 * fw - cl, sc - 1.2 * fh - ct, cx + 1.85 * fw - cl, sc + 1.2 * fh - ct], fill=255)
    a = a.filter(ImageFilter.GaussianBlur(max(1.0, 0.08 * fh)))
    im = portrait.crop((cl, ct, cr, cb)).convert("RGBA")
    im.putalpha(a)
    sz = (max(2, round(im.width * scale)), max(2, round(im.height * scale)))
    return im.resize(sz, Image.LANCZOS), (cl, ct), scale


def moved_box(fb, origin, scale, off):
    x0, y0, x1, y1 = fb
    return [int((x0 - origin[0]) * scale + off[0]), int((y0 - origin[1]) * scale + off[1]),
            int(-(-((x1 - origin[0]) * scale + off[0]) // 1)), int(-(-((y1 - origin[1]) * scale + off[1]) // 1))]


def face_record(it, spx, skin, box, method):
    s = skin[str(it["index"])]
    a = spx[it["index"]]["attrs"]
    return {"text": "", "kind": "personal", "pii_type": "face", "box": box, "box_method": method, "portrait_index": it["index"],
            "ita": s["ita"], "skin_bucket": s["bucket"], "skin_chardon": s["chardon"], "prompt_skin_word": a["skin_word"],
            "prompt_words": {"age": a["age"], "gender_word": a["gender_word"], "view_or_accessory": a["view_or_accessory"],
                             "light": a["light"], "glasses": a["glasses"], "hair": a["hair"]},
            "yunet_score": it["det_score"], "yunet_landmarks": it["landmarks"]}


def build(seed=SEED, meta=None, skin=None, raw=HERE / "images_raw"):
    meta = meta or json.loads((HERE / "images_meta.json").read_text())
    skin = skin or json.loads((HERE / "skin.json").read_text())
    items = {it["index"]: it for it in meta["items"]}
    spx = {s["index"]: s for s in meta["specs"]}
    ok = {i for i, it in items.items() if it["ok"] and it["kind"] != "bg" and str(i) in skin and skin[str(i)]["ita"] is not None}
    rng = random.Random(seed + 11)
    side = sorted(pick({i for i in ok if items[i]["kind"] == "side"}, N_PER_TYPE, rng, skin))
    acc = sorted(pick({i for i in ok if items[i]["kind"] == "acc"}, N_PER_TYPE, rng, skin))
    need = sum(GROUP_SIZES) + sum(SCENE_SIZES)
    pool = pick({i for i in ok if items[i]["kind"] == "pool"}, need, rng, skin)
    if len(pool) < need:
        raise SystemExit(f"need {need} pool portraits, have {len(pool)}: make more")
    rng.shuffle(pool)
    gsz, ssz = GROUP_SIZES[:], SCENE_SIZES[:]
    rng.shuffle(gsz); rng.shuffle(ssz)
    bgs = {u: sorted(i for i, it in items.items() if it["kind"] == "bg" and it["ok"] and spx[i]["use"] == u) for u in ("group", "scene")}
    hold = {t: set(rng.sample(range(N_PER_TYPE), N_HOLD)) for t in ("side_view", "accessory", "group", "scene")}
    font = ImageFont.truetype(FONT, 12)
    out, pp = [], 0
    jobs = [("side_view", k, [side[k]]) for k in range(N_PER_TYPE)] + [("accessory", k, [acc[k]]) for k in range(N_PER_TYPE)]
    for k in range(N_PER_TYPE):
        jobs.append(("group", k, pool[pp:pp + gsz[k]])); pp += gsz[k]
    for k in range(N_PER_TYPE):
        jobs.append(("scene", k, pool[pp:pp + ssz[k]])); pp += ssz[k]
    for n, (typ, k, ids) in enumerate(jobs):
        r = random.Random(seed * 1000 + n)
        tags, faces = [], []
        if typ in ("side_view", "accessory"):
            it = items[ids[0]]
            por = Image.open(raw / f"i{ids[0]:03d}.png").convert("RGB")
            z = r.choices([1.0, 0.55, 0.3], weights=[45, 30, 25])[0]
            S = 1024
            bg = tuple(int(v) for v in Image.open(raw / f"i{ids[0]:03d}.png").convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0)))
            img = Image.new("RGB", (S, S), bg)
            sz = round(S * z)
            off = (r.randint(0, S - sz), r.randint(0, S - sz)) if z < 1 else (0, 0)
            img.paste(por.resize((sz, sz), Image.LANCZOS), off)
            fb = [v * z for v in it["face_box"]]
            box = [int(fb[0] + off[0]), int(fb[1] + off[1]), int(-(-(fb[2] + off[0]) // 1)), int(-(-(fb[3] + off[1]) // 1))]
            faces.append(face_record(it, spx, skin, box, "YuNet on the source portrait, moved by the zoom-out placement"))
            tags.append(f"zoom:{z}")
        else:
            gp = typ == "group"
            W, H = 1024, 768
            u = "group" if gp else "scene"
            bi = r.choice(bgs[u])
            img = Image.open(raw / f"i{bi:03d}.png").convert("RGB")
            if r.random() < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            zf = r.choice([1.0, 0.85, 0.7])
            if zf < 1:
                cw, ch = int(W * zf), int(H * zf)
                x, y = r.randint(0, W - cw), r.randint(0, H - ch)
                img = img.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)
            tags += [f"background:i{bi:03d}", f"bg_zoom:{zf}"]
            m = len(ids)
            placed = []
            for j, pid in enumerate(ids):
                it = items[pid]
                por = Image.open(raw / f"i{pid:03d}.png").convert("RGB")
                fbw = it["face_box"][2] - it["face_box"][0]
                for _try in range(60):
                    if gp:
                        tfw = r.uniform(*{2: (150, 200), 3: (125, 170), 4: (105, 145), 5: (90, 125)}[m])
                        slot = W / m
                        cxp = slot * (j + 0.5) + r.uniform(-0.12, 0.12) * slot
                        bottom = H + r.uniform(0, 0.25) * tfw * 3
                    else:
                        yb = r.uniform(0.45, 0.95) * H
                        tfw = (14 + (50 - 14) * (yb - 0.4 * H) / (0.55 * H)) * r.uniform(0.8, 1.2)
                        tfw = max(12.0, tfw)
                        cxp = r.uniform(0.06, 0.94) * W
                        bottom = yb
                    cut, origin, sc = head_cutout(por, it["face_box"], tfw / fbw)
                    # place so that the crop's bottom edge sits at `bottom` and the face centre sits at cxp
                    fcx = ((it["face_box"][0] + it["face_box"][2]) / 2 - origin[0]) * sc
                    off = (round(cxp - fcx), round(bottom - cut.height))
                    box = moved_box(it["face_box"], origin, sc, off)
                    if box[0] < 4 or box[2] > W - 4 or box[1] < 26 or box[3] > H - 4:
                        continue
                    pad = 0.35 * (box[2] - box[0])
                    if any(not (box[2] + pad < p[0] or box[0] - pad > p[2] or box[3] + pad < p[1] or box[1] - pad > p[3]) for p in placed):
                        continue
                    break
                else:
                    raise SystemExit(f"could not place a face in picture {typ}_{k:03d}")
                placed.append(box)
                img.paste(cut, off, cut)
                faces.append(face_record(it, spx, skin, box, "YuNet box on the source portrait, moved and scaled by our own placement"))
            # people drawn later can overlap earlier shoulders but never an earlier face box (checked by the padding above)
        d = ImageDraw.Draw(img)
        tb = d.textbbox((3, 3), LABEL, font=font)
        d.rectangle([0, 0, tb[2] + 3, tb[3] + 3], fill=(255, 255, 255))
        d.text((3, 3), LABEL, fill=(190, 0, 0), font=font)
        lbox = [tb[0], tb[1], tb[2], tb[3]]
        blur = r.choice([0.8, 1.2, 1.6]) if r.random() < 0.25 else 0
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(blur)); tags.append(f"blur:{blur}")
        fmt = "png" if r.random() < 0.3 else "jpg"
        q = r.choice([40, 60, 80, 95]) if fmt == "jpg" else None
        tags.append(fmt + (f"_q{q}" if q else ""))
        ms = min(min(f["box"][2] - f["box"][0], f["box"][3] - f["box"][1]) for f in faces)
        tags.append("smallest_face:" + ("tiny_lt20px" if ms < 20 else "small_20_59px" if ms < 60 else "medium_60_149px" if ms < 150 else "large_ge150px"))
        tags.append(f"faces:{len(faces)}")
        for f in faces:
            tags.append("accessory:" + spx[f["portrait_index"]]["attrs"]["view_or_accessory"][:30]) if typ == "accessory" else None
        for f in faces:
            f["face_short_side_px"] = min(f["box"][2] - f["box"][0], f["box"][3] - f["box"][1])
        spans = faces + [{"text": LABEL, "kind": "other", "pii_type": None, "box": lbox}]
        name = f"{typ}_{k:03d}.{fmt}"
        entry = {"file": name, "type": typ, "split": "holdout" if k in hold[typ] else "dev", "variety": tags,
                 "width": img.width, "height": img.height, "portrait_indices": ids, "spans": spans}
        out.append((name, img, fmt, q, entry))
    return out


def encode(img, fmt, q):
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
    meta = json.loads((HERE / "images_meta.json").read_text())
    skin = json.loads((HERE / "skin.json").read_text())
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    entries, digests = [], {}
    for name, img, fmt, q, entry in build(SEED, meta=meta, skin=skin):
        data = encode(img, fmt, q)
        (out / name).write_bytes(data)
        digests[name] = sha(data)
        entries.append(entry)
    dropped = [{"index": it["index"], "kind": it["kind"], "attempts": it["attempts"], "n_faces_detected": it["n_faces_detected"]}
               for it in meta["items"] if not it["ok"]]
    used = {i for e in entries for i in e["portrait_indices"]}
    key = {"seed": SEED, "note": "SYNTHETIC TEST DATA. AI-made faces of people who do not exist. Boxes [x0,y0,x1,y1] in pixels. "
           "Face boxes come from the YuNet detector run on each source portrait, moved by our own placement (box_method says how). "
           "skin_bucket is MEASURED (ITA angle on the face pixels of the source portrait; light >41, medium 10..41, dark <=10); "
           "prompt_skin_word is what the prompt said. Text drawn on the pictures is only the label.",
           "image_model": meta["model"], "detector": meta["detector"], "yunet_sha256": meta["yunet_sha256"],
           "portrait_score_threshold": meta["portrait_score_threshold"], "tries": meta["tries"],
           "dropped_images_failed_face_check": dropped,
           "source_sha256": {f"i{it['index']:03d}.png": it["sha256"] for it in meta["items"] if it["ok"] and (it["index"] in used or it["kind"] == "bg")},
           "images": entries, "sha256": digests}
    Path(a.key).write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(entries)} pictures to {out} and {a.key}")


if __name__ == "__main__":
    main()
