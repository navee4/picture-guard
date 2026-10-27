"""The demo's logic (no browser, no Modal): limits, progress, the Muse Spark proof, privacy. The pipeline is the real one, the guard a fake."""
import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from picture_guard.demo import core, spark
from picture_guard.demo.core import Demo, Limited, Rejected
from picture_guard.remote.fake import FakeGuard

from tests.test_models import draw, needs_tesseract

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "demo_samples"


def png_bytes(lines=("Dear Katie Edwards", "Sort code 12-34-56 thanks")):
    b = io.BytesIO()
    draw(list(lines)).save(b, format="PNG")
    return b.getvalue()


def good_guard():
    return FakeGuard(values=[{"text": "Katie Edwards", "type": "name"}], face_count=0)


class Spark(unittest.TestCase):
    def test_body_has_exactly_the_safe_copy(self):
        safe = b"\x89PNG-safe"
        body = spark.build_body("hi", safe)
        spark.check_only_safe(body, spark.sha256(safe), spark.sha256(b"original"))
        self.assertEqual(spark.images_in_body(body), [safe])

    def test_original_is_refused(self):
        orig, safe = b"original-bytes", b"safe-bytes"
        with self.assertRaises(spark.SparkRefused):
            spark.check_only_safe(spark.build_body("hi", orig), spark.sha256(safe), spark.sha256(orig))

    def test_second_image_url_or_file_id_is_refused(self):
        safe = b"safe-bytes"
        h = spark.sha256(safe)
        for extra in ({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(b"other").decode()},
                      {"type": "input_image", "image_url": "https://example.com/x.png"}, {"type": "input_image", "file_id": "file_123"}):
            body = spark.build_body("q", safe)
            body["input"][0]["content"].append(extra)
            with self.assertRaises(spark.SparkRefused):
                spark.check_only_safe(body, h, spark.sha256(b"original"))

    def test_bytes_that_do_not_match_the_hash_are_refused(self):
        with self.assertRaises(spark.SparkRefused):
            spark.ask("q", b"abc", spark.sha256(b"different"), spark.sha256(b"o"), None)

    def test_fake_mode_sends_nothing(self):
        calls = []
        r = spark.ask("q", b"abc", spark.sha256(b"abc"), spark.sha256(b"o"), None, post=lambda *a: calls.append(a))
        self.assertEqual(calls, [])
        self.assertFalse(r["connected"])
        self.assertFalse(r["log"]["sent"])

    def test_real_mode_one_request_to_the_meta_host_with_the_safe_copy_only(self):
        seen = []

        def post(url, headers, payload, timeout):
            seen.append((url, headers, json.loads(payload)))
            return 200, json.dumps({"output": [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": "42"}]}]}).encode()
        safe = b"safe-bytes"
        r = spark.ask("what?", safe, spark.sha256(safe), spark.sha256(b"orig"), "KEY-FOR-TEST", post=post)
        self.assertEqual(r["answer"], "42")
        self.assertEqual(len(seen), 1)
        url, headers, body = seen[0]
        self.assertTrue(url.startswith("https://api.meta.ai/"))
        self.assertEqual(body["model"], "muse-spark-1.3")
        self.assertEqual([spark.sha256(i) for i in spark.images_in_body(body)], [spark.sha256(safe)])
        self.assertNotIn("KEY-FOR-TEST", json.dumps(r))  # the key is never in what we return or log

    def test_http_error_gives_a_short_message(self):
        safe = b"s"
        r = spark.ask("q", safe, spark.sha256(safe), spark.sha256(b"o"), "K", post=lambda *a: (401, json.dumps({"error": {"code": "invalid_api_key"}}).encode()))
        self.assertIsNone(r["answer"])
        self.assertIn("401", r["error"])


class Limits(unittest.TestCase):
    def setUp(self):
        self.t = [1000.0]
        self.demo = Demo(good_guard, SAMPLES, now=lambda: self.t[0])

    def test_rejects_non_pictures_empty_big_and_huge(self):
        for data in (b"", b"hello text", b"\x89PNG\r\n\x1a\n" + b"junk", b"\xff\xd8\xff" + b"x" * 10):
            with self.assertRaises(Rejected):
                self.demo.check_upload(data)
        with self.assertRaises(Rejected):
            self.demo.check_upload(b"\x89PNG\r\n\x1a\n" + b"0" * core.MAX_BYTES)
        big = io.BytesIO()
        Image.new("L", (5000, 4000)).save(big, format="PNG")
        with self.assertRaises(Rejected):
            self.demo.check_upload(big.getvalue())

    def test_sample_names_cannot_escape(self):
        for bad in ("../README.md", "/etc/passwd", "nope.png"):
            with self.assertRaises(Rejected):
                self.demo.sample_bytes(bad)

    def test_rate_limiter_per_visitor_and_window(self):
        rl = core.RateLimiter(2, 100, now=lambda: self.t[0])
        self.assertTrue(rl.allow("a") and rl.allow("a"))
        self.assertFalse(rl.allow("a"))
        self.assertTrue(rl.allow("b"))
        self.t[0] += 101
        self.assertTrue(rl.allow("a"))

    def test_samples_are_dev_pictures_only(self):
        key = json.loads((ROOT / "testset" / "key.json").read_text())
        split = {e["file"]: e["split"] for e in key["images"]}
        names = self.demo.sample_names()
        self.assertEqual(len(names), 4)
        for n in names:
            self.assertEqual(split[n], "dev", n)


@needs_tesseract
class Run(unittest.TestCase):
    def setUp(self):
        self.demo = Demo(good_guard, SAMPLES)

    def run_demo(self, data=None, visitor="v1"):
        return list(self.demo.protect_events(data or png_bytes(), visitor))

    def test_progress_then_done_with_counts_only(self):
        evs = self.run_demo()
        self.assertEqual(evs[0]["event"], "start")
        stages = [e for e in evs if e["event"] == "stage"]
        self.assertTrue({"read", "decide", "black_out", "check_safe"} <= {e["name"] for e in stages})
        self.assertIn("running", {e["status"] for e in stages})
        done = evs[-1]
        self.assertEqual(done["event"], "done")
        self.assertFalse(done["whole_black"])
        self.assertTrue(done["covered"])
        self.assertEqual(spark.sha256(base64.b64decode(done["safe_png_base64"])), done["safe_sha256"])
        self.assertNotEqual(done["safe_sha256"], done["original_sha256"])
        blob = json.dumps(evs)
        for private in ("Katie", "Edwards", "12-34-56"):
            self.assertNotIn(private, blob)

    def test_whole_black_gives_a_plain_reason(self):
        self.demo.guard_factory = lambda: FakeGuard(raise_error="down")
        done = self.run_demo()[-1]
        self.assertTrue(done["whole_black"])
        self.assertIn("Whole picture black", done["reason"])
        self.assertEqual(done["covered"], {})

    def test_ask_sends_only_the_safe_copy_and_proves_it(self):
        sent = []

        def post(url, headers, payload, timeout):
            sent.append(json.loads(payload))
            return 200, json.dumps({"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}).encode()
        self.demo.key, self.demo.post = "K", post
        done = self.run_demo()[-1]
        r = self.demo.ask(done["session"], "what is this?", "v1")
        self.assertEqual(r["answer"], "ok")
        imgs = spark.images_in_body(sent[0])
        self.assertEqual([spark.sha256(i) for i in imgs], [done["safe_sha256"]])
        self.assertNotIn(done["original_sha256"], [spark.sha256(i) for i in imgs])
        self.assertTrue(r["proof"]["sent_equals_safe_copy"])
        self.assertFalse(r["proof"]["sent_equals_original"])

    def test_ask_needs_a_session_and_a_question_and_is_rate_limited(self):
        done = self.run_demo()[-1]
        with self.assertRaises(Rejected):
            self.demo.ask("nope", "q", "v1")
        with self.assertRaises(Rejected):
            self.demo.ask(done["session"], "   ", "v1")
        for _ in range(core.ASK_PER_WINDOW):
            self.demo.ask(done["session"], "q", "v1")
        with self.assertRaises(Limited):
            self.demo.ask(done["session"], "q", "v1")

    def test_protect_is_rate_limited_per_visitor(self):
        for _ in range(core.PROTECT_PER_WINDOW):
            self.run_demo()
        with self.assertRaises(Limited):
            self.run_demo()
        self.assertTrue(self.run_demo(visitor="other")[-1]["event"] == "done")

    def test_nothing_is_left_in_the_temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.demo.tmp_dir = d
            self.run_demo()
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_the_demo_runs_the_same_pipeline_as_pg_protect(self):
        import picture_guard.demo.core as c
        from picture_guard import pipeline
        self.assertIs(c.pipeline, pipeline)


class Web(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from picture_guard.demo.web import create_app
        self.demo = Demo(good_guard, SAMPLES)
        self.c = TestClient(create_app(self.demo))

    def test_page_info_and_sample(self):
        self.assertIn("Picture guard", self.c.get("/").text)
        self.assertEqual(len(self.c.get("/api/info").json()["samples"]), 4)
        self.assertEqual(self.c.get("/api/sample/chat_005.png").status_code, 200)
        self.assertEqual(self.c.get("/api/sample/..%2FREADME.md").status_code, 404)

    def test_bad_upload_is_a_400_and_nothing_runs(self):
        r = self.c.post("/api/protect", files={"file": ("x.png", b"not a picture")})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.demo.waiting, 0)

    @needs_tesseract
    def test_upload_streams_ndjson_and_ask_works(self):
        r = self.c.post("/api/protect", files={"file": ("a.png", png_bytes(), "image/png")})
        self.assertEqual(r.status_code, 200)
        evs = [json.loads(x) for x in r.text.splitlines()]
        done = evs[-1]
        self.assertEqual(done["event"], "done")
        a = self.c.post("/api/ask", json={"session": done["session"], "question": "hi"}).json()
        self.assertFalse(a["connected"])
        self.assertTrue(a["proof"]["sent_equals_safe_copy"])


if __name__ == "__main__":
    unittest.main()
