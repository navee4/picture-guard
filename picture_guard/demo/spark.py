"""The Muse Spark step (Meta Model API). Only the safe copy may go out; the code proves it before every send.

Model: `muse-spark-1.3` (Standard mode: content not used for training; never a `-contributor` model). Endpoint: the Responses API,
`POST https://api.meta.ai/v1/responses`, bearer key, image as an `input_image` block holding a base64 data URL (docs: dev.meta.ai/docs).
The key is read from the environment (`META_MODEL_API_KEY`, set from the Modal secret `meta-model-api`). With no key, a fake answers
and nothing leaves the machine.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import urllib.error
import urllib.request

HOST = "api.meta.ai"
URL = f"https://{HOST}/v1/responses"
MODEL = "muse-spark-1.3"
MAX_QUESTION_CHARS = 500
TIMEOUT_S = 60


class SparkRefused(Exception):
    """The request was refused before it left: something other than the safe copy was in it."""


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_body(question: str, safe_png: bytes) -> dict:
    data_url = "data:image/png;base64," + base64.b64encode(safe_png).decode()
    return {"model": MODEL, "input": [{"role": "user", "content": [
        {"type": "input_text", "text": question},
        {"type": "input_image", "image_url": data_url}]}]}


def images_in_body(body) -> list[bytes]:
    """Every image the request would carry, decoded from its data URLs (found anywhere in the body, so nothing hides)."""
    found: list[bytes] = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            m = re.match(r"data:[\w/+.-]+;base64,(.*)$", x, re.S)
            if m:
                found.append(base64.b64decode(m.group(1)))
            elif x.startswith(("http://", "https://", "file_")):
                found.append(b"\x00url:" + x.encode())  # a URL or file id is never the safe copy: it will fail the check
    walk(body)
    return found


def check_only_safe(body, safe_sha: str, original_sha: str) -> list[str]:
    """Raises SparkRefused unless the body carries exactly one image whose SHA-256 is the safe copy's and not the original's."""
    imgs = images_in_body(body)
    hashes = [sha256(i) for i in imgs]
    if len(imgs) != 1:
        raise SparkRefused(f"the request carries {len(imgs)} images; exactly one (the safe copy) is allowed")
    if hashes[0] == original_sha or hashes[0] != safe_sha:
        raise SparkRefused("the image in the request is not the safe copy")
    return hashes


def _http_post(url: str, headers: dict, payload: bytes, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read()


def answer_text(resp: dict) -> str | None:
    for item in resp.get("output", []) or []:
        if isinstance(item, dict) and item.get("type") == "message":
            for part in item.get("content", []) or []:
                if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    return part["text"]
    return None


def ask(question: str, safe_png: bytes, safe_sha: str, original_sha: str, api_key: str | None, post=_http_post) -> dict:
    """{"answer": str|None, "error": str|None, "connected": bool, "log": {host, bytes, sha256, at, sent}}.
    The log holds a hash and a size, never picture bytes or text."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if sha256(safe_png) != safe_sha:
        raise SparkRefused("the bytes to send do not match the safe copy's hash")
    body = build_body(question, safe_png)
    hashes = check_only_safe(body, safe_sha, original_sha)
    payload = json.dumps(body).encode()
    log = {"host": HOST if api_key else "(nothing sent: Muse Spark not connected yet)", "image_bytes": len(safe_png), "request_bytes": len(payload),
           "image_sha256": hashes[0], "at": int(time.time()), "sent": False}
    if not api_key:
        return {"answer": ("Muse Spark is not connected yet, so this is a stand-in answer. Your question and the safe copy "
                           f"({len(safe_png):,} bytes, SHA-256 starting {safe_sha[:12]}) would have gone to the Meta Model API, and nothing else."),
                "error": None, "connected": False, "log": log}
    t0 = time.monotonic()
    try:
        status, raw = post(URL, {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, payload, TIMEOUT_S)
    except Exception as ex:  # noqa: BLE001
        return {"answer": None, "error": f"could not reach Muse Spark: {type(ex).__name__}", "connected": True, "log": {**log, "sent": True}}
    log["sent"] = True
    log["seconds"] = round(time.monotonic() - t0, 2)
    log["http_status"] = status
    if status != 200:
        code = None
        try:
            code = (json.loads(raw).get("error") or {}).get("code")
        except Exception:  # noqa: BLE001
            pass
        return {"answer": None, "error": f"Muse Spark answered HTTP {status}" + (f" ({code})" if isinstance(code, str) and len(code) < 60 else ""), "connected": True, "log": log}
    try:
        resp = json.loads(raw)
        text = answer_text(resp)
        usage = resp.get("usage")
        if isinstance(usage, dict):  # token counts only (numbers), never text
            log["usage"] = {k: v for k, v in usage.items() if isinstance(v, int) and not isinstance(v, bool)}
    except Exception:  # noqa: BLE001
        text = None
    if text is None:
        return {"answer": None, "error": "Muse Spark's answer could not be read", "connected": True, "log": log}
    return {"answer": text, "error": None, "connected": True, "log": log}
