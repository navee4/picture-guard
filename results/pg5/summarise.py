"""Extra tables for the PG-5 results file, from results/pg5/eval-testset-dev-ablation.json. Run: .venv/bin/python results/pg5/summarise.py"""
import collections
import json
from pathlib import Path

d = json.loads((Path(__file__).parent / "eval-testset-dev-ablation.json").read_text())
RULE_TYPES = ["account_number", "card_number", "dob", "email", "iban", "ni_number", "phone", "postcode", "sort_code"]
NO_RULE = ["address", "id_number", "name"]
t = collections.defaultdict(lambda: collections.Counter())
leak = collections.defaultdict(collections.Counter)
for r in d["pictures"]:
    for v in r["values"]:
        c = t[v["type"]]
        c["n"] += 1
        covered = (v["black_share"] or 0) >= 0.9
        read = bool(v["read_on_original"])
        c["covered"] += covered
        c["read"] += read
        c["read_and_covered"] += read and covered
        c["read_not_covered"] += read and not covered
        c["unread_covered"] += (not read) and covered
        c["unread"] += not read
        if not read:
            leak[v["type"]][r["type"]] += 1
print("| Value type | Planted | Tesseract read it (original) | Rules covered it (box 90%+ black) | Covered, of those read | Read but NOT covered | Never read by Tesseract | Never read and not covered |")
print("|---|---|---|---|---|---|---|---|")
for k in RULE_TYPES + NO_RULE:
    c = t[k]
    print(f"| {k}{' (no rule)' if k in NO_RULE else ''} | {c['n']} | {c['read']} | {c['covered']} | "
          f"{c['read_and_covered']} of {c['read']} ({100 * c['read_and_covered'] / max(1, c['read']):.0f}%) | {c['read_not_covered']} | {c['unread']} | {c['unread'] - c['unread_covered']} |")
tot = {k: sum(t[x][k] for x in RULE_TYPES) for k in ("n", "read", "covered", "read_and_covered", "read_not_covered", "unread")}
print(f"| **all 9 rule types** | {tot['n']} | {tot['read']} | {tot['covered']} | {tot['read_and_covered']} of {tot['read']} ({100 * tot['read_and_covered'] / tot['read']:.0f}%) | {tot['read_not_covered']} | {tot['unread']} | |")
print("\nLeak list by value type and picture type (planted values Tesseract never read on the original):")
for k in RULE_TYPES + NO_RULE:
    print(f"- {k}: {dict(leak[k])}")
print("\nTotals: values planted", sum(t[k]['n'] for k in t), "| never read", sum(t[k]['unread'] for k in t))
# readable share of ordinary text
tp = sum(r["n_plain_spans"] for r in d["pictures"])
print("ordinary spans", tp, "readable on original", sum(r["readback_original"]["plain_readable"] for r in d["pictures"]), "readable on safe copy (ablation)", sum(r["readback"]["plain_readable"] for r in d["pictures"]))
# the rule-covered-but-the-wrong-thing check: black share of plain text boxes
ps = [x for r in d["pictures"] for x in r["plain_box_nonblack_share"] if x is not None]
print("plain-text box pixels still visible (mean):", round(100 * sum(ps) / len(ps), 1), "%")
# by picture type: values read-and-covered
by = collections.defaultdict(collections.Counter)
for r in d["pictures"]:
    for v in r["values"]:
        if v["type"] in RULE_TYPES:
            b = by[r["type"]]; b["n"] += 1; b["covered"] += (v["black_share"] or 0) >= 0.9; b["left"] += bool(v["left_readable"])
print("\nBy picture type, values of the 9 rule types:", {k: f"{v['covered']} of {v['n']} covered, {v['left']} left readable" for k, v in by.items()})
