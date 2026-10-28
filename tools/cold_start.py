"""Cold start of the GPU app (ephemeral, our own): seconds until both models answer, then one warm call. Logs spend to the ledger.
Usage: PG_SPEND_CAP_USD=... python tools/cold_start.py <label>"""
import json
import sys
import time

from picture_guard.remote.client import ModalGuard

label = sys.argv[1] if len(sys.argv) > 1 else "cold"
png = open("demo_samples/id_card_001.png", "rb").read()
from PIL import Image
import io
buf = io.BytesIO(); Image.open(io.BytesIO(png)).convert("RGB").save(buf, "PNG")
t = time.perf_counter()
with ModalGuard(f"pg14-{label}", reserve_usd=1.0) as g:
    cold = g.cold_start_seconds
    t1 = time.perf_counter(); r = g.analyse(buf.getvalue()); first = time.perf_counter() - t1
    t1 = time.perf_counter(); r2 = g.analyse(buf.getvalue()); second = time.perf_counter() - t1
    print(json.dumps({"label": label, "cold_start_s": cold, "info": g.info, "first_call_s": round(first, 1), "second_call_s": round(second, 1),
                      "glimmer_s": (r2.get("glimmer") or {}).get("seconds"), "sam_s": (r2.get("sam") or {}).get("seconds"), "container_s": r2.get("container_seconds"), "total_s": round(time.perf_counter() - t, 1)}))
