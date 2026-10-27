"""Demo logic, with no web framework: limits, the pipeline run with live progress, sessions, and the Muse Spark question.

The pipeline is the same `picture_guard.pipeline.protect` that `pg protect` runs. Uploaded pictures live in memory-backed temp files
for the length of one run and are deleted at once; nothing is written to a Volume or logged. Logs and reports hold hashes, sizes,
counts and timings, never picture bytes or private text.
"""
from __future__ import annotations

import base64
import os
import queue
import tempfile
import threading
import time
from collections import deque
from pathlib import Path

from picture_guard import pipeline
from picture_guard.demo import spark

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000
PROTECT_PER_WINDOW = 8
ASK_PER_WINDOW = 12
WINDOW_S = 600
DAILY_PROTECT_CAP = 200  # whole demo, one container: a hard stop on cost
REQUEST_TIMEOUT_S = 240
SESSION_TTL_S = 900
MAX_SESSIONS = 20
MAX_WAITING = 3
STAGE_LABELS = {
    "read": "Reading the text on the picture", "decide": "Deciding what is private (AI model on our GPU)", "locate": "Placing the boxes",
    "faces": "Finding faces", "count_check": "Checking the face count", "black_out": "Covering them", "check_safe": "Re-reading the safe copy",
    "send": "Getting the safe copy ready to send"}
RULE_TEXT = {
    1: "A private value the AI saw could not be found on the picture's text, so it could not be covered safely.",
    2: "After covering, a private value could still be read on the safe copy.",
    3: "A step failed, timed out, or could not read enough of the picture to be sure.",
    4: "This kind of file is outside what Picture guard handles (one PNG or JPEG picture only).",
    5: "The AI counted more faces than the face finder covered."}


class Limited(Exception):
    pass


class Rejected(Exception):
    pass


class RateLimiter:
    def __init__(self, per_window: int, window_s: float = WINDOW_S, now=time.time):
        self.n, self.w, self.now, self.hits = per_window, window_s, now, {}

    def allow(self, who: str) -> bool:
        t = self.now()
        q = self.hits.setdefault(who, deque())
        while q and q[0] <= t - self.w:
            q.popleft()
        if len(q) >= self.n:
            return False
        q.append(t)
        return True


