"""Score the PG-2 runs on the 55 DEV face pictures. Light, runs on the Mac. Reads faces/results/*.json.

    python faces/score.py            # prints tables, writes faces/results/scores.json
"""
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spike"))
import common  # noqa: E402

R = HERE / "results"
key = json.loads((HERE / "key.json").read_text())
E = {e["file"]: e for e in key["images"] if e["split"] == "dev"}
assert len(E) == 55


def faces(e):
    return [s["box"] for s in e["spans"] if s["pii_type"] == "face"]


def group_of(e, box):
    """Groups a face can belong to: picture type, and 'small' = shorter side under 60 px (chat avatars)."""
    side = min(box[2] - box[0], box[3] - box[1])
    g = ["all", e["type"], "small_lt60px" if side < 60 else "large_ge60px", "skin_prompt:" + e["face_attrs"]["skin"]]
    return g


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def med(v):
    return round(st.median(v), 3) if v else None


def glimmer(path):
    d = json.loads(path.read_text())
    out = {"frames": {}, "seconds_per_picture_mean": None}
    recs = {r["file"]: r for r in d["results"]}
    out["parse_errors"] = sum(1 for r in d["results"] if r.get("parse_error"))
    out["seconds_per_picture_mean"] = round(st.mean(r["seconds"] for r in d["results"]), 2)
    out["seconds_per_picture_median"] = round(st.median(r["seconds"] for r in d["results"]), 2)
    out["peak_mib"] = d.get("peak_mib")
    out["gpu_name"] = d.get("gpu_name")
    out["load_seconds"] = d.get("load_seconds")
    for frame in ("px", "norm1000", "norm1"):
        G = {}
        fp = 0
        rep_pics = {"all": [0, 0], "id_card": [0, 0], "chat": [0, 0]}
        for name, e in E.items():
            rec = recs.get(name, {"items": []})
            preds = []
            for it in rec["items"]:
                if str(it.get("type", "")).lower() == "face" and common.valid_box(it.get("box")):
                    preds.append(common.convert_frame(it["box"], frame, e["width"], e["height"]))
            gts = faces(e)
            for t in ("all", e["type"]):
                rep_pics[t][1] += 1
                rep_pics[t][0] += bool(preds)
            fp += sum(1 for p in preds if not any(common.hits(g, p) for g in gts))
            for g in gts:
                ious = [common.iou(g, p) for p in preds]
                found = bool(preds)  # a face was reported somewhere in the picture
                hit = any(common.hits(g, p) for p in preds)
                best = max(ious) if ious else 0.0
                ar = None
                if ious:
                    bp = preds[ious.index(best)]
                    ar = common.area(bp) / max(1.0, common.area(g))
                for grp in group_of(e, g):
                    s = G.setdefault(grp, {"n": 0, "reported_pic": 0, "hit": 0, "iou50": 0, "iou": [], "ratio": []})
                    s["n"] += 1
                    s["reported_pic"] += found
                    s["hit"] += hit
                    s["iou50"] += best >= 0.5
                    s["iou"].append(best)
                    if ar is not None and hit:
                        s["ratio"].append(ar)
        out["frames"][frame] = {
            "false_face_boxes": fp,
            "pictures_with_a_face_reported": {k: f"{v[0]}/{v[1]} ({pct(*v)}%)" for k, v in rep_pics.items()},
            "groups": {k: {"n_faces": s["n"], "box_hit_rate_pct": pct(s["hit"], s["n"]), "hit": s["hit"], "strict_iou_ge_0.5_pct": pct(s["iou50"], s["n"]),
                           "median_best_iou": med(s["iou"]), "median_pred_to_true_area_ratio_of_hits": med(s["ratio"])}
                       for k, s in G.items()}}
    return out


def sam(path):
    d = json.loads(path.read_text())
    P = {p["file"]: p for p in d["pictures"]}
    G = {}
    false_masks = 0
    pics_with_mask = {"all": [0, 0], "id_card": [0, 0], "chat": [0, 0]}
    for name, e in E.items():
        p = P.get(name)
        gts = faces(e)
        for t in ("all", e["type"]):
            pics_with_mask[t][1] += 1
            pics_with_mask[t][0] += bool(p and p["n_masks"] > 0)
        if p:
            false_masks += sum(1 for m in p["masks"] if all(c == 0 for c in m["cov"]))
        for j, g in enumerate(gts):
            best, outer_cov = 0.0, 0.0
            if p and p["masks"]:
                k = max(range(len(p["masks"])), key=lambda i: p["masks"][i]["cov"][j])
                best = p["masks"][k]["cov"][j]
                o = p["masks"][k]["outer"]
                if o and best > 0:
                    ix = max(0, min(o[2], g[2]) - max(o[0], g[0])) * max(0, min(o[3], g[3]) - max(o[1], g[1]))
                    outer_cov = ix / max(1.0, common.area(g))
            union = p["union_cov"][j] if p else 0.0
            for grp in group_of(e, g):
                s = G.setdefault(grp, {"n": 0, "any": 0, "ge50": 0, "ge90": 0, "cov": [], "outer": [], "union": []})
                s["n"] += 1
                s["any"] += best > 0
                s["ge50"] += best >= 0.5
                s["ge90"] += best >= 0.9
                s["cov"].append(best); s["outer"].append(outer_cov); s["union"].append(union)
    secs = [p["seconds"] for p in d["pictures"]]
    return {"errors": len(d.get("errors", [])), "pictures_scored": len(d["pictures"]),
            "pictures_with_a_mask": {k: f"{v[0]}/{v[1]} ({pct(*v)}%)" for k, v in pics_with_mask.items()},
            "masks_touching_no_face": false_masks,
            "seconds_per_picture_mean": round(st.mean(secs), 2) if secs else None,
            "seconds_per_picture_median": round(st.median(secs), 2) if secs else None,
            "peak_mib_nvidia_smi": d.get("peak_mib_nvidia_smi"), "peak_mib_torch_allocated": d.get("peak_mib_torch_allocated"),
            "load_seconds": d.get("load_seconds"),
            "groups": {k: {"n_faces": s["n"], "found_any_overlap_pct": pct(s["any"], s["n"]), "found_cov_ge50_pct": pct(s["ge50"], s["n"]),
                           "found_cov_ge90_pct": pct(s["ge90"], s["n"]),
                           "mean_mask_coverage_pct": round(100 * st.mean(s["cov"]), 1),
                           "mean_outer_rectangle_coverage_pct": round(100 * st.mean(s["outer"]), 1),
                           "mean_union_of_all_masks_coverage_pct": round(100 * st.mean(s["union"]), 1)} for k, s in G.items()}}


if __name__ == "__main__":
    res = {}
    gp, sp = R / "glimmer_q4_faces_dev55.json", R / "sam31_faces_dev55.json"
    if gp.exists():
        res["glimmer"] = glimmer(gp)
    if sp.exists():
        res["sam"] = sam(sp)
    res["dev_faces"] = {"pictures": len(E), "faces": sum(len(faces(e)) for e in E.values()),
                        "id_card_faces": sum(len(faces(e)) for e in E.values() if e["type"] == "id_card"),
                        "chat_faces": sum(len(faces(e)) for e in E.values() if e["type"] == "chat")}
    (R / "scores.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
