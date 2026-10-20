"""Scoring and spend helpers shared by the spike scripts. Pure Python + numpy: runs on the Mac and in Modal.

Definitions (all on `personal` spans of key.json; `face` spans have no text, so they count for boxes only):
  value recall   planted value is found: a returned item has the same normalised text (lowercase, letters
                 and digits only). One returned item can satisfy only one planted span.
  box hit        some returned box (any text) has IoU >= 0.5 with the planted box, OR contains the
                 planted box's centre. The centre rule is lenient, so we also report how big the hitting
                 boxes are (median area ratio, returned / planted).
  value+box      the returned item that matched the text also hits the planted box.
  false alarm    a returned item that matches no planted personal span (by text or box) and lands on an
                 `other` span (same text, IoU >= 0.5, or contains its centre).
  readable share share of `other` spans whose centre is NOT inside any returned box.
"""
import json
import re
import statistics
from pathlib import Path

SPEND_CAP_USD = 25.0
# Modal public price page, read 20 Oct 2026 (modal.com/pricing). Dollars per second.
RATES = {"L40S": 0.000542, "H100": 0.001097, "cpu_core": 0.00003942, "mem_gib": 0.00000222}

TYPES = ["payslip", "letter", "id_card", "chat"]


def norm(s):
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def centre_in(inner, outer):
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def hits(planted_box, pred_box):
    return iou(planted_box, pred_box) >= 0.5 or centre_in(planted_box, pred_box)


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def valid_box(b):
    return isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)


def load_key(path):
    return json.loads(Path(path).read_text())


def select_eval(key, per_type=5, all_dev=False):
    """Dev pictures only. 5 per type (first by file name) for the quick run, or all 150 dev pictures."""
    out = []
    for t in TYPES:
        dev = sorted((e for e in key["images"] if e["type"] == t and e["split"] == "dev"), key=lambda e: e["file"])
        out += dev if all_dev else dev[:per_type]
    assert all(e["split"] == "dev" for e in out), "hold-out must never be run"
    return out


def convert_frame(box, frame, w, h):
    """Return box in pixels from the model's coordinate frame: px, norm1000 or norm1."""
    if frame == "px":
        return list(box)
    k = 1000.0 if frame == "norm1000" else 1.0
    return [box[0] * w / k, box[1] * h / k, box[2] * w / k, box[3] * h / k]


def score_picture(entry, preds):
    """preds: [{text, type, box (pixels)}]. Returns raw counts for one picture."""
    spans = entry["spans"]
    personal = [s for s in spans if s["kind"] == "personal"]
    other = [s for s in spans if s["kind"] == "other"]
    preds = [p for p in preds if valid_box(p.get("box"))]
    used = set()
    r = {"personal_text": 0, "found": 0, "found_box": 0, "personal_all": len(personal), "box_hit": 0,
         "type_ok": 0, "area_ratios": [], "other": len(other), "other_covered": 0,
         "preds": len(preds), "false_alarms": 0, "unmatched_other": 0, "by_type": {}}
    matched_pred = set()
    for s in personal:
        bt = r["by_type"].setdefault(s["pii_type"], {"n": 0, "found": 0, "box_hit": 0})
        bt["n"] += 1
        any_hit = [(iou(s["box"], p["box"]), j) for j, p in enumerate(preds) if hits(s["box"], p["box"])]
        if any_hit:
            r["box_hit"] += 1; bt["box_hit"] += 1
            j = max(any_hit)[1]
            r["area_ratios"].append(area(preds[j]["box"]) / max(1, area(s["box"])))
            matched_pred.add(j)
        if s["pii_type"] == "face":
            continue
        r["personal_text"] += 1
        cands = [(iou(s["box"], p["box"]), j) for j, p in enumerate(preds)
                 if j not in used and norm(p.get("text")) == norm(s["text"]) and norm(s["text"])]
        if cands:
            _, j = max(cands)
            used.add(j); matched_pred.add(j)
            r["found"] += 1; bt["found"] += 1
            if hits(s["box"], preds[j]["box"]):
                r["found_box"] += 1
            if str(preds[j].get("type", "")).lower() == s["pii_type"]:
                r["type_ok"] += 1
    other_norm = {norm(o["text"]) for o in other}
    for j, p in enumerate(preds):
        if j in matched_pred:
            continue
        on_other = norm(p.get("text")) in other_norm and norm(p.get("text")) != "" or \
            any(iou(o["box"], p["box"]) >= 0.5 or centre_in(o["box"], p["box"]) for o in other)
        r["false_alarms" if on_other else "unmatched_other"] += 1
    r["other_covered"] = sum(1 for o in other if any(centre_in(o["box"], p["box"]) for p in preds))
    return r


