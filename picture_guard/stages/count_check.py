"""Count faces a second way (Glimmer count against SAM masks). Day-1 stub: always not sure, so the whole picture is blacked out."""
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "count_check"


def run(ctx) -> StageResult:
    if ctx.ablation:
        return StageResult(OK, {"boxes": []}, "ABLATION: stub switched off; answers 'nothing found'")
    return StageResult(NOT_SURE, {}, "not built yet (day-1 stub)")
