"""Browser test of the redesigned demo page ("light table"). Skipped unless PG_DEMO_URL is set (a deployed demo, or `python -m picture_guard.demo.local`).

    PG_DEMO_URL=https://... .venv/bin/python -m unittest tests.e2e.test_demo_page -v
    PG_PAGE_ASK=1 also asks one question (a real Muse Spark call on a deployed demo with the secret; keep that to a few)
    PG_PAGE_HOSTS=out.json writes the list of every host the page contacted

Checks: the page contacts no host but its own; the four samples are buttons; progress per stage; bars stamp on the picture; the wipe slider
moves with the arrow keys and by pointer; chips list types and counts only; upload (PNG) and the size-limit message; the receipt; from 360 px
wide the page does not scroll sideways; with reduced motion the bars appear at once.
"""
import hashlib
import io
import json
import os
import time
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
URL = os.environ.get("PG_DEMO_URL", "").rstrip("/")
ASK = os.environ.get("PG_PAGE_ASK") == "1"
HOSTS_OUT = os.environ.get("PG_PAGE_HOSTS")


def run_sample(page, name, limited):
    """Click a sample; on HTTP 429 wait for the rate-limit window (8 pictures per visitor per 10 minutes), then click again."""
    for attempt in range(13):
        limited.clear()
        page.click(f"button[data-sample='{name}']")
        try:
            page.wait_for_function("!document.getElementById('resultCard').hidden", timeout=20_000)
            page.wait_for_timeout(500)
            if not limited or attempt == 12:  # the page also opens the result card to show a rate-limit message
                return
            time.sleep(60)
        except Exception:  # noqa: BLE001
            if not limited or attempt == 12:
                return
            time.sleep(60)


