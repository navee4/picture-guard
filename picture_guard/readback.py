"""Read-back check on a safe copy: run Tesseract and look for text. Needs the `tesseract` program; if it is not
installed the check says "not run" and the harness reports that, it does not guess."""
from __future__ import annotations

import re
import shutil
import subprocess


def available() -> bool:
    return shutil.which("tesseract") is not None


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", s.lower())


def ocr_text(path: str, psms=(11, 6), timeout_s: float = 90.0) -> str:
    """All text Tesseract reads, from two page-segmentation modes (sparse text, and one block), joined."""
    exe = shutil.which("tesseract")
    out = []
    for psm in psms:
        r = subprocess.run([exe, str(path), "stdout", "--psm", str(psm)], capture_output=True, text=True, timeout=timeout_s)
        if r.returncode != 0:
            raise RuntimeError(f"tesseract exit {r.returncode}: {r.stderr[:200]}")
        out.append(r.stdout)
    return "\n".join(out)


def found(value: str, text_norm: str) -> bool:
    v = norm(value)
    return bool(v) and v in text_norm
