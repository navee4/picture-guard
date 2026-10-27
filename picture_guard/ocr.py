"""Tesseract word boxes. Runs the `tesseract` program (CPU, no GPU, no network) and parses its TSV."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

PSMS = (6, 11)  # 6 = one block of text, 11 = sparse text. Two passes: a value one pass splits, the other may keep whole.
MIN_CONF = 0  # words are kept at any confidence; low-confidence words still hide text if covered


@dataclass
class Word:
    text: str
    conf: float
    box: tuple  # x0, y0, x1, y1 in picture pixels
    line: tuple  # (block, paragraph, line) ids from Tesseract


class TesseractMissing(RuntimeError):
    pass


def available() -> bool:
    return shutil.which("tesseract") is not None


def read_words(image: Image.Image, psm: int, timeout_s: float = 60.0) -> list[Word]:
    exe = shutil.which("tesseract")
    if exe is None:
        raise TesseractMissing("the tesseract program is not installed")
    with tempfile.TemporaryDirectory(prefix="pg-ocr-") as d:
        f = Path(d) / "in.png"
        image.save(f, format="PNG")
        r = subprocess.run([exe, str(f), "stdout", "--psm", str(psm), "tsv"], capture_output=True, text=True, timeout=timeout_s)
    if r.returncode != 0:
        raise RuntimeError(f"tesseract exit {r.returncode}: {r.stderr[:200]}")
    return parse_tsv(r.stdout)


def parse_tsv(tsv: str) -> list[Word]:
    words = []
    for row in tsv.splitlines()[1:]:
        c = row.split("\t", 11)
        if len(c) < 12 or c[0] != "5" or not c[11].strip():
            continue
        x, y, w, h = (int(v) for v in c[6:10])
        words.append(Word(c[11].strip(), float(c[10]), (x, y, x + w, y + h), (int(c[2]), int(c[3]), int(c[4]))))
    return words


def group_lines(words: list[Word]) -> list[list[Word]]:
    """Words grouped by Tesseract line, lines in reading order (top to bottom by their first word), words left to right."""
    by: dict = {}
    for w in words:
        by.setdefault(w.line, []).append(w)
    lines = [sorted(v, key=lambda w: w.box[0]) for v in by.values()]
    return sorted(lines, key=lambda ln: (min(w.box[1] for w in ln), ln[0].box[0]))


SCALES = (1, 2)  # the second read is on a picture enlarged 2x, which reads small or faint text a plain read misses


def read_passes(image: Image.Image, timeout_s: float = 60.0, cleanups: tuple = ()) -> dict:
    """{"1x-psm6", "1x-psm11", "2x-psm6", "2x-psm11", "2xc-psm6", "2xc-psm11"} -> words. Boxes of the 2x reads are scaled back to the picture."""
    out = {}
    for sc in SCALES:
        img = image if sc == 1 else image.resize((image.width * sc, image.height * sc), Image.LANCZOS)
        for psm in PSMS:
            words = read_words(img, psm, timeout_s)
            if sc != 1:
                for w in words:
                    w.box = tuple(int(round(v / sc)) for v in w.box)
            out[f"{sc}x-psm{psm}"] = words
    # a third read: grey, contrast stretched, 2x, sharpened. On 150 dev pictures it located 45 more AI-listed values than the other reads.
    boosted = ImageOps.autocontrast(image.convert("L"), cutoff=1).resize((image.width * 2, image.height * 2), Image.LANCZOS)
    boosted = boosted.filter(ImageFilter.UnsharpMask(2, 150, 3)).convert("RGB")
    for psm in PSMS:
        words = read_words(boosted, psm, timeout_s)
        for w in words:
            w.box = tuple(int(round(v / 2)) for v in w.box)
        out[f"2xc-psm{psm}"] = words
    for name in cleanups:  # extra reads on cleaned-up copies of the picture; each ADDS passes, so what was found before is still found
        cleaned = CLEANUP_FNS[name](image)
        if cleaned is None:  # nothing to clean (e.g. no dark areas)
            continue
        scale = 3 if name == "big3" else 2
        big = cleaned.resize((cleaned.width * scale, cleaned.height * scale), Image.LANCZOS)
        for psm in PSMS:
            words = read_words(big, psm, timeout_s)
            for w in words:
                w.box = tuple(int(round(v / scale)) for v in w.box)
            out[f"{name}-psm{psm}"] = words
    return out


# ---- picture clean-ups for the reader (day 6). Tesseract misses light text on dark backgrounds; these help it. ----
BLOCK = 24
DARK_MEAN = 110  # a block whose mean brightness is below this counts as dark background
MIN_DARK_SHARE = 0.015  # a dark area must cover at least this share of the picture
TILE = 64


def dark_areas(image: Image.Image) -> list:
    """Boxes of connected dark-background areas (found on a coarse grid of BLOCK x BLOCK blocks)."""
    g = np.asarray(image.convert("L"), dtype=np.float32)
    h, w = g.shape
    gh, gw = -(-h // BLOCK), -(-w // BLOCK)
    pad = np.full((gh * BLOCK, gw * BLOCK), 255.0, dtype=np.float32)
    pad[:h, :w] = g
    dark = pad.reshape(gh, BLOCK, gw, BLOCK).mean(axis=(1, 3)) < DARK_MEAN
    seen = np.zeros_like(dark)
    boxes = []
    for sy in range(gh):
        for sx in range(gw):
            if not dark[sy, sx] or seen[sy, sx]:
                continue
            stack, cells = [(sy, sx)], []
            seen[sy, sx] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < gh and 0 <= nx < gw and dark[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys, xs = [c[0] for c in cells], [c[1] for c in cells]
            box = (min(xs) * BLOCK, min(ys) * BLOCK, min(w, (max(xs) + 1) * BLOCK), min(h, (max(ys) + 1) * BLOCK))
            if len(cells) * BLOCK * BLOCK >= MIN_DARK_SHARE * w * h:
                boxes.append(box)
    return boxes


def invert_dark(image: Image.Image) -> Image.Image | None:
    boxes = dark_areas(image)
    if not boxes:
        return None
    out = image.convert("RGB").copy()
    for b in boxes:
        out.paste(ImageOps.invert(out.crop(b)), b)
    return out


def local_contrast(image: Image.Image) -> Image.Image:
    """Per-tile contrast stretch (flat tiles are left alone so noise is not blown up)."""
    g = image.convert("L")
    out = g.copy()
    for y in range(0, g.height, TILE):
        for x in range(0, g.width, TILE):
            box = (x, y, min(g.width, x + TILE), min(g.height, y + TILE))
            t = g.crop(box)
            if np.asarray(t).std() >= 8:
                out.paste(ImageOps.autocontrast(t, cutoff=2), box)
    return out.convert("RGB")


def invert_then_local(image: Image.Image) -> Image.Image | None:
    inv = invert_dark(image)
    return local_contrast(inv if inv is not None else image)


CLEANUP_FNS = {"inv": invert_dark, "loc": local_contrast, "big3": lambda im: im.convert("RGB"), "invloc": invert_then_local}
CLEANUPS = tuple(CLEANUP_FNS)
DEFAULT_CLEANUPS: tuple = ("loc",)  # chosen on the day-6 dev measurements (see PG9 results)
