"""Decide what is private (design steps 2 and 2b): pattern rules with check digits PLUS what Muse Glimmer lists, merged.

Glimmer runs on Modal (together with SAM, in one call) and is asked for the private values and a face count. Every value it
lists must be located on Tesseract's word boxes; a value that cannot be located is "not sure" (fail-safe rule 1) and the
picture goes black. A Glimmer error, time-out or answer that cannot be parsed is "not sure" too (rule 3).

The day-2 word list (rules.COMMON_WORDS) is no longer the gate. It is still computed, and its count is reported as
`unexplained_tokens`, only to measure how often it would have refused the picture.

In ablation mode (measurement only) no model is called and the day-2 behaviour applies.
"""
import math

from picture_guard import fallback, match, ocr, rules
from picture_guard.remote.client import RemoteError
from picture_guard.types import OK, NOT_SURE, StageResult

NAME = "decide"


def _overlap_small(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    sa, sb = (a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])
    return ix / max(1, min(sa, sb))


def _rule_findings(ctx):
    findings, unexplained = [], 0
    for label, words in ctx.data["words"].items():
        found, lines = rules.find_values(ocr.group_lines(words))
        claimed = {(f.line, k) for f in found for k in range(f.first, f.last + 1)}
        unexplained += rules.unexplained_tokens(lines, claimed)
        for f in found:
            if not any(_overlap_small(f.box, g["box"]) > 0.5 and g["type"] == f.type for g in findings):
                findings.append({"type": f.type, "rule": f.rule, "box": list(f.box), "pass": label, "text": f.text})
    return findings, unexplained


def run(ctx) -> StageResult:
    findings, unexplained = _rule_findings(ctx)
    by_type: dict = {}
    answer = {"values_found_by_type": by_type, "unexplained_tokens": unexplained, "word_list_would_refuse": unexplained > 0}
    if ctx.ablation:
        ctx.data["findings"] = findings
        for f in findings:
            by_type[f["type"]] = by_type.get(f["type"], 0) + 1
        answer["ablation_suppressed_not_sure"] = True
        return StageResult(OK, answer, f"ABLATION: rules only, no model; word list would {'refuse' if unexplained else 'accept'} this picture")
    if ctx.guard is None:
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 3}, "no models available (no Modal session): cannot judge names and addresses")
    import io
    buf = io.BytesIO()
    ctx.loaded.image.save(buf, format="PNG")
    try:
        resp = ctx.guard.analyse(buf.getvalue())
    except RemoteError as ex:
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 3}, f"the Modal call failed: {str(ex)[:160]}")
    g = resp.get("glimmer") if isinstance(resp, dict) else None
    if not isinstance(g, dict) or g.get("error") or not isinstance(g.get("values"), list):
        err = (g or {}).get("error") if isinstance(g, dict) else "no glimmer answer"
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 3}, f"Glimmer gave no usable answer: {str(err)[:160]}")
    ctx.data["remote"] = resp
    unlocated = 0
    unlocated_types: list = []
    n_glimmer = 0
    located: dict = {}  # index of a Glimmer value -> its boxes on Tesseract words
    pending: list = []  # (index, text, type) of values Tesseract cannot find
    for i, v in enumerate(g["values"]):
        text = v.get("text", "") if isinstance(v, dict) else ""
        if not isinstance(text, str) or not match.norm(text):
            return StageResult(NOT_SURE, {**answer, "failsafe_rule": 3}, "Glimmer listed a value with no text")
        n_glimmer += 1
        boxes = match.locate(text, ctx.data["words"])
        if boxes is None:
            pending.append((i, text, str(v.get("type", "other"))))
            continue
        located[i] = boxes
        for b in boxes:
            findings.append({"type": str(v.get("type", "other")), "rule": "glimmer", "box": list(b), "pass": "glimmer", "text": text})
    mode = ctx.options.get("fallback", "zoom")
    fb = {"mode": mode, "tried": 0, "by_zoom": 0, "by_line": 0, "frame": None, "frame_hits": None}
    if pending and mode != "none" and ctx.guard is not None and hasattr(ctx.guard, "glimmer_boxes"):
        pending = _fallback(ctx, g["values"], located, pending, mode, findings, fb)
    for _, text, typ in pending:
        unlocated += 1
        unlocated_types.append(typ)
    ctx.data["findings"] = findings
    for f in findings:
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
    answer.update(glimmer_values=n_glimmer, glimmer_values_unlocated=unlocated, glimmer_unlocated_types=unlocated_types, glimmer_seconds=g.get("seconds"), fallback=fb)
    if unlocated:
        return StageResult(NOT_SURE, {**answer, "failsafe_rule": 1}, f"{unlocated} of {n_glimmer} values Glimmer listed have no matching word boxes (fail-safe rule 1)")
    return StageResult(OK, answer, f"{len(findings)} rectangles from {n_glimmer} Glimmer values and the rules")


def _fallback(ctx, values, located, pending, mode, findings, fb) -> list:
    """Try to place the values Tesseract cannot find. Returns the ones still unplaced (they keep rule 1 alive)."""
    import io
    w, h = ctx.loaded.width, ctx.loaded.height
    buf = io.BytesIO()
    ctx.loaded.image.save(buf, format="PNG")
    texts = [v["text"] for v in values]
    try:
        resp = ctx.guard.glimmer_boxes(buf.getvalue(), texts)
    except RemoteError:
        return pending  # no boxes: rule 1 stands
    gb = resp.get("glimmer") if isinstance(resp, dict) else None
    if not isinstance(gb, dict) or gb.get("error") or not isinstance(gb.get("items"), list):
        return pending
    fb["tried"] = len(pending)
    by_text: dict = {}
    for it in gb["items"]:
        if isinstance(it, dict) and isinstance(it.get("text"), str) and isinstance(it.get("boxes"), list):
            by_text.setdefault(match.norm(it["text"]), []).extend(it["boxes"])
    anchors = [(by_text.get(match.norm(values[i]["text"]), []), bxs) for i, bxs in located.items()]
    frame, hits = fallback.calibrate([a for a in anchors if a[0]], w, h)
    fb["frame"], fb["frame_hits"] = frame, hits
    zoom_ok = mode in ("zoom", "zoom+line")
    if frame is None and not zoom_ok:
        return pending
    still = []
    regions = ctx.data.setdefault("fallback_regions", [])
    for i, text, typ in pending:
        placed, how = None, None
        if zoom_ok:  # a zoom read checks the value's own words inside the crop, so with no calibrated frame every frame may be tried
            for fr in ([frame] if frame else list(fallback.FRAMES)):
                rough = fallback.usable_boxes(by_text.get(match.norm(text), []), fr, w, h)
                if not rough:
                    continue
                exact, region = fallback.zoom_locate(ctx.loaded.image, text, rough)
                if exact:
                    placed, how = exact, "fallback-zoom"
                    regions.append({"box": region, "text": text})
                    break
        if placed is None and frame is not None and mode in ("line", "zoom+line"):
            rough = fallback.usable_boxes(by_text.get(match.norm(text), []), frame, w, h)
            if rough:
                placed, region = fallback.line_cover(ctx.data["words"], rough, w, h)
                how = "fallback-line"
                regions.append({"box": region, "text": text})
        if placed is None:
            still.append((i, text, typ))
            continue
        fb["by_zoom" if how == "fallback-zoom" else "by_line"] += 1
        for b in placed:
            findings.append({"type": typ, "rule": how, "box": [int(b[0]), int(b[1]), int(math.ceil(b[2])), int(math.ceil(b[3]))], "pass": how, "text": text})
    return still
