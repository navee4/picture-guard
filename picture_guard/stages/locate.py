"""Locate each private value: its rectangle is the union of the Tesseract word boxes it was matched to, plus a margin
(MARGIN_FRAC of the box height, at least MARGIN_PX; day 8 measured the choice). Not sure if a finding has no box, a box falls outside the picture,
or one box covers more than half the picture (a mis-grouped line)."""
from picture_guard import smart
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
    sm = ctx.options.get("smart") or {}  # day 9: {"ink": {"gap_frac": 0.5, ...} or None, "widen": True/False}; see picture_guard/smart.py
    ink, widen = sm.get("ink"), sm.get("widen")
    if widen:
        levels = [tuple(x) for x in sm.get("levels", smart.LEVELS)]
    elif sm:
        levels = [margins(ctx.options) if "margin" in ctx.options else (0.25, 3, 0.25, 3)]
    else:
        levels = [margins(ctx.options)]
    levels = [m if len(m) == 4 else (m[0], m[1], m[0], m[1]) for m in levels]
    per_level = [[] for _ in levels]
    for f in ctx.data.get("findings", []):
        x0, y0, x1, y1 = f["box"]
        if x1 <= x0 or y1 <= y0 or x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
            return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} value has no usable word box (fail-safe rule 1)")
        base = smart.ink_box(ctx.loaded.image, f["box"], **ink) if ink is not None else [x0, y0, x1, y1]
        for k, (hf, hpx, vf, vpx) in enumerate(levels):
            b = smart.grow(base, w, h, hf, hpx, vf, vpx)
            if (b[2] - b[0]) * (b[3] - b[1]) > 0.5 * w * h:
                return StageResult(NOT_SURE, {"failsafe_rule": 1}, f"a {f['type']} box covers more than half the picture")
            per_level[k].append(b)
    ctx.data["box_levels"] = per_level
    boxes = per_level[0]
    return StageResult(OK, {"boxes": boxes, "count": len(boxes)}, f"{len(boxes)} rectangles")
