"""pg eval: run the pipeline on each picture of a test set (one split) and measure the safe copy.

Reads the sets' key.json and picture folders only; imports nothing from them. The hold-out split is refused.
Product mode needs the Modal app: one session serves every picture of the run (the cold start is paid once and reported).
"""
from __future__ import annotations

import json
import statistics as st
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

from picture_guard import __version__, readback

ROOT = Path(__file__).resolve().parent.parent
SETS = {"testset": ROOT / "testset", "faces": ROOT / "faces", "faces_hard": ROOT / "faces_hard"}
BLACK_MAX = 16  # a pixel counts as black when its brightest channel is at most this
NO_RULE_TYPES = ["name", "address", "id_number"]
FAILSAFE_RULES = {1: "rule 1: a private value has no word box", 2: "rule 2: the safe copy still shows a private value",
                  3: "rule 3: a stage failed, timed out or read almost nothing", 4: "rule 4: type outside the scope",
                  5: "rule 5: Glimmer counts more faces than SAM found"}


def _black_share(black: np.ndarray, box) -> float | None:
    h, w = black.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(w, int(box[2])), min(h, int(box[3]))
    if x1 <= x0 or y1 <= y0:
        return None
    return float(black[y0:y1, x0:x1].mean())


def _reason(report: dict) -> str | None:
    """Which fail-safe rule made the picture go black, from the report (None if it did not)."""
    if not report["fail_safe"]["whole_black"]:
        return None
    for s in report["stages"]:
        if s["status"] in ("error", "timeout"):
            return FAILSAFE_RULES[3] + f" ({s['name']} {s['status']})"
        if s["status"] == "not_sure":
            return FAILSAFE_RULES.get(s["answer"].get("failsafe_rule", 3)) + f" ({s['name']})"
    return FAILSAFE_RULES[4] if not report["input"]["in_scope"] else "other: " + "; ".join(report["fail_safe"]["reasons"])[:80]


def _measure(entry, safe_path: Path, report: dict, do_ocr: bool, orig_path: Path | None = None) -> dict:
    img = Image.open(safe_path).convert("RGB")
    black = np.asarray(img).max(axis=2) <= BLACK_MAX
    values = [s for s in entry["spans"] if s["kind"] == "personal" and s["pii_type"] != "face" and s["text"]]
    faces = [s for s in entry["spans"] if s["pii_type"] == "face"]
    plain = [s for s in entry["spans"] if s["kind"] == "other" and s["text"]]
    calls = report.get("remote_calls") or []
    remote_s = round(sum(c["round_trip_seconds"] for c in calls), 3)
    rec = {
        "file": entry["file"], "type": entry["type"],
        "n_values": len(values), "n_faces": len(faces), "n_plain_spans": len(plain),
        "value_box_black_share": [_black_share(black, s["box"]) for s in values],
        "face_box_black_share": [_black_share(black, s["box"]) for s in faces],
        "plain_box_nonblack_share": [None if (b := _black_share(black, s["box"])) is None else 1 - b for s in plain],
        "whole_black_pixels": bool(black.all()),
        "whole_black_report": report["fail_safe"]["whole_black"],
        "reason": _reason(report),
        "pipeline_seconds": round(report["total_seconds"] + sum(c["round_trip_seconds"] for c in calls if c.get("replayed")), 3), "remote_seconds": remote_s, "mac_seconds": round(report["total_seconds"] - sum(c["round_trip_seconds"] for c in calls if not c.get("replayed")), 3),
        "glimmer_seconds": next((c["glimmer_seconds"] for c in calls if c.get("glimmer_seconds") is not None), None),
        "size_ok": (img.width, img.height) == (entry["width"], entry["height"]),
        "png_chunks": report["output"]["png_chunks"], "boxes_filled": report["output"]["boxes_filled"],
        "first_failure": next((x["name"] for x in report["stages"] if x["status"] not in ("ok", "skipped")), None),
        "fallback": next((x["answer"].get("fallback") for x in report["stages"] if x["name"] == "decide"), None),
        "word_list_would_refuse": next((x["answer"].get("word_list_would_refuse") for x in report["stages"] if x["name"] == "decide"), None),
    }
    rec["values"] = [{"type": v["pii_type"], "black_share": b, "left_readable": None, "read_on_original": None}
                     for v, b in zip(values, rec["value_box_black_share"])]
    if do_ocr:
        text = readback.norm(readback.ocr_text(str(safe_path)))
        rec["readback"] = {"values_left": [s["text"] for s in values if readback.found(s["text"], text)],
                           "plain_readable": sum(readback.found(s["text"], text) for s in plain)}
        for rv, v in zip(rec["values"], values):
            rv["left_readable"] = readback.found(v["text"], text)
        if orig_path is not None:  # the ceiling: what Tesseract reads when nothing is covered
            otext = readback.norm(readback.ocr_text(str(orig_path)))
            rec["readback_original"] = {"values_read": sum(readback.found(s["text"], otext) for s in values),
                                        "plain_readable": sum(readback.found(s["text"], otext) for s in plain)}
            for rv, v in zip(rec["values"], values):
                rv["read_on_original"] = readback.found(v["text"], otext)
    else:
        rec["readback"] = None
    return rec


