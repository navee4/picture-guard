"""Code that runs INSIDE the Modal container (an L40S GPU): Muse Glimmer through llama.cpp, and SAM 3.1.
No picture_guard imports here: the container only gets this file. Models are read from the Modal Volume `pg1-models`."""
from __future__ import annotations

import base64
import inspect
import io
import json
import os
import re
import subprocess
import tempfile
import threading
import time

MODELS = "/models"
GGUF = f"{MODELS}/meta-models__Muse-Glimmer-30B-GGUF/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"
MMPROJ = f"{MODELS}/meta-models__Muse-Glimmer-30B-GGUF/mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"
LLAMA = "/opt/llama.cpp/build/bin/llama-server"
VALUE_TYPES = ["name", "address", "postcode", "sort_code", "account_number", "ni_number", "card_number", "iban",
               "id_number", "dob", "email", "phone"]
PROMPT = (
    "Look at this picture. It may be a document, a screenshot or a photo. List every PRIVATE value written in it: "
    "person names, street or town address lines, postcodes, UK sort codes, bank account numbers, National Insurance "
    "numbers, card numbers, IBANs, ID numbers, dates of birth, email addresses and phone numbers. Do NOT list company "
    "or product names, field labels, titles, amounts, pay dates, message text or other ordinary text. Also count the "
    "human faces you can see, including small avatars and partly covered faces. Reply with ONLY a JSON object, no "
    'other words: {{"values": [{{"text": "<the value exactly as written>", "type": "<one of {types}>"}}], '
    '"face_count": <number>}}. If there are no private values, use an empty list.'
)


BOXES_PROMPT = (
    "This picture is {w} pixels wide and {h} pixels high. These texts are written in it: {texts}. For each text, give the "
    "box where it is written, as [x1, y1, x2, y2] in pixels from the top-left corner of the picture. If a text appears "
    "more than once, give every box. Reply with ONLY a JSON object, no other words: "
    '{{"items": [{{"text": "<the text exactly as given>", "boxes": [[x1, y1, x2, y2]]}}]}}.'
)


def parse_boxes(text: str) -> tuple[list, str | None]:
    """([{text, boxes: [[x1,y1,x2,y2], ...]}], error). Boxes that are not four numbers are dropped."""
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return [], "no JSON object in the answer"
    try:
        d = json.loads(t[a:b + 1])
    except Exception as ex:  # noqa: BLE001
        return [], f"JSON error: {str(ex)[:80]}"
    items = d.get("items")
    if not isinstance(items, list):
        return [], "`items` is missing or not a list"
    out = []
    for it in items:
        if not (isinstance(it, dict) and isinstance(it.get("text"), str) and isinstance(it.get("boxes"), list)):
            continue
        bx = [[float(v) for v in b] for b in it["boxes"]
              if isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in b)]
        out.append({"text": it["text"], "boxes": bx})
    return out, None


def gpu_mem_mib() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    return int(out.strip().splitlines()[0])


def parse_answer(text: str) -> tuple[list, int | None, str | None]:
    """(values, face_count, error). The answer must be a JSON object with a `values` list. A missing face_count gives None."""
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return [], None, "no JSON object in the answer"
    try:
        d = json.loads(t[a:b + 1])
    except Exception as ex:  # noqa: BLE001
        return [], None, f"JSON error: {str(ex)[:80]}"
    vals = d.get("values")
    if not isinstance(vals, list) or not all(isinstance(v, dict) and isinstance(v.get("text"), str) for v in vals):
        return [], None, "`values` is missing or not a list of {text, type}"
    values = [{"text": v["text"], "type": str(v.get("type", "other"))} for v in vals if v["text"].strip()]
    fc = d.get("face_count")
    fc = int(fc) if isinstance(fc, (int, float)) and not isinstance(fc, bool) and fc >= 0 else None
    return values, fc, None


