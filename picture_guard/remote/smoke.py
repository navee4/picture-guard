"""One picture through the Modal app and back: `.venv/bin/python -m picture_guard.remote.smoke <picture.png>`. Prints counts, never text."""
import io
import sys

from PIL import Image

from picture_guard.remote.client import ModalGuard

with ModalGuard("smoke") as g:
    print("cold start", g.cold_start_seconds, "s;", g.info)
    buf = io.BytesIO()
    Image.open(sys.argv[1]).convert("RGB").save(buf, format="PNG")
    for _ in range(2):
        r = g.analyse(buf.getvalue())
        gl, sm = r["glimmer"], r["sam"]
        print("glimmer: error", gl["error"], "| values", len(gl["values"]), "| face_count", gl["face_count"], "|", gl["seconds"], "s | tokens", gl.get("completion_tokens"))
        print("sam: error", sm["error"], "| masks", len(sm["masks"]), "|", sm["seconds"], "s | container", r["container_seconds"], "s | peak MiB", r["peak_mib"])
        print("types", [v["type"] for v in gl["values"]])
