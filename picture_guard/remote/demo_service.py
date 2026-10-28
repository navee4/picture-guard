"""The deployed demo: one Modal app with the web page (CPU, Tesseract) and the GPU class `Guard` (Glimmer + SAM).

Deploy with `python tools/deploy_demo.py` (it checks whether the Modal secret `meta-model-api` exists and runs `modal deploy`).
Limits: the web container and the GPU container are each capped at one (`max_containers=1`) and scale to zero when idle; each request
has a time limit; the page has a per-visitor rate limit and a daily cap.
"""
import os
from pathlib import Path

import modal

from picture_guard.remote.service import Guard, app as gpu_app

ROOT = Path(__file__).resolve().parent.parent.parent

app = modal.App("picture-guard-demo")
app.include(gpu_app)  # the GPU class `Guard` ships in the same deployed app

web_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("tesseract-ocr")
    .pip_install("pillow", "numpy", "fastapi", "python-multipart")
    # the container re-reads this module: it must see the same flag as the deploy, or Modal finds a different list of secrets and the container fails to start
    .env({"PG_HAVE_SPARK_SECRET": os.environ.get("PG_HAVE_SPARK_SECRET", "0")})
    .add_local_python_source("picture_guard")
    .add_local_dir(ROOT / "demo_samples", "/root/demo_samples")
)

secrets = []
if os.environ.get("PG_HAVE_SPARK_SECRET") == "1":  # set by tools/deploy_demo.py when the secret exists; the page says "not connected" otherwise
    secrets.append(modal.Secret.from_name("meta-model-api"))


@app.cls(image=web_image, cpu=8, memory=4096, secrets=secrets, timeout=300, scaledown_window=120, max_containers=1)
@modal.concurrent(max_inputs=6)
class Web:
    @modal.enter()
    def start(self):
        from picture_guard.demo.core import Demo
        from picture_guard.demo.web import create_app
        from picture_guard.remote.inapp import InAppGuard
        guard_cls = Guard()
        self.demo = Demo(lambda: InAppGuard(guard_cls), Path("/root/demo_samples"), spark_key=os.environ.get("META_MODEL_API_KEY") or None)
        self.app = create_app(self.demo, wake=lambda: guard_cls.ping.spawn())

    @modal.asgi_app()
    def serve(self):
        return self.app
