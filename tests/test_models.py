"""Day 3: Modal faked. Every way the models can go wrong gives a whole black picture; the face rules and check_safe."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from picture_guard import ocr
from picture_guard.pipeline import default_plan, protect
from picture_guard.remote.fake import FakeGuard
from picture_guard.stages.faces import grow
from picture_guard.types import OK, StageResult

needs_tesseract = unittest.skipUnless(ocr.available(), "tesseract is not installed")


def draw(lines):
    im = Image.new("RGB", (900, 420), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default(size=34)
    for i, t in enumerate(lines):
        d.text((30, 30 + i * 80), t, fill="black", font=f)
    return im


FACE = {"outer": [600, 100, 700, 220], "area": 9000, "prob": 0.9}


@needs_tesseract
class Models(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.src, self.out, self.rep = self.d / "in.png", self.d / "safe.png", self.d / "report.json"
        draw(["Dear Katie Edwards", "Sort code 12-34-56 thanks"]).save(self.src)
        self.name = [{"text": "Katie Edwards", "type": "name"}]

    def tearDown(self):
        self._t.cleanup()

    def run_pg(self, guard, plan=None, options=None):
        return protect(self.src, self.out, self.rep, plan or default_plan(), guard=guard, options=options)

    def black(self):
        return np.asarray(Image.open(self.out)).max() == 0

    def assert_whole_black(self, rep, stage, status):
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertTrue(self.black())
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == stage)["status"], status)

    def test_baseline_good_answer_is_not_whole_black(self):  # without this the tests below prove nothing
        rep = self.run_pg(FakeGuard(values=self.name, face_count=1, masks=[FACE]))
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        self.assertGreaterEqual(rep["output"]["boxes_filled"], 3)  # two values plus one face

    def test_modal_call_fails(self):
        self.assert_whole_black(self.run_pg(FakeGuard(raise_error="container crashed")), "decide", "not_sure")

    def test_modal_call_times_out(self):
        plan = default_plan()
        plan.detect[1].timeout_s = 0.3
        rep = self.run_pg(FakeGuard(sleep=3), plan)
        self.assert_whole_black(rep, "decide", "timeout")

    def test_modal_answer_is_junk(self):
        self.assert_whole_black(self.run_pg(FakeGuard(junk=True)), "decide", "not_sure")

    def test_glimmer_error_or_unparsable_answer(self):
        self.assert_whole_black(self.run_pg(FakeGuard(glimmer_error="no JSON object in the answer")), "decide", "not_sure")

    def test_glimmer_value_without_text(self):
        self.assert_whole_black(self.run_pg(FakeGuard(values=[{"text": "  ", "type": "name"}])), "decide", "not_sure")

    def test_sam_error(self):
        self.assert_whole_black(self.run_pg(FakeGuard(values=self.name, sam_error="CUDA out of memory")), "faces", "not_sure")

    def test_sam_mask_without_a_rectangle(self):
        self.assert_whole_black(self.run_pg(FakeGuard(values=self.name, masks=[{"outer": None}])), "faces", "not_sure")

    def test_glimmer_counts_more_faces_than_sam_is_rule_5(self):
        rep = self.run_pg(FakeGuard(values=self.name, face_count=2, masks=[FACE]))
        self.assert_whole_black(rep, "count_check", "not_sure")
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "count_check")["answer"]["failsafe_rule"], 5)

    def test_glimmer_counts_fewer_or_equal_is_fine(self):
        for fc in (0, 1):
            self.assertFalse(self.run_pg(FakeGuard(values=self.name, face_count=fc, masks=[FACE]))["fail_safe"]["whole_black"])

    def test_missing_face_count_is_not_sure(self):
        self.assert_whole_black(self.run_pg(FakeGuard(values=self.name, face_count=None, masks=[FACE])), "count_check", "not_sure")

    def test_face_rectangle_is_grown_15_percent_each_way(self):
        self.assertEqual(grow([100, 200, 200, 300], 1000, 1000), [85, 185, 215, 315])
        self.assertEqual(grow([0, 0, 100, 100], 1000, 1000), [0, 0, 115, 115])  # clipped at the picture edge
        self.assertEqual(grow([950, 950, 1000, 1000], 1000, 1000), [942, 942, 1000, 1000])
        self.assertEqual(self.run_pg(FakeGuard(values=self.name, face_count=1, masks=[FACE]))["stages"][3]["answer"]["boxes"], [[585, 82, 715, 238]])

    def test_check_safe_finds_a_value_still_readable(self):
        plan = default_plan()

        def no_cover(ctx):  # a black_out that forgets to cover anything
            ctx.safe_image = ctx.loaded.image.copy()
            return StageResult(OK, {}, "test: covered nothing")
        plan.black_out.run = no_cover
        rep = self.run_pg(FakeGuard(values=self.name), plan)
        self.assert_whole_black(rep, "check_safe", "not_sure")
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "check_safe")["answer"]["failsafe_rule"], 2)

    def test_check_safe_passes_when_covered(self):
        rep = self.run_pg(FakeGuard(values=self.name))
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "check_safe")["status"], "ok")

    def test_optional_glimmer_check_on_the_safe_copy(self):
        ok = self.run_pg(FakeGuard(values=self.name, check_values=[]), options={"check_glimmer": True})
        self.assertFalse(ok["fail_safe"]["whole_black"])
        self.assertEqual(ok["remote_calls"][-1]["call"], "glimmer_only")
        bad = self.run_pg(FakeGuard(values=self.name, check_values=[{"text": "x", "type": "name"}]), options={"check_glimmer": True})
        self.assert_whole_black(bad, "check_safe", "not_sure")
        off = self.run_pg(FakeGuard(values=self.name, check_values=[{"text": "x", "type": "name"}]))  # not asked: not called
        self.assertFalse(off["fail_safe"]["whole_black"])

    def test_original_is_never_in_the_report(self):
        self.run_pg(FakeGuard(values=self.name, face_count=1, masks=[FACE]))
        blob = self.rep.read_text()
        for private in ("Katie", "Edwards", "12-34-56"):
            self.assertNotIn(private, blob)


class Match(unittest.TestCase):
    def test_fuzzy_and_multiline_locate(self):
        from picture_guard import match
        W = lambda t, x, y: ocr.Word(t, 90, (x, y, x + 50, y + 12), (1, 1, y))  # noqa: E731
        passes = {"a": [W("Katie", 0, 0), W("Edwards", 60, 0), W("4", 0, 30), W("Heath", 60, 30), W("Inlet", 120, 30), W("GJ773l016", 0, 60)]}
        self.assertEqual(len(match.locate("Katie Edwards", passes)), 1)
        self.assertEqual(len(match.locate("4 Heath Inlet", passes)), 1)
        self.assertEqual(len(match.locate("GJ7731016", passes) or []), 1)  # OCR misread, close enough
        self.assertIsNone(match.locate("Zebediah Quux", passes))
        self.assertIsNone(match.locate("Katie Edwards, Nowhere Town", passes))  # one part of the value has no box
        self.assertIsNone(match.locate("Kate", passes))  # short values must match exactly


if __name__ == "__main__":
    unittest.main()
