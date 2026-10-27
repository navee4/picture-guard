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


def ocr_text_strict(path: str) -> str:
    """A harder read-back (day 6): the plain read PLUS reads of the picture with dark areas inverted and with local contrast stretched.
    A value that only these reads can see still counts as left readable."""
    import tempfile
    from pathlib import Path
    from PIL import Image
    from picture_guard import ocr
    img = Image.open(path).convert("RGB")
    parts = [ocr_text(path)]
    with tempfile.TemporaryDirectory(prefix="pg-rb-") as d:
        for i, name in enumerate(("inv", "loc", "invloc")):
            v = ocr.CLEANUP_FNS[name](img)
            if v is None:
                continue
            f = Path(d) / f"{i}.png"
            v.resize((v.width * 2, v.height * 2)).save(f)
            parts.append(ocr_text(str(f)))
    return "\n".join(parts)
