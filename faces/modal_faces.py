"""PG-2: make 75 AI portraits (SDXL base 1.0, Modal GPU) and locate each face with an independent detector (YuNet).

    modal run faces/modal_faces.py::make_portraits        # writes faces/portraits/*.png and faces/portraits_meta.json
    modal run faces/modal_faces.py::check_portraits       # regenerates 5 portraits, compares SHA-256 (determinism)

Spend cap for PG-2 is $10; ledger is faces/results/spend.jsonl.
"""
import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
sys.path.insert(0, str(ROOT / "faces"))
import common  # noqa: E402
import spec  # noqa: E402

common.LEDGER = ROOT / "faces" / "results" / "spend.jsonl"
common.SPEND_CAP_USD = 10.0

app = modal.App("pg2-faces")
vol = modal.Volume.from_name("pg2-faces", create_if_missing=True)
V = "/vol"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch", "diffusers", "transformers", "accelerate", "safetensors", "opencv-python-headless", "numpy", "pillow")
    .env({"HF_HOME": f"{V}/hf"})
    .add_local_file(ROOT / "faces" / "spec.py", "/root/spec.py")
    .add_local_file(ROOT / "spike" / "common.py", "/root/common.py")  # modal_faces imports common at load time
)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _load(torch):
    from diffusers import StableDiffusionXLPipeline
    pipe = StableDiffusionXLPipeline.from_pretrained(spec.SD_MODEL, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    return pipe.to("cuda")


def _gen(pipe, torch, prompt, negative, seed):
    g = torch.Generator(device="cuda").manual_seed(seed)
    img = pipe(prompt=prompt, negative_prompt=negative, num_inference_steps=30, guidance_scale=6.0, height=1024, width=1024, generator=g).images[0]
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return img, buf.getvalue()


def _detector():
    import urllib.request
    import cv2
    p = f"{V}/yunet.onnx"
    import os
    if not os.path.exists(p):
        urllib.request.urlretrieve(YUNET_URL, p)
    return cv2, cv2.FaceDetectorYN.create(p, "", (320, 320), 0.8, 0.3, 5000), p


@app.function(image=image, gpu="L40S", volumes={V: vol}, timeout=3000, cpu=4, memory=32768)
def make_portraits_remote(specs):
    import numpy as np
    import torch
    import diffusers
    vol.reload()
    t_start = time.time()
    cv2, det, onnx_path = _detector()
    pipe = _load(torch)
    out = {"diffusers": diffusers.__version__, "torch": str(torch.__version__), "yunet_sha256": _sha(open(onnx_path, "rb").read()),
           "portraits": [], "pngs": {}}
    for sp in specs:
        rec = None
        for attempt in range(4):  # a portrait must contain exactly one detected face; otherwise retry with a new seed
            seed = sp["seed"] + attempt * 100000
            img, png = _gen(pipe, torch, sp["prompt"], sp["negative"], seed)
            bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
            det.setInputSize((bgr.shape[1], bgr.shape[0]))
            _, faces = det.detect(bgr)
            n = 0 if faces is None else len(faces)
            rec = {"index": sp["index"], "seed_used": seed, "attempts": attempt + 1, "n_faces_detected": n, "sha256": _sha(png)}
            if n == 1:
                x, y, w, h = [float(v) for v in faces[0][:4]]
                rec.update(face_box=[max(0.0, x), max(0.0, y), min(1024.0, x + w), min(1024.0, y + h)], det_score=round(float(faces[0][14]), 4))
                break
        out["portraits"].append(rec)
        out["pngs"][sp["index"]] = png  # saved even when detection failed, so it can be looked at
    for i, png in out["pngs"].items():
        Path(f"{V}/portraits").mkdir(exist_ok=True)
        open(f"{V}/portraits/p{i:03d}.png", "wb").write(png)
    vol.commit()
    del out["pngs"]
    out["peak_gpu_mib"] = round(torch.cuda.max_memory_allocated() / 2**20)
    out["wall_seconds"] = time.time() - t_start
    return out


@app.local_entrypoint()
def make_portraits():
    specs = spec.build_specs()
    common.guard_budget(2.0)
    out = make_portraits_remote.remote(specs)
    common.log_spend("sdxl_portraits_75", out["wall_seconds"], "L40S", 4, 32, f"peak {out['peak_gpu_mib']} MiB")
    meta = {"model": spec.SD_MODEL, "diffusers": out["diffusers"], "torch": out["torch"], "detector": "OpenCV YuNet 2023mar (MIT)",
            "yunet_sha256": out["yunet_sha256"], "steps": 30, "guidance": 6.0, "size": 1024, "specs": specs, "portraits": out["portraits"]}
    (ROOT / "faces" / "portraits_meta.json").write_text(json.dumps(meta, indent=1))
    dest = ROOT / "faces" / "portraits"
    dest.mkdir(exist_ok=True)
    subprocess.run([str(ROOT / ".venv" / "bin" / "modal"), "volume", "get", "--force", "pg2-faces", "portraits", str(dest.parent)], check=True)
    bad = [p for p in out["portraits"] if p["n_faces_detected"] != 1]
    print("portraits", len(out["portraits"]), "not exactly one face after retries:", [(p["index"], p["n_faces_detected"]) for p in bad])
    print("attempts>1:", sum(p["attempts"] > 1 for p in out["portraits"]), "mean seconds each", round(out["wall_seconds"] / 75, 1))


@app.function(image=image, gpu="L40S", volumes={V: vol}, timeout=1200, cpu=4, memory=32768)
def regen(items):
    import torch
    vol.reload()
    t0 = time.time()
    pipe = _load(torch)
    res = []
    for sp, seed in items:
        _, png = _gen(pipe, torch, sp["prompt"], sp["negative"], seed)
        res.append({"index": sp["index"], "sha256": _sha(png)})
    return {"results": res, "wall_seconds": time.time() - t0}


@app.local_entrypoint()
def check_portraits(n: int = 5):
    meta = json.loads((ROOT / "faces" / "portraits_meta.json").read_text())
    by = {p["index"]: p for p in meta["portraits"]}
    pick = [meta["specs"][i] for i in range(0, 75, 75 // n)][:n]
    common.guard_budget(1.0)
    out = regen.remote([(sp, by[sp["index"]]["seed_used"]) for sp in pick])
    common.log_spend("sdxl_regen_check", out["wall_seconds"], "L40S", 4, 32, f"{n} portraits")
    same = [r["sha256"] == by[r["index"]]["sha256"] for r in out["results"]]
    print("regenerated", len(same), "identical SHA-256:", sum(same))
    (ROOT / "faces" / "results" / "portrait_determinism.json").write_text(json.dumps({"checked": [r["index"] for r in out["results"]], "identical": same}, indent=1))
