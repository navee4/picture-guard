"""Count faces a second way (design step 3c): Glimmer's face count against SAM's masks. If Glimmer counts MORE faces than SAM
found, a face was missed or only partly covered: not sure (fail-safe rule 5). A Glimmer count that is missing is not sure too."""
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "count_check"


def run(ctx) -> StageResult:
    if ctx.ablation:
        return StageResult(OK, {"boxes": []}, "ABLATION: no model called; answers 'nothing found'")
    resp = ctx.data.get("remote") or {}
    fc = (resp.get("glimmer") or {}).get("face_count")
    sam_n = ctx.data.get("sam_masks")
    if not isinstance(fc, int) or isinstance(fc, bool) or sam_n is None:
        return StageResult(NOT_SURE, {"failsafe_rule": 3}, "Glimmer gave no face count")
    answer = {"glimmer_faces": fc, "sam_faces": sam_n}
    if fc > sam_n:
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 5}, f"Glimmer counts {fc} faces, SAM found {sam_n} (fail-safe rule 5)")
    return StageResult(OK, answer, f"Glimmer counts {fc}, SAM found {sam_n}")