def run_eval(set_name: str, split: str, limit: int = 0, results_dir: str | None = None, ablation: bool = False, check_glimmer: bool = False,
             fallback: str = "zoom", replay: bool = False) -> int:
    if split != "dev":
        print(f"pg: error: split {split!r} refused. Only 'dev' may be run until day 9; the hold-out stays sealed.", file=sys.stderr)
        return 2
    from contextlib import nullcontext
    from picture_guard.pipeline import protect
    base = SETS[set_name]
    key = json.loads((base / "key.json").read_text())
    entries = [e for e in key["images"] if e["split"] == "dev"]  # picture files of other splits are never opened
    if limit:
        entries = entries[:limit]
    do_ocr = readback.available()
    out_dir = Path(results_dir) if results_dir else ROOT / "results" / ("pg7" if (fallback != "none" or replay) else "pg6")
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = ("-ablation" if ablation else "") + ("-checkglimmer" if check_glimmer else "") + (f"-fb-{fallback}" if fallback != "none" else "") + ("-replay" if replay and fallback == "none" else "")
    recs, failures = [], []
    t_start = time.time()
    session = nullcontext(None)
    if not ablation:
        from picture_guard.remote.client import ModalGuard
        session = ModalGuard(f"eval-{set_name}-dev{suffix}", reserve_usd=1.0)
        if replay:
            session = _replay_guard(set_name, entries, base, out_dir, f"eval-{set_name}-dev{suffix}")
    cold = info = None
    with session as guard, tempfile.TemporaryDirectory(prefix="pg-eval-") as tmp:
        if guard is not None:
            cold, info = guard.cold_start_seconds, guard.info
        tmp = Path(tmp)
        for e in entries:
            safe, rep = tmp / "safe.png", tmp / "report.json"
            t0 = time.perf_counter()
            try:
                report = protect(base / "images" / e["file"], safe, rep, ablation=ablation, guard=guard, options={"check_glimmer": check_glimmer, "fallback": fallback})
            except Exception as ex:  # noqa: BLE001  (a remote spend-cap stop ends the run; anything else is logged and the run goes on)
                failures.append({"file": e["file"], "error": f"{type(ex).__name__}: {str(ex)[:300]}"})
                if "spend cap" in str(ex):
                    break
                continue
            wall = time.perf_counter() - t0
            if guard is not None and getattr(guard, "calls", None) and set_name and not replay:  # debug copy of the model answers for made-up pictures: git-ignored
                dbg = out_dir / "debug"
                dbg.mkdir(exist_ok=True)
                with open(dbg / f"{set_name}{suffix}.jsonl", "a") as f:
                    f.write(json.dumps({"file": e["file"], "response": getattr(guard, "last", None)}) + "\n")
            m = _measure(e, safe, report, do_ocr, base / "images" / e["file"])
            m["wall_seconds"] = round(wall, 3)
            recs.append(m)
            safe.unlink(), rep.unlink()
    if guard is not None:
        cold, info = guard.cold_start_seconds, guard.info
    raw = {"tool_version": __version__, "set": set_name, "split": split, "pictures_asked": len(entries), "pictures_scored": len(recs),
           "mode": "ablation: NOT A PRODUCT RESULT" if ablation else "product", "check_glimmer": check_glimmer, "fallback": fallback, "replay_of_day3_answers": replay,
           "live_modal_calls": getattr(guard, "live_calls", None),
           "failures": failures, "tesseract_installed": do_ocr, "black_max_channel": BLACK_MAX,
           "modal": {"cold_start_seconds": cold, "container": info},
           "key_sha256": key.get("sha256"), "unix_time": int(t_start),
           "command": f".venv/bin/pg eval --set {set_name} --split {split}" + (" --ablation" if ablation else "") + (" --check-glimmer" if check_glimmer else "") + (f" --fallback {fallback}" if fallback != "none" else "") + (" --replay" if replay else "") + (f" --limit {limit}" if limit else ""),
           "summary": summarise(recs), "by_value_type": by_value_type(recs), "first_failure_stage": _tally(r.get("first_failure") for r in recs),
           "whole_black_reasons": _tally(r.get("reason") for r in recs if r["whole_black_pixels"]),
           "leak_list_still_readable": [{"file": r["file"], "picture_type": r["type"], "value_type": v["type"]}
                                        for r in recs for v in r["values"] if v["left_readable"]],
           "pictures": recs}
    (out_dir / f"eval-{set_name}-{split}{suffix}.json").write_text(json.dumps(raw, indent=1))
    table = render_table(set_name, split, raw)
    (out_dir / f"eval-{set_name}-{split}{suffix}.md").write_text(table)
    print(table)
    return 1 if failures else 0


