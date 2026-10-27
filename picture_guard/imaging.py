"""Open an input picture, write the safe copy. The safe copy is always a new PNG, the same size as the input,
with no metadata: it is rebuilt from raw pixels, so EXIF, GPS, ICC profiles and text chunks cannot come along."""
from __future__ import annotations

import hashlib
import io
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

MAX_PIXELS = 100_000_000
MAX_BYTES = 200 * 1024 * 1024
IN_SCOPE_FORMATS = {"PNG", "JPEG"}
ALLOWED_PNG_CHUNKS = {b"IHDR", b"IDAT", b"IEND"}

Image.MAX_IMAGE_PIXELS = None  # our own size check below runs before any pixel is decoded


class NotAPictureError(Exception):
    """The input is not a readable picture. Nothing is written when this is raised."""


@dataclass
class Loaded:
    image: Image.Image  # RGB, EXIF rotation already applied
    format: str
    width: int
    height: int
    frames: int
    stored_size: tuple  # (w, h) as stored in the file; differs from (width, height) when EXIF said "rotate"
    exif_rotated: bool
    in_scope: bool
    scope_why: str
    sha256: str
    nbytes: int


def load_picture(path: str | Path) -> Loaded:
    p = Path(path)
    if not p.is_file():
        raise NotAPictureError(f"{p} is not a file")
    if p.stat().st_size > MAX_BYTES:
        raise NotAPictureError(f"{p} is larger than {MAX_BYTES // 2**20} MiB")
    data = p.read_bytes()
    try:
        im = Image.open(io.BytesIO(data))
        fmt, (w, h), frames = im.format or "", im.size, getattr(im, "n_frames", 1)
        if w * h > MAX_PIXELS:
            raise NotAPictureError(f"{p} is {w}x{h}, more than {MAX_PIXELS:,} pixels")
        im.load()
        stored = im.size
        orientation = im.getexif().get(0x0112, 1)
        im = ImageOps.exif_transpose(im)  # rotate the pixels first; metadata is dropped later, on write
        rgb = _flatten(im)
        w, h = rgb.size
    except NotAPictureError:
        raise
    except Exception as ex:  # noqa: BLE001  (PIL raises many types for broken files)
        raise NotAPictureError(f"{p} is not a readable picture ({type(ex).__name__}: {str(ex)[:120]})") from ex
    if fmt not in IN_SCOPE_FORMATS:
        scope = (False, f"format {fmt or 'unknown'} is outside the scope (PNG and JPEG only)")
    elif frames > 1:
        scope = (False, f"{frames} frames; only single pictures are in scope")
    else:
        scope = (True, "PNG or JPEG, single frame")
    return Loaded(rgb, fmt, w, h, frames, stored, orientation not in (None, 1), scope[0], scope[1], hashlib.sha256(data).hexdigest(), len(data))


def _flatten(im: Image.Image) -> Image.Image:
    """RGB copy. Transparent pixels are put on white, which is what a viewer shows, so hidden colour under them is dropped."""
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    return im.convert("RGB")


def all_black(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGB", size, (0, 0, 0))


def write_safe_png(image: Image.Image, path: str | Path) -> None:
    """Rebuild from raw RGB bytes (nothing but pixels), save as PNG, rename into place."""
    clean = Image.frombytes("RGB", image.size, image.convert("RGB").tobytes())
    _atomic(path, lambda f: clean.save(f, format="PNG"))


def write_bytes(path: str | Path, data: bytes) -> None:
    _atomic(path, lambda f: f.write(data))


def _atomic(path, write):
    p = Path(path)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            write(f)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def png_chunks(path: str | Path) -> list[bytes]:
    """Chunk names of a PNG file, in order. Raises ValueError if it is not a well-formed PNG."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    out, i = [], 8
    while i < len(data):
        n, name = struct.unpack(">I4s", data[i:i + 8])
        out.append(name)
        i += 12 + n
    return out


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
