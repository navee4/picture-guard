"""PG-3: make AI portraits and empty backgrounds (SDXL base 1.0, Modal GPU) and check them with the YuNet face detector.

    modal run faces_hard/modal_hard.py::make_images --extra 0     # all specs from spec.py; --extra N adds a top-up batch (see below)
    modal run faces_hard/modal_hard.py::check_determinism         # regenerates 5 images, compares SHA-256

Portraits must contain exactly 1 face (YuNet score >= 0.8), else retry with seed + 100000 (3 tries, then dropped and logged).
Backgrounds must contain 0 faces at YuNet score >= 0.5, same retry rule.
Spend cap for PG-3 is $10; ledger is faces_hard/results/spend.jsonl.
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
sys.path.insert(0, str(ROOT / "faces_hard"))
import common  # noqa: E402
import spec  # noqa: E402

common.LEDGER = ROOT / "faces_hard" / "results" / "spend.jsonl"
common.SPEND_CAP_USD = 10.0

app = modal.App("pg3-faces")
vol = modal.Volume.from_name("pg3-faces", create_if_missing=True)
V = "/vol"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
PORTRAIT_SCORE, BG_SCORE, TRIES = 0.8, 0.5, 3

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch", "diffusers", "transformers", "accelerate", "safetensors", "opencv-python-headless", "numpy", "pillow")
    .env({"HF_HOME": f"{V}/hf"})
    .add_local_file(ROOT / "spike" / "common.py", "/root/common.py")  # modal_hard imports common at load time
    .add_local_file(ROOT / "faces_hard" / "spec.py", "/root/spec.py")
)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _load(torch):
    from diffusers import StableDiffusionXLPipeline
    pipe = StableDiffusionXLPipeline.from_pretrained(spec.SD_MODEL, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    return pipe.to("cuda")


def _gen(pipe, torch, sp, seed):
    g = torch.Generator(device="cuda").manual_seed(seed)
    img = pipe(prompt=sp["prompt"], negative_prompt=sp["negative"], num_inference_steps=30, guidance_scale=6.0,
               height=sp["height"], width=sp["width"], generator=g).images[0]
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return img, buf.getvalue()


def _detector(score):
    import os
    import urllib.request
    import cv2
    p = f"{V}/yunet.onnx"
    if not os.path.exists(p):
        urllib.request.urlretrieve(YUNET_URL, p)
    return cv2, cv2.FaceDetectorYN.create(p, "", (320, 320), score, 0.3, 5000), p


@app.function(image=image, gpu="L40S", volumes={V: vol}, timeout=3000, cpu=4, memory=32768)
def batch(specs):
    import numpy as np
    import torch
    import diffusers
    vol.reload()
    t_start = time.time()
    cv2_, det_p, onnx_path = _detector(PORTRAIT_SCORE)
    _, det_b, _ = _detector(BG_SCORE)
    pipe = _load(torch)
    out = {"diffusers": diffusers.__version__, "torch": str(torch.__version__), "yunet_sha256": _sha(open(onnx_path, "rb").read()),
           "items": []}
    Path(f"{V}/hard").mkdir(exist_ok=True)
    for sp in specs:
        rec = None
        for attempt in range(TRIES):
            seed = sp["seed"] + attempt * 100000
            img, png = _gen(pipe, torch, sp, seed)
            bgr = cv2_.cvtColor(np.asarray(img.convert("RGB")), cv2_.COLOR_RGB2BGR)
            det = det_b if sp["kind"] == "bg" else det_p
            det.setInputSize((bgr.shape[1], bgr.shape[0]))
            _, faces = det.detect(bgr)
            n = 0 if faces is None else len(faces)
            rec = {"index": sp["index"], "kind": sp["kind"], "seed_used": seed, "attempts": attempt + 1, "n_faces_detected": n,
                   "sha256": _sha(png)}
            ok = (n == 0) if sp["kind"] == "bg" else (n == 1)
            if n >= 1:
                rec["detections"] = [[round(float(v), 2) for v in f] for f in faces]  # x, y, w, h, 5 landmarks (x,y), score
            if ok:
                if sp["kind"] != "bg":
                    x, y, w, h = [float(v) for v in faces[0][:4]]
                    W, H = img.size
                    rec.update(face_box=[max(0.0, x), max(0.0, y), min(float(W), x + w), min(float(H), y + h)],
                               det_score=round(float(faces[0][14]), 4), landmarks=[round(float(v), 1) for v in faces[0][4:14]])
                rec["ok"] = True
                break
            rec["ok"] = False
        out["items"].append(rec)
        open(f"{V}/hard/i{sp['index']:03d}.png", "wb").write(png)  # saved even when the check failed, so it can be looked at
    vol.commit()
    out["peak_gpu_mib"] = round(torch.cuda.max_memory_allocated() / 2**20)
    out["wall_seconds"] = time.time() - t_start
    return out


@app.local_entrypoint()
def make_images(only: str = "", out_name: str = "images_meta.json"):
    """only: comma list of spec indices to (re)make; empty = all specs."""
    specs = spec.build_specs()
    if only:
        keep = {int(x) for x in only.split(",")}
        specs = [s for s in specs if s["index"] in keep]
    chunks = [specs[i::4] for i in range(4)]  # 4 containers in parallel
    common.guard_budget(2.5)
    t0 = time.time()
    results = []
    try:
        for r in batch.map(chunks):
            results.append(r)
    except BaseException as ex:  # log an estimate so the ledger stays honest
        common.log_spend(f"sdxl_images_FAILED_{type(ex).__name__}", 600, "L40S", 4, 32,
                         f"ESTIMATE after {time.time() - t0:.0f}s local wait; {str(ex)[:200]}")
        raise
    for k, r in enumerate(results):
        common.log_spend(f"sdxl_images_chunk{k}", r["wall_seconds"], "L40S", 4, 32, f"peak {r['peak_gpu_mib']} MiB; {len(r['items'])} images")
    items = sorted((it for r in results for it in r["items"]), key=lambda d: d["index"])
    path = ROOT / "faces_hard" / out_name
    meta = {"model": spec.SD_MODEL, "diffusers": results[0]["diffusers"], "torch": results[0]["torch"], "detector": "OpenCV YuNet 2023mar (MIT)",
            "yunet_sha256": results[0]["yunet_sha256"], "steps": 30, "guidance": 6.0, "portrait_score_threshold": PORTRAIT_SCORE,
            "bg_score_threshold": BG_SCORE, "tries": TRIES, "specs": specs, "items": items}
    path.write_text(json.dumps(meta, indent=1))
    dest = ROOT / "faces_hard" / "images_raw"
    dest.mkdir(exist_ok=True)
    got = ROOT / "faces_hard" / "hard"
    subprocess.run([str(ROOT / ".venv" / "bin" / "modal"), "volume", "get", "--force", "pg3-faces", "hard", str(ROOT / "faces_hard") + "/"], check=True)
    for f in got.glob("*.png"):
        f.replace(dest / f.name)
    got.rmdir()
    bad = [(it["index"], it["kind"], it["n_faces_detected"]) for it in items if not it["ok"]]
    print("images", len(items), "failed the face check after", TRIES, "seeds:", bad)
    print("attempts>1:", sum(it["attempts"] > 1 for it in items))


@app.function(image=image, gpu="L40S", volumes={V: vol}, timeout=1200, cpu=4, memory=32768)
def regen(items):
    import torch
    vol.reload()
    t0 = time.time()
    pipe = _load(torch)
    res = [{"index": sp["index"], "sha256": _sha(_gen(pipe, torch, sp, seed)[1])} for sp, seed in items]
    return {"results": res, "wall_seconds": time.time() - t0}


@app.local_entrypoint()
def check_determinism(n: int = 5, meta_name: str = "images_meta.json"):
    meta = json.loads((ROOT / "faces_hard" / meta_name).read_text())
    by = {it["index"]: it for it in meta["items"]}
    sp_by = {s["index"]: s for s in meta["specs"]}
    ids = [i for i in sorted(by) if by[i]["ok"]]
    pick = [ids[k * len(ids) // n] for k in range(n)]
    common.guard_budget(1.0)
    out = regen.remote([(sp_by[i], by[i]["seed_used"]) for i in pick])
    common.log_spend("sdxl_regen_check", out["wall_seconds"], "L40S", 4, 32, f"{n} images")
    same = [r["sha256"] == by[r["index"]]["sha256"] for r in out["results"]]
    print("regenerated", len(same), "identical SHA-256:", sum(same))
    (ROOT / "faces_hard" / "results" / "image_determinism.json").write_text(json.dumps({"checked": pick, "identical": same}, indent=1))
