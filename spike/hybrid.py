"""Offline (no Modal, no cost): Glimmer finds the text, Tesseract's word boxes give the location.
For each Glimmer item, look for consecutive OCR words on one line that spell the same normalised text.
If found, use their union box; otherwise keep Glimmer's own box.

    python spike/hybrid.py glimmer_q4_dev20 [psm3|psm11]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

R = Path(__file__).resolve().parent / "results"


def ocr_box(words, target):
    lines = {}
    for w in words:
        lines.setdefault(tuple(w["line"]), []).append(w)
    for ws in lines.values():
        for i in range(len(ws)):
            acc = ""
            for j in range(i, min(len(ws), i + 10)):
                acc += common.norm(ws[j]["text"])
                if acc == target:
                    seg = ws[i:j + 1]
                    return [min(w["box"][0] for w in seg), min(w["box"][1] for w in seg),
                            max(w["box"][2] for w in seg), max(w["box"][3] for w in seg)]
                if not target.startswith(acc):
                    break
    return None


def main(run, psm="psm3"):
    gl = json.loads((R / f"{run}.json").read_text())
    ts = json.loads((R / "tesseract_dev20.json").read_text())[psm]
    words = {r["file"]: r["words"] for r in ts["results"]}
    key = {e["file"]: e for e in common.load_key(R.parent / "out" / "dev" / "dev_key.json")["images"]}
    rows, swapped, total = [], 0, 0
    for r in gl["results"]:
        e = key[r["file"]]
        preds = []
        for it in r["items"]:
            if not common.valid_box(it.get("box")):
                continue
            b = it["box"]
            t = common.norm(it.get("text"))
            ob = ocr_box(words[r["file"]], t) if t else None
            total += 1
            if ob:
                b, swapped = ob, swapped + 1
            preds.append({"text": it.get("text", ""), "type": it.get("type", ""), "box": b})
        rows.append((e, common.score_picture(e, preds)))
    agg = common.aggregate(rows)
    print(f"{run} + tesseract {psm}: {swapped}/{total} Glimmer boxes replaced by OCR word boxes")
    print(json.dumps(agg, indent=1))
    (R / f"hybrid_{run}_{psm}.json").write_text(json.dumps({"replaced": swapped, "items": total, "score": agg}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
