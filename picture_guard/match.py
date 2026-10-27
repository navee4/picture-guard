"""Find a value (as the AI or a rule read it) on Tesseract's word boxes. Pure text and boxes; no model.

A value is located when a run of consecutive words on one line reads like it (SequenceMatcher ratio on letters and digits only,
at least THRESHOLD; short values must match exactly). A value that spans lines (an address) is split at line breaks and commas and
every part must be located. All occurrences are returned: a name often appears twice.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from picture_guard.ocr import Word, group_lines

THRESHOLD = 0.85
SHORT = 6  # values with fewer letters and digits than this must match exactly


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", s.lower())


def parts_of(value: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[\n,;]+", value) if len(norm(p)) >= 2]
    return parts or ([value.strip()] if norm(value) else [])


CONFUSABLE = str.maketrans({"o": "0", "i": "1", "l": "1", "|": "1", "s": "5", "b": "8", "z": "2", "g": "6", "q": "9", "t": "7"})


def digit_heavy(s: str) -> bool:
    return len(s) >= 5 and sum(c.isdigit() for c in s) >= 0.6 * len(s)


def _locate_part(part: str, lines: list[list[Word]], threshold: float, lenient: dict | None = None) -> list[tuple]:
    target = norm(part)
    if not target:
        return []
    digits = bool(lenient) and digit_heavy(target)  # numbers and codes: look-alike letters count as the digit they imitate
    if digits:
        threshold = lenient.get("digit_threshold", threshold)
        if lenient.get("confusables"):
            target = target.translate(CONFUSABLE)
    elif lenient:
        threshold = lenient.get("text_threshold", threshold)
    n = max(1, len(part.split()))
    hits = []
    for ln in lines:
        for i in range(len(ln)):
            for size in range(max(1, n - 1), n + 3):
                if i + size > len(ln):
                    break
                cand = norm("".join(w.text for w in ln[i:i + size]))
                if not cand:
                    continue
                if digits and lenient.get("confusables"):
                    cand = cand.translate(CONFUSABLE)
                if abs(len(cand) - len(target)) > max(2, len(target) // 3):
                    continue
                r = 1.0 if cand == target else (0.0 if len(target) < SHORT else SequenceMatcher(None, cand, target).ratio())
                if r >= threshold:
                    bx = [w.box for w in ln[i:i + size]]
                    hits.append((r, (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx))))
    hits.sort(key=lambda h: -h[0])
    kept: list[tuple] = []
    for r, b in hits:  # best first; drop a hit that mostly overlaps one already kept
        if not any(_overlap(b, k) > 0.5 for k in kept):
            kept.append(b)
    return kept


def _overlap(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix / max(1, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def locate(value: str, passes: dict, threshold: float = THRESHOLD, lenient: dict | None = None) -> list[tuple] | None:
    """Boxes for every occurrence of every part of `value`, over all OCR passes; None if some part is found nowhere."""
    grouped = {k: group_lines(ws) for k, ws in passes.items()}
    boxes: list[tuple] = []
    for part in parts_of(value):
        found = []
        for lines in grouped.values():
            for b in _locate_part(part, lines, threshold, lenient):
                if not any(_overlap(b, f) > 0.5 for f in found):
                    found.append(b)
        if not found:
            return None
        boxes += found
    return boxes
