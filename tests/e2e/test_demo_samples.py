"""Machine check of the four demo samples on the DEPLOYED demo: for each sample the safe copy that comes back must have every planted
value box and every planted face box at least 90% black (a whole-black picture passes: nothing shows). Skipped without PG_DEMO_URL.

    PG_DEMO_URL=https://... .venv/bin/python -m unittest tests.e2e.test_demo_samples -v
"""
import base64
import io
import json
import os
import unittest
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
URL = os.environ.get("PG_DEMO_URL", "").rstrip("/")


def post_sample(name):
    b = uuid.uuid4().hex
    body = f'--{b}\r\nContent-Disposition: form-data; name="sample"\r\n\r\n{name}\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(URL + "/api/protect", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    for attempt in range(13):  # the demo allows 8 pictures per visitor per 10 minutes: on HTTP 429 wait for the window, never fail for that
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                evs = [json.loads(x) for x in r.read().decode().splitlines() if x.strip()]
            return evs[-1]
        except urllib.error.HTTPError as ex:
            if ex.code != 429 or attempt == 12:
                raise
            time.sleep(60)


@unittest.skipUnless(URL, "set PG_DEMO_URL to run against the deployed demo")
class Samples(unittest.TestCase):
    def test_every_planted_box_is_covered(self):
        sources = json.loads((ROOT / "demo_samples" / "SOURCES.json").read_text())
        report = {}
        for name, src in sources.items():
            key = json.loads((ROOT / src / "key.json").read_text())
            entry = next(e for e in key["images"] if e["file"] == name)
            done = post_sample(name)
            self.assertEqual(done["event"], "done", name)
            black = np.asarray(Image.open(io.BytesIO(base64.b64decode(done["safe_png_base64"]))).convert("RGB")).max(axis=2) <= 16
            shares = []
            for s in entry["spans"]:
                if s["kind"] == "personal":
                    x0, y0, x1, y1 = s["box"]
                    shares.append(float(black[y0:y1, x0:x1].mean()))
            report[name] = {"whole_black": done["whole_black"], "planted": len(shares), "min_black_share": round(min(shares), 3) if shares else None}
            self.assertTrue(all(x >= 0.9 for x in shares), f"{name}: {sorted(shares)[:3]}")
        print(json.dumps(report))


if __name__ == "__main__":
    unittest.main()
