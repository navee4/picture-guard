"""Public-repo hygiene: committed text files must not name the private project, a private path, or a planted value from the test keys."""
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = {".md", ".py", ".txt", ".json", ".svg", ".html", ".toml", ".sh", ".cfg", ".yml", ".yaml"}
SKIP_PARTS = ("testset/key.json", "faces/key.json", "faces_hard/key.json")  # the keys hold the planted (made-up) values by design
# the words are assembled from pieces so that this file does not itself contain them (and a text rewrite of the history cannot mangle the list)
FORBIDDEN = [re.compile(p, re.I) for p in ("my" + "yaad", "my" + "memory", "/" + "Users/", "Documents/" + "Claude", "windows" + " vm")]


def tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    return [ROOT / f for f in out if f and (ROOT / f).suffix in TEXT and not any(f.endswith(s) for s in SKIP_PARTS) and (ROOT / f).exists()]


class PublicRepo(unittest.TestCase):
    def test_no_private_names_or_paths_in_tracked_text(self):
        bad = []
        for f in tracked_text_files():
            if f.name == "test_docs.py":
                continue
            txt = f.read_text(errors="ignore")
            for pat in FORBIDDEN:
                if pat.search(txt):
                    bad.append((str(f.relative_to(ROOT)), pat.pattern))
        self.assertEqual(bad, [])

    def test_docs_exist_and_follow_the_rulings(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("navee4", readme)
        self.assertIn("AI coding tools (Claude)", readme)
        self.assertIn("Apache-2.0", readme)
        self.assertTrue((ROOT / "LIMITS.md").exists())
        self.assertTrue((ROOT / "docs" / "pipeline.svg").exists())
        self.assertNotIn("https://", readme.split("Demo:")[1].split("\n")[0] if "Demo:" in readme else "", "the demo URL must not be in the repo yet")

    def test_no_planted_value_from_the_keys_in_docs_or_results_text(self):
        values = set()
        for k in ("testset", "faces", "faces_hard"):
            key = json.loads((ROOT / k / "key.json").read_text())
            for e in key["images"]:
                for s in e["spans"]:
                    if s["kind"] == "personal" and s["pii_type"] != "face" and len(s["text"]) >= 8:
                        values.add(s["text"].lower())
        files = [f for f in tracked_text_files() if f.suffix in (".md", ".svg", ".html") or "results" in f.parts]
        hits = []
        for f in files:
            if f.name == "key.json":
                continue
            txt = f.read_text(errors="ignore").lower()
            for v in values:
                if v in txt:
                    hits.append(f.name)
                    break
        self.assertEqual(hits, [])


    @unittest.skipUnless(os.environ.get("PG_SUBMIT") == "1", "set PG_SUBMIT=1 when the links exist")
    def test_no_link_placeholder_left_in_readme(self):
        txt = (ROOT / "README.md").read_text()
        left = [w for w in ("DEMO_LINK", "VIDEO_LINK", "REPO_LINK") if w in txt]
        self.assertEqual(left, [], "replace the placeholders in README.md before submitting")


if __name__ == "__main__":
    unittest.main()
