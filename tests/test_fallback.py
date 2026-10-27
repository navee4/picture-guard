"""Day 4: fallbacks for values Tesseract cannot find (zoom read, line cover) and the region re-check. Modal is faked."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from picture_guard import fallback, ocr
from picture_guard.pipeline import default_plan, protect
from picture_guard.remote.fake import FakeGuard
from picture_guard.remote.client import RemoteError
from picture_guard.stages import check_safe
from picture_guard.types import Context, OK, NOT_SURE

from tests.test_models import draw, needs_tesseract

NAME_ITEM = {"text": "Katie Edwards", "boxes": [[30, 25, 330, 70]]}  # px frame, where the name is drawn
GHOST_ITEM = {"text": "Zed Quillfeather", "boxes": [[30, 105, 330, 150]]}


class Frames(unittest.TestCase):
    def test_pixels_vs_thousandths_vs_unit(self):
        w, h = 2000, 1000
        t = [(600, 300, 800, 350)]
        px = [([[600, 300, 800, 350]], t)]
        k = [([[300, 300, 400, 350]], t)]  # x/2000*1000 = 300..400 on a 1000-wide frame
        u = [([[0.3, 0.3, 0.4, 0.35]], t)]
        self.assertEqual(fallback.calibrate(px, w, h)[0], "px")
        self.assertEqual(fallback.calibrate(k, w, h)[0], "norm1000")
        self.assertEqual(fallback.calibrate(u, w, h)[0], "norm1")

    def test_no_anchor_or_a_tie_is_unresolved(self):
        self.assertIsNone(fallback.calibrate([], 900, 900)[0])
        self.assertIsNone(fallback.calibrate([([[0, 0, 5, 5]], [(500, 500, 600, 600)])], 900, 900)[0])

    def test_junk_and_huge_boxes_are_dropped(self):
        self.assertEqual(fallback.usable_boxes([[5, 5, 1, 1], ["a"], [0, 0, 900, 900], [10, 10, 80, 40]], "px", 900, 900), [[10.0, 10.0, 80.0, 40.0]])


@needs_tesseract
class Fallbacks(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.src, self.out, self.rep = self.d / "in.png", self.d / "safe.png", self.d / "report.json"
        draw(["Katie Edwards", "Sort code 12-34-56 thanks"]).save(self.src)
        self.values = [{"text": "Katie Edwards", "type": "name"}, {"text": "Zed Quillfeather", "type": "name"}]

    def tearDown(self):
        self._t.cleanup()

    def run_pg(self, guard, mode):
        return protect(self.src, self.out, self.rep, default_plan(), guard=guard, options={"fallback": mode})

    def black(self):
        return np.asarray(Image.open(self.out)).max() == 0

    def guard(self, **kw):
        return FakeGuard(values=self.values, box_items=[NAME_ITEM, GHOST_ITEM], **kw)

    def test_baseline_without_fallback_unlocated_value_is_rule_1(self):
        rep = self.run_pg(self.guard(), "none")
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["failsafe_rule"], 1)

    def test_line_cover_places_the_value_and_covers_its_line(self):
        rep = self.run_pg(self.guard(), "line")
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        a = np.asarray(Image.open(self.out).convert("L"))
        self.assertEqual(a[105:150, 30:330].max(), 0)  # the rough box is black
        d = next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["fallback"]
        self.assertEqual((d["by_line"], d["frame"]), (1, "px"))

    def test_zoom_places_the_value_when_the_zoom_read_finds_it(self):
        with mock.patch.object(fallback, "zoom_locate", return_value=([[30, 105, 330, 150]], [0, 90, 400, 170])):
            rep = self.run_pg(self.guard(), "zoom")
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["fallback"]["by_zoom"], 1)

    def test_zoom_with_no_calibrated_frame_tries_every_frame(self):
        g = FakeGuard(values=self.values, box_items=[GHOST_ITEM])  # no anchor: no frame can be calibrated
        seen = []

        def fake(image, value, rough):
            seen.append(rough[0])
            return None, [0, 0, 10, 10]
        with mock.patch.object(fallback, "zoom_locate", side_effect=fake):
            rep = self.run_pg(g, "zoom")
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(len(seen), 2)  # px and norm1000 were tried; norm1 turns this pixel box into a huge one, which is dropped

    def test_default_mode_is_zoom(self):
        rep = protect(self.src, self.out, self.rep, default_plan(), guard=self.guard())
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["fallback"]["mode"], "zoom")

    def test_zoom_that_finds_nothing_leaves_rule_1(self):
        rep = self.run_pg(self.guard(), "zoom")  # the value is not on the picture: the zoom read cannot find it
        self.assertTrue(rep["fail_safe"]["whole_black"])

    def test_zoom_then_line_falls_back_to_the_line(self):
        rep = self.run_pg(self.guard(), "zoom+line")
        self.assertFalse(rep["fail_safe"]["whole_black"], rep["fail_safe"])
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "decide")["answer"]["fallback"]["by_line"], 1)

    def test_box_call_fails_error_or_junk_is_whole_black(self):
        for g in (self.guard(raise_error="gone"), self.guard(box_error="JSON error: x")):
            rep = self.run_pg(g, "line")
            self.assertTrue(rep["fail_safe"]["whole_black"])
        junk = FakeGuard(values=self.values, box_items=[{"text": "Zed Quillfeather", "boxes": [["a", "b"]]}, {"text": "x"}])
        self.assertTrue(self.run_pg(junk, "line")["fail_safe"]["whole_black"])

    def test_no_anchor_means_unresolved_and_whole_black(self):
        g = FakeGuard(values=self.values, box_items=[GHOST_ITEM])  # no box for the located value: no anchor
        self.assertTrue(self.run_pg(g, "line")["fail_safe"]["whole_black"])

    def test_boxes_that_miss_every_anchor_are_unresolved(self):
        g = FakeGuard(values=self.values, box_items=[{"text": "Katie Edwards", "boxes": [[600, 300, 700, 340]]}, GHOST_ITEM])
        self.assertTrue(self.run_pg(g, "line")["fail_safe"]["whole_black"])

    def test_report_holds_no_private_text(self):
        self.run_pg(self.guard(), "line")
        txt = self.rep.read_text()
        self.assertNotIn("Zed Quillfeather", txt)
        self.assertNotIn("Katie", txt)


@needs_tesseract
class RegionRecheck(unittest.TestCase):
    def ctx(self, safe):
        loaded = mock.Mock(width=safe.width, height=safe.height)
        c = Context(loaded=loaded, in_path="", out_path="", safe_image=safe)
        c.data = {"findings": []}
        return c

    def test_region_that_still_shows_its_value_turns_the_picture_black(self):
        safe = draw(["Katie Edwards"])
        c = self.ctx(safe)
        c.data["fallback_regions"] = [{"box": [0, 0, 400, 100], "text": "Katie Edwards"}]
        r = check_safe.run(c)
        self.assertEqual(r.status, NOT_SURE)
        self.assertEqual(r.answer["failsafe_rule"], 2)

    def test_covered_region_passes(self):
        safe = draw(["Katie Edwards"])
        safe.paste((0, 0, 0), (0, 0, 420, 110))
        c = self.ctx(safe)
        c.data["fallback_regions"] = [{"box": [0, 0, 400, 100], "text": "Katie Edwards"}]
        r = check_safe.run(c)
        self.assertEqual(r.status, OK, r.why)
        self.assertEqual(r.answer["regions_rechecked"], 1)

    def test_empty_region_is_not_sure(self):
        c = self.ctx(draw(["x"]))
        c.data["fallback_regions"] = [{"box": [10, 10, 10, 10], "text": "x"}]
        self.assertEqual(check_safe.run(c).status, NOT_SURE)


if __name__ == "__main__":
    unittest.main()
