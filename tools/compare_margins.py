"""Table of margin settings from eval JSON files: python tools/compare_margins.py results/pg12/ink05 results/pg11/final ..."""
import json
import sys
from pathlib import Path

TYPES = ("chat", "id_card", "letter", "payslip")


def load(d, s):
    fs = sorted(Path(d).glob(f"eval-{s}-dev*.json"))
    return json.loads(fs[0].read_text()) if fs else None


def row(d):
    t, f, h = load(d, "testset"), load(d, "faces"), load(d, "faces_hard")
    if not t:
        return None
    k = t["summary"]["all"]["kept"]
    by = {ty: t["summary"][ty]["kept"] for ty in TYPES}
    share = lambda x: f"{x['plain_readable']}/{x['plain_spans']} ({100 * x['plain_readable'] / max(1, x['plain_spans']):.0f}%)"
    pb = lambda r: r["summary"]["all"]["whole_black_pixels"] if r else None
    fcov = lambda r: (r["summary"]["all"]["kept"]["face_boxes_90_black"], r["summary"]["all"]["kept"]["face_boxes"]) if r else None
    return {
        "setting": Path(d).name, "pictures": t["pictures_scored"],
        "black t/f/fh": f"{pb(t)}/{pb(f)}/{pb(h)}",
        "under90": k["value_boxes"] - k["value_boxes_90_black"], "50-90": k["values_50_90_pixels"], "<50": k["values_under_50_pixels"],
        "leak plain/strict": f"{k['values_left_readable']}/{k['values_left_readable_strict']}" + ("" if not f else f" f:{f['summary']['all']['kept']['values_left_readable']}"),
        "faces cov": f"{fcov(f)} {fcov(h)}",
        "overall": share(k), **{ty: share(by[ty]) for ty in TYPES},
    }


if __name__ == "__main__":
    rows = [r for r in (row(d) for d in sys.argv[1:]) if r]
    cols = list(rows[0])
    print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
