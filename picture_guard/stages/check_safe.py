"""Check the safe copy (design step 5): read it again with Tesseract (plain and 2x) and look for private values.
Not sure (so the whole picture goes black, fail-safe rule 2) if (a) any pattern rule finds a value, or (b) any value `decide`
found (a rule match or a value Glimmer listed) can still be read on the safe copy.

Optional, off by default: `options["check_glimmer"]` asks Glimmer for private values on the safe copy too; any value it lists
means not sure. It costs a second Glimmer call per picture; it is measured separately before anyone makes it the default."""
import io

from picture_guard import match, ocr, rules
from picture_guard.remote.client import RemoteError
from picture_guard.types import NOT_SURE, OK, StageResult

NAME = "check_safe"


def run(ctx) -> StageResult:
    if ctx.ablation:
        return StageResult(OK, {"boxes": []}, "ABLATION: no check run; answers 'nothing found'")
    safe = ctx.safe_image
    passes = ocr.read_passes(safe)
    for label, words in passes.items():
        found, _ = rules.find_values(ocr.group_lines(words))
        if found:
            return StageResult(NOT_SURE, {"failsafe_rule": 2, "still_found_by_rules": len(found)}, f"{len(found)} pattern-rule values are still readable on the safe copy (fail-safe rule 2)")
    left = 0
    for f in ctx.data.get("findings", []):
        if f.get("text") and match.locate(f["text"], passes) is not None:
            left += 1
    if left:
        return StageResult(NOT_SURE, {"failsafe_rule": 2, "still_readable": left}, f"{left} values found by decide can still be read on the safe copy (fail-safe rule 2)")
    answer = {"still_found_by_rules": 0, "still_readable": 0}
    if ctx.options.get("check_glimmer") and ctx.guard is not None:
        buf = io.BytesIO()
        safe.save(buf, format="PNG")
        try:
            g = ctx.guard.glimmer_only(buf.getvalue()).get("glimmer") or {}
        except RemoteError as ex:
            return StageResult(NOT_SURE, {"failsafe_rule": 3}, f"the second Glimmer call failed: {str(ex)[:120]}")
        if g.get("error") or not isinstance(g.get("values"), list):
            return StageResult(NOT_SURE, {"failsafe_rule": 3}, f"the second Glimmer call gave no usable answer: {str(g.get('error'))[:120]}")
        answer.update(glimmer_check_values=len(g["values"]), glimmer_check_seconds=g.get("seconds"))
        if g["values"]:
            return StageResult(NOT_SURE, {**answer, "failsafe_rule": 2}, f"Glimmer still lists {len(g['values'])} private values on the safe copy (fail-safe rule 2)")
    return StageResult(OK, answer, "nothing private could be read on the safe copy")