def _replay_guard(set_name, entries, base, out_dir, run_name):
    """Saved day-3 Glimmer/SAM answers (git-ignored, results/pg6/debug) looked up by the hash of the PNG that `decide` sends."""
    import io
    from picture_guard import imaging
    from picture_guard.remote.replay import ReplayGuard, key_of
    dbg = ROOT / "results" / "pg6" / "debug" / f"{set_name}.jsonl"
    saved_by_file = {}
    for line in dbg.read_text().splitlines():
        r = json.loads(line)
        saved_by_file[r["file"]] = r["response"]
    day3 = json.loads((ROOT / "results" / "pg6" / f"eval-{set_name}-dev.json").read_text())
    trip_by_file = {p["file"]: p["remote_seconds"] for p in day3["pictures"]}
    saved, trips = {}, {}
    for e in entries:
        if e["file"] in saved_by_file and saved_by_file[e["file"]]:
            buf = io.BytesIO()
            imaging.load_picture(base / "images" / e["file"]).image.save(buf, format="PNG")
            k = key_of(buf.getvalue())
            saved[k], trips[k] = saved_by_file[e["file"]], trip_by_file.get(e["file"], 0.0)
    return ReplayGuard(saved, trips, out_dir / "debug" / f"boxes-{set_name}.jsonl", run_name)


def _tally(it):
    out: dict = {}
    for x in it:
        out[str(x)] = out.get(str(x), 0) + 1
    return out


def _mean(v):
    v = [x for x in v if x is not None]
    return round(st.mean(v), 4) if v else None


