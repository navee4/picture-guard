"""PG-1 model spike on Modal. Ephemeral apps only (`modal run`), never `modal deploy`.

Order (see spike/README.md):
    modal run spike/modal_app.py::download_glimmer          # weights -> Volume pg1-models (CPU only)
    modal run spike/modal_app.py::glimmer --model q4        # steps 2+3: 4-bit on L40S, 20 dev pictures
    modal run spike/modal_app.py::tesseract                 # step 6: plain OCR on CPU, same 20 pictures
    modal run spike/modal_app.py::download_sam              # needs Modal secret `huggingface` (HF_TOKEN)
    modal run spike/modal_app.py::sam                       # step 5: SAM 3.1 mask coverage, 3 prompt kinds

Only dev pictures are ever mounted (spike/prepare_dev.py stages them). The hold-out is never run.
Spend is appended to spike/results/spend.jsonl and checked against the $25 cap before every GPU run.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

app = modal.App("pg1-spike")
vol = modal.Volume.from_name("pg1-models", create_if_missing=True)
MODELS = "/models"
DEV_DIR = ROOT / "spike" / "out" / "dev"
RESULTS = ROOT / "spike" / "results"

GGUF_REPO = "meta-models/Muse-Glimmer-30B-GGUF"
GGUF_FILES = {"q4": "Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf", "q4xl": "Muse-Glimmer-30B-KQuant-Dynamic-Q4_K_XL.gguf"}
MMPROJ = "mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"

# ---- images -------------------------------------------------------------------------------------------
dl_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub[hf_transfer]").env(
    {"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": f"{MODELS}/hf"})

# llama.cpp must be build b10353 or newer (Muse Glimmer arch support). Built from master with CUDA for L40S (sm_89) + H100 (sm_90).
llama_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "cmake", "build-essential", "curl", "libcurl4-openssl-dev")
    .run_commands(
        "git clone --depth 1 https://github.com/ggml-org/llama.cpp /opt/llama.cpp",
        "cd /opt/llama.cpp && LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake -B build -DBUILD_SHARED_LIBS=OFF "
        "-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES='89;90' -DLLAMA_CURL=OFF "
        "&& LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake --build build --config Release -j 8 --target llama-server",
    )
    .pip_install("requests", "numpy")
    .add_local_file(ROOT / "spike" / "common.py", "/root/common.py", copy=True)
    .add_local_dir(DEV_DIR / "images", "/data/images")
    .add_local_file(DEV_DIR / "dev_key.json", "/data/dev_key.json")
)

tess_image = (
    modal.Image.debian_slim(python_version="3.12").apt_install("tesseract-ocr").pip_install("pytesseract", "pillow", "numpy")
    .add_local_file(ROOT / "spike" / "common.py", "/root/common.py", copy=True)
    .add_local_dir(DEV_DIR / "images", "/data/images")
    .add_local_file(DEV_DIR / "dev_key.json", "/data/dev_key.json")
)

sam_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.10.0", "torchvision", index_url="https://download.pytorch.org/whl/cu128")
    .run_commands("git clone --depth 1 https://github.com/facebookresearch/sam3 /opt/sam3 && cd /opt/sam3 && pip install -e .")
    .pip_install("huggingface_hub[hf_transfer]", "pillow", "numpy", "einops", "pycocotools", "psutil")
    .env({"HF_HOME": f"{MODELS}/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_file(ROOT / "spike" / "common.py", "/root/common.py", copy=True)
    .add_local_dir(DEV_DIR / "images", "/data/images")
    .add_local_file(DEV_DIR / "dev_key.json", "/data/dev_key.json")
)

PII_TYPES = ["name", "address", "postcode", "sort_code", "account_number", "ni_number", "card_number",
             "iban", "id_number", "dob", "email", "phone", "face"]
PROMPT = (
    "This is a made-up test picture. Find every PERSONAL value in it: person names, street or town address lines, "
    "postcodes, UK sort codes, bank account numbers, National Insurance numbers, card numbers, IBANs, ID numbers, "
    "dates of birth, email addresses, phone numbers, and faces. Do NOT list company names, field labels, titles, "
    "amounts, pay dates, message text or other ordinary text. The picture is {w} pixels wide and {h} pixels high. "
    "Reply with ONLY a JSON list, no other words. Each item: "
    '{{"text": "<the value exactly as written, empty for a face>", "type": "<one of {types}>", '
    '"box": [x0, y0, x1, y1]}} where box is the value\'s bounding box in pixels, measured from the top-left of this picture.'
)


def _gpu_mem_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,name", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout.strip().splitlines()[0]
    used, name = out.rsplit(",", 1)
    return int(used), name.strip()


# ---- step 0: download weights into the Volume (CPU container, no GPU) -----------------------------------
@app.function(image=dl_image, volumes={MODELS: vol}, timeout=3600, cpu=4, memory=8192)
def _download(repo: str, files: list):
    from huggingface_hub import snapshot_download
    t0 = time.time()
    path = snapshot_download(repo, local_dir=f"{MODELS}/{repo.replace('/', '__')}", allow_patterns=files)
    vol.commit()
    return {"path": path, "seconds": time.time() - t0}


@app.local_entrypoint()
def download_glimmer(model: str = "q4"):
    r = _download.remote(GGUF_REPO, [GGUF_FILES[model], MMPROJ])
    common.log_spend(f"download_glimmer_{model}", r["seconds"], None, 4, 8, "CPU download to Volume")
    print(r)


# ---- steps 2+3: Muse Glimmer on llama.cpp ---------------------------------------------------------------
def _parse_items(text):
    import re
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()
    for cand in (t, t[t.find("["): t.rfind("]") + 1] if "[" in t else ""):
        try:
            v = json.loads(cand)
            if isinstance(v, dict):
                v = v.get("items") or v.get("values") or [v]
            return [x for x in v if isinstance(x, dict)], None
        except Exception as e:  # noqa: BLE001
            err = str(e)
    return [], f"parse error: {err}"


def _glimmer_impl(model: str, names: list, reasoning: str, extra_flags: list):
    import base64
    import threading
    import requests
    t_start = time.time()
    gguf = f"{MODELS}/{GGUF_REPO.replace('/', '__')}/{GGUF_FILES[model]}"
    mmproj = f"{MODELS}/{GGUF_REPO.replace('/', '__')}/{MMPROJ}"
    ver = subprocess.run(["/opt/llama.cpp/build/bin/llama-server", "--version"], capture_output=True, text=True)
    cmd = ["/opt/llama.cpp/build/bin/llama-server", "-m", gguf, "--mmproj", mmproj, "-a", "glimmer", "-ngl", "99",
           "-c", "32768", "-np", "1", "--host", "127.0.0.1", "--port", "8080", "--jinja",
           "--temp", "1.0", "--top-p", "0.95", "--top-k", "64",
           "--chat-template-kwargs", json.dumps({"reasoning_strength": reasoning})] + extra_flags
    log = open("/tmp/server.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    peak = {"mib": 0, "gpu": ""}
    stop = threading.Event()

    def poll():
        while not stop.is_set():
            try:
                used, name = _gpu_mem_mib()
                peak["mib"] = max(peak["mib"], used); peak["gpu"] = name
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
    threading.Thread(target=poll, daemon=True).start()
    t0 = time.time()
    ready = False
    while time.time() - t0 < 900:
        if proc.poll() is not None:
            break
        try:
            if requests.get("http://127.0.0.1:8080/health", timeout=2).status_code == 200:
                ready = True; break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    load_s = time.time() - t0
    out = {"llama_version": (ver.stdout + ver.stderr).strip()[-300:], "cmd": " ".join(cmd), "load_seconds": round(load_s, 1),
           "ready": ready, "results": []}
    if not ready:
        proc.kill(); stop.set()
        out["server_log_tail"] = open("/tmp/server.log").read()[-4000:]
        out["wall_seconds"] = time.time() - t_start
        return out
    out["peak_mib_after_load"] = peak["mib"]
    key = {e["file"]: e for e in json.load(open("/data/dev_key.json"))["images"]}
    for name in names:
        e = key[name]
        assert e["split"] == "dev"
        b64 = base64.b64encode(open(f"/data/images/{name}", "rb").read()).decode()
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        body = {"model": "glimmer", "max_tokens": 6000, "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": PROMPT.format(w=e["width"], h=e["height"], types=", ".join(PII_TYPES))}]}]}
        t1 = time.time()
        try:
            r = requests.post("http://127.0.0.1:8080/v1/chat/completions", json=body, timeout=900).json()
            m = r["choices"][0]["message"]
            items, err = _parse_items(m.get("content"))
            rec = {"file": name, "seconds": round(time.time() - t1, 2), "items": items, "parse_error": err,
                   "content": m.get("content"), "reasoning_chars": len(m.get("reasoning_content") or ""),
                   "usage": r.get("usage"), "finish": r["choices"][0].get("finish_reason")}
        except Exception as ex:  # noqa: BLE001
            rec = {"file": name, "seconds": round(time.time() - t1, 2), "items": [], "parse_error": f"request failed: {ex}"}
        out["results"].append(rec)
    stop.set(); proc.terminate()
    out["peak_mib"] = peak["mib"]; out["gpu_name"] = peak["gpu"]
    out["server_log_tail"] = open("/tmp/server.log").read()[-2500:]
    out["wall_seconds"] = time.time() - t_start
    return out


@app.function(image=llama_image, gpu="L40S", volumes={MODELS: vol}, timeout=3600, cpu=4, memory=32768)
def glimmer_l40s(model, names, reasoning, extra_flags):
    vol.reload()
    return _glimmer_impl(model, names, reasoning, extra_flags)


def _score_glimmer(out, key_entries, run):
    """Score under three coordinate frames; the best frame on dev is the 'model frame' (inferred, not documented)."""
    by_file = {e["file"]: e for e in key_entries}
    report = {}
    for frame in ("px", "norm1000", "norm1"):
        rows = []
        for rec in out["results"]:
            e = by_file[rec["file"]]
            preds = []
            for it in rec["items"]:
                if common.valid_box(it.get("box")):
                    preds.append({"text": it.get("text", ""), "type": it.get("type", ""),
                                  "box": common.convert_frame(it["box"], frame, e["width"], e["height"])})
            rows.append((e, common.score_picture(e, preds)))
        report[frame] = common.aggregate(rows)
    return report


@app.local_entrypoint()
def glimmer(model: str = "q4", all_dev: bool = False, reasoning: str = "low", tag: str = "", flags: str = "--image-max-tokens 4096"):
    key = common.load_key(DEV_DIR / "dev_key.json")
    entries = common.select_eval(key, all_dev=all_dev)
    names = [e["file"] for e in entries]
    common.guard_budget(3.0 if not all_dev else 10.0)
    out = glimmer_l40s.remote(model, names, reasoning, flags.split())
    run = f"glimmer_{model}_{'dev150' if all_dev else 'dev20'}{tag}"
    common.log_spend(run, out["wall_seconds"], "L40S", 4, 32, f"ready={out['ready']} load={out['load_seconds']}s")
    if out["ready"]:
        out["score_by_frame"] = _score_glimmer(out, entries, run)
        secs = [r["seconds"] for r in out["results"]]
        out["seconds_per_picture_mean"] = round(sum(secs) / len(secs), 2)
        out["seconds_per_picture_median"] = sorted(secs)[len(secs) // 2]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("results", "score_by_frame", "server_log_tail")}, indent=1))
    if out["ready"]:
        for fr, agg in out["score_by_frame"].items():
            print(fr, json.dumps(agg["all"]))
    else:
        print(out["server_log_tail"][-1500:])


# ---- step 6: Tesseract on CPU --------------------------------------------------------------------------
@app.function(image=tess_image, cpu=2, memory=4096, timeout=1800)
def tesseract_run(names, psm):
    import pytesseract
    from PIL import Image
    t_start = time.time()
    res = []
    for n in names:
        t0 = time.time()
        d = pytesseract.image_to_data(Image.open(f"/data/images/{n}").convert("RGB"), config=f"--psm {psm}",
                                      output_type=pytesseract.Output.DICT)
        words = [{"text": d["text"][i], "box": [d["left"][i], d["top"][i], d["left"][i] + d["width"][i], d["top"][i] + d["height"][i]],
                  "line": (d["block_num"][i], d["par_num"][i], d["line_num"][i]), "conf": d["conf"][i]}
                 for i in range(len(d["text"])) if d["text"][i].strip()]
        res.append({"file": n, "seconds": round(time.time() - t0, 2), "words": words})
    return {"version": str(pytesseract.get_tesseract_version()), "psm": psm, "results": res, "wall_seconds": time.time() - t_start}


def _tess_preds(words, entry):
    """Word-box recall: a planted value is found if consecutive words on one line spell it (normalised)."""
    import itertools
    lines = {}
    for w in words:
        lines.setdefault(tuple(w["line"]), []).append(w)
    preds = []
    for s in (x for x in entry["spans"] if x["kind"] == "personal" and x["pii_type"] != "face"):
        target, best = common.norm(s["text"]), None
        for ws in lines.values():
            for i in range(len(ws)):
                acc = ""
                for j in range(i, min(len(ws), i + 10)):
                    acc += common.norm(ws[j]["text"])
                    if acc == target:
                        bx = [min(w["box"][0] for w in ws[i:j + 1]), min(w["box"][1] for w in ws[i:j + 1]),
                              max(w["box"][2] for w in ws[i:j + 1]), max(w["box"][3] for w in ws[i:j + 1])]
                        if best is None or common.iou(bx, s["box"]) > common.iou(best, s["box"]):
                            best = bx
                    elif not target.startswith(acc):
                        break
        if best:
            preds.append({"text": s["text"], "type": s["pii_type"], "box": best})
    return preds


@app.local_entrypoint()
def tesseract(all_dev: bool = False):
    key = common.load_key(DEV_DIR / "dev_key.json")
    entries = common.select_eval(key, all_dev=all_dev)
    names = [e["file"] for e in entries]
    final = {}
    for psm in (3, 11):
        out = tesseract_run.remote(names, psm)
        common.log_spend(f"tesseract_psm{psm}", out["wall_seconds"], None, 2, 4, "CPU")
        by_file = {e["file"]: e for e in entries}
        rows = [(by_file[r["file"]], common.score_picture(by_file[r["file"]], _tess_preds(r["words"], by_file[r["file"]])))
                for r in out["results"]]
        secs = [r["seconds"] for r in out["results"]]
        out["score"] = common.aggregate(rows)
        out["seconds_per_picture_mean"] = round(sum(secs) / len(secs), 2)
        final[f"psm{psm}"] = out
        print(f"psm {psm}", json.dumps(out["score"]["all"]), "s/pic", out["seconds_per_picture_mean"])
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"tesseract_{'dev150' if all_dev else 'dev20'}.json").write_text(json.dumps(final, indent=1))


# ---- step 5: SAM 3.1 -----------------------------------------------------------------------------------
@app.function(image=dl_image, volumes={MODELS: vol}, secrets=[modal.Secret.from_name("huggingface")], timeout=1800)
def _download_sam():
    from huggingface_hub import hf_hub_download
    t0 = time.time()
    for f in ("config.json", "sam3.1_multiplex.pt", "merges.txt", "vocab.json", "tokenizer.json"):
        hf_hub_download("facebook/sam3.1", f)
    vol.commit()
    return {"seconds": time.time() - t0}


@app.local_entrypoint()
def download_sam():
    r = _download_sam.remote()
    common.log_spend("download_sam", r["seconds"], None, 0.125, 0.25, "CPU download to Volume")


@app.function(image=sam_image, gpu="L40S", volumes={MODELS: vol}, secrets=[modal.Secret.from_name("huggingface")],
              timeout=3600, cpu=4, memory=32768)
def sam_run(jobs):
    """jobs: [{file, key_boxes:[{box,pii_type,text}], glimmer_boxes:[[x0,y0,x1,y1]...]}]. Returns coverage numbers."""
    import os
    import shutil
    import threading
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
                peak["mib"] = max(peak["mib"], _gpu_mem_mib()[0])
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
    threading.Thread(target=poll, daemon=True).start()
    t0 = time.time()
    predictor = build_sam3_predictor(version="sam3.1", use_fa3=False, async_loading_frames=False)
    load_s = time.time() - t0
    out = {"load_seconds": round(load_s, 1), "pictures": []}

    def prompt(sid, **kw):
        return predictor.handle_request(dict(type="add_prompt", session_id=sid, frame_index=0, **kw))["outputs"]

    def masks_of(o, w, h):
        m = np.asarray(o["out_binary_masks"])
        if m.size == 0:
            return {}, m
        ids = [int(i) for i in np.asarray(o["out_obj_ids"])]
        if m.shape[-2:] != (h, w):
            m = np.stack([np.asarray(Image.fromarray(x.astype(np.uint8) * 255).resize((w, h))) > 127 for x in m])
        return dict(zip(ids, m.astype(bool))), m.astype(bool)

    for job in jobs:
        name = job["file"]
        img = Image.open(f"/data/images/{name}").convert("RGB")
        w, h = img.size
        d = f"/tmp/frames/{name}"
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        img.save(f"{d}/00000.jpg", quality=95)  # the video loader reads a folder of JPEG frames
        t1 = time.time()
        sid = predictor.handle_request(dict(type="start_session", resource_path=d))["session_id"]
        rec = {"file": name, "w": w, "h": h, "key_cov": [], "glimmer_cov": [], "text_cov": []}

        def rel(b):
            return [[b[0] / w, b[1] / h, (b[2] - b[0]) / w, (b[3] - b[1]) / h]]  # relative xywh
        # (a) the key's own boxes as box prompts (best case)
        for k, s in enumerate(job["key_boxes"]):
            o = prompt(sid, bounding_boxes=rel(s["box"]), bounding_box_labels=[1], obj_id=k + 1)
            ms, _ = masks_of(o, w, h)
            m = ms.get(k + 1)
            rec["key_cov"].append({"pii_type": s["pii_type"], "cov": common.coverage(m, s["box"]) if m is not None else 0.0, "got_mask": m is not None})
        predictor.handle_request(dict(type="reset_session", session_id=sid))
        # (b) Glimmer's boxes as box prompts (real case): per planted box, the best returned box that hits it
        for k, s in enumerate(job["key_boxes"]):
            cands = [(common.iou(s["box"], g), g) for g in job["glimmer_boxes"] if common.hits(s["box"], g)]
            if not cands:
                rec["glimmer_cov"].append({"pii_type": s["pii_type"], "cov": 0.0, "got_mask": False, "had_box": False})
                continue
            g = max(cands)[1]
            o = prompt(sid, bounding_boxes=rel(g), bounding_box_labels=[1], obj_id=1000 + k)
            ms, _ = masks_of(o, w, h)
            m = ms.get(1000 + k)
            rec["glimmer_cov"].append({"pii_type": s["pii_type"], "cov": common.coverage(m, s["box"]) if m is not None else 0.0,
                                       "got_mask": m is not None, "had_box": True})
        predictor.handle_request(dict(type="reset_session", session_id=sid))
        # (c) text prompts: "text" for text spans, "face" for faces; union of all returned masks
        for phrase in ("text", "face"):
            o = prompt(sid, text=phrase)
            _, allm = masks_of(o, w, h)
            union = allm.any(axis=0) if allm.size else np.zeros((h, w), bool)
            for s in job["key_boxes"]:
                if (phrase == "face") == (s["pii_type"] == "face"):
                    rec["text_cov"].append({"pii_type": s["pii_type"], "prompt": phrase, "cov": common.coverage(union, s["box"]), "n_masks": int(len(allm))})
            predictor.handle_request(dict(type="reset_session", session_id=sid))
        predictor.handle_request(dict(type="close_session", session_id=sid))
        rec["seconds"] = round(time.time() - t1, 2)
        out["pictures"].append(rec)
    stop.set()
    out["peak_mib_nvidia_smi"] = peak["mib"]
    out["peak_mib_torch_allocated"] = round(torch.cuda.max_memory_allocated() / 2**20)
    out["gpu_name"] = torch.cuda.get_device_name(0)
    out["wall_seconds"] = time.time() - t_start
    return out


@app.local_entrypoint()
def sam(glimmer_run: str = "glimmer_q4_dev20", frame: str = "px", all_dev: bool = False):
    key = common.load_key(DEV_DIR / "dev_key.json")
    entries = common.select_eval(key, all_dev=all_dev)
    gl = json.loads((RESULTS / f"{glimmer_run}.json").read_text())
    gl_by = {r["file"]: r for r in gl["results"]}
    jobs = []
    for e in entries:
        gboxes = [common.convert_frame(it["box"], frame, e["width"], e["height"]) for it in gl_by.get(e["file"], {}).get("items", [])
                  if common.valid_box(it.get("box"))]
        jobs.append({"file": e["file"], "glimmer_boxes": gboxes,
                     "key_boxes": [{"box": s["box"], "pii_type": s["pii_type"], "text": s["text"]} for s in e["spans"] if s["kind"] == "personal"]})
    common.guard_budget(3.0)
    out = sam_run.remote(jobs)
    common.log_spend("sam31_dev20", out["wall_seconds"], "L40S", 4, 32, f"load={out['load_seconds']}s")
    summ = {}
    for kind in ("key_cov", "glimmer_cov", "text_cov"):
        vals = [c["cov"] for p in out["pictures"] for c in p[kind]]
        summ[kind] = {"n": len(vals), "mean_coverage": round(sum(vals) / max(1, len(vals)), 3),
                      "share_ge_0.5": round(sum(v >= 0.5 for v in vals) / max(1, len(vals)), 3),
                      "share_ge_0.9": round(sum(v >= 0.9 for v in vals) / max(1, len(vals)), 3)}
    out["summary"] = summ
    out["seconds_per_picture_mean"] = round(sum(p["seconds"] for p in out["pictures"]) / len(out["pictures"]), 2)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "sam31_dev20.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "pictures"}, indent=1))
