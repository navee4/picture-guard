"""Read the words and their exact spots with Tesseract (design step 1). Six passes: a plain read, a 2x enlarged read and a 2x contrast-stretched sharpened read,
each as block text (psm 6) and sparse text (psm 11). The enlarged read catches small or faint text the plain read misses.

Not sure when Tesseract reads almost nothing (fewer than MIN_WORDS words at confidence 30 or more): then it cannot
tell a blank picture from a picture it cannot read (fail-safe rule 3). A missing or crashing Tesseract is an error.
"""
from picture_guard import ocr
from picture_guard.types import OK, NOT_SURE, StageResult

NAME = "read"
MIN_WORDS = 5


def run(ctx) -> StageResult:
    passes = ocr.read_passes(ctx.loaded.image)
    ctx.data["words"] = passes
    sure_words = max(sum(w.conf >= 30 for w in ws) for ws in passes.values())
    answer = {"words_by_pass": {p: len(ws) for p, ws in passes.items()}, "words_conf30_best_pass": sure_words}
    if sure_words < MIN_WORDS:
        if ctx.ablation:
            return StageResult(OK, {**answer, "ablation_suppressed_not_sure": True}, f"ABLATION: read {sure_words} confident words, below {MIN_WORDS}; would be not sure")
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 3}, f"read only {sure_words} confident words (need {MIN_WORDS}): cannot tell blank from unreadable")
    return StageResult(OK, answer, f"read {sure_words} confident words")
