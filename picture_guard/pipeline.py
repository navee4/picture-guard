"""The pipeline: read -> decide -> locate -> faces -> count check -> black out -> check the safe copy -> send.

Any "not sure", error or time-out in a stage leads to the fail-safe: the whole picture black. The safe copy is
written here, not in a stage, so "new PNG, same size, no metadata" holds whatever a stage does.
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from picture_guard import __version__, imaging
from picture_guard.stages import black_out, check_safe, count_check, decide, faces, locate, read, send
from picture_guard.types import OK, Context, StageResult

DEFAULT_TIMEOUT_S = 120.0
MODEL_TIMEOUT_S = 300.0  # decide waits for Modal (Glimmer about 6-15 s when warm)
SHORT_TIMEOUT_S = 30.0


@dataclass
class Stage:
    name: str
    run: Callable[[Context], StageResult]
    timeout_s: float = DEFAULT_TIMEOUT_S


def _stage(mod, timeout_s=DEFAULT_TIMEOUT_S) -> Stage:
    return Stage(mod.NAME, mod.run, timeout_s)


DETECT = [_stage(read), _stage(decide, MODEL_TIMEOUT_S), _stage(locate), _stage(faces), _stage(count_check)]
BLACK_OUT = _stage(black_out, SHORT_TIMEOUT_S)
CHECK = _stage(check_safe)
SEND = _stage(send, SHORT_TIMEOUT_S)


@dataclass
class Plan:
    detect: list
    black_out: Stage
    check: Stage
    send: Stage


def default_plan() -> Plan:
    return Plan([replace(s) for s in DETECT], replace(BLACK_OUT), replace(CHECK), replace(SEND))  # fresh copies: callers may edit


def _call(stage: Stage, ctx: Context) -> dict:
    """Run one stage in a daemon thread so a hang cannot hold us. Returns the report record for the stage."""
    box: dict = {}

    def target():
        try:
            box["result"] = stage.run(ctx)
        except BaseException as ex:  # noqa: BLE001
            box["error"] = f"{type(ex).__name__}: {str(ex)[:300]}"
            box["tb"] = traceback.format_exc()[-1500:]

    t0 = time.perf_counter()
    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(stage.timeout_s)
    secs = round(time.perf_counter() - t0, 4)
    rec = {"name": stage.name, "seconds": secs}
    if th.is_alive():
        rec.update(status="timeout", answer={}, why=f"no answer within {stage.timeout_s} s")
    elif "error" in box:
        rec.update(status="error", answer={}, why=box["error"], traceback=box["tb"])
    else:
        r = box.get("result")
        if not isinstance(r, StageResult) or not isinstance(r.answer, dict):
            rec.update(status="error", answer={}, why=f"stage returned {type(r).__name__}, not a StageResult")
        elif r.status == OK:
            rec.update(status="ok", answer=r.answer, why=r.why)
            ctx.results[stage.name] = r
        else:
            rec.update(status="not_sure", answer=r.answer, why=r.why)
    return rec


def _skipped(name: str, because: str) -> dict:
    return {"name": name, "seconds": 0.0, "status": "skipped", "answer": {}, "why": f"skipped: {because}"}


def preflight(in_path, out_path, report_path) -> None:
    """Refuse bad input before anything expensive starts (a Modal session costs money). Writes nothing."""
    if len({Path(p).resolve() for p in (in_path, out_path, report_path)}) != 3:
        raise ValueError("input, safe copy and report must be three different files")
    imaging.load_picture(in_path)


def protect(in_path, out_path, report_path, plan: Plan | None = None, ablation: bool = False, guard=None, options: dict | None = None) -> dict:
    """Write the safe copy and the report. Raises NotAPictureError (nothing written) if the input is not a picture."""
    plan = plan or default_plan()
    ins, outs, reps = (Path(p).resolve() for p in (in_path, out_path, report_path))
    if len({ins, outs, reps}) != 3:
        raise ValueError("input, safe copy and report must be three different files")
    t_all = time.perf_counter()
    if guard is not None and hasattr(guard, "reset_calls"):
        guard.reset_calls()
    loaded = imaging.load_picture(ins)  # raises before anything is written
    ctx = Context(loaded=loaded, in_path=str(ins), out_path=str(outs), ablation=ablation, guard=guard, options=options or {})
    stages, reasons = [], []

    if not loaded.in_scope:
        reasons.append(f"intake: {loaded.scope_why}")
    for st in plan.detect:
        if reasons and not ablation:  # an earlier stage already forced the fail-safe: do not spend time on the rest
            stages.append(_skipped(st.name, reasons[0]))
            continue
        rec = _call(st, ctx)
        stages.append(rec)
        if rec["status"] != "ok":
            reasons.append(f"{rec['name']}: {rec['status']}: {rec['why']}")

    ctx.fail_safe = bool(reasons)
    if not ctx.fail_safe:  # only sure stages feed boxes in; their answers carry "boxes": [[x0, y0, x1, y1], ...]
        for name in ("locate", "faces"):
            ctx.boxes += list(ctx.results[name].answer.get("boxes", [])) if name in ctx.results else []
    rec = _call(plan.black_out, ctx)
    stages.append(rec)
    if rec["status"] != "ok" or ctx.safe_image is None:
        reasons.append(f"{plan.black_out.name}: {rec['status']}: {rec['why']}")
        ctx.fail_safe = True
        ctx.safe_image = imaging.all_black((loaded.width, loaded.height))

    rec = _skipped(plan.check.name, "the whole picture is already black") if ctx.fail_safe else _call(plan.check, ctx)
    stages.append(rec)
    if rec["status"] == "skipped":
        pass
    elif rec["status"] != "ok" and not ctx.fail_safe:
        reasons.append(f"{plan.check.name}: {rec['status']}: {rec['why']}")
        ctx.fail_safe = True
        ctx.safe_image = imaging.all_black((loaded.width, loaded.height))
    elif rec["status"] != "ok":
        reasons.append(f"{plan.check.name}: {rec['status']}: {rec['why']}")

    if ctx.safe_image.size != (loaded.width, loaded.height):  # a stage handed back the wrong size: never trust it
        reasons.append(f"black_out: safe copy was {ctx.safe_image.size}, input is {(loaded.width, loaded.height)}")
        ctx.fail_safe = True
        ctx.safe_image = imaging.all_black((loaded.width, loaded.height))

    imaging.write_safe_png(ctx.safe_image, outs)
    chunks = imaging.png_chunks(outs)
    if not set(chunks) <= imaging.ALLOWED_PNG_CHUNKS:  # cannot happen with write_safe_png; refuse to keep it if it does
        imaging.write_safe_png(imaging.all_black((loaded.width, loaded.height)), outs)
        reasons.append(f"output: unexpected PNG chunks {[c.decode() for c in chunks]}")
        ctx.fail_safe = True
        chunks = imaging.png_chunks(outs)

    stages.append(_call(plan.send, ctx))
    report = {
        "tool": "picture_guard", "version": __version__,
        "mode": "ablation: NOT A PRODUCT RESULT (unbuilt stages switched off)" if ablation else "product",
        "input": {
            "file": ins.name, "sha256": loaded.sha256, "bytes": loaded.nbytes, "format": loaded.format,
            "width": loaded.width, "height": loaded.height, "frames": loaded.frames, "in_scope": loaded.in_scope,
            "stored_size": list(loaded.stored_size), "exif_rotated": loaded.exif_rotated},
        "stages": stages,
        "fail_safe": {"whole_black": ctx.fail_safe, "reasons": reasons},
        "output": {"file": outs.name, "format": "PNG", "width": loaded.width, "height": loaded.height,
                   "sha256": imaging.sha256_file(outs), "png_chunks": [c.decode() for c in chunks],
                   "boxes_filled": 0 if ctx.fail_safe else len(ctx.boxes)},
        "total_seconds": round(time.perf_counter() - t_all, 4),
        "remote_calls": list(getattr(guard, "calls", []) or []),
    }
    imaging.write_bytes(reps, (json.dumps(report, indent=1) + "\n").encode())
    return report
