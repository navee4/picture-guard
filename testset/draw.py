"""Canvas that records draw ops and spans, and a renderer that applies the 'variety' effects.

A picture is a JSON-able `spec`: size, background, ops, spans, variety. `render(spec, omit=i)`
draws the picture without span i (used by check.py to prove every span is really drawn).
"""
import io
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = "/System/Library/Fonts/Supplemental/"
FAMILIES = {
    "arial": ("Arial.ttf", "Arial Bold.ttf"),
    "georgia": ("Georgia.ttf", "Georgia Bold.ttf"),
    "courier": ("Courier New.ttf", "Courier New Bold.ttf"),
    "verdana": ("Verdana.ttf", "Verdana Bold.ttf"),
    "trebuchet": ("Trebuchet MS.ttf", "Trebuchet MS Bold.ttf"),
    "times": ("Times New Roman.ttf", "Times New Roman Bold.ttf"),
}


@lru_cache(maxsize=None)
def font(fname: str, size: int):
    return ImageFont.truetype(FONT_DIR + fname, size)


_probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))


class Canvas:
    def __init__(self, w, h, bg, family, scale):
        self.w, self.h, self.bg = w, h, tuple(bg)
        self.family, self.scale = family, scale
        self.ops, self.spans = [], []

    def font_file(self, bold=False):
        return FAMILIES[self.family][1 if bold else 0]

    def px(self, size):
        return max(8, round(size * self.scale))

    def width(self, text, size, bold=False):
        return font(self.font_file(bold), self.px(size)).getlength(text)

    def rect(self, box, fill, outline=None, radius=0, width=1):
        self.ops.append({"t": "rect", "box": list(box), "fill": list(fill) if fill else None,
                         "outline": list(outline) if outline else None, "radius": radius, "width": width})

    def ellipse(self, box, fill):
        self.ops.append({"t": "ellipse", "box": list(box), "fill": list(fill)})

    def text(self, xy, text, size, fill, bold=False, kind="other", pii=None, track=True):
        """Draw text with its top-left at xy. Returns the x just past the text."""
        fname, px = self.font_file(bold), self.px(size)
        f = font(fname, px)
        x, y = xy
        if not text:
            return x
        l, t, r, b = _probe.textbbox((x, y), text, font=f)
        span = None
        if track:
            span = len(self.spans)
            self.spans.append({"text": text, "kind": kind, "pii_type": pii,
                               "box": [l - 1, t - 1, r + 1, b + 1]})
        self.ops.append({"t": "text", "xy": [x, y], "text": text, "font": fname, "px": px,
                         "fill": list(fill), "span": span})
        return x + f.getlength(text)

    def line_h(self, size):
        return round(self.px(size) * 1.35)

    def face(self, box, skin, hair, eye):
        span = len(self.spans)
        self.spans.append({"text": "", "kind": "personal", "pii_type": "face", "box": list(box)})
        self.ops.append({"t": "face", "box": list(box), "skin": list(skin), "hair": list(hair),
                         "eye": list(eye), "span": span})

    def spec(self, variety):
        return {"w": self.w, "h": self.h, "bg": list(self.bg), "ops": self.ops,
                "spans": self.spans, "variety": variety}


def _draw_face(d, box, skin, hair, eye):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    d.pieslice((x0, y0, x1, y0 + h * 0.7), 180, 360, fill=tuple(hair))
    d.ellipse((x0 + w * 0.08, y0 + h * 0.12, x1 - w * 0.08, y1), fill=tuple(skin))
    d.pieslice((x0, y0, x1, y0 + h * 0.62), 190, 350, fill=tuple(hair))
    ey = y0 + h * 0.5
    for cx in (x0 + w * 0.34, x0 + w * 0.66):
        d.ellipse((cx - w * 0.06, ey - h * 0.04, cx + w * 0.06, ey + h * 0.04), fill=tuple(eye))
    d.arc((x0 + w * 0.3, y0 + h * 0.62, x1 - w * 0.3, y0 + h * 0.88), 20, 160, fill=(120, 40, 40), width=3)


def _rot_box(box, angle, w, h, pad):
    """Axis-aligned box around `box` after PIL rotate(angle) (counter-clockwise, about the centre)."""
    if angle:
        th = math.radians(angle)
        cx, cy = w / 2, h / 2
        pts = []
        for x, y in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])):
            dx, dy = x - cx, y - cy
            pts.append((cx + dx * math.cos(th) + dy * math.sin(th), cy - dx * math.sin(th) + dy * math.cos(th)))
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        box = [min(xs), min(ys), max(xs), max(ys)]
    x0 = max(0, math.floor(box[0] - pad)); y0 = max(0, math.floor(box[1] - pad))
    x1 = min(w, math.ceil(box[2] + pad)); y1 = min(h, math.ceil(box[3] + pad))
    return [x0, y0, x1, y1]


def final_boxes(spec):
    v = spec["variety"]
    pad = 1 + (math.ceil(2 * v["blur"]) if v.get("blur") else 0)
    return [_rot_box(s["box"], v.get("rotate", 0), spec["w"], spec["h"], pad) for s in spec["spans"]]


def render(spec, omit=None):
    """Return the picture as a PIL RGB image, before file encoding. `omit` = span index to leave out."""
    w, h, v = spec["w"], spec["h"], spec["variety"]
    img = Image.new("RGB", (w, h), tuple(spec["bg"]))
    d = ImageDraw.Draw(img)
    for op in spec["ops"]:
        t = op["t"]
        if op.get("span") is not None and op["span"] == omit:
            continue
        if t == "rect":
            kw = dict(fill=tuple(op["fill"]) if op["fill"] else None,
                      outline=tuple(op["outline"]) if op["outline"] else None, width=op["width"])
            if op["radius"]:
                d.rounded_rectangle(op["box"], radius=op["radius"], **kw)
            else:
                d.rectangle(op["box"], **kw)
        elif t == "ellipse":
            d.ellipse(op["box"], fill=tuple(op["fill"]))
        elif t == "text":
            d.text(tuple(op["xy"]), op["text"], font=font(op["font"], op["px"]), fill=tuple(op["fill"]))
        elif t == "face":
            _draw_face(d, op["box"], op["skin"], op["hair"], op["eye"])
    if v.get("rotate"):
        img = img.rotate(v["rotate"], resample=Image.BICUBIC, fillcolor=tuple(spec["bg"]))
    if v.get("low_contrast"):
        a = np.asarray(img, dtype=np.float32)
        k = v["low_contrast"]
        img = Image.fromarray(np.clip(150 + (a - 128) * k, 0, 255).astype(np.uint8))
    if v.get("blur"):
        img = img.filter(ImageFilter.GaussianBlur(v["blur"]))
        a = np.asarray(img, dtype=np.float32)
        grad = np.linspace(v["shade"], 1.0, w, dtype=np.float32)[None, :, None]  # phone-photo shading
        img = Image.fromarray(np.clip(a * grad, 0, 255).astype(np.uint8))
    if v.get("noise"):
        rs = np.random.RandomState(v["noise_seed"])
        a = np.asarray(img, dtype=np.float32) + rs.normal(0, v["noise"], (h, w, 1))
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img


def encode(img, v) -> bytes:
    buf = io.BytesIO()
    if v["format"] == "png":
        img.save(buf, "PNG", compress_level=6)
    else:
        img.save(buf, "JPEG", quality=v["jpeg_q"], subsampling=2, optimize=False)
    return buf.getvalue()