@unittest.skipUnless(URL, "set PG_DEMO_URL to run against a demo")
class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.hosts = set()
        cls.limited = []

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        if HOSTS_OUT:
            Path(HOSTS_OUT).write_text(json.dumps(sorted(cls.hosts)))

    def new_page(self, width=1280, height=900, **kw):
        ctx = self.browser.new_context(viewport={"width": width, "height": height}, **kw)
        page = ctx.new_page()
        page.on("request", lambda r: self.hosts.add(urlparse(r.url).netloc))
        page.on("response", lambda r: self.limited.append(r) if r.status == 429 and "/api/protect" in r.url else None)
        self.addCleanup(ctx.close)
        page.goto(URL + "/")
        page.wait_for_selector("button[data-sample]")
        return page

    def test_light_table_end_to_end_and_no_third_party_request(self):
        page = self.new_page()
        self.assertIn("Covers private details in a picture before an AI sees it", page.inner_text("header"))
        self.assertIn("Hackathon demo", page.inner_text("#banner"))
        names = [b.get_attribute("data-sample") for b in page.query_selector_all("button[data-sample]")]
        for n in ("payslip_000.jpg", "letter_000.png", "chat_005.png", "id_card_001.png"):
            self.assertIn(n, names)
        self.assertIn("goes only to our own GPU, never to Meta", page.inner_text("#ends") if not page.is_hidden("#ends") else page.content())
        # fonts are our own files
        fonts = page.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family)")
        self.assertIn("Bricolage Grotesque", fonts)
        page.evaluate("window.__stamps=0;new MutationObserver(m=>{window.__stamps=Math.max(window.__stamps,document.querySelectorAll('.stamp').length)}).observe(document.getElementById('bars'),{childList:true})")
        run_sample(page, "payslip_000.jpg", self.limited)
        page.wait_for_selector("#st-read.ok, #st-read.not_sure, #st-read.error", timeout=300_000)
        page.wait_for_function("document.getElementById('wipe').style.display==='block'", timeout=300_000)
        self.assertGreater(page.evaluate("window.__stamps"), 0, "bars were stamped on the picture")
        self.assertGreater(len(page.query_selector_all("#stages li")), 5, "one line per stage")
        self.assertEqual(page.evaluate("[...document.querySelectorAll('#stages li')].filter(li=>li.querySelector('.mark').textContent==='○').length"), 0, "every stage got a mark")
        chips = page.inner_text("#covered")
        self.assertTrue(chips.strip())
        self.assertIn("×", chips + page.inner_text("#verdict"), "types and counts")
        # the safe copy is what the hash says
        h_safe = page.inner_text("#hSafe")
        src = page.get_attribute("#safe", "src")
        import base64
        self.assertEqual(hashlib.sha256(base64.b64decode(src.split(",", 1)[1])).hexdigest(), h_safe)
        self.assertEqual(page.inner_text("#hOrig"), hashlib.sha256((ROOT / "demo_samples" / "payslip_000.jpg").read_bytes()).hexdigest())
        # wipe slider: arrow keys and pointer
        w = page.locator("#wipe")
        w.focus()
        page.wait_for_timeout(1500)  # the opening glide ends
        a = int(w.get_attribute("aria-valuenow"))
        page.keyboard.press("ArrowLeft")
        self.assertEqual(int(w.get_attribute("aria-valuenow")), max(0, a - 5))
        page.keyboard.press("End")
        self.assertEqual(int(w.get_attribute("aria-valuenow")), 100)
        page.keyboard.press("Home")
        self.assertEqual(int(w.get_attribute("aria-valuenow")), 0)
        self.assertIn("inset(0px 100% 0px 0px)", page.eval_on_selector("#safe", "e => getComputedStyle(e).clipPath"))
        box = page.locator("#stage").bounding_box()
        wb = w.bounding_box()
        page.mouse.move(wb["x"] + wb["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] / 2, steps=5)
        page.mouse.up()
        self.assertTrue(60 <= int(w.get_attribute("aria-valuenow")) <= 80, "dragging moves the line")
        focus_ring = page.evaluate("(()=>{document.getElementById('wipe').focus();return getComputedStyle(document.getElementById('wipe').querySelector('i')).boxShadow})()")
        self.assertNotEqual(focus_ring, "none", "visible focus on the slider")
        # the receipt before any question
        self.assertEqual(page.inner_text("#hSent"), "nothing sent yet")
        self.assertIn("What left this machine", page.inner_text("#proofCard"))
        self.assertIn("never sent to Meta", page.inner_text("#inside"))
        if ASK:
            page.fill("#q", "What kind of document is this?")
            page.click("#askBtn")
            page.wait_for_function("document.getElementById('hSent').textContent.length === 64", timeout=120_000)
            self.assertEqual(page.inner_text("#hSent"), h_safe)
            self.assertIn("Sent hash = safe copy hash", page.inner_text("#hCheck"))
            self.assertTrue(page.inner_text("#answer").strip())
            self.assertIn("product improvement", page.inner_text("#sparkNote"))

    def test_upload_png_and_size_limit(self):
        from PIL import Image
        page = self.new_page()
        buf = io.BytesIO()
        Image.new("RGB", (400, 300), (250, 250, 245)).save(buf, "PNG")
        page.set_input_files("#file", {"name": "plain.png", "mimeType": "image/png", "buffer": buf.getvalue()})
        page.wait_for_selector("#cleanBtn:not([hidden])")
        self.assertEqual(page.inner_text("#cleanBtn"), "Clean this picture")
        self.assertFalse(page.is_hidden("#orig"), "the upload shows on the table before it is cleaned")
        page.click("#cleanBtn")
        page.wait_for_function("!document.getElementById('resultCard').hidden", timeout=20_000)
        page.wait_for_function("document.getElementById('hSafe').textContent.length === 64", timeout=300_000)
        self.assertEqual(page.inner_text("#hOrig"), hashlib.sha256(buf.getvalue()).hexdigest())
        # a file over the limit is refused in the page, with a plain message
        big = {"name": "big.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 10)}
        page.set_input_files("#file", big)
        self.assertIn("over the 5 MB limit", page.inner_text("#note"))
        # a file that is not a picture comes back as a plain error from the server
        page.set_input_files("#file", {"name": "x.png", "mimeType": "image/png", "buffer": b"not a picture"})
        page.click("#cleanBtn")
        page.wait_for_function("document.getElementById('verdict').textContent.length>0", timeout=20_000)
        self.assertTrue(page.inner_text("#verdict").strip())

    def test_phone_width_and_reduced_motion(self):
        page = self.new_page(width=360, height=740, reduced_motion="reduce", has_touch=True)
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 360, "no sideways scroll at 360 px")
        page.evaluate("window.__stamps=0;new MutationObserver(()=>{window.__stamps=Math.max(window.__stamps,document.querySelectorAll('.stamp').length)}).observe(document.getElementById('bars'),{childList:true})")
        run_sample(page, "payslip_000.jpg", self.limited)
        page.wait_for_function("document.getElementById('wipe').style.display==='block'", timeout=300_000)
        self.assertGreater(page.evaluate("window.__stamps"), 0)
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.stamp')||document.body).animationName") in ("none", ""), True)
        self.assertEqual(int(page.locator("#wipe").get_attribute("aria-valuenow")), 50, "with reduced motion the line is at the middle at once")
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 360, "no sideways scroll after a result")

    def test_first_view_has_the_payslip_on_the_table_and_the_button_at_both_widths(self):
        for w, h in ((1440, 900), (390, 844)):
            page = self.new_page(width=w, height=h)
            page.wait_for_function("document.getElementById('orig').complete && document.getElementById('orig').naturalWidth>0", timeout=30_000)
            self.assertFalse(page.is_hidden("#orig"), f"an image lies on the table at {w} px")
            self.assertIn("payslip", page.get_attribute("#orig", "src"))
            btn = page.locator("#cleanBtn")
            self.assertEqual(btn.inner_text(), "Clean this picture")
            bb = btn.bounding_box()
            self.assertTrue(bb and bb["y"] >= 0 and bb["y"] + bb["height"] <= h, f"the button is inside the first screen at {w} px")
            ob = page.locator("#orig").bounding_box()
            self.assertTrue(ob["y"] < h - 60, f"the picture starts inside the first screen at {w} px")
            self.assertEqual(page.evaluate("document.querySelectorAll('.stamp').length"), 0, "the page does not run by itself")

    def test_bars_are_solid_black_at_every_frame_and_chips_use_plain_names(self):
        page = self.new_page()
        page.evaluate("""window.__bad=[];window.__seen=0;window.__sampler=setInterval(()=>{document.querySelectorAll('.stamp').forEach(e=>{window.__seen++;
          const c=getComputedStyle(e); if(c.opacity!=='1'||c.backgroundColor!=='rgb(0, 0, 0)') window.__bad.push([c.opacity,c.backgroundColor]);});},8)""")
        page.click("#cleanBtn")
        page.wait_for_function("document.querySelectorAll('.stamp').length>0", timeout=300_000, polling=20)
        rect = page.evaluate("(()=>{const r=document.querySelector('.stamp').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        page.wait_for_timeout(60)
        png = page.screenshot(clip={"x": max(0, rect["x"] - 1), "y": max(0, rect["y"] - 1), "width": 2, "height": 2})
        from PIL import Image
        px = Image.open(io.BytesIO(png)).convert("RGB").getpixel((1, 1))
        self.assertEqual(px, (0, 0, 0), "a pixel at a bar's centre, mid-stamp, is pure black")
        page.wait_for_function("document.getElementById('wipe').style.display==='block'", timeout=60_000)
        page.evaluate("clearInterval(window.__sampler)")
        self.assertGreater(page.evaluate("window.__seen"), 0)
        self.assertEqual(page.evaluate("window.__bad"), [], "every bar had opacity 1 and background rgb(0, 0, 0) at every sampled frame")
        raw = {"name", "address", "postcode", "dob", "ni_number", "sort_code", "account_number", "card_number", "iban", "email", "phone", "id_number", "face", "other"}
        chips = [c.strip() for c in page.eval_on_selector_all(".chip", "els => els.map(e => e.textContent)")]
        self.assertTrue(chips)
        for c in chips:
            label = c.rsplit("×", 1)[0].strip()
            self.assertNotIn(label, raw, f"chip shows a raw type code: {c}")
            self.assertNotIn("_", label)
            self.assertTrue(label[0].isupper(), f"sentence case: {c}")

    def test_mobile_run_brings_the_table_into_view(self):
        page = self.new_page(width=390, height=844, has_touch=True)
        page.evaluate("window.scrollTo(0,0)")
        page.click("#cleanBtn")
        page.wait_for_timeout(1500)
        top = page.evaluate("document.querySelector('.paper').getBoundingClientRect().top")
        self.assertTrue(0 <= top < 844, f"the table's top is inside the viewport after the click (top={top})")
        page.wait_for_function("document.getElementById('wipe').style.display==='block'", timeout=300_000)

    def test_a_hash_mismatch_is_said_in_plain_words(self):
        page = self.new_page()
        run_sample(page, "chat_005.png", self.limited)
        page.wait_for_function("document.getElementById('hSafe').textContent.length === 64", timeout=300_000)
        bad = {"answer": "x", "error": None, "connected": True, "request_log": [{"host": "api.meta.ai", "image_bytes": 1, "image_sha256": "0" * 64, "sent": False}],
               "safe_sha256": "1" * 64, "original_sha256": "2" * 64, "proof": {"sent_equals_safe_copy": False, "sent_equals_original": False}}
        page.route("**/api/ask", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(bad)))
        page.fill("#q", "hello")
        page.click("#askBtn")
        page.wait_for_function("document.getElementById('hSent').textContent.length === 64", timeout=30_000)
        self.assertEqual(page.inner_text("#hCheck"), "The hashes do not match. Nothing was sent.")
        self.assertNotIn("MISMATCH", page.content())

    def test_the_page_contacts_only_its_own_host(self):
        page = self.new_page()
        own = urlparse(URL).netloc
        run_sample(page, "chat_005.png", self.limited)
        page.wait_for_function("document.getElementById('hSafe').textContent.length === 64", timeout=300_000)
        self.assertEqual({h for h in self.hosts if h}, {own}, "every request went to the demo's own address")


if __name__ == "__main__":
    unittest.main()
