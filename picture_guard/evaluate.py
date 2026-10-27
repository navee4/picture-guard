"""pg eval: run `pg protect` on each picture of a test set (one split) and measure the safe copy.

Reads the sets' key.json and picture folders only; imports nothing from them. The hold-out split is refused.
"""
from __future__ import annotations

import json
import statistics as st
import subprocess
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


def _black_share(black: np.ndarray, box) -> float | None:
    h, w = black.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(w, int(box[2])), min(h, int(box[3]))
    if x1 <= x0 or y1 <= y0:
        return None
    return float(black[y0:y1, x0:x1].mean())


def _measure(entry, safe_path: Path, report: dict, do_ocr: bool, orig_path: Path | None = None) -> dict:
    img = Image.open(safe_path).convert("RGB")
    black = np.asarray(img).max(axis=2) <= BLACK_MAX
    values = [s for s in entry["spans"] if s["kind"] == "personal" and s["pii_type"] != "face" and s["text"]]
    faces = [s for s in entry["spans"] if s["pii_type"] == "face"]
    plain = [s for s in entry["spans"] if s["kind"] == "other" and s["text"]]
    rec = {
        "file": entry["file"], "type": entry["type"],
        "n_values": len(values), "n_faces": len(faces), "n_plain_spans": len(plain),
        "value_box_black_share": [_black_share(black, s["box"]) for s in values],
        "face_box_black_share": [_black_share(black, s["box"]) for s in faces],
        "plain_box_nonblack_share": [None if (b := _black_share(black, s["box"])) is None else 1 - b for s in plain],
        "whole_black_pixels": bool(black.all()),
        "whole_black_report": report["fail_safe"]["whole_black"],
        "pipeline_seconds": report["total_seconds"],
        "size_ok": (img.width, img.height) == (entry["width"], entry["height"]),
        "png_chunks": report["output"]["png_chunks"],
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
            rec["leak_list"] = [{"type": v["pii_type"], "kind": "never read by Tesseract on the original"}
                                for v in values if not readback.found(v["text"], otext)]
    else:
        rec["readback"] = None
    return rec


def run_eval(set_name: str, split: str, limit: int = 0, results_dir: str | None = None, ablation: bool = False) -> int:
    if split != "dev":
        print(f"pg: error: split {split!r} refused. Only 'dev' may be run until day 9; the hold-out stays sealed.", file=sys.stderr)
        return 2
    base = SETS[set_name]
    key = json.loads((base / "key.json").read_text())
    entries = [e for e in key["images"] if e["split"] == "dev"]  # picture files of other splits are never opened
    if limit:
        entries = entries[:limit]
    do_ocr = readback.available()
    out_dir = Path(results_dir) if results_dir else ROOT / "results" / "pg4"
    out_dir.mkdir(parents=True, exist_ok=True)
    recs, failures = [], []
    t_start = time.time()
    with tempfile.TemporaryDirectory(prefix="pg-eval-") as tmp:
        tmp = Path(tmp)
        for e in entries:
            safe, rep = tmp / "safe.png", tmp / "report.json"
            t0 = time.perf_counter()
            r = subprocess.run([sys.executable, "-m", "picture_guard", "protect", str(base / "images" / e["file"]),
                                "--out", str(safe), "--report", str(rep)] + (["--ablation"] if ablation else []), capture_output=True, text=True, cwd=ROOT)
            wall = time.perf_counter() - t0
            if r.returncode != 0:
                failures.append({"file": e["file"], "exit": r.returncode, "stderr": r.stderr[-400:]})
                continue
            m = _measure(e, safe, json.loads(rep.read_text()), do_ocr, base / "images" / e["file"])
            m["first_failure"] = next((x["name"] for x in json.loads(rep.read_text())["stages"] if x["status"] not in ("ok", "skipped")), None)
            m["boxes_filled"] = json.loads(rep.read_text())["output"]["boxes_filled"]
            m["wall_seconds"] = round(wall, 3)
            recs.append(m)
            safe.unlink(), rep.unlink()
    raw = {"tool_version": __version__, "set": set_name, "split": split, "pictures_asked": len(entries), "pictures_scored": len(recs),
           "mode": "ablation: NOT A PRODUCT RESULT" if ablation else "product", "failures": failures, "tesseract_installed": do_ocr, "black_max_channel": BLACK_MAX,
           "key_sha256": key.get("sha256"), "unix_time": int(t_start),
           "command": f".venv/bin/pg eval --set {set_name} --split {split}" + (" --ablation" if ablation else "") + (f" --limit {limit}" if limit else ""),
           "summary": summarise(recs), "by_value_type": by_value_type(recs), "first_failure_stage": _tally(r.get("first_failure") for r in recs),
           "pictures": recs}
    suffix = "-ablation" if ablation else ""
    (out_dir / f"eval-{set_name}-{split}{suffix}.json").write_text(json.dumps(raw, indent=1))
    table = render_table(set_name, split, raw)
    (out_dir / f"eval-{set_name}-{split}{suffix}.md").write_text(table)
    print(table)
    return 1 if failures else 0


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
            "wall_seconds_mean": _mean([r["wall_seconds"] for r in sel]),
            "readback": ({"values_left": sum(len(x["values_left"]) for x in rb),
                          "plain_readable": sum(x["plain_readable"] for x in rb)} if ran else "not run"),
        }
    return out


