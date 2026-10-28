"""Day 2: EXIF rotation, skipped stages, the real read/decide/locate/black_out chain on a drawn picture, report privacy."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from picture_guard import imaging, ocr, readback
from picture_guard.pipeline import default_plan, protect
from picture_guard.remote.fake import FakeGuard
from picture_guard.types import NOT_SURE, OK, StageResult

TEXT_OK = ["Sort code 12-34-56", "Account number 12345678", "Date of birth 12 Jan 1976", "Total 12.50 thanks"]
needs_tesseract = unittest.skipUnless(ocr.available(), "tesseract is not installed")


def draw(lines, size=(900, 420)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default(size=34)
    for i, t in enumerate(lines):
        d.text((30, 30 + i * 80), t, fill="black", font=f)
    return im


def with_stubs_sure(plan):  # kept for the tests that only look at reading and rotation; the model stages answer through a fake Modal
    return plan


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.out, self.rep = self.d / "safe.png", self.d / "report.json"

    def tearDown(self):
        self._t.cleanup()


class ExifRotation(Base):
    def test_rotation_is_applied_before_everything_and_then_dropped(self):
        im = Image.new("RGB", (120, 80), "white")
        ImageDraw.Draw(im).rectangle([0, 0, 19, 19], fill=(255, 0, 0))  # red square, top-left as stored
        ex = Image.Exif()
        ex[0x0112] = 6  # "rotate 90 degrees clockwise to display"
        src = self.d / "rot.jpg"
        im.save(src, exif=ex, quality=100)
        rep = protect(src, self.out, self.rep, with_stubs_sure(_plan_all_sure()))
        out = Image.open(self.out)
        self.assertEqual(out.size, (80, 120))  # width and height swapped
        a = np.asarray(out.convert("RGB"))
        self.assertGreater(a[5, 75, 0], 200)  # red is now top-right
        self.assertLess(a[5, 75, 1], 80)
        self.assertGreater(a[5, 5].min(), 200)  # and the old top-left corner is white
        self.assertTrue(rep["input"]["exif_rotated"])
        self.assertEqual(rep["input"]["stored_size"], [120, 80])
        self.assertEqual(rep["output"]["width"], 80)
        self.assertEqual(set(imaging.png_chunks(self.out)), {b"IHDR", b"IDAT", b"IEND"})
        self.assertEqual(len(out.getexif()), 0)

    def test_whole_black_copy_has_the_rotated_size(self):
        src = self.d / "rot.jpg"
        ex = Image.Exif()
        ex[0x0112] = 8
        Image.new("RGB", (100, 40), "white").save(src, exif=ex)
        protect(src, self.out, self.rep, default_plan())
        self.assertEqual(Image.open(self.out).size, (40, 100))

    @needs_tesseract
    def test_sideways_photo_is_read_after_rotation(self):
        upright = draw(TEXT_OK)
        sideways = upright.rotate(90, expand=True)  # stored on its side ...
        ex = Image.Exif()
        ex[0x0112] = 6  # ... with the tag that says "turn it 90 degrees clockwise" to display it upright
        src = self.d / "side.png"
        sideways.save(src, exif=ex)
        rep = protect(src, self.out, self.rep, default_plan(), guard=FakeGuard())
        self.assertEqual(Image.open(self.out).size, upright.size)
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        self.assertGreaterEqual(rep["output"]["boxes_filled"], 3)


def _plan_all_sure():
    p = default_plan()
    for st in p.detect:
        st.run = lambda ctx: StageResult(OK, {}, "test: sure")
    return p


@needs_tesseract
class RealChain(Base):
    def setUp(self):
        super().setUp()
        self.src = self.d / "doc.png"
        draw(TEXT_OK).save(self.src)

    def test_values_are_covered_and_ordinary_text_stays(self):
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=FakeGuard(), options={"margin": (0.25, 3)})  # a tight margin keeps the label beside the value
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        status = {s["name"]: s["status"] for s in rep["stages"]}
        for n in ("read", "decide", "locate", "black_out"):
            self.assertEqual(status[n], "ok", n)
        found = next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["values_found_by_type"]
        self.assertEqual(set(found), {"sort_code", "account_number", "dob"})
        text = readback.norm(readback.ocr_text(str(self.out)))
        for planted in ("12-34-56", "12345678", "12 Jan 1976"):
            self.assertFalse(readback.found(planted, text), planted)
        self.assertTrue(readback.found("thanks", text))  # ordinary text is still readable
        self.assertTrue(readback.found("Sort code", text))  # labels too

    def test_default_margin_covers_the_value_and_leaves_distant_text(self):
        draw(["Dear Katie Edwards", "", "", "", "Kind regards and thanks"]).save(self.src)
        g = FakeGuard(values=[{"text": "Katie Edwards", "type": "name"}])
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=g)  # the default (wide) margin
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        text = readback.norm(readback.ocr_text(str(self.out)))
        self.assertFalse(readback.found("Katie", text))
        self.assertTrue(readback.found("thanks", text))

    def test_report_holds_no_private_text(self):
        g = FakeGuard(values=[{"text": "Katie Edwards", "type": "name"}])
        draw(["Dear Katie Edwards", "Sort code 12-34-56 thanks"]).save(self.src)
        protect(self.src, self.out, self.rep, default_plan(), guard=g)
        blob = self.rep.read_text()
        for planted in ("12-34-56", "Katie", "Edwards", "thanks"):  # rule values, Glimmer values and ordinary words
            self.assertNotIn(planted, blob)
        self.assertIn("remote_calls", blob)

    def test_a_glimmer_value_is_located_and_covered(self):
        draw(["Dear Katie Edwards", "Sort code 12-34-56"]).save(self.src)
        g = FakeGuard(values=[{"text": "Katie Edwards", "type": "name"}])
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=g, options={"margin": (0.25, 3)})
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        text = readback.norm(readback.ocr_text(str(self.out)))
        self.assertFalse(readback.found("Katie", text))
        self.assertFalse(readback.found("12-34-56", text))
        self.assertTrue(readback.found("Dear", text))
        decide = next(s for s in rep["stages"] if s["name"] == "decide")
        self.assertEqual(decide["answer"]["glimmer_values"], 1)
        self.assertEqual(decide["answer"]["glimmer_values_unlocated"], 0)

    def test_a_glimmer_value_with_no_word_box_is_rule_1(self):
        draw(["Dear Katie Edwards", "Sort code 12-34-56"]).save(self.src)
        g = FakeGuard(values=[{"text": "Zebediah Quux", "type": "name"}])
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=g)
        self.assertTrue(rep["fail_safe"]["whole_black"])
        decide = next(s for s in rep["stages"] if s["name"] == "decide")
        self.assertEqual((decide["status"], decide["answer"]["failsafe_rule"]), ("not_sure", 1))
        self.assertEqual(np.asarray(Image.open(self.out)).max(), 0)
        status = {s["name"]: s["status"] for s in rep["stages"]}
        self.assertEqual(status["locate"], "skipped")  # later stages do not run after the first "not sure"
        self.assertEqual(status["faces"], "skipped")
        self.assertEqual(status["check_safe"], "skipped")

    def test_the_word_list_is_only_measured_not_a_gate(self):
        draw(["Dear Katie Edwards", "Sort code 12-34-56"]).save(self.src)
        g = FakeGuard(values=[{"text": "Katie Edwards", "type": "name"}])
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=g)
        decide = next(s for s in rep["stages"] if s["name"] == "decide")
        self.assertTrue(decide["answer"]["word_list_would_refuse"])  # day 2 would have refused ...
        self.assertFalse(rep["fail_safe"]["whole_black"])  # ... day 3 does not

    def test_no_guard_means_whole_black(self):
        rep = protect(self.src, self.out, self.rep)
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertIn("no models available", rep["fail_safe"]["reasons"][0])

    def test_blank_picture_is_not_sure_at_read(self):
        Image.new("RGB", (400, 300), "white").save(self.src)
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=FakeGuard())
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "read")["status"], "not_sure")

    def test_ablation_is_labelled_and_covers_without_the_alarms(self):
        draw(["Dear Katie Edwards", "Sort code 12-34-56"]).save(self.src)
        rep = protect(self.src, self.out, self.rep, ablation=True)
        self.assertIn("NOT A PRODUCT RESULT", rep["mode"])
        self.assertFalse(rep["fail_safe"]["whole_black"])
        self.assertGreaterEqual(rep["output"]["boxes_filled"], 1)
        text = readback.norm(readback.ocr_text(str(self.out)))
        self.assertFalse(readback.found("12-34-56", text))
        self.assertTrue(readback.found("Katie", text))  # the name is NOT covered: the rules cannot see it


class SkipLogic(Base):
    def test_stage_after_a_not_sure_is_skipped_and_reported(self):
        p = _plan_all_sure()
        p.detect[1].run = lambda ctx: StageResult(NOT_SURE, {}, "unsure")
        src = self.d / "a.png"
        Image.new("RGB", (50, 50), "white").save(src)
        rep = protect(src, self.out, self.rep, p)
        st = [s["status"] for s in rep["stages"]]
        self.assertEqual(st[:5], ["ok", "not_sure", "skipped", "skipped", "skipped"])
        self.assertEqual(st[5], "ok")  # black_out still runs and writes the whole black picture
        self.assertEqual(st[6], "skipped")  # check_safe has nothing to check
        self.assertIn("skipped", rep["stages"][2]["why"])


if __name__ == "__main__":
    unittest.main()
