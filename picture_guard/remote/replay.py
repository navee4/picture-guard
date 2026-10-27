"""Replay saved Modal answers for dev pictures, so a re-run pays only for calls that were never made.

Used by `pg eval --replay`. The saved Glimmer/SAM answers of an earlier run are looked up by the SHA-256 of the PNG bytes that
`decide` would send; the box answers of the fallback are kept in a cache file the same way. A call with no saved answer goes
to the real Modal app, which is started only then (and stopped at exit). Made-up dev pictures only; the cache files are git-ignored.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from picture_guard.remote.client import ModalGuard, RemoteError


def key_of(png: bytes) -> str:
    return hashlib.sha256(png).hexdigest()


class ReplayGuard:
    def __init__(self, analyse_by_key: dict, round_trip_by_key: dict, boxes_cache: Path, run_name: str):
        self.saved, self.trips, self.boxes_path, self.run_name = analyse_by_key, round_trip_by_key, Path(boxes_cache), run_name
        self.boxes: dict = {}
        if self.boxes_path.exists():
            for line in self.boxes_path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.boxes[r["key"]] = r
        self.calls: list = []
        self.live: ModalGuard | None = None
        self.cold_start_seconds = None
        self.info = None
        self.live_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.live is not None:
            self.live.__exit__(*exc)

    def reset_calls(self):
        self.calls = []

    def _live(self) -> ModalGuard:
        if self.live is None:
            self.live = ModalGuard(self.run_name, reserve_usd=1.0).__enter__()
            self.cold_start_seconds, self.info = self.live.cold_start_seconds, self.live.info
        return self.live

    def analyse(self, png: bytes) -> dict:
        k = key_of(png)
        if k in self.saved:
            r = self.saved[k]
            self.calls.append({"call": "analyse", "replayed": True, "round_trip_seconds": self.trips.get(k, r.get("container_seconds") or 0.0),
                               "container_seconds": r.get("container_seconds"), "glimmer_seconds": (r.get("glimmer") or {}).get("seconds"),
                               "sam_seconds": (r.get("sam") or {}).get("seconds")})
            return r
        live = self._live()
        n = len(live.calls)
        out = live.analyse(png)
        self.live_calls += 1
        self.calls += live.calls[n:]
        return out

    def glimmer_only(self, png: bytes) -> dict:
        live = self._live()
        n = len(live.calls)
        out = live.glimmer_only(png)
        self.calls += live.calls[n:]
        return out

    def glimmer_boxes(self, png: bytes, texts: list) -> dict:
        k = key_of(png) + ":" + hashlib.sha256(json.dumps(texts).encode()).hexdigest()[:16]
        if k in self.boxes:
            r = self.boxes[k]
            self.calls.append({"call": "glimmer_boxes", "replayed": True, "round_trip_seconds": r["round_trip_seconds"],
                               "container_seconds": r["answer"].get("container_seconds"), "glimmer_seconds": (r["answer"].get("glimmer") or {}).get("seconds"), "sam_seconds": None})
            return r["answer"]
        live = self._live()
        n = len(live.calls)
        out = live.glimmer_boxes(png, texts)
        self.live_calls += 1
        new = live.calls[n:]
        self.calls += new
        self.boxes[k] = {"key": k, "round_trip_seconds": new[-1]["round_trip_seconds"] if new else 0.0, "answer": out}
        self.boxes_path.parent.mkdir(parents=True, exist_ok=True)
        with self.boxes_path.open("a") as f:
            f.write(json.dumps(self.boxes[k]) + "\n")
        return out
