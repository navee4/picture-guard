"""Make the made-up staff badge for Saltmarsh Care Services (the made-up employer on payslip_000).

    .venv/bin/python badge/make_badge.py

Writes next to this file: staff_badge.png (85.6 x 54 mm at 600 dpi, 2022 x 1276 px), staff_badge_print.pdf (A4, badge at 100% scale,
front only, thin cut marks) and staff_badge_key.json (the made-up private values and where they sit, same shape as testset/key.json).
No barcode, no QR code, no magnetic stripe: Picture guard does not read them, so a code would carry private data past it.
All values are made up. The portrait is AI-made (SDXL, faces/portraits/p011.png, kept locally; the raw portraits are not committed), see LICENCES.md."""
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PORTRAIT = ROOT / "faces" / "portraits" / "p011.png"
FONT = ROOT / "picture_guard" / "demo" / "static" / "fonts"
SCALE = 600 / 96  # CSS px are 1/96 inch; 600 dpi
W_MM, H_MM = 85.6, 54.0

PERSON = {
    "name": "Katie Edwards", "staff_no": "SCS-04817", "dob": "12 Jan 1976",
    "mobile": "07700 900431", "email": "katie.edwards@example.net",
}
BRAND = "#0F6E78"

fonts = sorted(FONT.glob("Bricolage*.woff2"))
font_b64 = base64.b64encode(fonts[0].read_bytes()).decode() if fonts else ""
photo_b64 = base64.b64encode(PORTRAIT.read_bytes()).decode()

BADGE = f"""
<div id="badge">
  <div class="top">
    <svg class="logo" viewBox="0 0 40 40"><rect width="40" height="40" rx="9" fill="#fff"/><path d="M6 24c4-6 8-6 12 0s8 6 12 0 4-3 4-3" fill="none" stroke="{BRAND}" stroke-width="3.6" stroke-linecap="round"/><circle cx="20" cy="12" r="3.6" fill="{BRAND}"/></svg>
    <div class="co"><b>Saltmarsh</b><span>Care Services</span></div>
    <div class="role">STAFF</div>
  </div>
  <div class="body">
    <img id="photo" src="data:image/png;base64,{photo_b64}">
    <div class="info">
      <div id="name" class="name">{PERSON['name']}</div>
      <div class="title">Senior Care Assistant</div>
      <div class="team">Community Support Team</div>
      <dl>
        <dt>Staff no.</dt><dd id="staff_no">{PERSON['staff_no']}</dd>
        <dt>Born</dt><dd id="dob">{PERSON['dob']}</dd>
        <dt>Mobile</dt><dd id="mobile">{PERSON['mobile']}</dd>
        <dt>Email</dt><dd id="email">{PERSON['email']}</dd>
      </dl>
      <div class="dates"><span>Issued <b>04/2026</b></span><span>Expires <b>04/2027</b></span></div>
    </div>
  </div>
  <div class="foot"><span>If found, please return to Saltmarsh Care Services, Fictional Employer, Nowhere</span><b>SYNTHETIC TEST DATA</b></div>
</div>"""

CSS = f"""
@font-face {{ font-family: Bricolage; src: url(data:font/woff2;base64,{font_b64}); font-weight: 200 800; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ font-family: Bricolage, "Helvetica Neue", Arial, sans-serif; color: #1B2430; background: #fff; }}
#badge {{ width: {W_MM}mm; height: {H_MM}mm; border-radius: 3.2mm; background: #fff; border: 0.2mm solid #cfd6dc; overflow: hidden; position: relative; }}
.top {{ height: 11.5mm; background: {BRAND}; color: #fff; display: flex; align-items: center; gap: 2.2mm; padding: 0 3.5mm; }}
.logo {{ width: 7.6mm; height: 7.6mm; }}
.co {{ display: flex; flex-direction: column; line-height: 1.02; }}
.co b {{ font-size: 4.3mm; font-weight: 700; letter-spacing: 0.1mm; }}
.co span {{ font-size: 2.5mm; font-weight: 400; opacity: .92; letter-spacing: 0.35mm; }}
.role {{ margin-left: auto; font-size: 2.6mm; font-weight: 600; letter-spacing: 0.5mm; border: 0.25mm solid rgba(255,255,255,.7); border-radius: 1mm; padding: 0.4mm 1.4mm; }}
.body {{ display: flex; gap: 3.2mm; padding: 2.6mm 3.5mm 0; height: 33mm; }}
#photo {{ width: 22mm; height: 28.5mm; object-fit: cover; object-position: 50% 12%; border-radius: 1.6mm; border: 0.25mm solid #cfd6dc; flex: none; }}
.info {{ min-width: 0; }}
.name {{ font-size: 4.5mm; font-weight: 700; line-height: 1.1; white-space: nowrap; }}
.title {{ font-size: 2.9mm; font-weight: 600; color: {BRAND}; margin-top: 0.5mm; }}
.team {{ font-size: 2.5mm; color: #4A5766; }}
dl {{ display: grid; grid-template-columns: 11.5mm 1fr; row-gap: 0.45mm; margin-top: 1.5mm; font-size: 2.45mm; line-height: 1.15; }}
dt {{ color: #4A5766; }} dd {{ font-weight: 500; white-space: nowrap; }}
.dates {{ display: flex; gap: 4mm; margin-top: 0.9mm; font-size: 2.45mm; color: #4A5766; white-space: nowrap; }}
.dates b {{ color: #1B2430; font-weight: 500; }}
.foot {{ position: absolute; left: 0; right: 0; bottom: 0; height: 7.4mm; background: #EEF3F5; border-top: 0.2mm solid #d5dde2; padding: 0.9mm 3.5mm 0; display: flex; flex-direction: column; font-size: 1.95mm; color: #4A5766; line-height: 1.25; }}
.foot b {{ font-size: 2.2mm; letter-spacing: 0.3mm; color: #1B2430; }}
"""

