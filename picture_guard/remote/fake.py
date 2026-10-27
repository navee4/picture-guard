"""A stand-in for the Modal session, for tests. Same answers as the real app, no network, no GPU."""
from __future__ import annotations

import time

from picture_guard.remote.client import RemoteError


class FakeGuard:
    def __init__(self, values=None, face_count=0, masks=None, glimmer_error=None, sam_error=None, raise_error=None, sleep=0.0,
                 junk=False, check_values=None, box_items=None, box_error=None):
        self.values, self.face_count, self.masks = values or [], face_count, masks or []
        self.glimmer_error, self.sam_error, self.raise_error, self.sleep, self.junk = glimmer_error, sam_error, raise_error, sleep, junk
        self.check_values = check_values or []
        self.box_items, self.box_error = box_items or [], box_error
        self.calls: list = []
        self.cold_start_seconds = 0.0

    def reset_calls(self):
        self.calls = []

    def _maybe_fail(self):
        if self.sleep:
            time.sleep(self.sleep)
        if self.raise_error:
            raise RemoteError(self.raise_error)

    def analyse(self, png: bytes):
        self._maybe_fail()
        self.calls.append({"call": "analyse", "round_trip_seconds": 0.01, "container_seconds": 0.01, "glimmer_seconds": 0.01, "sam_seconds": 0.01})
        if self.junk:
            return "yes"
        return {"glimmer": {"values": [dict(v) for v in self.values], "face_count": self.face_count, "error": self.glimmer_error, "seconds": 0.01},
                "sam": {"masks": [dict(m) for m in self.masks], "error": self.sam_error, "seconds": 0.01}, "container_seconds": 0.01, "peak_mib": 0}

    def glimmer_only(self, png: bytes):
        self._maybe_fail()
        self.calls.append({"call": "glimmer_only", "round_trip_seconds": 0.01, "container_seconds": 0.01, "glimmer_seconds": 0.01, "sam_seconds": None})
        return {"glimmer": {"values": [dict(v) for v in self.check_values], "face_count": 0, "error": None, "seconds": 0.01}, "sam": None, "container_seconds": 0.01}

    def glimmer_boxes(self, png: bytes, texts: list):
        self._maybe_fail()
        self.calls.append({"call": "glimmer_boxes", "round_trip_seconds": 0.01, "container_seconds": 0.01, "glimmer_seconds": 0.01, "sam_seconds": None})
        return {"glimmer": {"items": [dict(i) for i in self.box_items], "error": self.box_error, "seconds": 0.01}, "container_seconds": 0.01}
