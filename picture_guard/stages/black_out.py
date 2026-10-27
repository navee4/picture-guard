"""Black out. Fail-safe: the whole picture black. Otherwise: solid black over each located rectangle."""
from PIL import ImageDraw

from picture_guard import imaging
from picture_guard.types import OK, StageResult

NAME = "black_out"


def run(ctx) -> StageResult:
    w, h = ctx.loaded.width, ctx.loaded.height
    if ctx.fail_safe:
        ctx.safe_image = imaging.all_black((w, h))
        return StageResult(OK, {"whole_black": True, "boxes_filled": 0}, "fail-safe: the whole picture is black")
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
