"""Why does a Glimmer value have no word box? Per-value diagnosis for the whole-black pictures of one picture type (day 7).

Reads saved Glimmer answers (git-ignored results/pg6/debug), the key and the pictures of the DEV split; runs Tesseract (CPU) with the
default reads. Writes numbers and categories only: no value text, no picture text, goes into the committed files.

    .venv/bin/python tools/diagnose_chats.py --set testset --type chat --eval results/pg9/eval-testset-dev-fb-zoom-clean-loc.json
"""
import argparse
import json
import re
import statistics as st
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
from PIL import Image

from picture_guard import match, ocr

ROOT = Path(__file__).resolve().parent.parent


def sim(a: str, b: str) -> float:
    a, b = match.norm(a), match.norm(b)
    return 1.0 if a == b and a else (SequenceMatcher(None, a, b).ratio() if a and b else 0.0)


def words_near(passes: dict, box, pad_frac=0.5):
    """Words (any pass) whose centre is inside the box grown by pad_frac of its height."""
    h = box[3] - box[1]
    p = pad_frac * h
    x0, y0, x1, y1 = box[0] - p, box[1] - p, box[2] + p, box[3] + p
    out = []
    for ws in passes.values():
        out += [w for w in ws if x0 <= (w.box[0] + w.box[2]) / 2 <= x1 and y0 <= (w.box[1] + w.box[3]) / 2 <= y1]
    return out


def best_read_similarity(value: str, near: list) -> float:
    """Best similarity of the planted value to any run of consecutive words among those read near its box (same pass line)."""
    best = 0.0
    lines: dict = {}
    for w in near:
        lines.setdefault((id(w) // 1, w.line), []).append(w)
    texts = [w.text for w in near]
    if not texts:
        return 0.0
    joined = " ".join(texts)
    best = max(best, sim(value, joined))
    n = len(value.split())
    for i in range(len(texts)):
        for size in range(1, n + 3):
            if i + size <= len(texts):
                best = max(best, sim(value, " ".join(texts[i:i + size])))
    return round(best, 3)


def text_look(img: np.ndarray, box) -> dict:
    x0, y0, x1, y1 = [int(v) for v in box]
    reg = img[max(0, y0):y1, max(0, x0):x1].astype(float)
    if reg.size == 0:
        return {}
    lum = reg.mean(axis=2)
    lo, hi = np.percentile(lum, 5), np.percentile(lum, 95)
    bg_is_dark = np.median(lum) < 110
    return {"height_px": int(y1 - y0), "contrast": round(float((hi - lo) / 255), 2), "background": "dark" if bg_is_dark else "light",
            "bg_colour_bin": "grey" if reg.reshape(-1, 3).std(axis=0).mean() < 20 and 60 < np.median(lum) < 200 else ("white" if np.median(lum) >= 200 else ("dark" if bg_is_dark else "colour"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="testset")
    ap.add_argument("--type", default="chat")
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", default="results/pg10/diagnosis")
    ap.add_argument("--all-pictures", action="store_true", help="every picture of the type, not only the whole-black ones")
    a = ap.parse_args()
    base = ROOT / a.set
    key = json.loads((base / "key.json").read_text())
    ent = {e["file"]: e for e in key["images"] if e["split"] == "dev"}
    ev = json.loads((ROOT / a.eval).read_text())
    pics = [p for p in ev["pictures"] if p["type"] == a.type and (a.all_pictures or p["whole_black_pixels"])]
    saved = {}
    for line in (ROOT / "results" / "pg6" / "debug" / f"{a.set}.jsonl").read_text().splitlines():
        r = json.loads(line)
        saved[r["file"]] = r["response"]
    rows, per_pic = [], []
    for p in pics:
        e = ent[p["file"]]
        im = Image.open(base / "images" / p["file"]).convert("RGB")
        arr = np.asarray(im)
        passes = ocr.read_passes(im, cleanups=ocr.DEFAULT_CLEANUPS)
        gl = (saved.get(p["file"]) or {}).get("glimmer") or {}
        planted = [s for s in e["spans"] if s["kind"] == "personal" and s["pii_type"] != "face" and s["text"]]
        other = [s for s in e["spans"] if s["kind"] == "other" and s["text"]]
        n_unloc = 0
        for v in gl.get("values", []):
            text = v.get("text", "")
            if match.locate(text, passes) is not None:
                continue
            n_unloc += 1
            # which planted value is this (best similarity over whole value or its parts)?
            cands = [(max([sim(text, s["text"])] + [sim(text, q) for q in match.parts_of(s["text"])] + [sim(q, s["text"]) for q in match.parts_of(text)]), s) for s in planted]
            ps, pbest = max(cands, key=lambda c: c[0], default=(0.0, None))
            os_, obest = max(((sim(text, s["text"]), s) for s in other), key=lambda c: c[0], default=(0.0, None))
            row = {"file": p["file"], "glimmer_type": v.get("type"), "variety": e["variety"]}
            if pbest is not None and ps >= 0.99 or (pbest is not None and ps >= 0.8):
                near = words_near(passes, pbest["box"])
                read_sim = best_read_similarity(pbest["text"], near)
                row.update(planted=True, planted_type=pbest["pii_type"], glimmer_to_planted_similarity=round(ps, 3), words_read_near_box=len(near),
                           best_read_similarity=read_sim, **text_look(arr, pbest["box"]))
                if len(near) == 0:
                    row["cause"] = "A: Tesseract reads no word at the value"
                elif read_sim >= 0.85:
                    row["cause"] = "C: words are read and look right but matching still fails"
                elif read_sim >= 0.5:
                    row["cause"] = "B1: read with errors (similarity 0.5-0.85)"
                else:
                    row["cause"] = "B2: read as something else (similarity under 0.5)"
                if ps < 0.99:
                    row["glimmer_misread_planted"] = True
            elif obest is not None and os_ >= 0.8:
                row.update(planted=False, cause="E: Glimmer lists ordinary text (not private) and Tesseract cannot find it", glimmer_to_ordinary_similarity=round(os_, 3))
            else:
                row.update(planted=False, cause="F: Glimmer lists something that is not on the picture's key (misread or invented)", best_similarity_to_any_span=round(max(ps, os_), 3))
            rows.append(row)
        per_pic.append({"file": p["file"], "unlocated_values": n_unloc, "whole_black": p["whole_black_pixels"], "variety": e["variety"]})
    causes = {}
    for r in rows:
        c = r["cause"].split(":")[0]
        causes[c] = causes.get(c, 0) + 1
    by_pic: dict = {}
    for r in rows:
        by_pic.setdefault(r["file"], set()).add(r["cause"].split(":")[0])
    out = {"set": a.set, "type": a.type, "pictures": len(pics), "unlocated_values": len(rows), "cause_counts": dict(sorted(causes.items())),
           "pictures_by_cause_set": {" + ".join(sorted(k)): sum(1 for v in by_pic.values() if v == k) for k in {frozenset(v) for v in by_pic.values()}},
           "rows": rows, "per_picture": per_pic}
    Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / f"{a.out}-{a.type}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("pictures", "unlocated_values", "cause_counts", "pictures_by_cause_set")}, indent=1))


if __name__ == "__main__":
    main()