def by_value_type(recs: list) -> dict:
    out: dict = {}
    for r in recs:
        for v in r.get("values", []):
            t = out.setdefault(v["type"], {"n": 0, "black_ge90": 0, "black_sum": 0.0, "left_readable": 0, "read_on_original": 0, "ocr_ran": 0})
            t["n"] += 1
            b = v["black_share"] or 0.0
            t["black_sum"] += b
            t["black_ge90"] += b >= 0.9
            if v["left_readable"] is not None:
                t["ocr_ran"] += 1
                t["left_readable"] += bool(v["left_readable"])
                t["read_on_original"] += bool(v["read_on_original"])
    return {k: {**v, "black_mean": round(v.pop("black_sum") / v["n"], 4)} for k, v in sorted(out.items())}


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_table(set_name: str, split: str, raw: dict) -> str:
    s = raw["summary"]
    L = [f"## {set_name}, split {split}, mode: {raw['mode']} ({raw['pictures_scored']} of {raw['pictures_asked']} pictures scored, version {raw['tool_version']})", ""]
    if raw["mode"] != "product":
        L += ["**ABLATION: NOT A PRODUCT RESULT.** Unbuilt stages answered 'nothing found' and the 'rules cannot judge this' alarm was off. Measurement only.", ""]
    if not raw["tesseract_installed"]:
        L += ["Read-back by Tesseract: **not run** (the `tesseract` program is not installed on this Mac).", ""]
    L += ["| Type | Pictures | Planted values | Value boxes black (mean / min) | Faces | Face boxes black (mean / min) | "
          "Plain-text pixels still visible | Whole picture black | Values left readable | Plain spans readable | s/picture (pipeline / wall) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, x in s.items():
        rb = x["readback"]
        left = "not run" if rb == "not run" else str(rb["values_left"])
        pr = "not run" if rb == "not run" else f"{rb['plain_readable']} of {x['plain_spans']}"
        vb = "none planted" if not x["planted_values"] else f"{_pct(x['value_boxes_black_share_mean'])} / {_pct(x['value_boxes_black_share_min'])}"
        fb = "none planted" if not x["planted_faces"] else f"{_pct(x['face_boxes_black_share_mean'])} / {_pct(x['face_boxes_black_share_min'])}"
        wb = f"{x['whole_black_pixels']} of {x['pictures']} ({_pct(x['whole_black_pixels'] / x['pictures'] if x['pictures'] else None)})"
        L.append(f"| {label} | {x['pictures']} | {x['planted_values']} | {vb} | {x['planted_faces']} | {fb} | "
                 f"{_pct(x['plain_text_boxes_nonblack_share_mean'])} | {wb} | {left} | {pr} | "
                 f"{x['pipeline_seconds_mean']} / {x['wall_seconds_mean']} |")
    a = s["all"]
    L += ["", f"Pictures whose first not-sure or failing stage was: {raw['first_failure_stage']} (None = no stage failed)."]
    if raw["by_value_type"]:
        L += ["", "| Value type | Planted | Box 90%+ black | Mean black share | Left readable on safe copy | Read by Tesseract on the original |", "|---|---|---|---|---|---|"]
        for k, v in raw["by_value_type"].items():
            ran = v["ocr_ran"] > 0
            L.append(f"| {k} | {v['n']} | {v['black_ge90']} ({_pct(v['black_ge90'] / v['n'])}) | {_pct(v['black_mean'])} | "
                     f"{v['left_readable'] if ran else 'not run'} | {str(v['read_on_original']) + ' of ' + str(v['n']) if ran else 'not run'} |")
    L += ["", f"Report says whole-black but pixels disagree: {a['report_and_pixels_disagree']}. Safe copy wrong size: {a['size_wrong']}. "
          f"Safe copies with metadata chunks: {a['metadata_chunks_found']}. Pictures that failed to run: {len(raw['failures'])}.", ""]
    return "\n".join(L)
