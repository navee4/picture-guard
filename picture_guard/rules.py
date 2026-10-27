"""Pattern rules with check digits (design step 2b). Pure text in, findings out; no model, no image.

Rules: UK sort code + account number, National Insurance number (format and allowed prefixes), payment card (Luhn),
IBAN (mod-97), email, UK phone, UK postcode, date of birth next to a label.

OCR swaps allowed, only inside a token that is mostly digits (at least one real digit, and digits plus swap
characters make up 60% or more of the token's letters and digits): O and o -> 0; I, l and | -> 1; S -> 5.
Spaces and dashes inside a value are ignored when the check digit is computed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from picture_guard.ocr import Word

SWAPS = {"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5"}
TYPES = ["card_number", "iban", "sort_code", "account_number", "ni_number", "email", "phone", "postcode", "dob"]


@dataclass
class Finding:
    type: str
    rule: str
    line: int  # index into the lines list given to find_values
    first: int  # word index range inside that line, inclusive
    last: int
    box: tuple  # union of the word boxes


@dataclass
class Line:
    words: list
    text: str
    view: str  # same length as text, OCR swaps applied inside digit-heavy tokens
    spans: list  # (start, end) of each word in text
    near: list = None  # every word of the same OCR pass, for labels that sit beside or above a value


def make_line(words: list[Word]) -> Line:
    text, spans, view = "", [], ""
    for w in words:
        if text:
            text += " "
            view += " "
        spans.append((len(text), len(text) + len(w.text)))
        text += w.text
        view += _digit_view(w.text)
    return Line(words, text, view, spans)


def _digit_view(tok: str) -> str:
    core = [c for c in tok if c.isalnum() or c in "|"]
    digits = sum(c.isdigit() for c in core)
    swaps = sum(c in SWAPS for c in core)
    if digits and core and (digits + swaps) / len(core) >= 0.6:
        return "".join(SWAPS.get(c, c) for c in tok)
    return tok


def luhn_ok(digits: str) -> bool:
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    tot = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            d -= 9 if d > 9 else 0
        tot += d
    return tot % 10 == 0


def iban_ok(s: str) -> bool:
    s = s.upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", s):
        return False
    rearranged = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


_NI_BAD_PREFIX = {"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"}


def ni_ok(prefix: str, suffix: str) -> bool:
    p = prefix.upper()
    return (len(p) == 2 and p[0] in "ABCEGHJKLMNOPRSTWXYZ" and p[1] in "ABCEGHJKLMNPRSTWXYZ"
            and p not in _NI_BAD_PREFIX and suffix.upper() in "ABCD")


def phone_ok(s: str) -> bool:
    s = re.sub(r"[ \-()]", "", s)
    return bool(re.fullmatch(r"(?:\+44|0044)0?[1-9]\d{8,9}|0[1-9]\d{8,9}", s))


_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
_DATE = [re.compile(p, re.I) for p in (
    rf"(?<!\d)\d{{1,2}}[ ./-]+(?:\d{{1,2}}|{_MONTH})[ ./,-]+(?:19|20)?\d{{2}}(?!\d)",
    rf"\b{_MONTH}\.?[ ]+\d{{1,2}}(?:st|nd|rd|th)?,?[ ]+(?:19|20)\d{{2}}(?!\d)")]
_DOB_LABEL = re.compile(r"d\.?\s?o\.?\s?b\b|birth|born", re.I)
_ACC_LABEL = re.compile(r"acc(?:ount|t)?\b|a/c", re.I)
_SORT_LABEL = re.compile(r"sort|s/c", re.I)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_POSTCODE = re.compile(r"(?<![A-Z0-9])[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}(?![A-Z0-9])")
_NI = re.compile(r"(?<![A-Z0-9])([A-Z]{2})\s?\d{2}\s?\d{2}\s?\d{2}\s?([A-D])(?![A-Z0-9])")
_SORT = re.compile(r"(?<!\d)\d{2}[-– ]\d{2}[-– ]\d{2}(?!\d)")
_ACC = re.compile(r"(?<!\d)\d{8}(?!\d)")


def _geo_context(line: Line, start: int) -> str:
    """Words that sit directly above (within 1.8 line heights, within 150 px sideways) or to the left on the same row (within
    500 px) of the word at `start`. Labels are often laid out that way, which a text line does not show."""
    if not line.near:
        return ""
    k = next((i for i, (a, b) in enumerate(line.spans) if a <= start < b or start < a), None)
    if k is None:
        return ""
    x0, y0, x1, y1 = line.words[k].box
    h = max(1, y1 - y0)
    above, left = [], []
    for w in line.near:
        a0, b0, a1, b1 = w.box
        if w.box == line.words[k].box:
            continue
        if b1 <= y0 + 0.3 * h and y0 - b1 <= 1.8 * h and a0 < x1 + 150 and a1 > x0 - 150:
            above.append(w)
        elif a1 <= x0 + 2 and x0 - a1 <= 500 and min(b1, y1) - max(b0, y0) >= 0.5 * h:
            left.append(w)
    above.sort(key=lambda w: (w.box[1], w.box[0]))
    left.sort(key=lambda w: w.box[0])
    return " ".join(w.text for w in above + left)


def _context(line: Line, prev: Line | None, start: int) -> str:
    before = line.text[max(0, start - 30):start]
    if line.near:  # positions are known: use what is really above or beside the value, not just the previous text line
        return _geo_context(line, start) + " " + before
    if not before.strip() and prev is not None:
        before = prev.text[-30:] + " " + before
    return before


def _tokens(line: Line):
    for m in re.finditer(r"\S+", line.view):
        yield m.start(), m.end()


def _free(claimed: list, a: int, b: int) -> bool:
    return all(b <= x or a >= y for x, y in claimed)


def _line_findings(line: Line, prev: Line | None) -> list[tuple]:
    """(type, rule, start, end) character spans in line.text. Rules run in an order that lets stronger checks claim digits first."""
    out: list[tuple] = []
    claimed: list = []

    def add(t, rule, a, b):
        if _free(claimed, a, b):
            out.append((t, rule, a, b))
            claimed.append((a, b))
            return True
        return False

    toks = list(_tokens(line))
    v = line.view
    # card: windows of up to 6 digit-only tokens, 13-19 digits, Luhn
    i = 0
    while i < len(toks):
        best = None
        for j in range(i, min(i + 6, len(toks))):
            seg = v[toks[i][0]:toks[j][1]]
            if not re.fullmatch(r"[0-9 -]+", seg):
                break
            if luhn_ok(re.sub(r"\D", "", seg)):
                best = j
        if best is not None and add("card_number", "luhn", toks[i][0], toks[best][1]):
            i = best + 1
        else:
            i += 1
    # iban: window of alphanumeric tokens starting with 2 letters + 2 digits, mod-97
    t = line.text
    for i, (a, b) in enumerate(toks):
        if not re.match(r"[A-Za-z]{2}\d{2}", t[a:b]):
            continue
        best = None
        acc = ""
        for j in range(i, min(i + 9, len(toks))):
            piece = t[toks[j][0]:toks[j][1]]
            if not piece.isalnum():
                break
            acc += piece
            if len(acc) > 34:
                break
            if iban_ok(acc):
                best = j
        if best is not None:
            add("iban", "mod97", a, toks[best][1])
    # sort code, then account number
    for m in _SORT.finditer(v):
        ctx = _context(line, prev, m.start())
        followed = re.match(r"\W{0,12}(?:acc\w*\W{0,6})?\d{8}(?!\d)", v[m.end():], re.I)
        if _SORT_LABEL.search(ctx[-20:]) or followed:
            add("sort_code", "sort_code_label_or_account_follows", m.start(), m.end())
    for m in _ACC.finditer(v):
        ctx = _context(line, prev, m.start())
        after_sort = any(ty == "sort_code" and 0 <= m.start() - e <= 14 for ty, _, _, e in out)
        if after_sort or _ACC_LABEL.search(ctx[-25:]):
            add("account_number", "account_label_or_after_sort_code", m.start(), m.end())
    # phone: windows of up to 4 tokens made of digits and ( ) + -
    i = 0
    while i < len(toks):
        best = None
        for j in range(i, min(i + 4, len(toks))):
            seg = v[toks[i][0]:toks[j][1]]
            if not re.fullmatch(r"[0-9 ()+-]+", seg):
                break
            if phone_ok(seg):
                best = j
        if best is not None and add("phone", "uk_number_shape", toks[i][0], toks[best][1]):
            i = best + 1
        else:
            i += 1
    # NI number: letters from the text, digits may use the OCR view
    for src in (t.upper(), v.upper()):
        for m in _NI.finditer(src):
            if ni_ok(m.group(1), m.group(2)):
                add("ni_number", "ni_prefix_and_suffix", m.start(), m.end())
    for m in _EMAIL.finditer(t):
        add("email", "email_shape", m.start(), m.end())
    # OCR often breaks an address into pieces ("jane. doe@example.org", "jane doe@mail test"): a token with an @ takes
    # the word before it (when that word is letters, possibly with a trailing dot) and a dot-less domain takes the next word.
    for i, (a, b) in enumerate(toks):
        tok = t[a:b]
        if "@" not in tok or any(a < ea and b > sa for _, _, sa, ea in out):
            continue
        lo, hi = a, b
        if i > 0 and re.fullmatch(r"[A-Za-z0-9._-]{2,}", t[toks[i - 1][0]:toks[i - 1][1]]):
            lo = toks[i - 1][0]
        if "." not in tok.split("@", 1)[-1] and i + 1 < len(toks) and re.fullmatch(r"[A-Za-z]{2,}", t[toks[i + 1][0]:toks[i + 1][1]]):
            hi = toks[i + 1][1]
        add("email", "at_sign_with_ocr_splits", lo, hi)
    for m in _POSTCODE.finditer(t.upper()):
        add("postcode", "uk_postcode_shape", m.start(), m.end())
    # date of birth: a date whose label (dob, date of birth, born) is within 30 characters before it
    for rx in _DATE:
        for m in rx.finditer(v):
            if _DOB_LABEL.search(_context(line, prev, m.start())):
                add("dob", "date_after_dob_label", m.start(), m.end())
    return out


def find_values(lines: list[list[Word]]) -> tuple[list[Finding], list[Line]]:
    made = [make_line(ws) for ws in lines]
    everything = [w for ws in lines for w in ws]
    for ln in made:
        ln.near = everything
    found: list[Finding] = []
    for li, line in enumerate(made):
        for ty, rule, a, b in _line_findings(line, made[li - 1] if li else None):
            idx = [k for k, (s, e) in enumerate(line.spans) if s < b and e > a]
            if not idx:
                continue
            bx = [line.words[k].box for k in idx]
            found.append(Finding(ty, rule, li, idx[0], idx[-1],
                                 (min(x[0] for x in bx), min(x[1] for x in bx), max(x[2] for x in bx), max(x[3] for x in bx))))
    return found, made


# ---- "can the rules judge this picture?" ---------------------------------------------------------------------------
# Names and addresses have no rule. A picture is only cleared when every word read is either inside a rule match,
# a number shape we can judge as harmless (amount, short number, numeric date), or an ordinary word from this closed list.
COMMON_WORDS = set("""
a an the and or but if of to in on at for from with by as is are was were be been am it its this that these those i you he she we
they me my your our their his her him them us not no yes ok okay hi hello hey thanks thank please can could will would do does did
have has had just now when what where who how why so up out about more all any some one two three new day days time today tomorrow
yesterday morning evening night see soon later again here there then than too very also still back get got let know think need want
good great fine sorry well going coming ready done sent received message messages read sent delivered typing online seen reply
date total amount balance account number sort code pay paid period payment gross net tax income pension basic overtime description
reference ref statement invoice page issue issued expiry expires valid type card bank name address postcode post phone mobile email
id dob birth born employee employer department payroll ni sincerely regards yours dear faithfully kind best monthly weekly annual year
month week due from hours rate deductions deduction earnings allowances student loan holiday bonus commission national insurance
synthetic test data fictional
""".split())
_AMOUNT = re.compile(r"[£$€]?\d[\d,]*(?:\.\d+)?%?")
_SHORTCODE = re.compile(r"\d{1,4}[A-Za-z]")  # a tax code such as 1060L
_NUMDATE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")


def unexplained_tokens(lines: list[Line], claimed: set) -> int:
    """How many tokens the rules cannot account for. `claimed` is {(line index, word index)} inside rule matches."""
    n = 0
    for li, line in enumerate(lines):
        for wi, w in enumerate(line.words):
            if (li, wi) in claimed:
                continue
            tok = w.text.strip(".,:;!?()\"'£$€%&*#-–—/·•|[]{}<>=+_~@")
            if not tok:
                continue
            if any(c.isdigit() for c in tok):
                digits = sum(c.isdigit() for c in tok)
                if (_AMOUNT.fullmatch(w.text.strip(".,:;")) and (digits <= 4 or "." in tok)) or _NUMDATE.fullmatch(tok) or _SHORTCODE.fullmatch(tok) or len(tok) <= 4:
                    continue
                n += 1
            elif len(tok) <= 1 or tok.lower() in COMMON_WORDS:
                continue
            else:
                n += 1
    return n
