"""Locate each private value: its rectangle is the union of the Tesseract word boxes it was matched to, plus a margin
of a quarter of the box height (at least 3 px). Not sure if a finding has no box, a box falls outside the picture,
or one box covers more than half the picture (a mis-grouped line)."""
from picture_guard.types import OK, NOT_SURE, StageResult

NAME = "locate"


def run(ctx) -> StageResult:
    w, h = ctx.loaded.width, ctx.loaded.height
    boxes = []
    for f in ctx.data.get("findings", []):
        x0, y0, x1, y1 = f["box"]
        if x1 <= x0 or y1 <= y0 or x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
            return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} value has no usable word box (fail-safe rule 1)")
        pad = max(3, round(0.25 * (y1 - y0)))
        b = [max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)]
        if (b[2] - b[0]) * (b[3] - b[1]) > 0.5 * w * h:
            return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} box covers more than half the picture")
        boxes.append(b)
    return StageResult(OK, {"boxes": boxes, "count": len(boxes)}, f"{len(boxes)} rectangles")
