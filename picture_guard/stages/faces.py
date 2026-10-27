"""Locate faces (design step 3b): SAM 3.1 with the prompt "face" on Modal. The box is the mask's outer rectangle grown by 15%
of its width and height on each side (clipped to the picture). Not sure if SAM errored or returned nothing usable.
The SAM answer came back with the Glimmer answer in the `decide` call (one trip to Modal)."""
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "faces"
GROW = 0.15


def grow(box, w, h, frac=GROW):
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * frac, (y1 - y0) * frac
    return [max(0, int(round(x0 - dx))), max(0, int(round(y0 - dy))), min(w, int(round(x1 + dx))), min(h, int(round(y1 + dy)))]


def run(ctx) -> StageResult:
    if ctx.ablation:
        return StageResult(OK, {"boxes": []}, "ABLATION: no model called; answers 'nothing found'")
    resp = ctx.data.get("remote")
    sam = resp.get("sam") if isinstance(resp, dict) else None
    if not isinstance(sam, dict) or sam.get("error") or not isinstance(sam.get("masks"), list):
        err = sam.get("error") if isinstance(sam, dict) else "no SAM answer"
        return StageResult(NOT_SURE, {"failsafe_rule": 3}, f"SAM gave no usable answer: {str(err)[:160]}")
    w, h = ctx.loaded.width, ctx.loaded.height
    boxes = []
    for m in sam["masks"]:
        o = m.get("outer") if isinstance(m, dict) else None
        if not (isinstance(o, list) and len(o) == 4 and all(isinstance(v, (int, float)) for v in o) and o[2] > o[0] and o[3] > o[1]):
            return StageResult(NOT_SURE, {"failsafe_rule": 3}, "SAM returned a mask without a usable rectangle")
        boxes.append(grow(o, w, h))
    ctx.data["sam_masks"] = len(boxes)
    return StageResult(OK, {"boxes": boxes, "masks": len(boxes), "sam_seconds": sam.get("seconds")}, f"{len(boxes)} faces (mask rectangles grown {int(GROW * 100)}%)")
