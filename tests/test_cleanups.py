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
        self.assertEqual(ocr.DEFAULT_CLEANUPS, ("loc", "dig"))

    def test_strict_readback_reads_light_on_dark(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = f"{d}/a.png"
            light_on_dark("Zed Quillfeather").save(p)
            self.assertTrue(readback.found("Zed Quillfeather", readback.norm(readback.ocr_text_strict(p))))


if __name__ == "__main__":
    unittest.main()


@needs_tesseract
class DigitsAndMatching(unittest.TestCase):
    def test_digits_reader_adds_only_digit_characters(self):
        im = Image.new("RGB", (900, 200), "white")
        ImageDraw.Draw(im).text((30, 60), "card is 4000 0566 5566 5556", fill="black", font=ImageFont.load_default(size=40))
        words = ocr.read_passes(im, cleanups=("dig",))
        dig = [w.text for k, ws in words.items() if k.startswith("dig-") for w in ws]
        self.assertTrue(dig)
        self.assertTrue(all(set(t) <= set(ocr.DIGIT_CHARS) for t in dig))
        self.assertIn("4000", " ".join(dig))

    def test_polarity_pass_flips_dark_tiles_only(self):
        im = Image.new("RGB", (256, 128), "white")
        d = ImageDraw.Draw(im)
        d.rectangle([128, 0, 256, 128], fill=(30, 60, 160))
        d.text((140, 40), "Hello", fill="white", font=ImageFont.load_default(size=30))
        d.text((10, 40), "World", fill="black", font=ImageFont.load_default(size=30))
        out = np.asarray(ocr.polarity_contrast(im).convert("L"))
        self.assertGreater(out[5, 200], 200)  # the blue bubble's background is light now
        self.assertGreater(out[5, 20], 200)  # the white half stays light

    def test_look_alike_matching_is_off_by_default_and_never_loosens_text(self):
        from picture_guard import match
        from picture_guard.ocr import Word
        w = [Word("5O-9I-2O", 90, (0, 0, 80, 20), (1, 1, 1))]  # "50-91-20" read with letter look-alikes
        passes = {"1x": w}
        self.assertIsNone(match.locate("50-91-20", passes))
        self.assertIsNotNone(match.locate("50-91-20", passes, lenient={"confusables": True}))
        names = {"1x": [Word("Katle", 90, (0, 0, 50, 20), (1, 1, 1))]}
        self.assertIsNone(match.locate("Katie Edwards", names, lenient={"confusables": True}))
