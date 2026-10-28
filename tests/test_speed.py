"""PG-14: the speed changes must not change a result."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from picture_guard import ocr
from picture_guard.pipeline import protect


def picture():
    img = Image.new("RGB", (420, 160), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 20), "Sort code 12-34-56 Account 12345678", fill="black")
    d.text((20, 60), "Statement for the month of May", fill="black")
    dark = Image.new("RGB", (420, 50), (20, 20, 20))
    ImageDraw.Draw(dark).text((20, 15), "Light text on dark ground 4929 0000 0000 0001", fill=(240, 240, 240))
    img.paste(dark, (0, 100))
    return img


def flat(passes):
    return {k: [(w.text, w.box, w.line) for w in v] for k, v in passes.items()}


class ParallelReads(unittest.TestCase):
    def test_same_words_boxes_and_key_order_as_one_after_the_other(self):
        img = picture()
        with mock.patch.dict(os.environ, {"PG_OCR_WORKERS": "1"}):
            serial = ocr.read_passes(img, cleanups=ocr.DEFAULT_CLEANUPS + ("inv",))
        with mock.patch.dict(os.environ, {"PG_OCR_WORKERS": "6"}):
            parallel = ocr.read_passes(img, cleanups=ocr.DEFAULT_CLEANUPS + ("inv",))
        self.assertEqual(list(serial), list(parallel))
        self.assertEqual(flat(serial), flat(parallel))


class FakeGuard:
    def __init__(self, fail=False):
        self.calls, self.n, self.fail = [], 0, fail

    def reset_calls(self):
        self.calls = []

    def analyse(self, png):
        self.n += 1
        if self.fail:
            from picture_guard.remote.client import RemoteError
            raise RemoteError("down")
        return {"glimmer": {"values": [{"text": "12345678", "type": "account_number"}], "face_count": 0, "error": None, "seconds": 1.0}, "sam": {"masks": [], "error": None}, "container_seconds": 1.0}


class Prefetch(unittest.TestCase):
    def run_once(self, guard):
        d = Path(tempfile.mkdtemp())
        picture().save(d / "in.png")
        rep = protect(d / "in.png", d / "out.png", d / "r.json", guard=guard, options={"fallback": "none"})
        return rep, (d / "out.png").read_bytes()

    def test_one_model_call_per_picture_and_a_deterministic_safe_copy(self):
        g = FakeGuard()
        rep1, png1 = self.run_once(g)
        rep2, png2 = self.run_once(g)
        self.assertEqual(g.n, 2)
        self.assertEqual(png1, png2)
        self.assertFalse(rep1["fail_safe"]["whole_black"])

    def test_a_failed_model_call_still_means_whole_black(self):
        rep, _ = self.run_once(FakeGuard(fail=True))
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertIn("decide", rep["fail_safe"]["reasons"][0])


if __name__ == "__main__":
    unittest.main()
