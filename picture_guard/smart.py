"""Smart margin (day 9). Two ways to avoid a wide box everywhere:

B, ink-aware (`options["smart"]["ink"]`): start from the word box plus a small even margin, then extend it along the text line to
where the printed ink of the value ends (stop at a background gap of GAP x the text height). Ink is any pixel that differs from the
band's own background colour, so light text on dark bubbles counts too.

A, widen on re-read (`options["smart"]["widen"]`): black out at the narrowest level, read each value's neighbourhood on the safe copy
with the strict reads, and widen the box of any value of which a part can still be read, level by level. Out of levels: not sure.
Pure functions on a PIL picture and Tesseract word lists; no model.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from picture_guard import match

INK_DIFF = 48          # a pixel is ink if some colour channel differs from the band background by more than this
LEVELS = ((0.25, 3), (0.5, 5), (0.75, 6), (1.0, 8))  # widening steps; the last is the day-8 default
MIN_PART = 3           # a fragment of a value shorter than this (letters and digits) is not counted as "readable"


def _mode_colour(img: np.ndarray) -> np.ndarray:
    flat = img.reshape(-1, img.shape[-1]).astype(np.int16)
    q = flat // 16
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    return flat[key == np.bincount(key).argmax()].mean(axis=0)


def _ink(img: np.ndarray, bg: np.ndarray | None = None) -> np.ndarray:
    """Boolean mask of ink pixels: differs from the background colour (default: the most common colour of `img`)."""
    bg = _mode_colour(img) if bg is None else bg
    return (np.abs(img.astype(np.int16) - bg).max(axis=2) > INK_DIFF)


def _background(image: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> np.ndarray:
    """Background colour beside a text line: the most common colour in the strips just above and below it (text bands can be mostly ink)."""
    th = max(2, y1 - y0)
    h = image.shape[0]
    strips = [image[max(0, y0 - th // 2):y0, x0:x1], image[y1:min(h, y1 + th // 2), x0:x1]]
    strips = [s for s in strips if s.size]
    return _mode_colour(np.concatenate([s.reshape(-1, 1, 3) for s in strips])) if strips else _mode_colour(image[y0:y1, x0:x1])


def _run_edge(has: np.ndarray, start: int, step: int, gap: int) -> int:
    """From `start` walk in direction `step` over a 1-D ink profile; return the last index with ink reached
    without crossing a gap of more than `gap` empty cells."""
    last, empty, i = start, 0, start
    while 0 <= i < len(has):
        if has[i]:
            last, empty = i, 0
        else:
            empty += 1
            if empty > gap:
                break
        i += step
    return last


def ink_box(image: Image.Image, box, gap_frac: float = 0.5, cap_frac: float = 3.0, vgap: int = 1, vcap_frac: float = 0.35) -> list:
    """The word box grown along its line over the ink that continues it. Never shrinks the box."""
    w, h = image.size
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    th = max(1, y1 - y0)
    capx = int(round(cap_frac * th))
    gap = max(1, int(round(gap_frac * th)))
    bx0, bx1 = max(0, x0 - capx), min(w, x1 + capx)
    by0, by1 = max(0, y0 - th // 2), min(h, y1 + th // 2)
    arr = np.asarray(image.convert("RGB"))
    band = arr[y0:y1, bx0:bx1]
    if band.size == 0:
        return [x0, y0, x1, y1]
    bg = _background(arr, bx0, bx1, y0, y1)
    has = _ink(band, bg).any(axis=0)
    nx0 = bx0 + _run_edge(has, x0 - bx0, -1, gap) if has[: max(1, x0 - bx0 + 1)].any() else x0
    nx1 = bx0 + _run_edge(has, min(len(has) - 1, x1 - bx0 - 1), 1, gap) + 1
    nx0, nx1 = min(nx0, x0), max(nx1, x1)
    vc = int(round(vcap_frac * th))
    ty0, ty1 = max(0, y0 - vc), min(h, y1 + vc)
    rows = _ink(arr[ty0:ty1, nx0:nx1], bg).any(axis=1)
    ny0 = ty0 + _run_edge(rows, y0 - ty0, -1, vgap) if rows.any() else y0
    ny1 = ty0 + _run_edge(rows, min(len(rows) - 1, y1 - ty0 - 1), 1, vgap) + 1
    return [nx0, min(ny0, y0), nx1, max(ny1, y1)]


def grow(box, w: int, h: int, hf: float, hpx: int, vf: float, vpx: int) -> list:
    th = box[3] - box[1]
    padx, pady = max(hpx, round(hf * th)), max(vpx, round(vf * th))
    return [max(0, box[0] - padx), max(0, box[1] - pady), min(w, box[2] + padx), min(h, box[3] + pady)]


def part_readable(value: str, words, region) -> bool:
    """True if some word read inside `region` is a fragment (MIN_PART letters/digits or more) of the value, or the value's own word."""
    target = match.norm(value)
    toks = [match.norm(t) for t in value.replace(",", " ").split()]
    for wd in words:
        cx, cy = (wd.box[0] + wd.box[2]) / 2, (wd.box[1] + wd.box[3]) / 2
        if not (region[0] <= cx <= region[2] and region[1] <= cy <= region[3]):
            continue
        t = match.norm(wd.text)
        if len(t) < MIN_PART:
            continue
        if t in target or any(len(k) >= MIN_PART and (k in t or match.SequenceMatcher(None, t, k).ratio() >= match.THRESHOLD) for k in toks):
            return True
    return False
