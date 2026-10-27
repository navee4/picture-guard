"""Fallbacks for a private value that Glimmer lists but Tesseract cannot find on the picture (fail-safe rule 1).

Glimmer gives a rough box. It is a guide only, never the final box on its own:
  1. Calibrate: Glimmer's coordinate frame changes (pixels, 0-1000, 0-1). The values Tesseract DID find are anchors:
     the frame whose boxes overlap the anchors best wins. No clear winner or no anchor: unresolved (the picture goes black).
  2. zoom: crop the area round the box with a wide margin, enlarge it, read it with Tesseract again and locate the value's
     words in the crop. Found: those exact word boxes are used. Not found: unresolved.
  3. line: black out every text line the box touches (all their words, across the full line) plus the padded box itself.

Every fallback box also becomes a region that `check_safe` reads again after the black-out (the region re-check).
Pure functions; no model, no network.
"""
from __future__ import annotations

import math

from PIL import Image

from picture_guard import match, ocr

FRAMES = ("px", "norm1000", "norm1")
MODES = ("none", "zoom", "line", "zoom+line")  # the default is "zoom": the only one that passed the day-4 rule (see PG7 results)
ANCHOR_IOU = 0.3  # a rough box counts as hitting an anchor at this overlap
MAX_BOX_SHARE = 0.25  # a Glimmer box larger than this share of the picture is not a usable guide
ZOOM = 2
MAX_CROP_SIDE = 2400


def valid_box(b) -> bool:
    return (isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in b)
            and b[2] > b[0] and b[3] > b[1])


def to_px(box, frame: str, w: int, h: int) -> list:
    sx, sy = {"px": (1.0, 1.0), "norm1000": (w / 1000, h / 1000), "norm1": (float(w), float(h))}[frame]
    x0, y0, x1, y1 = box
    return [min(x0, x1) * sx, min(y0, y1) * sy, max(x0, x1) * sx, max(y0, y1) * sy]


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix
    return ix / ua if ua > 0 else 0.0


def calibrate(anchors: list, w: int, h: int) -> tuple[str | None, dict]:
    """anchors: [(glimmer_boxes_as_given, tesseract_boxes)] for values Tesseract located. Returns (frame or None, hits by frame)."""
    hits = {}
    for fr in FRAMES:
        n = 0
        for gboxes, tboxes in anchors:
            gp = [to_px(g, fr, w, h) for g in gboxes if valid_box(g)]
            if any(iou(g, t) >= ANCHOR_IOU for g in gp for t in tboxes):
                n += 1
        hits[fr] = n
    best = max(hits.values(), default=0)
    winners = [f for f, n in hits.items() if n == best]
    if best < 1 or len(winners) != 1:  # none at all, or a tie (a picture where two frames mean the same thing is tied only if no anchor decides)
        return None, hits
    return winners[0], hits


def usable_boxes(boxes, frame: str, w: int, h: int) -> list:
    out = []
    for g in boxes or []:
        if not valid_box(g):
            continue
        b = to_px(g, frame, w, h)
        b = [max(0.0, b[0]), max(0.0, b[1]), min(float(w), b[2]), min(float(h), b[3])]
        if b[2] - b[0] < 2 or b[3] - b[1] < 2 or (b[2] - b[0]) * (b[3] - b[1]) > MAX_BOX_SHARE * w * h:
            continue
        out.append(b)
    return out


def pad_box(b, w: int, h: int, fx: float, fy: float, min_x: float = 0, min_y: float = 0) -> list:
    px, py = max(min_x, fx * (b[2] - b[0])), max(min_y, fy * (b[3] - b[1]))
    return [max(0, int(b[0] - px)), max(0, int(b[1] - py)), min(w, int(math.ceil(b[2] + px))), min(h, int(math.ceil(b[3] + py)))]


def union(boxes) -> list:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def zoom_locate(image: Image.Image, value: str, rough: list) -> tuple[list | None, list]:
    """(exact word boxes in picture pixels or None, region read). `rough`: Glimmer's boxes for this value, in pixels."""
    w, h = image.size
    region = pad_box(union(rough), w, h, 0.75, 1.5, 40, 30)
    crop = image.crop(tuple(region))
    z = max(1, min(ZOOM, MAX_CROP_SIDE // max(crop.width, crop.height, 1)))
    if z > 1:
        crop = crop.resize((crop.width * z, crop.height * z), Image.LANCZOS)
    passes = ocr.read_passes(crop)
    boxes = match.locate(value, passes)
    if boxes is None:
        return None, region
    return [[region[0] + b[0] / z, region[1] + b[1] / z, region[0] + b[2] / z, region[1] + b[3] / z] for b in boxes], region


def line_cover(all_words: list, value_rough: list, w: int, h: int) -> tuple[list, list]:
    """(rectangles, region). All words (from every Tesseract pass) are `ocr.Word`s with box and line ids; `all_words` is
    {pass: [Word]}. Cover: the padded rough box, plus the full extent of every line whose words sit on the box."""
    covers = []
    for g in value_rough:
        bh = g[3] - g[1]
        padded = pad_box(g, w, h, 0.5, 0.5, 20, 8)
        covers.append(padded)
        band_y0, band_y1 = g[1] - 0.25 * bh, g[3] + 0.25 * bh
        band_x0, band_x1 = g[0] - (g[2] - g[0]), g[2] + (g[2] - g[0])
        for words in all_words.values():
            lines: dict = {}
            for wd in words:
                lines.setdefault(wd.line, []).append(wd)
            for ln in lines.values():
                touched = [wd for wd in ln if band_y0 <= (wd.box[1] + wd.box[3]) / 2 <= band_y1 and wd.box[2] >= band_x0 and wd.box[0] <= band_x1]
                if touched:
                    covers.append(pad_box(union([wd.box for wd in ln]), w, h, 0.0, 0.25, 4, 3))
    region = pad_box(union(covers), w, h, 0.1, 0.5, 8, 8)
    return covers, region
