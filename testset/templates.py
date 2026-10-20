"""The four picture types. Each returns a Canvas filled with made-up content."""
import datetime

from draw import Canvas
from values import (BANKS, CHAT_APPS, EMPLOYERS, ID_ISSUERS, NATIONALITIES)

INK = (25, 25, 30)
GREY = (90, 90, 100)
RED = (190, 30, 30)
LOREM = ["we are writing to confirm the changes made to your account this month",
         "please check the details shown below and tell us if anything looks wrong",
         "no action is needed unless you want to change your preferences",
         "our offices are closed on bank holidays and replies may take a little longer",
         "thank you for being a customer and for your patience while we update our systems",
         "you can find more information on our website or by visiting any branch",
         "this notice replaces any earlier notice we sent about the same matter",
         "keep this letter in a safe place as you may need it for your records"]


def banner(c, y=None):
    y = c.h - c.line_h(15) - 12 if y is None else y
    c.text((c.w // 2 - c.width("SYNTHETIC TEST DATA", 15, True) / 2, y), "SYNTHETIC TEST DATA", 15, RED, bold=True)


def money(rng, lo, hi):
    return f"£{rng.randint(lo * 100, hi * 100) / 100:,.2f}"


def date_str(rng, y0=2026, fmt="%d %b %Y"):
    d = datetime.date(y0, 1, 1) + datetime.timedelta(days=rng.randint(0, 270))
    return d.strftime(fmt)


def wrap(c, text, size, max_w, bold=False):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if c.width(trial, size, bold) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def payslip(rng, p, family, scale):
    c = Canvas(900, 1200, (250, 250, 246), family, scale)
    emp = rng.choice(EMPLOYERS)
    c.rect((30, 30, 870, 1170), None, outline=(170, 170, 175), width=2)
    c.text((60, 55), emp, 32, INK, bold=True)
    c.text((60, 55 + c.line_h(32)), "Payroll Department  ·  Fictional Employer", 14, GREY)
    c.text((c.w - 60 - c.width("PAYSLIP", 30, True), 58), "PAYSLIP", 30, INK, bold=True)
    c.rect((60, 150, 840, 153), (60, 60, 70))
    y, lh = 185, c.line_h(18)
    rows = [("Employee name", p.name, "name"), ("Address", p.street, "address"), ("", p.city, "address"),
            ("Postcode", p.postcode, "postcode"), ("NI number", p.ni, "ni_number"),
            ("Date of birth", p.dob, "dob"), ("Sort code", p.sort_code, "sort_code"),
            ("Account number", p.account, "account_number")]
    for label, val, pii in rows:
        if label:
            c.text((60, y), label, 18, GREY)
        c.text((330, y), val, 18, INK, bold=rng.random() < 0.3, kind="personal", pii=pii)
        y += lh
    y += 15
    c.text((60, y), "Pay period", 18, GREY)
    c.text((330, y), f"{date_str(rng, fmt='%d %b %Y')} to {date_str(rng, fmt='%d %b %Y')}", 18, INK)
    y += lh
    c.text((60, y), "Date of pay", 18, GREY)
    c.text((330, y), date_str(rng, fmt="%d/%m/%Y"), 18, INK)
    y += lh
    c.text((60, y), "Tax code", 18, GREY)
    c.text((330, y), rng.choice(["1257L", "1100L", "BR", "1060L"]), 18, INK)
    y += lh + 20
    c.rect((60, y, 840, y + c.line_h(18) + 8), (225, 228, 235))
    c.text((70, y + 4), "Description", 18, INK, bold=True)
    c.text((640, y + 4), "Amount", 18, INK, bold=True)
    y += c.line_h(18) + 18
    for desc in ["Basic pay", "Overtime", "Income tax", "Employee NI", "Pension", "Net pay"]:
        c.text((70, y), desc, 18, INK, bold=(desc == "Net pay"))
        c.text((640, y), money(rng, 40 if desc != "Net pay" else 900, 400 if desc != "Net pay" else 3200),
               18, INK, bold=(desc == "Net pay"))
        y += lh
    banner(c)
    return c, "payslip"


def letter(rng, p, family, scale):
    c = Canvas(900, 1200, (255, 255, 252), family, scale)
    bank = rng.choice(BANKS)
    c.text((60, 55), bank, 30, (30, 60, 110), bold=True)
    c.text((60, 55 + c.line_h(30)), "1 Fictional Row, Nowhere  ·  fictional sender", 13, GREY)
    y = 170
    lh = c.line_h(17)
    for text, pii in [(p.name, "name"), (p.street, "address"), (p.city, "address"), (p.postcode, "postcode")]:
        c.text((60, y), text, 17, INK, kind="personal", pii=pii)
        y += lh
    ref = f"Our ref: {rng.randint(100000, 999999)}"
    c.text((c.w - 60 - c.width(date_str(rng), 17), 170), date_str(rng), 17, INK)
    c.text((c.w - 60 - c.width(ref, 17), 170 + lh), ref, 17, GREY)
    y += 25
    x = c.text((60, y), "Dear ", 17, INK)
    x = c.text((x, y), p.name, 17, INK, kind="personal", pii="name")
    c.text((x, y), ",", 17, INK)
    y += lh + 10
    c.text((60, y), "Notice about your account", 20, INK, bold=True)
    y += lh + 10
    for para in rng.sample(LOREM, 3):
        for ln in wrap(c, para.capitalize() + ".", 17, 780):
            c.text((60, y), ln, 17, INK)
            y += lh
        y += 8
    y += 10
    rows = [("Account number", p.account, "account_number"), ("Sort code", p.sort_code, "sort_code"),
            ("IBAN", p.iban, "iban"), ("Card number", p.card_spaced, "card_number"),
            ("Email on file", p.email, "email"), ("Phone on file", p.phone, "phone")]
    for label, val, pii in rng.sample(rows, 4):
        c.text((80, y), label + ":", 17, GREY)
        c.text((300, y), val, 17, INK, kind="personal", pii=pii)
        y += lh
    y += 25
    c.text((60, y), "Yours sincerely,", 17, INK)
    y += lh * 2
    staff = f"{rng.choice(['Priya', 'Tomasz', 'Ellen', 'Gareth', 'Ngozi'])} {rng.choice(['Marsh', 'Okafor', 'Lindqvist', 'Hale'])}"
    c.text((60, y), staff, 17, INK, kind="personal", pii="name")
    y += lh
    c.text((60, y), "Customer Services Team", 17, GREY)
    banner(c)
    return c, "letter"


def id_card(rng, p, family, scale):
    c = Canvas(1000, 640, (176, 160, 138), family, scale)  # table-top colour
    issuer = rng.choice(ID_ISSUERS)
    tint = rng.choice([(214, 232, 240), (232, 240, 214), (240, 226, 214), (226, 214, 240)])
    c.rect((40, 40, 960, 560), tint, outline=(80, 80, 90), radius=26, width=3)
    c.rect((40, 40, 960, 110), (60, 80, 120), radius=26)
    c.rect((40, 80, 960, 110), (60, 80, 120))
    c.text((70, 52), issuer, 28, (255, 255, 255), bold=True)
    c.text((c.w - 70 - c.width("IDENTITY CARD", 22, True), 58), "IDENTITY CARD", 22, (255, 255, 255), bold=True)
    skin = rng.choice([(240, 200, 170), (210, 160, 120), (150, 100, 70), (95, 62, 45)])
    hair = rng.choice([(40, 30, 25), (110, 70, 40), (200, 170, 90), (150, 150, 150)])
    c.rect((70, 140, 310, 420), (205, 215, 225), outline=(90, 90, 100), width=2)
    c.face((115, 175, 265, 385), skin, hair, (30, 30, 40))
    sx, y, lh = 350, 135, c.line_h(18)
    surname, given = p.last.upper(), p.first
    rows = [("Surname", surname, "name"), ("Given names", given, "name"), ("Date of birth", p.dob, "dob"),
            ("ID number", p.id_number, "id_number"), ("Address", p.street, "address"),
            ("", f"{p.city}, {p.postcode}", None)]
    for label, val, pii in rows:
        c.text((sx, y), label, 13, GREY)
        y += c.line_h(13) - 2
        if pii:
            c.text((sx, y), val, 20, INK, bold=True, kind="personal", pii=pii)
        else:
            # "City, POSTCODE" is two values on one line
            city, pc = val.rsplit(", ", 1)
            x = c.text((sx, y), city, 20, INK, bold=True, kind="personal", pii="address")
            x = c.text((x, y), ", ", 20, INK, bold=True, track=False)
            c.text((x, y), pc, 20, INK, bold=True, kind="personal", pii="postcode")
        y += lh + 6
    exp = (p.dob_dt.replace(day=min(p.dob_dt.day, 28), year=2030 + rng.randint(0, 4))).strftime("%d/%m/%Y")
    c.text((70, 450), "Expires", 13, GREY)
    c.text((70, 450 + c.line_h(13) - 2), exp, 20, INK, bold=True)
    c.text((220, 450), "Nationality", 13, GREY)
    c.text((220, 450 + c.line_h(13) - 2), NATIONALITIES[issuer], 20, INK, bold=True)
    banner(c, y=585)
    return c, "id_card"


CHAT_PLAIN = ["Running a bit late, see you at the cafe at six", "Did you get the tickets for Saturday?",
              "Haha that was brilliant", "Can you bring the blue folder tomorrow?", "Thanks so much, speak soon",
              "Just leaving work now", "What time does the film start?", "Sounds good to me"]


def chat(rng, p, family, scale):
    dark = rng.random() < 0.4
    bg = (18, 20, 28) if dark else (240, 242, 247)
    c = Canvas(600, 1000, bg, family, scale)
    app = rng.choice(CHAT_APPS)
    bar = (32, 36, 52) if dark else (255, 255, 255)
    fg = (235, 235, 240) if dark else (25, 25, 30)
    sub = (150, 155, 170) if dark else (110, 110, 120)
    mine = (46, 110, 220) if dark else (60, 130, 240)
    theirs = (48, 52, 70) if dark else (255, 255, 255)
    c.rect((0, 0, 600, 90), bar)
    c.text((20, 12), app, 15, sub)
    c.text((20, 12 + c.line_h(15)), p.name, 20, fg, bold=True, kind="personal", pii="name")
    pii_msgs = [
        [("my number is ", None), (p.phone, "phone")], [("email me at ", None), (p.email, "email")],
        [("sort code ", None), (p.sort_code, "sort_code"), (" account ", None), (p.account, "account_number")],
        [("the iban is ", None), (p.iban, "iban")], [("card is ", None), (p.card_spaced, "card_number")],
        [("I live at ", None), (f"{p.street}, {p.postcode}", "address")],
        [("my NI number is ", None), (p.ni, "ni_number")], [("ID number ", None), (p.id_number, "id_number")],
        [("born on ", None), (p.dob, "dob")], [("it's under ", None), (p.name, "name")],
    ]
    msgs = [[(t, None)] for t in rng.sample(CHAT_PLAIN, 5)] + rng.sample(pii_msgs, 4)
    rng.shuffle(msgs)
    y, size, lh, max_w = 115, 17, c.line_h(17), 400
    for i, segs in enumerate(msgs):
        lines, cur, cur_w = [], [], 0.0
        for text, pii in segs:
            toks = [(text, pii)] if pii else [(w + " ", None) for w in text.split()]
            for tk, tpii in toks:
                tw = c.width(tk, size)
                if cur and cur_w + tw > max_w:
                    lines.append(cur); cur, cur_w = [], 0.0
                cur.append((tk, tpii)); cur_w += tw
        lines.append(cur)
        widest = max(sum(c.width(t, size) for t, _ in ln) for ln in lines)
        bw, bh = widest + 30, lh * len(lines) + 18
        right = (i % 2 == 0)
        x0 = 600 - 20 - bw if right else 20
        c.rect((x0, y, x0 + bw, y + bh), mine if right else theirs, radius=18)
        tc = (255, 255, 255) if (right or dark) else (25, 25, 30)
        ty = y + 9
        for ln in lines:
            tx = x0 + 15
            run, run_x = "", tx
            for t, pii in ln:
                if pii:
                    if run:
                        c.text((run_x, ty), run.rstrip(), size, tc)
                        tx = run_x + c.width(run, size); run = ""
                    tx = c.text((tx, ty), t, size, tc, kind="personal", pii=pii)
                    run_x = tx
                else:
                    if not run:
                        run_x = tx
                    run += t
                    tx = run_x + c.width(run, size)
            if run:
                c.text((run_x, ty), run.rstrip(), size, tc)
            ty += lh
        stamp = f"{rng.randint(8, 22):02d}:{rng.randint(0, 59):02d}"
        sx = x0 + bw - c.width(stamp, 11) if right else x0
        c.text((sx, y + bh + 3), stamp, 11, sub)
        y += bh + c.line_h(11) + 14
    banner(c, y=965)
    return c, "chat"


TEMPLATES = {"payslip": payslip, "letter": letter, "id_card": id_card, "chat": chat}
