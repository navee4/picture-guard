import unittest

from PIL import Image, ImageDraw

from picture_guard import smart


def line_picture():
    img = Image.new("RGB", (400, 60), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 60, 36], fill="black")    # a label
    d.rectangle([160, 20, 230, 36], fill="black")  # the value, as Tesseract boxed it: 170..220
    d.rectangle([232, 20, 260, 36], fill="black")  # its tail, 2 px away
    d.rectangle([330, 20, 360, 36], fill="black")  # unrelated text far away
    return img


class InkBox(unittest.TestCase):
    def test_extends_over_adjacent_ink_only(self):
        b = smart.ink_box(line_picture(), [170, 20, 220, 37], gap_frac=0.5)
        self.assertLessEqual(b[0], 160)
        self.assertGreaterEqual(b[2], 260)
        self.assertGreater(b[0], 60)    # the label is separate ink
        self.assertLess(b[2], 330)      # so is the far text

    def test_never_shrinks(self):
        b = smart.ink_box(Image.new("RGB", (100, 40), "white"), [10, 10, 50, 26])
        self.assertEqual(b, [10, 10, 50, 26])

    def test_light_text_on_dark_counts_as_ink(self):
        img = Image.new("RGB", (200, 40), (20, 20, 20))
        ImageDraw.Draw(img).rectangle([60, 10, 120, 26], fill=(240, 240, 240))
        b = smart.ink_box(img, [80, 10, 100, 27])
        self.assertLessEqual(b[0], 60)
        self.assertGreaterEqual(b[2], 120)


class PartReadable(unittest.TestCase):
    class W:
        def __init__(self, text, box):
            self.text, self.box = text, box

    def test_fragment_inside_region(self):
        w = [self.W("5678", (10, 10, 40, 20))]
        self.assertTrue(smart.part_readable("1234 5678", w, (0, 0, 100, 40)))

    def test_fragment_outside_region_or_too_short(self):
        self.assertFalse(smart.part_readable("1234 5678", [self.W("5678", (300, 10, 340, 20))], (0, 0, 100, 40)))
        self.assertFalse(smart.part_readable("1234 5678", [self.W("56", (10, 10, 20, 20))], (0, 0, 100, 40)))


if __name__ == "__main__":
    unittest.main()
