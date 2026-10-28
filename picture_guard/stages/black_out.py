"""Black out. Fail-safe: the whole picture black. Otherwise: solid black over each located rectangle."""
from PIL import ImageDraw

from picture_guard import imaging, ocr, smart
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "black_out"


def run(ctx) -> StageResult:
    w, h = ctx.loaded.width, ctx.loaded.height
    if ctx.fail_safe:
        ctx.safe_image = imaging.all_black((w, h))
        return StageResult(OK, {"whole_black": True, "boxes_filled": 0}, "fail-safe: the whole picture is black")
    if (ctx.options.get("smart") or {}).get("widen") and ctx.data.get("box_levels"):
        return _widen(ctx)
    img = ctx.loaded.image.copy()
    d = ImageDraw.Draw(img)
    filled = 0
    for x0, y0, x1, y1 in ctx.boxes:
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(w, int(x1)), min(h, int(y1))
        if x1 > x0 and y1 > y0:
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(0, 0, 0))
            filled += 1
    ctx.safe_image = img
    return StageResult(OK, {"whole_black": False, "boxes_filled": filled}, f"filled {filled} rectangles")


WIDEN_READS = ("loc", "dig", "inv", "invloc")  # the strict reads: the default ones plus the dark-area ones


def _fill(image, boxes):
    img = image.copy()
    d = ImageDraw.Draw(img)
    w, h = img.size
    for x0, y0, x1, y1 in boxes:
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(w, int(x1)), min(h, int(y1))
        if x1 > x0 and y1 > y0:
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(0, 0, 0))
    return img


def _widen(ctx) -> StageResult:
    """Day 9, option A: fill at the narrowest level, read the safe copy with the strict reads, widen the box of every value of which a
    part can still be read, and repeat. A value still partly readable at the widest level: not sure (the whole picture goes black)."""
    levels = ctx.data["box_levels"]
    findings = ctx.data["findings"]
    n = len(levels[0])
    face_boxes = list(ctx.boxes[n:])
    cur = [0] * n
    steps = 0
    while True:
        boxes = [levels[cur[i]][i] for i in range(n)]
        img = _fill(ctx.loaded.image, boxes + face_boxes)
        passes = ocr.read_passes(img, cleanups=WIDEN_READS)
        words = [wd for ws in passes.values() for wd in ws]
        bad = []
        for i, f in enumerate(findings):
            if not f.get("text"):
                continue
            wide = levels[-1][i]
            th = wide[3] - wide[1]
            region = [wide[0] - th // 2, wide[1] - th // 2, wide[2] + th // 2, wide[3] + th // 2]
            if smart.part_readable(f["text"], words, region):
                bad.append(i)
        if not bad:
            break
        steps += 1
        for i in bad:
            if cur[i] + 1 >= len(levels):
                return StageResult(NOT_SURE, {"failsafe_rule": 2, "widen_exhausted": True}, "a value is still partly readable at the widest margin (fail-safe rule 2)")
            cur[i] += 1
    ctx.boxes = boxes + face_boxes
    ctx.safe_image = img
    return StageResult(OK, {"whole_black": False, "boxes_filled": len(ctx.boxes), "widen_steps": steps, "widen_levels": cur}, f"filled {len(ctx.boxes)} rectangles after {steps} widening steps")
