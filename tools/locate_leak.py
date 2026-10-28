"""Where did the strict read-back match a planted value on a safe copy? Usage: python tools/locate_leak.py <set> <file> <scratch-dir>
Re-runs each ink-aware setting on one dev picture (replay), reads the safe copy with the strict reads, and reports for every word that
contains the value whether it sits inside the planted box. Prints box positions and value types only (no picture text)."""
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

from picture_guard import match, ocr, readback
from picture_guard.evaluate import SETS, _replay_guard
from picture_guard.pipeline import protect

SETTINGS = {
    "ink025": {"smart": {"ink": {"gap_frac": 0.25}}},
    "ink05": {"smart": {"ink": {"gap_frac": 0.5}}},
    "ink10": {"smart": {"ink": {"gap_frac": 1.0}}},
    "inkv": {"smart": {"ink": {"gap_frac": 1.0}}, "margin": (0.25, 3, 1.0, 8)},
    "inkv_widen": {"smart": {"ink": {"gap_frac": 1.0}, "widen": True, "levels": [[0.25, 3, 1.0, 8], [0.5, 5, 1.0, 8], [0.75, 6, 1.0, 8], [1.0, 8, 1.0, 8]]}},
}


def inside(b, p):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return p[0] <= cx <= p[2] and p[1] <= cy <= p[3]


def main(set_name, fname, scratch):
    base = SETS[set_name]
    key = json.loads((base / "key.json").read_text())
    entry = next(e for e in key["images"] if e["file"] == fname)
    values = [s for s in entry["spans"] if s["kind"] == "personal" and s["pii_type"] != "face" and s["text"]]
    guard = _replay_guard(set_name, [entry], base, Path(scratch), "leakcheck")
    for name, opts in SETTINGS.items():
        with tempfile.TemporaryDirectory() as d:
            safe, rep = Path(d) / "s.png", Path(d) / "r.json"
            with guard as g:
                protect(base / "images" / fname, safe, rep, guard=g, options={"fallback": "zoom", **opts})
            img = Image.open(safe).convert("RGB")
            variants = {"plain": img}
            for n in ("inv", "loc", "invloc"):
                v = ocr.CLEANUP_FNS[n](img)
                if v is not None:
                    variants[n] = v
            full = readback.norm(readback.ocr_text_strict(str(safe)))
            print(f"== {name}")
            for v in values:
                if not readback.found(v["text"], full):
                    continue
                t = readback.norm(v["text"])
                hits = []
                for vn, vi in variants.items():
                    for sc in (1, 2):
                        im = vi if sc == 1 else vi.resize((vi.width * 2, vi.height * 2))
                        for psm in (11, 6):
                            for w in ocr.read_words(im, psm):
                                if t in match.norm(w.text):
                                    b = tuple(round(c / sc) for c in w.box)
                                    hits.append((vn, sc, psm, b, inside(b, v["box"])))
                print(f"  value type {v['pii_type']} planted box {v['box']}: matched in strict text; word-level hits: {len(hits)}")
                for h in hits:
                    print(f"    read={h[0]} x{h[1]} psm{h[2]} box={h[3]} inside_planted_box={h[4]}")
                if not hits:
                    print("    no single word contains it: the match comes from words joined across a gap")


if __name__ == "__main__":
    main(*sys.argv[1:4])