def summarise(recs: list) -> dict:
    out = {}
    for label, sel in [("all", recs)] + [(t, [r for r in recs if r["type"] == t]) for t in sorted({r["type"] for r in recs})]:
        vs = [x for r in sel for x in r["value_box_black_share"] if x is not None]
        fs = [x for r in sel for x in r["face_box_black_share"] if x is not None]
        ps = [x for r in sel for x in r["plain_box_nonblack_share"] if x is not None]
        rb = [r["readback"] for r in sel]
        ran = bool(rb) and all(x is not None for x in rb)
        kept = [r for r in sel if not r["whole_black_pixels"]]
        kf = [x for r in kept for x in r["face_box_black_share"] if x is not None]
        kv = [x for r in kept for x in r["value_box_black_share"] if x is not None]
        out[label] = {
            "pictures": len(sel), "planted_values": sum(r["n_values"] for r in sel), "planted_faces": sum(r["n_faces"] for r in sel),
            "plain_spans": sum(r["n_plain_spans"] for r in sel),
            "value_boxes_black_share_mean": _mean(vs), "value_boxes_black_share_min": min(vs) if vs else None,
            "face_boxes_black_share_mean": _mean(fs), "face_boxes_black_share_min": min(fs) if fs else None,
            "plain_text_boxes_nonblack_share_mean": _mean(ps),
            "whole_black_pixels": sum(r["whole_black_pixels"] for r in sel),
            "whole_black_report": sum(r["whole_black_report"] for r in sel),
            "report_and_pixels_disagree": sum(r["whole_black_pixels"] != r["whole_black_report"] for r in sel),
            "size_wrong": sum(not r["size_ok"] for r in sel),
            "metadata_chunks_found": sum(not set(r["png_chunks"]) <= {"IHDR", "IDAT", "IEND"} for r in sel),
            "pipeline_seconds_mean": _mean([r["pipeline_seconds"] for r in sel]),
            "mac_seconds_mean": _mean([r["mac_seconds"] for r in sel]), "remote_seconds_mean": _mean([r["remote_seconds"] for r in sel]),
            "wall_seconds_mean": _mean([r["wall_seconds"] for r in sel]),
            "word_list_would_have_refused": sum(bool(r["word_list_would_refuse"]) for r in sel),
            "word_list_judged": sum(r["word_list_would_refuse"] is not None for r in sel),
            "readback": ({"values_left": sum(len(x["values_left"]) for x in rb),
                          "plain_readable": sum(x["plain_readable"] for x in rb)} if ran else "not run"),
            "kept": {  # pictures that were NOT blacked out whole: this is where the product's covering shows
                "pictures": len(kept), "planted_values": sum(r["n_values"] for r in kept), "planted_faces": sum(r["n_faces"] for r in kept),
                "plain_spans": sum(r["n_plain_spans"] for r in kept),
                "values_left_readable": sum(len(r["readback"]["values_left"]) for r in kept) if ran else None,
                "value_boxes_90_black": sum(x >= 0.9 for x in kv), "value_boxes": len(kv),
                "face_boxes_90_black": sum(x >= 0.9 for x in kf), "face_boxes": len(kf), "face_black_mean": _mean(kf),
                "plain_readable": sum(r["readback"]["plain_readable"] for r in kept) if ran else None,
                "plain_readable_on_original": sum(r["readback_original"]["plain_readable"] for r in kept) if ran and all("readback_original" in r for r in kept) else None,
            },
        }
    return out


