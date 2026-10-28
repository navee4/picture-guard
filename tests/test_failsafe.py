"""Unit tests for the fail-safe rules and the safe copy. Run: .venv/bin/python -m unittest discover -s tests -t ."""
import io
import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from picture_guard import imaging
from picture_guard.imaging import NotAPictureError
from picture_guard.pipeline import Stage, default_plan, protect
from picture_guard.types import NOT_SURE, OK, StageResult

ROOT = Path(__file__).resolve().parent.parent
BOX = [10, 20, 50, 40]


def sure(name, answer=None):
    return lambda ctx: StageResult(OK, answer or {}, "test: sure")


def sure_plan():
    """Every stage sure; locate hands back one box, so the result is NOT a whole-black picture."""
    p = default_plan()
    for st in p.detect:
        st.run = sure(st.name, {"boxes": [BOX]} if st.name == "locate" else None)
    p.check.run = sure("check_safe")
    return p


def replace(plan, name, fn, timeout_s=None):
    stages = [plan.black_out, plan.check, plan.send] + plan.detect
    st = next(s for s in stages if s.name == name)
    st.run = fn
    if timeout_s is not None:
        st.timeout_s = timeout_s


def raiser(ctx):
    raise RuntimeError("boom")


def sleeper(ctx):
    time.sleep(3)
    return StageResult(OK, {}, "late")


def exif_jpeg(path, size=(120, 80)):
    im = Image.effect_noise(size, 60).convert("RGB")
    ex = Image.Exif()
    ex[0x010F] = "TestCamMaker"
    ex[0x0132] = "2026:10:27 10:00:00"
    ex.get_ifd(0x8825).update({1: "N", 2: (51.0, 30.0, 0.0), 3: "W", 4: (0.0, 7.0, 0.0)})
    im.save(path, format="JPEG", exif=ex)


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.out, self.rep = self.d / "safe.png", self.d / "report.json"
        self.src = self.d / "in.jpg"
        exif_jpeg(self.src)

    def tearDown(self):
        self._t.cleanup()

    def run_pg(self, plan=None, src=None):
        return protect(src or self.src, self.out, self.rep, plan)

    def pixels(self):
        return np.asarray(Image.open(self.out).convert("RGB"))


