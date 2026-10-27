"""The eval harness must not give 100% black to a picture that is not black. Run: .venv/bin/python -m unittest discover -s tests -t ."""
import json
import unittest
from pathlib import Path

from picture_guard import evaluate

ROOT = Path(__file__).resolve().parent.parent


class Measure(unittest.TestCase):
    def test_untouched_picture_scores_as_unprotected(self):
        key = json.loads((ROOT / "testset" / "key.json").read_text())
        e = next(x for x in key["images"] if x["split"] == "dev" and x["type"] == "payslip")
        fake_report = {"fail_safe": {"whole_black": False}, "total_seconds": 0, "output": {"png_chunks": ["IHDR", "IDAT", "IEND"]}}
        m = evaluate._measure(e, ROOT / "testset" / "images" / e["file"], fake_report, do_ocr=False)
        self.assertFalse(m["whole_black_pixels"])
        self.assertLess(max(m["value_box_black_share"]), 0.5)  # planted boxes are mostly NOT black in the original
        self.assertGreater(min(m["plain_box_nonblack_share"]), 0.5)

    def test_holdout_files_are_never_listed(self):
        key = json.loads((ROOT / "testset" / "key.json").read_text())
        dev = [x for x in key["images"] if x["split"] == "dev"]
        self.assertEqual(len(dev), 150)
        self.assertTrue(all(x["split"] == "dev" for x in dev))


if __name__ == "__main__":
    unittest.main()
