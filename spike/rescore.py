"""Offline (no cost): re-parse saved raw model text with the fixed parser and rescore.

    python spike/rescore.py glimmer_bf16_dev20
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

R = Path(__file__).resolve().parent / "results"


def parse_last_list(text):
    t = text or ""
    starts = [m.start() for m in re.finditer(r"\[\s*\{", t)]
    end = t.rfind("]")
    if not starts or end < starts[-1]:
        return [], "no JSON list found"
    try:
        return [x for x in json.loads(t[starts[-1]:end + 1]) if isinstance(x, dict)], None
    except Exception as e:  # noqa: BLE001
        return [], f"parse error: {e}"


def main(run):
    d = json.loads((R / f"{run}.json").read_text())
    key = {e["file"]: e for e in common.load_key(R.parent / "out" / "dev" / "dev_key.json")["images"]}
    out = {}
    for frame in ("px", "norm1000"):
        rows, bad = [], 0
        for r in d["results"]:
            items, err = parse_last_list(r.get("content"))
            bad += bool(err)
            e = key[r["file"]]
            preds = [{"text": i.get("text", ""), "type": i.get("type", ""),
                      "box": common.convert_frame(i["box"], frame, e["width"], e["height"])}
                     for i in items if common.valid_box(i.get("box"))]
            rows.append((e, common.score_picture(e, preds)))
        out[frame] = {"unparsed": bad, "score": common.aggregate(rows)}
    (R / f"{run}_rescored.json").write_text(json.dumps(out, indent=1))
    for fr, v in out.items():
        a = v["score"]["all"]
        print(fr, "unparsed", v["unparsed"], {k: a[k] for k in ("value_recall", "box_hit_rate", "value_and_box", "false_alarms_per_picture", "readable_share", "returned_items")})


if __name__ == "__main__":
    main(sys.argv[1])
