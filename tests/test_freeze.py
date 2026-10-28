"""The frozen pipeline must not change after the tag `freeze-1` (only the answer step, the demo page, docs and tests may)."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ["picture_guard/pipeline.py", "picture_guard/ocr.py", "picture_guard/fallback.py", "picture_guard/match.py", "picture_guard/readback.py",
          "picture_guard/rules.py", "picture_guard/imaging.py", "picture_guard/smart.py", "picture_guard/stages", "picture_guard/remote/container_impl.py",
          "FREEZE.md"]


class Frozen(unittest.TestCase):
    def test_pipeline_files_equal_the_freeze_tag(self):
        have = subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/freeze-1"], cwd=ROOT, capture_output=True, text=True)
        if have.returncode != 0:
            self.skipTest("tag freeze-1 not present in this checkout")
        diff = subprocess.run(["git", "diff", "--stat", "freeze-1", "--"] + FROZEN, cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual(diff.strip(), "", "a frozen pipeline file changed after freeze-1")
