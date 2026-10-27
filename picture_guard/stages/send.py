"""Send. Day-1 stub: no network call. It records what it would send (the safe copy only, never the original)."""
from pathlib import Path

from picture_guard import imaging
from picture_guard.types import OK, StageResult

NAME = "send"
DESTINATION = "Muse Spark through the Meta Model API (not called)"


def run(ctx) -> StageResult:
    answer = {"would_send": {"destination": DESTINATION, "file": ctx.out_path, "bytes": Path(ctx.out_path).stat().st_size,
                             "sha256": imaging.sha256_file(ctx.out_path), "is_original": False},
              "network_calls": 0}
    return StageResult(OK, answer, "recorded only; nothing was sent")
