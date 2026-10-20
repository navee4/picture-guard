"""Make the 200-picture test set and key.json from a fixed seed.

    python testset/generate.py [--out DIR] [--key PATH]
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from draw import FAMILIES, encode, final_boxes, render
from templates import TEMPLATES
from values import Person

SEED = 20261020
TYPES = ["payslip", "letter", "id_card", "chat"]
HOLDOUT = {"payslip": 12, "letter": 13, "id_card": 12, "chat": 13}  # 50 hold-out in total
PER_TYPE = 50
HERE = Path(__file__).resolve().parent


def build_specs(seed=SEED):
    """Return [(name, type, split, spec)] — fully determined by the seed."""
    out = []
    for ti, typ in enumerate(TYPES):
        for i in range(PER_TYPE):
            n = ti * PER_TYPE + i
            rng = random.Random(seed * 1000 + n)
            p = Person(rng, seed * 1000 + n)
            family = rng.choice(sorted(FAMILIES))
            scale = rng.choice([0.9, 1.0, 1.0, 1.1])
            canvas, _ = TEMPLATES[typ](rng, p, family, scale)
            v = {"font": family, "scale": scale}
            tags = [f"font:{family}", f"scale:{scale}"]
            if rng.random() < 0.45:
                v["rotate"] = round(rng.choice([-1, 1]) * rng.uniform(0.6, 3.0), 2); tags.append(f"rotate:{v['rotate']}")
            if rng.random() < 0.35:
                v["noise"] = rng.choice([6, 10, 16]); v["noise_seed"] = rng.randint(0, 2**31 - 1); tags.append("scan_noise")
            if rng.random() < 0.2:
                v["low_contrast"] = rng.choice([0.4, 0.5, 0.6]); tags.append("low_contrast")
            if rng.random() < 0.25:
                v["blur"] = rng.choice([0.8, 1.2, 1.6]); v["shade"] = rng.choice([0.75, 0.85]); tags.append("phone_blur")
            v["format"] = "jpg" if rng.random() < 0.5 else "png"
            if v["format"] == "jpg":
                v["jpeg_q"] = rng.choice([55, 75, 90])
            tags.append(v["format"] + (f"_q{v['jpeg_q']}" if v["format"] == "jpg" else ""))
            v["tags"] = tags
            name = f"{typ}_{i:03d}.{v['format']}"
            split = "holdout" if i >= PER_TYPE - HOLDOUT[typ] else "dev"
            out.append((name, typ, split, canvas.spec(v)))
    return out


def key_entry(name, typ, split, spec):
    boxes = final_boxes(spec)
    spans = [{"text": s["text"], "kind": s["kind"], "pii_type": s["pii_type"], "box": b}
             for s, b in zip(spec["spans"], boxes)]
    return {"file": name, "type": typ, "split": split, "variety": spec["variety"]["tags"],
            "width": spec["w"], "height": spec["h"], "spans": spans}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "images"))
    ap.add_argument("--key", default=str(HERE / "key.json"))
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    entries, digests = [], {}
    for name, typ, split, spec in build_specs(a.seed):
        data = encode(render(spec), spec["variety"])
        (out / name).write_bytes(data)
        digests[name] = hashlib.sha256(data).hexdigest()
        entries.append(key_entry(name, typ, split, spec))
    key = {"seed": a.seed, "note": "SYNTHETIC TEST DATA. Boxes are [x0,y0,x1,y1] pixels in the saved picture.",
           "images": entries, "sha256": digests}
    Path(a.key).write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(entries)} pictures to {out} and {a.key}")


if __name__ == "__main__":
    main()
