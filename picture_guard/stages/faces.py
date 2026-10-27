"""Locate faces (SAM 3.1, prompt face; mask outer rectangle grown by 15%). Day-1 stub: always not sure, so the whole picture is blacked out."""
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "faces"


def run(ctx) -> StageResult:
    if ctx.ablation:
        return StageResult(OK, {"boxes": []}, "ABLATION: stub switched off; answers 'nothing found'")
    return StageResult(NOT_SURE, {}, "not built yet (day-1 stub)")
