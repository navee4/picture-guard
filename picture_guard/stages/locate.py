"""Locate each private value: its rectangle is the union of the Tesseract word boxes it was matched to, plus a margin
(MARGIN_FRAC of the box height, at least MARGIN_PX; day 8 measured the choice). Not sure if a finding has no box, a box falls outside the picture,
or one box covers more than half the picture (a mis-grouped line)."""
from picture_guard.types import OK, NOT_SURE, StageResult

NAME = "locate"
# (horizontal fraction of the text height, horizontal minimum px, vertical fraction, vertical minimum px). Day 7 was (0.25, 3, 0.25, 3).
# `options["margin"]` overrides it with these four numbers, or with two (used for both directions).
MARGIN = (1.0, 8, 1.0, 8)


def margins(options: dict) -> tuple:
    m = tuple(options.get("margin", MARGIN))
    return m if len(m) == 4 else (m[0], m[1], m[0], m[1])


def run(ctx) -> StageResult:
    w, h = ctx.loaded.width, ctx.loaded.height
    hf, hpx, vf, vpx = margins(ctx.options)
    boxes = []
    for f in ctx.data.get("findings", []):
        x0, y0, x1, y1 = f["box"]
        if x1 <= x0 or y1 <= y0 or x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
            return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} value has no usable word box (fail-safe rule 1)")
        padx, pady = max(hpx, round(hf * (y1 - y0))), max(vpx, round(vf * (y1 - y0)))
        b = [max(0, x0 - padx), max(0, y0 - pady), min(w, x1 + padx), min(h, y1 + pady)]
        if (b[2] - b[0]) * (b[3] - b[1]) > 0.5 * w * h:
            return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} box covers more than half the picture")
        boxes.append(b)
    return StageResult(OK, {"boxes": boxes, "count": len(boxes)}, f"{len(boxes)} rectangles")
