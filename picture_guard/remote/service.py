"""The Modal app: one L40S container serves Muse Glimmer (llama.cpp, 4-bit) and SAM 3.1 together.

Used only through `picture_guard.remote.client.ModalGuard`, which runs it as an ephemeral app (`app.run()`), never `modal deploy`.
Weights come from the Volume `pg1-models` (Glimmer GGUF files and the SAM cache in `hf/`); SAM's gated download uses the Modal
secret `huggingface-secret`. Nothing is baked into the image.
"""
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
MODELS = "/models"

app = modal.App("picture-guard")
vol = modal.Volume.from_name("pg1-models")

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install("git", "cmake", "build-essential", "curl", "libcurl4-openssl-dev")
    .run_commands(
        "git clone --depth 1 https://github.com/ggml-org/llama.cpp /opt/llama.cpp",
        "cd /opt/llama.cpp && LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake -B build -DBUILD_SHARED_LIBS=OFF "
        "-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES='89;90' -DLLAMA_CURL=OFF "
        "&& LIBRARY_PATH=/usr/local/cuda/lib64/stubs cmake --build build --config Release -j 8 --target llama-server",
    )
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.10.0", "torchvision", index_url="https://download.pytorch.org/whl/cu128")
    .run_commands("git clone --depth 1 https://github.com/facebookresearch/sam3 /opt/sam3 && cd /opt/sam3 && pip install -e .")
    .pip_install("huggingface_hub[hf_transfer]", "pillow", "numpy", "einops", "pycocotools", "psutil", "requests")
    .env({"HF_HOME": f"{MODELS}/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_file(HERE / "container_impl.py", "/root/container_impl.py", copy=True)
)


@app.cls(image=image, gpu="L40S", volumes={MODELS: vol}, secrets=[modal.Secret.from_name("huggingface-secret")],
         timeout=1800, cpu=4, memory=32768, scaledown_window=600, max_containers=1)
class Guard:
    @modal.enter()
    def start(self):
        import container_impl
        self.engine = container_impl.Engine()

    @modal.method()
    def ping(self) -> dict:
        return self.engine.info()

    @modal.method()
    def analyse(self, png: bytes) -> dict:
        """Glimmer (private values, face count) and SAM ("face" masks) on one picture."""
        return self.engine.analyse(png, with_sam=True)

    @modal.method()
    def glimmer_only(self, png: bytes) -> dict:
        return self.engine.analyse(png, with_sam=False)

    @modal.method()
    def glimmer_boxes(self, png: bytes, texts: list) -> dict:
        """Glimmer's rough boxes for texts already known. Used only by the fallback for values Tesseract cannot find."""
        t = __import__("time").time()
        out = {"glimmer": self.engine.run_glimmer_boxes(png, texts)}
        out["container_seconds"] = round(__import__("time").time() - t, 2)
        return out
