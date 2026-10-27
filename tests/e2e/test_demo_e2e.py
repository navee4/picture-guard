"""End-to-end test: a real browser drives the DEPLOYED demo. Skipped unless PG_DEMO_URL is set (the URL is not kept in the repo).

    PG_DEMO_URL=https://... .venv/bin/python -m unittest tests.e2e.test_demo_e2e -v

Checks with a made-up dev sample: a safe copy comes back; the hash of the bytes sent to Muse Spark equals the safe copy's hash and is
never the original's; no planted private text appears in any response; the original's bytes never come back from the server.
"""
import base64
import hashlib
import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
URL = os.environ.get("PG_DEMO_URL", "").rstrip("/")
SAMPLE = os.environ.get("PG_DEMO_SAMPLE", "payslip_000.jpg")
SHOT = os.environ.get("PG_DEMO_SHOT")  # optional: where to save a screenshot of the finished page


def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())


@unittest.skipUnless(URL, "set PG_DEMO_URL to run against the deployed demo")
class DemoE2E(unittest.TestCase):
    def test_sample_end_to_end(self):
        from playwright.sync_api import sync_playwright
        original = (ROOT / "demo_samples" / SAMPLE).read_bytes()
        orig_sha = hashlib.sha256(original).hexdigest()
        src = json.loads((ROOT / "demo_samples" / "SOURCES.json").read_text())[SAMPLE]
        key = json.loads((ROOT / src / "key.json").read_text())
        entry = next(e for e in key["images"] if e["file"] == SAMPLE and e["split"] == "dev")
        private = [s["text"] for s in entry["spans"] if s["kind"] == "personal" and s["text"] and s["pii_type"] != "face"]
        bodies, requests = [], []
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(viewport={"width": 1100, "height": 1500})
            page.add_init_script("""window.__bodies=[];const _f=window.fetch;window.fetch=async(...a)=>{const r=await _f(...a);
              if(/api\\/(protect|ask|info)/.test(String(a[0]))) r.clone().text().then(t=>window.__bodies.push(t)); return r;};""")
            page.on("request", lambda r: requests.append(r) if "/api/" in r.url else None)
            page.goto(URL + "/")
            self.assertIn("Hackathon demo", page.inner_text("#banner"))
            page.click(f"button[data-sample='{SAMPLE}']")
            page.wait_for_selector("#resultCard:not([hidden])", timeout=300_000)
            page.wait_for_function("document.getElementById('hSafe').textContent.length === 64", timeout=300_000)
            self.assertTrue(page.eval_on_selector("#safe", "i => i.complete && i.naturalWidth > 0"), "a safe copy came back")
            h_orig, h_safe = page.inner_text("#hOrig"), page.inner_text("#hSafe")
            self.assertEqual(h_orig, orig_sha)
            self.assertNotEqual(h_safe, h_orig)
            safe_src = page.get_attribute("#safe", "src")
            safe_bytes = base64.b64decode(safe_src.split(",", 1)[1])
            self.assertEqual(hashlib.sha256(safe_bytes).hexdigest(), h_safe, "the shown hash is the hash of the shown safe copy")
            page.fill("#q", "What kind of document is this?")
            page.click("#askBtn")
            page.wait_for_function("document.getElementById('hSent').textContent.length === 64", timeout=120_000)
            h_sent = page.inner_text("#hSent")
            self.assertEqual(h_sent, h_safe, "sent-bytes hash equals the safe-copy hash")
            self.assertNotEqual(h_sent, orig_sha, "the original's hash is never sent")
            self.assertIn("Sent hash = safe copy hash", page.inner_text("#hCheck"))
            self.assertTrue(page.inner_text("#answer").strip())
            if SHOT:
                page.screenshot(path=SHOT, full_page=True)
            texts = page.evaluate("window.__bodies")
            posted = [r.post_data_buffer or b"" for r in requests]
            b.close()
        blob = norm(" ".join(t for t in texts if t))
        for p in private:
            self.assertNotIn(norm(p), blob, "private text appeared in a response")
        o64 = base64.b64encode(original).decode()
        self.assertNotIn(o64[:200], " ".join(texts), "the original's bytes came back from the server")
        for data in posted[1:]:  # the question request carries a session id and text, never a picture
            self.assertNotIn(b"PNG", data[:200])


if __name__ == "__main__":
    unittest.main()
