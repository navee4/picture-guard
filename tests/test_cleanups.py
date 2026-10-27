"""Day 6: reader clean-ups. They only ADD reads, so anything found before is still found."""
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from picture_guard import ocr, readback
from tests.test_models import needs_tesseract


def light_on_dark(text="Katie Edwards", size=(900, 300)):
    im = Image.new("RGB", size, (20, 24, 30))
    d = ImageDraw.Draw(im)
    d.text((40, 100), text, fill=(235, 235, 235), font=ImageFont.load_default(size=44))
    return im


class Geometry(unittest.TestCase):
    def test_dark_picture_is_one_dark_area_and_light_picture_none(self):
        self.assertEqual(len(ocr.dark_areas(light_on_dark())), 1)
        self.assertEqual(ocr.dark_areas(Image.new("RGB", (900, 300), "white")), [])
        self.assertIsNone(ocr.invert_dark(Image.new("RGB", (900, 300), "white")))

    def test_inversion_only_changes_the_dark_area(self):
        im = Image.new("RGB", (960, 480), "white")
        ImageDraw.Draw(im).rectangle([0, 240, 960, 480], fill=(15, 15, 15))
        out = np.asarray(ocr.invert_dark(im))
        self.assertGreater(out[100, 100].min(), 200)  # the white half stays white
        self.assertGreater(out[400, 100].min(), 200)  # the dark half is now light
        self.assertEqual(out.shape, (480, 960, 3))

    def test_local_contrast_keeps_size_and_leaves_flat_tiles(self):
        im = Image.new("RGB", (200, 130), (120, 120, 120))
        out = ocr.local_contrast(im)
        self.assertEqual(out.size, im.size)
        self.assertTrue((np.asarray(out) == 120).all())


@needs_tesseract
class Passes(unittest.TestCase):
    def test_cleanups_add_passes_and_keep_the_base_ones(self):
        im = light_on_dark()
        base = ocr.read_passes(im)
        more = ocr.read_passes(im, cleanups=("inv", "loc"))
        self.assertTrue(set(base) < set(more))
        self.assertIn("loc-psm6", more)
        self.assertIn("inv-psm11", more)

    def test_inverted_read_finds_light_on_dark_text(self):
        words = ocr.read_passes(light_on_dark(), cleanups=("inv",))
        text = " ".join(w.text for ws in words.values() for w in ws).lower()
        self.assertIn("katie", text)
        for ws in words.values():
            for w in ws:
                self.assertTrue(0 <= w.box[0] <= 900 and 0 <= w.box[1] <= 300)  # boxes are back in picture pixels

    def test_no_dark_area_means_no_inverted_pass(self):
        words = ocr.read_passes(Image.new("RGB", (400, 200), "white"), cleanups=("inv",))
        self.assertNotIn("inv-psm6", words)

    def test_default_cleanup_is_the_one_measured_on_day_6(self):
        self.assertEqual(ocr.DEFAULT_CLEANUPS, ("loc",))

    def test_strict_readback_reads_light_on_dark(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = f"{d}/a.png"
            light_on_dark("Zed Quillfeather").save(p)
            self.assertTrue(readback.found("Zed Quillfeather", readback.norm(readback.ocr_text_strict(p))))


if __name__ == "__main__":
    unittest.main()
