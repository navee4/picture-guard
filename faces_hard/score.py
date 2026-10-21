"""Score the PG-3 runs on the 60 DEV harder-face pictures. Light, runs on the Mac. Reads faces_hard/results/*.json.

    python faces_hard/score.py       # prints a summary, writes faces_hard/results/scores.json
"""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spike"))
import common  # noqa: E402

R = HERE / "results"
key = json.loads((HERE / "key.json").read_text())
E = {e["file"]: e for e in key["images"] if e["split"] == "dev"}
assert len(E) == 60


def faces(e):
    return [s for s in e["spans"] if s["pii_type"] == "face"]


def size_bucket(f):
    s = f["face_short_side_px"]
    return "lt20px" if s < 20 else "20-59px" if s < 60 else "60-149px" if s < 150 else "ge150px"


def groups(e, f):
    return ["all", "type:" + e["type"], "skin:" + f["skin_bucket"], "size:" + size_bucket(f), f"type:{e['type']}|skin:{f['skin_bucket']}"]


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def union_rect_cov(rects, box):
    x0, y0, x1, y1 = box
    m = np.zeros((y1 - y0, x1 - x0), bool)
    for r in rects:
        if r is None:
            continue
        a, b, c, d = (int(round(v)) for v in (max(r[0], x0), max(r[1], y0), min(r[2], x1), min(r[3], y1)))
        if c > a and d > b:
            m[b - y0:d - y0, a - x0:c - x0] = True
    return float(m.mean())


def grow(r, m=0.15):
    if r is None:
        return None
    w, h = r[2] - r[0], r[3] - r[1]
    return [r[0] - m * w, r[1] - m * h, r[2] + m * w, r[3] + m * h]


def per_face_sam(d):
    P = {p["file"]: p for p in d["pictures"]}
    rows = []
    for name, e in E.items():
        p = P.get(name)
        for j, f in enumerate(faces(e)):
            best = max((m["cov"][j] for m in p["masks"]), default=0.0) if p else 0.0
            ur = union_rect_cov([m["outer"] for m in p["masks"]], f["box"]) if p else 0.0
            urm = union_rect_cov([grow(m["outer"]) for m in p["masks"]], f["box"]) if p else 0.0
            bs = 0.0
            if p and p["masks"]:
                k = max(range(len(p["masks"])), key=lambda i: p["masks"][i]["cov"][j])
                if p["masks"][k]["cov"][j] > 0:
                    bs = union_rect_cov([p["masks"][k]["outer"]], f["box"])
            rows.append({"file": name, "type": e["type"], "face": f, "e": e, "mask_cov": best, "rect_union_cov": ur, "rect_margin_cov": urm, "rect_best_cov": bs})
    return rows