class SafeCopy(Base):
    def test_no_metadata_with_exif_and_gps_in_input(self):
        self.assertIn(b"TestCamMaker", self.src.read_bytes())  # the test input really carries the data
        for plan in (default_plan(), sure_plan()):  # whole-black path and the path that copies real pixels
            self.run_pg(plan)
            data = self.out.read_bytes()
            self.assertEqual(set(imaging.png_chunks(self.out)), {b"IHDR", b"IDAT", b"IEND"})
            for needle in (b"Exif", b"TestCamMaker", b"GPS", b"2026:10:27", b"tEXt", b"eXIf", b"iCCP"):
                self.assertNotIn(needle, data)
            im = Image.open(self.out)
            self.assertEqual(im.format, "PNG")
            self.assertFalse(im.info.keys() - {"dpi"} and im.info)  # nothing in the info dict
            self.assertEqual(len(im.getexif()), 0)

    def test_png_text_chunks_and_profile_are_dropped(self):
        from PIL.PngImagePlugin import PngInfo
        meta = PngInfo()
        meta.add_text("Author", "SecretAuthorName")
        p = self.d / "in.png"
        Image.new("RGB", (60, 40), (200, 10, 10)).save(p, pnginfo=meta, dpi=(300, 300))
        self.run_pg(sure_plan(), p)
        self.assertNotIn(b"SecretAuthorName", self.out.read_bytes())
        self.assertEqual(set(imaging.png_chunks(self.out)), {b"IHDR", b"IDAT", b"IEND"})

    def test_same_size_and_new_png_for_each_mode(self):
        for mode, size in [("RGBA", (33, 21)), ("P", (64, 64)), ("L", (7, 9)), ("RGB", (301, 5))]:
            p = self.d / f"m_{mode}.png"
            Image.effect_noise(size, 50).convert(mode).save(p)
            self.run_pg(default_plan(), p)
            self.assertEqual(Image.open(self.out).size, size)
            self.assertNotEqual(self.out.read_bytes(), p.read_bytes())

    def test_default_day1_plan_is_always_whole_black(self):
        rep = self.run_pg()
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(self.pixels().max(), 0)
        self.assertTrue(json.loads(self.rep.read_text())["fail_safe"]["whole_black"])
        names = [s["name"] for s in rep["stages"]]
        self.assertEqual(names, ["read", "decide", "locate", "faces", "count_check", "black_out", "check_safe", "send"])
        for s in rep["stages"]:
            self.assertIn("seconds", s), self.assertIn("why", s), self.assertIn("answer", s)

    def test_sure_plan_fills_only_the_box(self):
        rep = self.run_pg(sure_plan())
        self.assertFalse(rep["fail_safe"]["whole_black"])
        a = self.pixels().copy()
        x0, y0, x1, y1 = BOX
        self.assertEqual(a[y0:y1, x0:x1].max(), 0)
        self.assertGreater(a.max(), 0)
        a[y0:y1, x0:x1] = 0
        orig = np.asarray(Image.open(self.src).convert("RGB")).copy()
        orig[y0:y1, x0:x1] = 0
        self.assertTrue((a == orig).all())

    def test_out_of_scope_format_is_whole_black(self):
        p = self.d / "in.gif"
        Image.new("P", (30, 30)).save(p)
        rep = self.run_pg(sure_plan(), p)
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertTrue(any("outside the scope" in r for r in rep["fail_safe"]["reasons"]))
        self.assertEqual(self.pixels().max(), 0)


class StageFailures(Base):
    NAMES = ["read", "decide", "locate", "faces", "count_check", "black_out", "check_safe"]

    def test_baseline_sure_plan_is_not_whole_black(self):  # without this the tests below prove nothing
        self.assertFalse(self.run_pg(sure_plan())["fail_safe"]["whole_black"])

    def test_error_in_any_stage_gives_whole_black(self):
        for name in self.NAMES:
            plan = sure_plan()
            replace(plan, name, raiser)
            rep = self.run_pg(plan)
            self.assertTrue(rep["fail_safe"]["whole_black"], name)
            self.assertEqual(self.pixels().max(), 0, name)
            rec = next(s for s in rep["stages"] if s["name"] == name)
            self.assertEqual(rec["status"], "error", name)
            self.assertIn("boom", rec["why"])

    def test_timeout_in_any_stage_gives_whole_black(self):
        for name in self.NAMES:
            plan = sure_plan()
            replace(plan, name, sleeper, timeout_s=0.2)
            t0 = time.perf_counter()
            rep = self.run_pg(plan)
            self.assertLess(time.perf_counter() - t0, 2.0, name)  # we did not wait for the sleeper
            self.assertTrue(rep["fail_safe"]["whole_black"], name)
            self.assertEqual(self.pixels().max(), 0, name)
            self.assertEqual(next(s for s in rep["stages"] if s["name"] == name)["status"], "timeout", name)

    def test_not_sure_in_any_stage_gives_whole_black(self):
        for name in self.NAMES:
            if name == "black_out":
                continue  # black_out has no "not sure": it either fills or fails
            plan = sure_plan()
            replace(plan, name, lambda ctx: StageResult(NOT_SURE, {}, "unsure"))
            rep = self.run_pg(plan)
            self.assertTrue(rep["fail_safe"]["whole_black"], name)
            self.assertEqual(self.pixels().max(), 0, name)

    def test_a_stage_that_returns_junk_is_an_error(self):
        plan = sure_plan()
        replace(plan, "faces", lambda ctx: "yes")
        rep = self.run_pg(plan)
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(next(s for s in rep["stages"] if s["name"] == "faces")["status"], "error")

    def test_black_out_that_returns_the_wrong_size_is_not_trusted(self):
        plan = sure_plan()

        def bad(ctx):
            ctx.safe_image = Image.new("RGB", (5, 5), (255, 255, 255))
            return StageResult(OK, {}, "wrong size")
        replace(plan, "black_out", bad)
        rep = self.run_pg(plan)
        self.assertTrue(rep["fail_safe"]["whole_black"])
        self.assertEqual(Image.open(self.out).size, (120, 80))
        self.assertEqual(self.pixels().max(), 0)

    def test_send_makes_no_network_call(self):
        def no_net(*a, **k):
            raise AssertionError("network used")
        orig = (socket.socket.connect, socket.create_connection, socket.getaddrinfo)
        socket.socket.connect, socket.create_connection, socket.getaddrinfo = no_net, no_net, no_net
        try:
            rep = self.run_pg()
        finally:
            socket.socket.connect, socket.create_connection, socket.getaddrinfo = orig
        send = rep["stages"][-1]
        self.assertEqual(send["status"], "ok")
        self.assertEqual(send["answer"]["network_calls"], 0)
        self.assertFalse(send["answer"]["would_send"]["is_original"])
        self.assertEqual(send["answer"]["would_send"]["sha256"], rep["output"]["sha256"])


