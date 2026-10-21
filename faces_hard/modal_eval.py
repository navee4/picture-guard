"""PG-3: run SAM 3.1 ("face" prompt) and Muse Glimmer 4-bit (reasoning low) on the 60 DEV harder-face pictures. Modal only.

    modal run faces_hard/modal_eval.py::glimmer_faces
    modal run faces_hard/modal_eval.py::sam_faces

Only dev pictures are staged (spike/out/faces_hard_dev). The face hold-out is never mounted, never run.
Spend ledger: faces_hard/results/spend.jsonl, cap $10. Glimmer and SAM code is PG-1's, imported unchanged. Same prompt, flags and SAM calls as PG-2.
"""
import json
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
import common  # noqa: E402
import modal_app as pg1  # noqa: E402  (PG-1 helpers: PROMPT, _glimmer_impl, image recipes)

common.LEDGER = ROOT / "faces_hard" / "results" / "spend.jsonl"
common.SPEND_CAP_USD = 10.0  # PG-3 cap

app = modal.App("pg3-eval")
FACES_DEV = ROOT / "spike" / "out" / "faces_hard_dev"
RESULTS = ROOT / "faces_hard" / "results"
MODELS = pg1.MODELS
vol = modal.Volume.from_name("pg1-models")  # PG-1's model volume, read only use; must already exist

_code = [(ROOT / "spike" / "common.py", "/root/common.py"), (ROOT / "spike" / "modal_app.py", "/root/modal_app.py")]


def _with_data(img):
    for src, dst in _code:
        img = img.add_local_file(src, dst, copy=True)
    return img.add_local_dir(FACES_DEV / "images", "/data/images").add_local_file(FACES_DEV / "dev_key.json", "/data/dev_key.json")


