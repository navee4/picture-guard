"""Deploy the demo to Modal (unlisted URL; scales to zero). Run from the repo root: `.venv/bin/python tools/deploy_demo.py`.
Muse Spark is connected only if the Modal secret `meta-model-api` (key `META_MODEL_API_KEY`) exists; otherwise the page says so."""
import json
import os
import subprocess
import sys

r = subprocess.run([sys.executable, "-m", "modal", "secret", "list", "--json"], capture_output=True, text=True)
have = False
try:
    have = any(s.get("name") == "meta-model-api" for s in json.loads(r.stdout))
except Exception:  # noqa: BLE001
    pass
print("Muse Spark secret:", "found, will connect" if have else "not found, the page will say not connected")
env = {**os.environ, "PG_HAVE_SPARK_SECRET": "1" if have else "0"}
sys.exit(subprocess.run([sys.executable, "-m", "modal", "deploy", "-m", "picture_guard.remote.demo_service"], env=env).returncode)
