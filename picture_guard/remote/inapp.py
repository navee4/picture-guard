"""The guard used by the deployed demo: the same calls as `ModalGuard`, made from inside the Modal app (no new app session)."""
from __future__ import annotations

import time

from picture_guard.remote.client import RemoteError


class InAppGuard:
    def __init__(self, guard_cls):
        self._cls = guard_cls
        self.calls: list = []

    def reset_calls(self):
        self.calls = []

    def _call(self, name: str, *args) -> dict:
        t0 = time.perf_counter()
        try:
            out = getattr(self._cls, name).remote(*args)
        except BaseException as ex:  # noqa: BLE001
            raise RemoteError(f"{name} failed: {type(ex).__name__}: {str(ex)[:200]}") from ex
        self.calls.append({"call": name, "round_trip_seconds": round(time.perf_counter() - t0, 2), "container_seconds": out.get("container_seconds"),
                           "glimmer_seconds": (out.get("glimmer") or {}).get("seconds"), "sam_seconds": (out.get("sam") or {}).get("seconds")})
        return out

    def analyse(self, png: bytes) -> dict:
        return self._call("analyse", png)

    def glimmer_only(self, png: bytes) -> dict:
        return self._call("glimmer_only", png)

    def glimmer_boxes(self, png: bytes, texts: list) -> dict:
        return self._call("glimmer_boxes", png, list(texts))
