"""Day 7: which matching rules locate more Glimmer values, and do they ever place a box on the wrong spot? Offline, from cached reads
(tools/cache_passes.py) and saved Glimmer answers. Numbers only; no value text is written."""
import argparse
import json
import pickle
from difflib import SequenceMatcher
from pathlib import Path

from picture_guard import match
from picture_guard.ocr import Word

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = {
    "V0 current": (None, False),
    "V1 look-alikes": ({"confusables": True}, False),
    "V6 digits reader only (thresholds as now)": (None, True),
    "V7 look-alikes + digits reader": ({"confusables": True}, True),
    "V2 + digit threshold 0.80": ({"confusables": True, "digit_threshold": 0.80}, False),
    "V3 V2 + digits reader": ({"confusables": True, "digit_threshold": 0.80}, True),
    "V4 V3 + text threshold 0.80": ({"confusables": True, "digit_threshold": 0.80, "text_threshold": 0.80}, True),
    "V5 V2 + digit threshold 0.75": ({"confusables": True, "digit_threshold": 0.75}, True),
}


def sim(a, b):
    a, b = match.norm(a), match.norm(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def overlap(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix / max(1, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="testset")
    ap.add_argument("--out", default="results/pg10/matching-experiment.json")
    a = ap.parse_args()
    key = json.loads((ROOT / a.set / "key.json").read_text())
    ent = {e["file"]: e for e in key["images"] if e["split"] == "dev"}
    saved = {}
    for line in (ROOT / "results/pg6/debug" / f"{a.set}.jsonl").read_text().splitlines():
        r = json.loads(line)
        saved[r["file"]] = ((r.get("response") or {}).get("glimmer") or {}).get("values") or []
    res = {v: {} for v in VARIANTS}
    for f, e in ent.items():
        pk = ROOT / "results/pg10/debug" / f"passes-{a.set}" / f"{f}.pkl"
        if not pk.exists() or not saved.get(f):
            continue
        raw = pickle.load(open(pk, "rb"))
        planted = [s for s in e["spans"] if s["kind"] == "personal" and s["pii_type"] != "face" and s["text"]]
        for vname, (lenient, use_dig) in VARIANTS.items():
            passes = {k: [Word(*w) for w in ws] for k, ws in raw.items() if use_dig or not k.startswith("dig-")}
            st = res[vname].setdefault(e["type"], {"values": 0, "located": 0, "pictures": 0, "pictures_all_located": 0, "located_wrong_spot": 0, "located_right_spot": 0, "located_not_planted": 0})
            st["pictures"] += 1
            allok = True
            for v in saved[f]:
                st["values"] += 1
                boxes = match.locate(v["text"], passes, lenient=lenient)
                if boxes is None:
                    allok = False
                    continue
                st["located"] += 1
                best = max(((max([sim(v["text"], s["text"])] + [sim(q, s["text"]) for q in match.parts_of(v["text"])]), s) for s in planted), key=lambda c: c[0], default=(0, None))
                if best[1] is None or best[0] < 0.8:
                    st["located_not_planted"] += 1
                elif any(overlap(b, best[1]["box"]) >= 0.3 for b in boxes):
                    st["located_right_spot"] += 1
                else:
                    st["located_wrong_spot"] += 1
                    st.setdefault("wrong_spot_cases", []).append({"file": f, "glimmer_type": v.get("type"), "planted_type": best[1]["pii_type"], "similarity": round(best[0], 3)})
            st["pictures_all_located"] += allok
    Path(ROOT / a.out).write_text(json.dumps(res, indent=1))
    for vname, by in res.items():
        tot = {k: sum(x[k] for x in by.values()) for k in ("values", "located", "pictures", "pictures_all_located", "located_wrong_spot", "located_right_spot", "located_not_planted")}
        print(vname, "| all types:", tot, "| chat:", by.get("chat"))


if __name__ == "__main__":
    main()