class Engine:
    def __init__(self):
        import torch  # noqa: F401
        t0 = time.time()
        self.peak = {"mib": 0}
        self._stop = threading.Event()
        threading.Thread(target=self._poll, daemon=True).start()
        cmd = [LLAMA, "-m", GGUF, "--mmproj", MMPROJ, "-a", "glimmer", "-ngl", "99", "-c", "32768", "-np", "1",
               "--host", "127.0.0.1", "--port", "8080", "--jinja", "--temp", "1.0", "--top-p", "0.95", "--top-k", "64",
               "--image-max-tokens", "4096", "--chat-template-kwargs", json.dumps({"reasoning_strength": "low"})]
        self.log = open("/tmp/llama.log", "w")
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT)
        import requests
        self.requests = requests
        ready = False
        while time.time() - t0 < 900 and self.proc.poll() is None:
            try:
                if requests.get("http://127.0.0.1:8080/health", timeout=2).status_code == 200:
                    ready = True
                    break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        if not ready:
            raise RuntimeError("llama-server did not start: " + open("/tmp/llama.log").read()[-1500:])
        self.glimmer_load_seconds = round(time.time() - t0, 1)
        t1 = time.time()
        from sam3.model_builder import build_sam3_predictor
        self.sam = build_sam3_predictor(version="sam3.1", use_fa3=False, async_loading_frames=False)
        ok = set(inspect.signature(self.sam.model.init_state).parameters)  # SAM 3.1 multiplex init_state takes fewer kwargs
        orig = self.sam.model.init_state
        self.sam.model.init_state = lambda *a, **k: orig(*a, **{x: y for x, y in k.items() if x in ok})
        self.sam_load_seconds = round(time.time() - t1, 1)
        self.load_seconds = round(time.time() - t0, 1)

    def _poll(self):
        while not self._stop.is_set():
            try:
                self.peak["mib"] = max(self.peak["mib"], gpu_mem_mib())
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)

    def info(self) -> dict:
        import torch
        return {"glimmer_load_seconds": self.glimmer_load_seconds, "sam_load_seconds": self.sam_load_seconds,
                "load_seconds": self.load_seconds, "gpu": torch.cuda.get_device_name(0), "peak_mib": self.peak["mib"]}

    def run_glimmer(self, png: bytes) -> dict:
        from PIL import Image
        t = time.time()
        try:
            w, h = Image.open(io.BytesIO(png)).size
            b64 = base64.b64encode(png).decode()
            body = {"model": "glimmer", "max_tokens": 6000, "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": PROMPT.format(types=", ".join(VALUE_TYPES))}]}]}
            r = self.requests.post("http://127.0.0.1:8080/v1/chat/completions", json=body, timeout=600).json()
            msg = r["choices"][0]["message"]
            values, fc, err = parse_answer(msg.get("content"))
            return {"values": values, "face_count": fc, "error": err, "seconds": round(time.time() - t, 2),
                    "finish": r["choices"][0].get("finish_reason"), "completion_tokens": (r.get("usage") or {}).get("completion_tokens"),
                    "w": w, "h": h}
        except Exception as ex:  # noqa: BLE001
            return {"values": [], "face_count": None, "error": f"request failed: {type(ex).__name__}: {str(ex)[:150]}", "seconds": round(time.time() - t, 2)}

    def run_glimmer_boxes(self, png: bytes, texts: list) -> dict:
        """Where does Glimmer say each text is? A rough guide only; the Mac side checks and calibrates it."""
        from PIL import Image
        t = time.time()
        try:
            w, h = Image.open(io.BytesIO(png)).size
            b64 = base64.b64encode(png).decode()
            prompt = BOXES_PROMPT.format(w=w, h=h, texts=json.dumps(list(texts), ensure_ascii=False))
            body = {"model": "glimmer", "max_tokens": 6000, "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}, {"type": "text", "text": prompt}]}]}
            r = self.requests.post("http://127.0.0.1:8080/v1/chat/completions", json=body, timeout=600).json()
            items, err = parse_boxes(r["choices"][0]["message"].get("content"))
            return {"items": items, "error": err, "seconds": round(time.time() - t, 2), "w": w, "h": h}
        except Exception as ex:  # noqa: BLE001
            return {"items": [], "error": f"request failed: {type(ex).__name__}: {str(ex)[:150]}", "seconds": round(time.time() - t, 2)}

    def run_sam(self, png: bytes) -> dict:
        import numpy as np
        from PIL import Image
        t = time.time()
        try:
            img = Image.open(io.BytesIO(png)).convert("RGB")
            w, h = img.size
            with tempfile.TemporaryDirectory() as d:
                path = f"{d}/in.png"
                img.save(path)
                sid = self.sam.handle_request(dict(type="start_session", resource_path=path))["session_id"]
                self.sam.handle_request(dict(type="reset_session", session_id=sid))
                o = self.sam.handle_request(dict(type="add_prompt", session_id=sid, frame_index=0, text="face"))["outputs"]
                self.sam.handle_request(dict(type="close_session", session_id=sid))
            m = np.asarray(o["out_binary_masks"])
            if m.size and m.shape[-2:] != (h, w):
                m = np.stack([np.asarray(Image.fromarray(x.astype(np.uint8) * 255).resize((w, h))) > 127 for x in m])
            m = m.astype(bool) if m.size else np.zeros((0, h, w), bool)
            probs = [float(x) for x in np.asarray(o["out_probs"]).ravel()] if "out_probs" in o else [None] * len(m)
            masks = []
            for k in range(len(m)):
                ys, xs = np.nonzero(m[k])
                if len(xs):
                    masks.append({"outer": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], "area": int(m[k].sum()),
                                  "prob": None if probs[k] is None else round(probs[k], 3)})
            return {"masks": masks, "error": None, "seconds": round(time.time() - t, 2)}
        except Exception as ex:  # noqa: BLE001
            return {"masks": [], "error": f"{type(ex).__name__}: {str(ex)[:150]}", "seconds": round(time.time() - t, 2)}

    def analyse(self, png: bytes, with_sam: bool = True) -> dict:
        t = time.time()
        out: dict = {}
        th = threading.Thread(target=lambda: out.__setitem__("sam", self.run_sam(png) if with_sam else None))
        th.start()
        out["glimmer"] = self.run_glimmer(png)
        th.join()
        out["container_seconds"] = round(time.time() - t, 2)
        out["peak_mib"] = self.peak["mib"]
        return out
