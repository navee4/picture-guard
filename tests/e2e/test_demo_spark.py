"""Machine check of the REAL Muse Spark answer path on the DEPLOYED demo, on the four made-up samples. Skipped without PG_DEMO_URL.

    PG_DEMO_URL=https://... PG_SPARK_OUT=/path/answers.json .venv/bin/python -m unittest tests.e2e.test_demo_spark -v

For each sample one fixed question is asked (4 Muse Spark calls in all). Checks: the page does not say "not connected"; the request log
names the Meta Model API host and says sent; the image hash sent equals the safe-copy hash and never the original's; an answer comes back;
no planted private text from the sample's key appears in the question, the answer, any response body or the request log.
"""
import hashlib
import json
import os
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
URL = os.environ.get("PG_DEMO_URL", "").rstrip("/")
OUT = os.environ.get("PG_SPARK_OUT")
QUESTIONS = {
    "payslip_000.jpg": "What is the net pay and the pay period?",
    "letter_000.png": "What is this letter asking me to do?",
    "chat_005.png": "Summarise this chat in one sentence.",
    "id_card_001.png": "What kind of document is this?",
}


def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())


@unittest.skipUnless(URL, "set PG_DEMO_URL to run against the deployed demo")
class RealSpark(unittest.TestCase):
    def test_four_samples_real_answers(self):
        from playwright.sync_api import sync_playwright
        results = {}
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            for sample, question in QUESTIONS.items():
                original = (ROOT / "demo_samples" / sample).read_bytes()
                orig_sha = hashlib.sha256(original).hexdigest()
                src = json.loads((ROOT / "demo_samples" / "SOURCES.json").read_text())[sample]
                key = json.loads((ROOT / src / "key.json").read_text())
                entry = next(e for e in key["images"] if e["file"] == sample and e["split"] == "dev")
                private = [s["text"] for s in entry["spans"] if s["kind"] == "personal" and s["text"] and s["pii_type"] != "face"]
                page = b.new_page(viewport={"width": 1100, "height": 1500})
                bodies, asks, limited = [], [], []
                page.on("response", lambda r: limited.append(r) if r.status == 429 and "/api/protect" in r.url else None)

                def on_resp(r):
                    if "/api/" in r.url and r.request.method in ("GET", "POST"):
                        try:
                            t = r.text()
                        except Exception:  # noqa: BLE001
                            return
                        bodies.append(t)
                        if r.url.endswith("/api/ask"):
                            asks.append(json.loads(t))
                page.on("response", on_resp)
                page.add_init_script("""window.__asks=[];const _f=window.fetch;window.fetch=async(...a)=>{const r=await _f(...a);
                  if(/api\\/ask/.test(String(a[0]))) r.clone().text().then(t=>window.__asks.push(t)); return r;};""")
                page.goto(URL + "/")
                page.wait_for_function("document.getElementById('sparkNote').textContent.length > 0", timeout=60_000)
                note = page.inner_text("#sparkNote")
                self.assertNotIn("not connected", note.lower(), "the page says Muse Spark is not connected")
                self.assertIn("product improvement", note, "the free-credit note is on the page")
                for attempt in range(13):  # the demo allows 8 pictures per visitor per 10 minutes: wait on HTTP 429
                    limited.clear()
                    page.click(f"button[data-sample='{sample}']")
                    try:
                        page.wait_for_function("!document.getElementById('resultCard').hidden", timeout=20_000)
                        break
                    except Exception:  # noqa: BLE001
                        if not limited or attempt == 12:
                            break
                        time.sleep(60)
                page.wait_for_function("document.getElementById('hSafe').textContent.length === 64", timeout=300_000)
                h_safe = page.inner_text("#hSafe")
                self.assertEqual(page.inner_text("#hOrig"), orig_sha)
                page.fill("#q", question)
                t0 = time.monotonic()
                page.click("#askBtn")
                page.wait_for_function("(()=>{const t=document.getElementById('answer').textContent.trim(); return t.length>0 && t!=='Asking…';})()", timeout=180_000)
                wall = round(time.monotonic() - t0, 2)
                page.wait_for_function("window.__asks.length > 0", timeout=30_000)
                asks = [json.loads(t) for t in page.evaluate("window.__asks")]
                self.assertEqual(len(asks), 1, "exactly one Muse Spark call per sample")
                a = asks[0]
                self.assertTrue(a["connected"], "connected")
                self.assertIsNone(a["error"], a["error"])
                self.assertTrue(a["answer"] and a["answer"].strip())
                log = a["request_log"][-1]
                self.assertEqual(log["host"], "api.meta.ai")
                self.assertTrue(log["sent"])
                self.assertEqual(log["image_sha256"], h_safe, "image hash sent equals the safe-copy hash")
                self.assertNotEqual(log["image_sha256"], orig_sha, "the original's hash was never sent")
                self.assertEqual(page.inner_text("#hSent"), h_safe)
                self.assertTrue(a["proof"]["sent_equals_safe_copy"] and not a["proof"]["sent_equals_original"])
                for p in private:
                    if len(norm(p)) >= 4:
                        self.assertNotIn(norm(p), norm(a["answer"] + " " + question + " " + json.dumps(a["request_log"])), f"private text in the answer/question/log ({sample})")
                        self.assertNotIn(norm(p), norm(" ".join(bodies)), f"private text in a response ({sample})")
                results[sample] = {"question": question, "answer": a["answer"], "seconds_wall_ask": wall, "log": log, "image_sha256_sent": log["image_sha256"],
                                   "safe_sha256": h_safe, "original_sha256": orig_sha}
                page.close()
            b.close()
        if OUT:
            Path(OUT).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    unittest.main()
