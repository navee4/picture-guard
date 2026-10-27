"""Tesseract word boxes. Runs the `tesseract` program (CPU, no GPU, no network) and parses its TSV."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

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