class BadInput(Base):
    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "picture_guard", *args], capture_output=True, text=True, cwd=ROOT)

    def assert_refused(self, src):
        r = self.cli("protect", str(src), "--out", str(self.out), "--report", str(self.rep))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("pg: error:", r.stderr)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.rep.exists())
        self.assertEqual([p.name for p in self.d.iterdir() if p.name.startswith(".")], [])  # no half-written temp file left
        return r.stderr

    def test_text_file_named_png(self):
        p = self.d / "fake.png"
        p.write_text("this is not a picture")
        self.assertIn("not a readable picture", self.assert_refused(p))

    def test_empty_file(self):
        p = self.d / "empty.jpg"
        p.write_bytes(b"")
        self.assert_refused(p)

    def test_truncated_png(self):
        buf = io.BytesIO()
        Image.effect_noise((200, 200), 80).convert("RGB").save(buf, format="PNG")
        p = self.d / "cut.png"
        p.write_bytes(buf.getvalue()[: len(buf.getvalue()) // 2])
        self.assert_refused(p)

    def test_missing_file_and_directory(self):
        self.assertIn("is not a file", self.assert_refused(self.d / "nope.png"))
        self.assertIn("is not a file", self.assert_refused(self.d))

    def test_oversize_dimensions(self):
        p = self.d / "huge.png"
        p.write_bytes(_png_header_only(20000, 20000))
        self.assertIn("more than", self.assert_refused(p))

    def test_output_may_not_overwrite_the_input(self):
        before = self.src.read_bytes()
        r = self.cli("protect", str(self.src), "--out", str(self.src), "--report", str(self.rep))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.src.read_bytes(), before)
        self.assertFalse(self.rep.exists())

    def test_holdout_is_refused(self):
        r = self.cli("eval", "--set", "faces", "--split", "holdout")
        self.assertEqual(r.returncode, 2)
        self.assertIn("hold-out stays sealed", r.stderr)

    def test_holdout_final_needs_the_freeze_tag_on_head(self):
        r = self.cli("eval", "--set", "faces", "--split", "holdout", "--final", "--results-dir", str(Path(self.tmp.name) / "final") if hasattr(self, "tmp") else "/tmp/pg-final-test")
        self.assertEqual(r.returncode, 2)
        self.assertRegex(r.stderr, "freeze-1|clean|already")


def _png_header_only(w, h):
    """A PNG signature + IHDR claiming w x h, nothing else: size is read from the header before any decode."""
    import struct
    import zlib
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunk = lambda n, d: struct.pack(">I", len(d)) + n + d + struct.pack(">I", zlib.crc32(n + d))  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


if __name__ == "__main__":
    unittest.main()