PAGE = f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body style='padding:0'>{BADGE}"

SHEET = f"""<!doctype html><meta charset=utf-8><style>{CSS}
@page {{ size: A4; margin: 0; }}
html, body {{ width: 210mm; height: 297mm; }}
#wrap {{ position: absolute; left: 62.2mm; top: 40mm; width: {W_MM}mm; height: {H_MM}mm; }}
.m {{ position: absolute; background: #000; }}
.h {{ height: 0.15mm; width: 5mm; }} .v {{ width: 0.15mm; height: 5mm; }}
#note {{ position: absolute; left: 62.2mm; top: 100mm; font-size: 3mm; color: #4A5766; width: 86mm; line-height: 1.4; }}
</style><body>
<div id="wrap">{BADGE}</div>
<div class="m h" style="left:55.2mm;top:40mm"></div><div class="m h" style="left:148.8mm;top:40mm"></div>
<div class="m h" style="left:55.2mm;top:94mm"></div><div class="m h" style="left:148.8mm;top:94mm"></div>
<div class="m v" style="left:62.2mm;top:33mm"></div><div class="m v" style="left:147.8mm;top:33mm"></div>
<div class="m v" style="left:62.2mm;top:94mm"></div><div class="m v" style="left:147.8mm;top:94mm"></div>
<div id="note">Print at 100% (no "fit to page"). Cut on the marks, front only. Made-up staff badge: Saltmarsh Care Services is a made-up employer, the portrait is AI-made. Synthetic test data.</div>"""


def yunet_box(photo):
    """The portrait's YuNet face box (portraits_meta.json, index 11) in badge pixels; the photo is 'cover'-fitted, height governs."""
    fb = [308.5389, 222.1982, 582.8639, 630.5918]
    sc = (photo[3] - photo[1]) / 1024.0
    offx = (1024 * sc - (photo[2] - photo[0])) / 2
    return [round(photo[0] - offx + fb[0] * sc), round(photo[1] + fb[1] * sc), round(photo[0] - offx + fb[2] * sc), round(photo[1] + fb[3] * sc)]


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 400, "height": 300}, device_scale_factor=SCALE)
        pg.set_content(PAGE)
        pg.wait_for_timeout(300)
        el = pg.query_selector("#badge")
        el.screenshot(path=str(HERE / "staff_badge.png"))
        from PIL import Image
        im = Image.open(HERE / "staff_badge.png")
        im.crop((0, 0, 2022, 1276)).save(HERE / "staff_badge.png")
        origin = pg.evaluate("(() => { const r = document.querySelector('#badge').getBoundingClientRect(); return [r.left, r.top]; })()")
        spans = []
        for fid, typ in (("name", "name"), ("staff_no", "other"), ("dob", "dob"), ("mobile", "phone"), ("email", "email")):
            r = pg.evaluate(f"(() => {{ const e = document.querySelector('#{fid}'); const rg = document.createRange(); rg.selectNodeContents(e); const r = rg.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }})()")
            box = [round((r[0] - origin[0]) * SCALE), round((r[1] - origin[1]) * SCALE), round((r[2] - origin[0]) * SCALE), round((r[3] - origin[1]) * SCALE)]
            val = {"name": PERSON["name"], "staff_no": PERSON["staff_no"], "dob": PERSON["dob"], "mobile": PERSON["mobile"], "email": PERSON["email"]}[fid]
            spans.append({"text": val, "kind": "personal", "pii_type": typ, "box": box})
        fr = pg.evaluate("(() => { const r = document.querySelector('#photo').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })()")
        face = [round((fr[0] - origin[0]) * SCALE), round((fr[1] - origin[1]) * SCALE), round((fr[2] - origin[0]) * SCALE), round((fr[3] - origin[1]) * SCALE)]
        key = {"note": "made-up values; box = pixel box in staff_badge.png; portrait faces/portraits/p011.png (AI-made, SDXL)",
               "images": [{"file": "staff_badge.png", "type": "staff_badge", "width": 2022, "height": 1276, "spans": spans, "faces": [{"box": yunet_box(face), "source": "YuNet box of faces/portraits/p011.png (portraits_meta.json) mapped onto the badge photo"}]}]}
        (HERE / "staff_badge_key.json").write_text(json.dumps(key, indent=1) + "\n")
        pg2 = b.new_page()
        pg2.set_content(SHEET)
        pg2.wait_for_timeout(300)
        pg2.pdf(path=str(HERE / "staff_badge_print.pdf"), prefer_css_page_size=True, print_background=True)
        b.close()


if __name__ == "__main__":
    main()