def aggregate(rows):
    """rows: list of (entry, score_picture result). Returns {'all': {...}, 'payslip': {...}, ...}."""
    out = {}
    groups = {"all": rows, **{t: [x for x in rows if x[0]["type"] == t] for t in TYPES}}
    for g, rs in groups.items():
        if not rs:
            continue
        s = lambda k: sum(r[k] for _, r in rs)  # noqa: E731
        ratios = [a for _, r in rs for a in r["area_ratios"]]
        out[g] = {
            "pictures": len(rs),
            "value_recall": round(s("found") / max(1, s("personal_text")), 3),
            "box_hit_rate": round(s("box_hit") / max(1, s("personal_all")), 3),
            "value_and_box": round(s("found_box") / max(1, s("personal_text")), 3),
            "type_accuracy_of_found": round(s("type_ok") / max(1, s("found")), 3),
            "false_alarms_per_picture": round(s("false_alarms") / len(rs), 2),
            "other_spans_hit_by_false_alarm": None,
            "unmatched_items_per_picture": round(s("unmatched_other") / len(rs), 2),
            "readable_share": round(1 - s("other_covered") / max(1, s("other")), 3),
            "median_box_area_ratio": round(statistics.median(ratios), 2) if ratios else None,
            "planted_text_values": s("personal_text"), "planted_personal_spans": s("personal_all"),
            "returned_items": s("preds"),
        }
        out[g].pop("other_spans_hit_by_false_alarm")
    return out


def coverage(mask, box):
    """Share of the planted box (x0,y0,x1,y1 pixels) that a boolean mask (H,W) covers."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    h, w = mask.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(mask[y0:y1, x0:x1].mean())


# --- spend ledger -----------------------------------------------------------------------------------

LEDGER = Path(__file__).resolve().parent / "results" / "spend.jsonl"


def cost_usd(wall_s, gpu=None, cpu_cores=0, mem_gib=0):
    rate = (RATES[gpu] if gpu else 0) + cpu_cores * RATES["cpu_core"] + mem_gib * RATES["mem_gib"]
    return wall_s * rate


def spent_total():
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(l)["usd"] for l in LEDGER.read_text().splitlines() if l.strip())


def log_spend(run, wall_s, gpu, cpu_cores, mem_gib, note=""):
    usd = cost_usd(wall_s, gpu, cpu_cores, mem_gib)
    LEDGER.parent.mkdir(exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"run": run, "gpu": gpu, "gpu_seconds": round(wall_s, 1) if gpu else 0,
                            "wall_seconds": round(wall_s, 1), "cpu_cores": cpu_cores, "mem_gib": mem_gib,
                            "usd": round(usd, 4), "note": note}) + "\n")
    total = spent_total()
    print(f"[spend] {run}: {wall_s:.0f}s on {gpu or 'cpu'} = ${usd:.2f}; running total ${total:.2f} of ${SPEND_CAP_USD:.0f}")
    return usd


def guard_budget(reserve_usd):
    """Refuse to start GPU work that could push the total past the cap."""
    total = spent_total()
    if total + reserve_usd > SPEND_CAP_USD:
        raise SystemExit(f"STOP: spent ${total:.2f}, this run may cost ${reserve_usd:.2f}; cap ${SPEND_CAP_USD:.0f}")