def sam(path):
    d = json.loads(path.read_text())
    rows = per_face_sam(d)
    G = {}
    for r in rows:
        for g in groups(r["e"], r["face"]):
            s = G.setdefault(g, {"n": 0, "found": 0, "ge50": 0, "cov": [], "ru": [], "rb": [], "ru90": 0, "ru100": 0, "rm90": 0, "rm100": 0})
            s["n"] += 1
            s["found"] += r["mask_cov"] > 0
            s["ge50"] += r["mask_cov"] >= 0.5
            s["cov"].append(r["mask_cov"]); s["ru"].append(r["rect_union_cov"]); s["rb"].append(r["rect_best_cov"])
            s["ru90"] += r["rect_union_cov"] >= 0.9
            s["ru100"] += r["rect_union_cov"] >= 0.999
            s["rm90"] += r["rect_margin_cov"] >= 0.9
            s["rm100"] += r["rect_margin_cov"] >= 0.999
    P = {p["file"]: p for p in d["pictures"]}
    nomask = {}
    for name, e in E.items():
        p = P.get(name)
        nm = sum(1 for m in p["masks"] if all(c == 0 for c in m["cov"])) if p else 0
        t = nomask.setdefault(e["type"], {"pictures": 0, "masks_touching_no_face": 0, "pictures_with_such_a_mask": 0, "masks_total": 0, "true_faces": 0})
        t["pictures"] += 1; t["masks_touching_no_face"] += nm; t["pictures_with_such_a_mask"] += nm > 0
        t["masks_total"] += p["n_masks"] if p else 0; t["true_faces"] += len(faces(e))
    secs = [p["seconds"] for p in d["pictures"]]
    leaks = [{"file": r["file"], "type": r["type"], "face_px": r["face"]["face_short_side_px"], "skin_bucket": r["face"]["skin_bucket"],
              "ita": r["face"]["ita"], "view_or_accessory": r["face"]["prompt_words"]["view_or_accessory"],
              "mask_covers_pct": round(100 * r["mask_cov"], 1), "rect_covers_pct": round(100 * r["rect_union_cov"], 1), "rect_with_margin_covers_pct": round(100 * r["rect_margin_cov"], 1),
              "kind": "missed (no mask touches it)" if r["mask_cov"] == 0 else "partly covered (rectangles cover under 90%)"}
             for r in rows if r["rect_union_cov"] < 0.9]
    return {"errors": len(d.get("errors", [])), "pictures_scored": len(d["pictures"]), "load_seconds": d.get("load_seconds"),
            "seconds_per_picture_mean": round(st.mean(secs), 2), "seconds_per_picture_median": round(st.median(secs), 2),
            "peak_mib_nvidia_smi": d.get("peak_mib_nvidia_smi"), "peak_mib_torch_allocated": d.get("peak_mib_torch_allocated"),
            "masks_by_type": nomask,
            "groups": {k: {"n_faces": s["n"], "found_any_overlap_pct": pct(s["found"], s["n"]), "mask_covers_50pct_plus": pct(s["ge50"], s["n"]),
                           "mean_mask_coverage_pct": round(100 * st.mean(s["cov"]), 1),
                           "mean_rectangles_coverage_pct": round(100 * st.mean(s["ru"]), 1),
                           "rectangles_cover_90pct_plus": pct(s["ru90"], s["n"]), "rectangles_cover_all": pct(s["ru100"], s["n"]),
                           "with_15pct_margin_cover_90pct_plus": pct(s["rm90"], s["n"]), "with_15pct_margin_cover_all": pct(s["rm100"], s["n"]),
                           "mean_best_single_mask_rectangle_coverage_pct": round(100 * st.mean(s["rb"]), 1)}
                       for k, s in sorted(G.items())},
            "leak_list": leaks}, rows


def glimmer(path):
    d = json.loads(path.read_text())
    recs = {r["file"]: r for r in d["results"]}
    out = {"seconds_per_picture_mean": round(st.mean(r["seconds"] for r in d["results"]), 2),
           "seconds_per_picture_median": round(st.median(r["seconds"] for r in d["results"]), 2), "peak_mib": d.get("peak_mib"),
           "load_seconds": d.get("load_seconds"), "parse_errors": sum(1 for r in d["results"] if r.get("parse_error")), "frames": {}}
    counts = {}
    either = {}
    for frame in ("px", "norm1000"):
        G, fp, cnt = {}, 0, {}
        for name, e in E.items():
            rec = recs.get(name, {"items": []})
            preds = [common.convert_frame(it["box"], frame, e["width"], e["height"]) for it in rec["items"]
                     if str(it.get("type", "")).lower() == "face" and common.valid_box(it.get("box"))]
            n_true = len(faces(e))
            counts[name] = len([it for it in rec["items"] if str(it.get("type", "")).lower() == "face"])
            t = cnt.setdefault(e["type"], {"pictures": 0, "count_equal": 0, "count_over": 0, "count_under": 0, "true_faces": 0, "reported_faces": 0})
            t["pictures"] += 1; t["true_faces"] += n_true; t["reported_faces"] += counts[name]
            t["count_equal"] += counts[name] == n_true; t["count_over"] += counts[name] > n_true; t["count_under"] += counts[name] < n_true
            fp += sum(1 for p in preds if not any(common.hits(f["box"], p) for f in faces(e)))
            for f in faces(e):
                hit = any(common.hits(f["box"], p) for p in preds)
                either.setdefault((name, tuple(f["box"])), []).append(hit)
                for g in groups(e, f):
                    s = G.setdefault(g, {"n": 0, "hit": 0})
                    s["n"] += 1; s["hit"] += hit
        out["frames"][frame] = {"false_face_boxes": fp, "count_vs_truth_by_type": cnt,
                                "box_hit": {k: {"n_faces": s["n"], "hit": s["hit"], "hit_pct": pct(s["hit"], s["n"])} for k, s in sorted(G.items())}}
    out["hit_in_either_frame"] = {"note": "upper bound: picks the better frame per face using the truth, so it cannot be done in use",
                                  "n_faces": len(either), "hit": sum(any(v) for v in either.values()),
                                  "hit_pct": pct(sum(any(v) for v in either.values()), len(either))}
    return out, counts