# same recipes as PG-1 (layers are cached), then PG-2 code and DEV face pictures
llama_image = _with_data(
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "cmake", "build-essential", "curl", "libcurl4-openssl-dev")
    .run_commands(
        "git clone --depth 1 https://github.com/ggml-org/llama.cpp /opt/llama.cpp",
        "cd /opt/llama.cpp && LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake -B build -DBUILD_SHARED_LIBS=OFF "
        "-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES='89;90' -DLLAMA_CURL=OFF "
        "&& LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake --build build --config Release -j 8 --target llama-server",
    )
    .pip_install("requests", "numpy")
)
sam_image = _with_data(
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.10.0", "torchvision", index_url="https://download.pytorch.org/whl/cu128")
    .run_commands("git clone --depth 1 https://github.com/facebookresearch/sam3 /opt/sam3 && cd /opt/sam3 && pip install -e .")
    .pip_install("huggingface_hub[hf_transfer]", "pillow", "numpy", "einops", "pycocotools", "psutil")
    .env({"HF_HOME": f"{MODELS}/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


def _entries():
    return json.loads((FACES_DEV / "dev_key.json").read_text())["images"]


def _faces(e):
    return [s["box"] for s in e["spans"] if s["pii_type"] == "face"]


@app.function(image=llama_image, gpu="L40S", volumes={MODELS: vol}, timeout=3600, cpu=4, memory=32768)
def glimmer_remote(names, reasoning, flags):
    vol.reload()
    return pg1._glimmer_impl("q4", names, reasoning, flags)


@app.function(image=sam_image, gpu="L40S", volumes={MODELS: vol}, secrets=[modal.Secret.from_name("huggingface-secret")],
              timeout=3600, cpu=4, memory=32768)
def sam_remote(jobs, phrase):
    """Per picture: fresh session, one text prompt, keep every returned mask (nothing is merged here)."""
    import inspect
    import threading
    import traceback
    import numpy as np
    import torch
    from PIL import Image
    vol.reload()
    t_start = time.time()
    from sam3.model_builder import build_sam3_predictor
    peak = {"mib": 0}
    stop = threading.Event()

    def poll():
        while not stop.is_set():
            try:
                peak["mib"] = max(peak["mib"], pg1._gpu_mem_mib()[0])
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
    threading.Thread(target=poll, daemon=True).start()
    t0 = time.time()
    predictor = build_sam3_predictor(version="sam3.1", use_fa3=False, async_loading_frames=False)
    load_s = time.time() - t0
    # SAM 3.1 multiplex init_state does not take the kwargs the base predictor passes (TypeError in PG-1): drop them.
    _orig = predictor.model.init_state
    _ok = set(inspect.signature(_orig).parameters)
    predictor.model.init_state = lambda *a, **k: _orig(*a, **{x: y for x, y in k.items() if x in _ok})
    out = {"load_seconds": round(load_s, 1), "phrase": phrase, "pictures": [], "errors": []}
    for job in jobs:
        name = job["file"]
        try:
            w, h = Image.open(f"/data/images/{name}").size
            t1 = time.time()
            sid = predictor.handle_request(dict(type="start_session", resource_path=f"/data/images/{name}"))["session_id"]
            predictor.handle_request(dict(type="reset_session", session_id=sid))
            o = predictor.handle_request(dict(type="add_prompt", session_id=sid, frame_index=0, text=phrase))["outputs"]
            m = np.asarray(o["out_binary_masks"])
            if m.size and m.shape[-2:] != (h, w):
                m = np.stack([np.asarray(Image.fromarray(x.astype(np.uint8) * 255).resize((w, h))) > 127 for x in m])
            m = m.astype(bool) if m.size else np.zeros((0, h, w), bool)
            probs = [round(float(x), 3) for x in np.asarray(o["out_probs"]).ravel()] if "out_probs" in o else None
            sec = round(time.time() - t1, 2)
            predictor.handle_request(dict(type="close_session", session_id=sid))
            masks = []
            for k in range(len(m)):
                ys, xs = np.nonzero(m[k])
                masks.append({"area": int(m[k].sum()), "outer": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                              "cov": [round(common.coverage(m[k], b), 4) for b in job["face_boxes"]]})
            union = m.any(axis=0) if len(m) else np.zeros((h, w), bool)
            out["pictures"].append({"file": name, "w": w, "h": h, "seconds": sec, "n_masks": len(m), "probs": probs, "masks": masks,
                                    "union_cov": [round(common.coverage(union, b), 4) for b in job["face_boxes"]]})
        except Exception:  # noqa: BLE001
            out["errors"].append({"file": name, "traceback": traceback.format_exc()[-2500:]})
            if len(out["errors"]) >= 2 and not out["pictures"]:
                break
    stop.set()
    out["peak_mib_nvidia_smi"] = peak["mib"]
    out["peak_mib_torch_allocated"] = round(torch.cuda.max_memory_allocated() / 2**20)
    out["gpu_name"] = torch.cuda.get_device_name(0)
    out["wall_seconds"] = time.time() - t_start
    return out


def _run(label, fn, *args, reserve, est_usd):
    """Call a remote function; if it throws, log an estimate so the ledger stays honest."""
    common.guard_budget(reserve)
    t0 = time.time()
    try:
        return fn.remote(*args)
    except BaseException as ex:
        common.log_spend(f"{label}_FAILED_{type(ex).__name__}", est_usd / common.cost_usd(1, "L40S", 4, 32), "L40S", 4, 32,
                         f"ESTIMATE after {time.time() - t0:.0f}s local wait; {str(ex)[:200]}")
        raise


@app.local_entrypoint()
def glimmer_faces(reasoning: str = "low", flags: str = "--image-max-tokens 4096", tag: str = ""):
    entries = _entries()
    assert all(e["split"] == "dev" for e in entries) and len(entries) == 60
    out = _run("glimmer_q4_faces_dev60", glimmer_remote, [e["file"] for e in entries], reasoning, flags.split(), reserve=2.0, est_usd=0.6)
    run = f"glimmer_q4_faces_dev60{tag}"
    common.log_spend(run, out["wall_seconds"], "L40S", 4, 32, f"ready={out['ready']} load={out['load_seconds']}s")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("results", "server_log_tail")}, indent=1)[:2500])
    if not out["ready"]:
        print(out["server_log_tail"][-1500:])
    else:
        print("parse errors:", sum(1 for r in out["results"] if r.get("parse_error")), "of", len(out["results"]))


@app.local_entrypoint()
def sam_faces(phrase: str = "face", tag: str = ""):
    entries = _entries()
    assert all(e["split"] == "dev" for e in entries) and len(entries) == 60
    jobs = [{"file": e["file"], "face_boxes": _faces(e)} for e in entries]
    out = _run("sam31_faces_dev60", sam_remote, jobs, phrase, reserve=1.5, est_usd=0.3)
    run = f"sam31_faces_dev60{tag}"
    common.log_spend(run, out["wall_seconds"], "L40S", 4, 32, f"load={out['load_seconds']}s")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "pictures"}, indent=1)[:3000])
    print("pictures", len(out["pictures"]), "with >=1 mask", sum(p["n_masks"] > 0 for p in out["pictures"]))
