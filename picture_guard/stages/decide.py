"""Decide what is private by pattern rules with check digits (design step 2b). No AI model yet (Glimmer comes on day 3).

Product rule for "not sure": the rules have no way to judge names, addresses or any value type they do not know.
So the stage is sure only when every token Tesseract read is accounted for: inside a rule match, a harmless number
shape, or an ordinary word from a closed list (rules.COMMON_WORDS). Any other word or long id-like token means the
picture may hold a value the rules cannot judge, and the answer is "not sure".
"""
from picture_guard import ocr, rules
from picture_guard.types import OK, NOT_SURE, StageResult

NAME = "decide"


def _overlap_small(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    sa, sb = (a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])
    return ix / max(1, min(sa, sb))


def run(ctx) -> StageResult:
    findings, unexplained = [], 0
    for psm, words in ctx.data["words"].items():
        found, lines = rules.find_values(ocr.group_lines(words))
        claimed = {(f.line, k) for f in found for k in range(f.first, f.last + 1)}
        unexplained += rules.unexplained_tokens(lines, claimed)
        for f in found:
            if not any(_overlap_small(f.box, g["box"]) > 0.5 and g["type"] == f.type for g in findings):
                findings.append({"type": f.type, "rule": f.rule, "box": list(f.box), "psm": psm})
    ctx.data["findings"] = findings
    by_type: dict = {}
    for f in findings:
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
    answer = {"values_found_by_type": by_type, "unexplained_tokens": unexplained}
    if unexplained and not ctx.ablation:
        return StageResult(NOT_SURE, answer, f"{unexplained} tokens the rules cannot judge (possible names, addresses or other values)")
    if unexplained:
        answer["ablation_suppressed_not_sure"] = True
        return StageResult(OK, answer, f"ABLATION: {unexplained} tokens the rules cannot judge; would be not sure")
    return StageResult(OK, answer, f"{len(findings)} values found; every token read is accounted for")