def by_value_type(recs: list) -> dict:
    out: dict = {}
    for r in recs:
        for v in r.get("values", []):
            t = out.setdefault(v["type"], {"n": 0, "black_ge90": 0, "black_sum": 0.0, "left_readable": 0, "read_on_original": 0, "ocr_ran": 0,
                                           "n_kept": 0, "left_readable_kept": 0})
            t["n"] += 1
            b = v["black_share"] or 0.0
            t["black_sum"] += b
            t["black_ge90"] += b >= 0.9
            if not r["whole_black_pixels"]:
                t["n_kept"] += 1
                t["left_readable_kept"] += bool(v["left_readable"])
            if v["left_readable"] is not None:
                t["ocr_ran"] += 1
                t["left_readable"] += bool(v["left_readable"])
                t["read_on_original"] += bool(v["read_on_original"])
    return {k: {**v, "black_mean": round(v.pop("black_sum") / v["n"], 4)} for k, v in sorted(out.items())}


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_table(set_name: str, split: str, raw: dict) -> str:
    s = raw["summary"]
    L = [f"## {set_name}, split {split}, mode: {raw['mode']}{', second Glimmer check on the safe copy ON' if raw['check_glimmer'] else ''} "
         f"({raw['pictures_scored']} of {raw['pictures_asked']} pictures scored, version {raw['tool_version']})", ""]
    if raw["mode"] != "product":
        L += ["**ABLATION: NOT A PRODUCT RESULT.** No model was called; unbuilt-model stages answered 'nothing found' and the 'cannot judge' alarms were off. Measurement only.", ""]
    if raw["modal"]["cold_start_seconds"] is not None:
        L += [f"Modal: cold start {raw['modal']['cold_start_seconds']} s (both models loaded); container {raw['modal']['container']}.", ""]
    L += ["| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | "
          "Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |", "|---|---|---|---|---|---|---|---|"]
    for label, x in s.items():
        k = x["kept"]
        rb = x["readback"]
        wb = f"{x['whole_black_pixels']} of {x['pictures']} ({_pct(x['whole_black_pixels'] / x['pictures'] if x['pictures'] else None)})"
        left_k = "not run" if k["values_left_readable"] is None else f"{k['values_left_readable']} / {k['planted_values']}"
        pr = "not run" if k["plain_readable"] is None else f"{k['plain_readable']} of {k['plain_spans']} ({k['plain_readable_on_original']})"
        faces = f"{k['face_boxes_90_black']} of {k['face_boxes']}" if k["face_boxes"] else "none planted"
        wbl = "not run" if rb == "not run" else str(rb["values_left"] - (k["values_left_readable"] or 0))
        L.append(f"| {label} | {x['pictures']} | {wb} | {left_k} | {faces} | {pr} | {wbl} | {x['mac_seconds_mean']} / {x['remote_seconds_mean']} / {x['pipeline_seconds_mean']} |")
    L += ["", f"Why pictures went whole black: {json.dumps(raw['whole_black_reasons'], indent=0)}", f"First not-sure or failing stage: {raw['first_failure_stage']} (None = no stage failed)."]
    a = s["all"]
    L += [f"The day-2 word list would have refused {a['word_list_would_have_refused']} of {a['word_list_judged']} pictures that reached `decide`."]
    fbs = [r["fallback"] for r in raw["pictures"] if r.get("fallback") and r["fallback"].get("tried")]
    if fbs:
        L += [f"Fallback ({raw['fallback']}): tried on {len(fbs)} pictures, {sum(f['tried'] for f in fbs)} values; placed by zoom {sum(f['by_zoom'] for f in fbs)}, by line cover {sum(f['by_line'] for f in fbs)}; "
              f"no clear frame in {sum(f['frame'] is None for f in fbs)} pictures. Frames chosen: {_tally(f['frame'] for f in fbs)}."]
    if raw["by_value_type"]:
        L += ["", "| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |", "|---|---|---|---|---|---|"]
        for k, v in raw["by_value_type"].items():
            ran = v["ocr_ran"] > 0
            L.append(f"| {k} | {v['n']} | {v['n_kept']} | {v['left_readable_kept'] if ran else 'not run'} | {v['black_ge90']} ({_pct(v['black_ge90'] / v['n'])}) | {v['left_readable'] if ran else 'not run'} |")
    L += ["", f"Report says whole-black but pixels disagree: {a['report_and_pixels_disagree']}. Safe copy wrong size: {a['size_wrong']}. "
          f"Safe copies with metadata chunks: {a['metadata_chunks_found']}. Pictures that failed to run: {len(raw['failures'])}.", ""]
    return "\n".join(L)