def sniff(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    return None


def plain_reason(report: dict) -> str | None:
    if not report["fail_safe"]["whole_black"]:
        return None
    for s in report["stages"]:
        if s["status"] in ("not_sure", "error", "timeout"):
            rule = s["answer"].get("failsafe_rule", 3) if s["status"] == "not_sure" else 3
            return f"Whole picture black. {RULE_TEXT.get(rule, RULE_TEXT[3])}"
    return f"Whole picture black. {RULE_TEXT[4]}"


class Demo:
    def __init__(self, guard_factory, samples_dir: Path, spark_key: str | None = None, post=spark._http_post, now=time.time, tmp_dir: str | None = None):
        self.guard_factory, self.samples_dir, self.key, self.post, self.now = guard_factory, Path(samples_dir), spark_key, post, now
        self.tmp_dir = tmp_dir or ("/dev/shm" if os.path.isdir("/dev/shm") else None)  # memory-backed where there is one
        self.rl_protect, self.rl_ask = RateLimiter(PROTECT_PER_WINDOW, now=now), RateLimiter(ASK_PER_WINDOW, now=now)
        self.sessions: dict = {}
        self.lock = threading.Lock()
        self.busy = threading.Semaphore(1)  # one run at a time: one container, one GPU
        self.waiting = 0
        self.day, self.day_count = None, 0
        self.last_wake = 0.0

    def info(self) -> dict:
        return {"samples": self.sample_names(), "max_bytes": MAX_BYTES, "spark_connected": bool(self.key), "spark_model": spark.MODEL,
                "stages": [{"name": k, "label": v} for k, v in STAGE_LABELS.items()],
                "banner": "Hackathon demo. Pictures are processed in memory and not stored. Please use made-up pictures."}

    def sample_names(self) -> list:
        return sorted(p.name for p in self.samples_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))

    def sample_bytes(self, name: str) -> bytes:
        if name not in self.sample_names():  # a name from the list only: no path tricks
            raise Rejected("no such sample")
        return (self.samples_dir / name).read_bytes()

    def _sweep(self):
        t = self.now()
        for k in [k for k, v in self.sessions.items() if v["at"] < t - SESSION_TTL_S]:
            del self.sessions[k]
        while len(self.sessions) >= MAX_SESSIONS:
            del self.sessions[min(self.sessions, key=lambda k: self.sessions[k]["at"])]

    def check_upload(self, data: bytes) -> None:
        if not data:
            raise Rejected("the file is empty")
        if len(data) > MAX_BYTES:
            raise Rejected(f"the file is over the {MAX_BYTES // (1024 * 1024)} MB limit")
        if sniff(data) is None:
            raise Rejected("only PNG or JPEG pictures are accepted")
        from io import BytesIO
        from PIL import Image
        try:
            with Image.open(BytesIO(data)) as im:
                w, h = im.size
        except Exception as ex:  # noqa: BLE001
            raise Rejected("that file is not a readable picture") from ex
        if w * h > MAX_PIXELS:
            raise Rejected(f"the picture is over {MAX_PIXELS // 1_000_000} megapixels")

    def protect_events(self, data: bytes, visitor: str):
        """Yields progress events (dicts), then one final {"event": "done", ...}. Raises Rejected/Limited before any work."""
        self.check_upload(data)
        today = time.strftime("%Y-%m-%d", time.gmtime(self.now()))
        with self.lock:
            if self.day != today:
                self.day, self.day_count = today, 0
            if self.day_count >= DAILY_PROTECT_CAP:
                raise Limited("the demo's daily limit is used up; please try again tomorrow")
            if not self.rl_protect.allow(visitor):
                raise Limited(f"too many pictures from you: at most {PROTECT_PER_WINDOW} every {WINDOW_S // 60} minutes")
            if self.waiting >= MAX_WAITING:
                raise Limited("the demo is busy; please try again in a minute")
            self.waiting += 1
            self.day_count += 1
        q: queue.Queue = queue.Queue()
        out: dict = {}

        def work():
            try:
                with self.busy:
                    q.put({"event": "start"})
                    with tempfile.TemporaryDirectory(prefix="pg-demo-", dir=self.tmp_dir) as d:
                        d = Path(d)
                        src, safe, rep = d / f"in.{sniff(data)}", d / "safe.png", d / "report.json"
                        src.write_bytes(data)
                        guard = self.guard_factory()
                        report = pipeline.protect(src, safe, rep, guard=guard, options={"fallback": "zoom", "on_stage": lambda e: q.put({"event": "stage", **e, "label": STAGE_LABELS.get(e["name"], e["name"])})})
                        out["safe"] = safe.read_bytes()
                        out["report"] = report
            except BaseException as ex:  # noqa: BLE001
                out["error"] = f"{type(ex).__name__}"
            finally:
                with self.lock:
                    self.waiting -= 1
                q.put(None)

        threading.Thread(target=work, daemon=True).start()
        t0 = time.time()
        while True:
            try:
                ev = q.get(timeout=max(0.1, REQUEST_TIMEOUT_S - (time.time() - t0)))
            except queue.Empty:
                yield {"event": "error", "message": "this took too long and was stopped"}
                return
            if ev is None:
                break
            yield ev
        if "error" in out:
            yield {"event": "error", "message": "something went wrong inside the demo; no picture was kept"}
            return
        yield self._done(out["safe"], out["report"], data)

    def _done(self, safe: bytes, report: dict, original: bytes) -> dict:
        decide = next((s for s in report["stages"] if s["name"] == "decide"), {"answer": {}})
        faces = next((s for s in report["stages"] if s["name"] == "faces"), {"answer": {}})
        covered = dict(decide["answer"].get("values_found_by_type") or {})
        n_faces = faces["answer"].get("masks", 0) if faces.get("status") == "ok" else 0
        whole = report["fail_safe"]["whole_black"]
        sid = base64.urlsafe_b64encode(os.urandom(12)).decode()
        orig_sha, safe_sha = report["input"]["sha256"], report["output"]["sha256"]
        assert spark.sha256(safe) == safe_sha  # the hash we show is the hash of the bytes we hold
        with self.lock:
            self._sweep()
            self.sessions[sid] = {"safe": safe, "safe_sha": safe_sha, "original_sha": orig_sha, "at": self.now(), "log": []}
        return {"event": "done", "session": sid, "whole_black": whole, "reason": plain_reason(report), "covered": {} if whole else covered,
                "faces_covered": 0 if whole else n_faces, "boxes_filled": report["output"]["boxes_filled"],
                "safe_png_base64": base64.b64encode(safe).decode(), "original_sha256": orig_sha, "safe_sha256": safe_sha,
                "original_bytes": len(original), "safe_bytes": len(safe),
                "stages": [{"name": s["name"], "label": STAGE_LABELS.get(s["name"], s["name"]), "status": s["status"], "seconds": s["seconds"]} for s in report["stages"]],
                "total_seconds": report["total_seconds"], "fail_safe_rules": [r.split(":")[0] for r in report["fail_safe"]["reasons"]],
                "stayed_inside": "The original went only to this demo's own Modal containers (text reading on CPU; Muse Glimmer and SAM on our GPU). It was never sent to Meta's API."}

    def ask(self, sid: str, question: str, visitor: str) -> dict:
        if not (question or "").strip():
            raise Rejected("please type a question")
        with self.lock:
            s = self.sessions.get(sid)
            if s is None or s["at"] < self.now() - SESSION_TTL_S:
                raise Rejected("that picture is no longer in memory; please run it again")
            if not self.rl_ask.allow(visitor):
                raise Limited(f"too many questions from you: at most {ASK_PER_WINDOW} every {WINDOW_S // 60} minutes")
        r = spark.ask(question, s["safe"], s["safe_sha"], s["original_sha"], self.key, self.post)
        with self.lock:
            s["log"].append(r["log"])
            log = list(s["log"])
        return {"answer": r["answer"], "error": r["error"], "connected": r["connected"], "request_log": log,
                "safe_sha256": s["safe_sha"], "original_sha256": s["original_sha"],
                "proof": {"sent_equals_safe_copy": r["log"]["image_sha256"] == s["safe_sha"], "sent_equals_original": r["log"]["image_sha256"] == s["original_sha"]}}
