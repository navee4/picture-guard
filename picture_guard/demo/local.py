"""UI smoke server on this Mac: the real page and pipeline, but a FAKE guard (no models, so most pictures go whole black).
For checking the page only. `python -m picture_guard.demo.local` then open http://127.0.0.1:8765"""
from pathlib import Path

import uvicorn

from picture_guard.demo.core import Demo
from picture_guard.demo.web import create_app
from picture_guard.remote.fake import FakeGuard

demo = Demo(lambda: FakeGuard(values=[], face_count=0), Path(__file__).resolve().parent.parent.parent / "demo_samples")
app = create_app(demo)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
