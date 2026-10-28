"""Day 8: the margin round each located value box."""
import unittest

from picture_guard.stages import locate
from picture_guard.types import Context, OK, NOT_SURE


class Loaded:
    width, height = 1000, 800


def run(box, options=None):
    ctx = Context(loaded=Loaded(), in_path="", out_path="", options=options or {})
    ctx.data["findings"] = [{"type": "name", "box": box, "text": "x"}]
    return locate.run(ctx)


class Margin(unittest.TestCase):
    def test_default_is_the_day_8_choice(self):
        self.assertEqual(locate.MARGIN, (1.0, 8, 1.0, 8))

    def test_margin_is_a_multiple_of_the_text_height_with_a_pixel_floor(self):
        r = run([100, 100, 200, 120])  # height 20 -> pad max(8, 20) = 20
        self.assertEqual(r.status, OK)
        self.assertEqual(r.answer["boxes"][0], [80, 80, 220, 140])
        r = run([100, 100, 200, 104])  # height 4 -> pad max(8, 4) = 8
        self.assertEqual(r.answer["boxes"][0], [92, 92, 208, 112])

    def test_override_and_clipping_to_the_picture(self):
        r = run([0, 0, 50, 20], {"margin": (0.25, 3)})
        self.assertEqual(r.answer["boxes"][0], [0, 0, 55, 25])
        r = run([980, 780, 1000, 800])
        self.assertEqual(r.answer["boxes"][0], [960, 760, 1000, 800])

    def test_four_numbers_set_horizontal_and_vertical_margins_apart(self):
        r = run([100, 100, 200, 120], {"margin": (0.25, 3, 1.0, 8)})  # height 20: horizontal pad 5, vertical pad 20
        self.assertEqual(r.answer["boxes"][0], [95, 80, 205, 140])

    def test_a_box_that_grows_past_half_the_picture_is_not_sure(self):
        r = run([100, 100, 900, 700])
        self.assertEqual(r.status, NOT_SURE)


if __name__ == "__main__":
    unittest.main()
