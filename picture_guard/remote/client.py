"""Mac side of the Modal app. A session starts the ephemeral app, waits until both models are loaded (the cold start),
sends pictures one at a time and stops the app on exit. Spend is logged to a ledger and checked against a cap."""
from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER = ROOT / "results" / "pg6" / "spend.jsonl"
SPEND_CAP_USD = 15.0
# Modal list prices used in earlier runs (USD per second): L40S GPU, per CPU core, per GiB of memory. This container: 4 cores, 32 GiB.
RATE_PER_SECOND = 0.000542 + 4 * 0.00003942 + 32 * 0.00000222


class RemoteError(Exception):
    """A call to the Modal app failed. The pipeline turns this into the whole black picture."""


def spent_total(ledger: Path = LEDGER) -> float:
    if not ledger.exists():
        return 0.0
    return sum(json.loads(x)["usd"] for x in ledger.read_text().splitlines() if x.strip())


def log_spend(run: str, seconds: float, note: str = "", ledger: Path = LEDGER) -> float:
    usd = round(seconds * RATE_PER_SECOND, 4)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps({"run": run, "seconds": round(seconds, 1), "usd": usd, "note": note}) + "\n")
    print(f"[spend] {run}: {seconds:.0f} s = ${usd:.2f}; running total ${spent_total(ledger):.2f} of ${SPEND_CAP_USD:.0f}")
    return usd


class ModalGuard:
    """with ModalGuard(run_name) as guard: guard.analyse(png_bytes) -> dict"""

    def __init__(self, run_name: str = "session", reserve_usd: float = 1.0, ledger: Path = LEDGER, cap_usd: float = SPEND_CAP_USD):
        self.run_name, self.reserve, self.ledger, self.cap = run_name, reserve_usd, ledger, cap_usd
        self.calls: list[dict] = []  # timings of the calls since the last reset: no picture text
        self.cold_start_seconds = None
        self.info = None

    def _check_cap(self):
        used = spent_total(self.ledger) + (time.time() - self._t_session) * RATE_PER_SECOND
        if used + 0.2 > self.cap:
            raise RemoteError(f"spend cap: ${used:.2f} used of ${self.cap:.0f}; stopping")

    def __enter__(self):
        if spent_total(self.ledger) + self.reserve > self.cap:
            raise RemoteError(f"spend cap: ${spent_total(self.ledger):.2f} spent, session reserve ${self.reserve:.2f}, cap ${self.cap:.0f}")
        import modal
        from picture_guard.remote.service import Guard, app
        self._stack = contextlib.ExitStack()
        self._t_session = time.time()
        try:
            self._stack.enter_context(modal.enable_output())
            self._stack.enter_context(app.run())
            self._cls = Guard()
            t0 = time.perf_counter()
            self.info = self._cls.ping.remote()  # returns when the container has both models loaded
            self.cold_start_seconds = round(time.perf_counter() - t0, 1)
        except BaseException as ex:
            self._finish(f"FAILED {type(ex).__name__}")
            raise RemoteError(f"could not start the Modal app: {type(ex).__name__}: {str(ex)[:200]}") from ex
        return self

    def _finish(self, note=""):
        try:
            self._stack.close()
        finally:
            log_spend(self.run_name, time.time() - self._t_session, note or "session wall time (upper bound: includes image build and cold start)", self.ledger)

    def __exit__(self, *exc):
        self._finish()

    def reset_calls(self):
        self.calls = []

    def _call(self, name: str, png: bytes) -> dict:
        self._check_cap()
        t0 = time.perf_counter()
        try:
            out = getattr(self._cls, name).remote(png)
        except BaseException as ex:  # noqa: BLE001
            raise RemoteError(f"{name} failed: {type(ex).__name__}: {str(ex)[:200]}") from ex
        self.last = out  # kept in memory for debugging runs on made-up pictures only
        self.calls.append({"call": name, "round_trip_seconds": round(time.perf_counter() - t0, 2), "container_seconds": out.get("container_seconds"),
                           "glimmer_seconds": (out.get("glimmer") or {}).get("seconds"), "sam_seconds": (out.get("sam") or {}).get("seconds")})
        return out

    def analyse(self, png: bytes) -> dict:
        return self._call("analyse", png)

    def glimmer_only(self, png: bytes) -> dict:
        return self._call("glimmer_only", png)