def count_rule(samrows, samd, counts):
    """Glimmer counts more faces than SAM made masks  ->  black out the whole picture."""
    P = {p["file"]: p for p in samd["pictures"]}
    leaky = {}
    for r in samrows:
        if r["rect_union_cov"] < 0.9:
            leaky[r["file"]] = leaky.get(r["file"], 0) + 1
    res = {"pictures": 0, "blacked_out_by_rule": 0, "rule_fires_on_leaky_picture": 0, "rule_fires_on_clean_picture": 0,
           "leaky_pictures": len(leaky), "leaky_pictures_caught": 0, "leaky_pictures_not_caught": [], "by_type": {}}
    for name, e in E.items():
        g, s = counts.get(name, 0), P[name]["n_masks"] if name in P else 0
        fires = g > s
        res["pictures"] += 1; res["blacked_out_by_rule"] += fires
        bt = res["by_type"].setdefault(e["type"], {"pictures": 0, "fires": 0})
        bt["pictures"] += 1; bt["fires"] += fires
        if name in leaky:
            res["leaky_pictures_caught"] += fires
            if not fires:
                res["leaky_pictures_not_caught"].append({"file": name, "true_faces": len(faces(e)), "sam_masks": s, "glimmer_count": g,
                                                         "faces_leaking": leaky[name]})
            res["rule_fires_on_leaky_picture"] += fires
        else:
            res["rule_fires_on_clean_picture"] += fires
    res["share_pictures_blacked_out_pct"] = pct(res["blacked_out_by_rule"], res["pictures"])
    return res


if __name__ == "__main__":
    res = {}
    gp, sp = R / "glimmer_q4_faces_dev60.json", R / "sam31_faces_dev60.json"
    dev_faces = [f for e in E.values() for f in faces(e)]
    from collections import Counter
    res["dev_set"] = {"pictures": 60, "faces": len(dev_faces), "faces_by_type": dict(Counter(e["type"] for e in E.values() for _ in faces(e))),
                      "faces_by_measured_skin_bucket": dict(Counter(f["skin_bucket"] for f in dev_faces)),
                      "faces_by_size": dict(Counter(size_bucket(f) for f in dev_faces))}
    allf = [f for e in key["images"] for f in faces(e)]
    res["whole_set"] = {"pictures": 80, "faces": len(allf), "faces_by_measured_skin_bucket": dict(Counter(f["skin_bucket"] for f in allf)),
                        "faces_by_chardon_band": dict(Counter(f["skin_chardon"] for f in allf))}
    if sp.exists():
        res["sam"], rows = sam(sp)
    if gp.exists():
        res["glimmer"], counts = glimmer(gp)
    if sp.exists() and gp.exists():
        res["count_rule"] = count_rule(rows, json.loads(sp.read_text()), counts)
    (R / "scores.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ("sam", "glimmer")}, indent=1))
