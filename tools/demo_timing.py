"""Time the deployed demo: POST each sample to /api/protect, print wall time and per-stage seconds. Usage: python tools/demo_timing.py URL [rounds]
The first request after idle is the cold one. Samples are made-up dev pictures. No picture text is printed."""
import json
import sys
import time
import urllib.request
import uuid

SAMPLES = ["payslip_000.jpg", "letter_000.png", "id_card_001.png", "chat_005.png"]


def one(url, name):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"sample\"\r\n\r\n{name}\r\n--{b}--\r\n").encode()
    req = urllib.request.Request(url + "/api/protect", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    t0, first, done = time.perf_counter(), None, None
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            ev = json.loads(line)
            if first is None:
                first = time.perf_counter() - t0
            if ev.get("event") == "done":
                done = ev
    wall = time.perf_counter() - t0
    st = {s["name"]: s["seconds"] for s in done["stages"]} if done else {}
    return {"sample": name, "wall": round(wall, 1), "first_event": round(first or 0, 1), "whole_black": done and done["whole_black"], "report_total": done and done["total_seconds"], "stages": st}


if __name__ == "__main__":
    url = sys.argv[1].rstrip("/")
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for rd in range(rounds):
        for name in SAMPLES:
            print(json.dumps({"round": rd, **one(url, name)}), flush=True)
