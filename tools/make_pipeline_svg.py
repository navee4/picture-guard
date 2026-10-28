"""Draws docs/pipeline.svg (plain SVG, no libraries) so the picture can be checked in the repo. Run: python tools/make_pipeline_svg.py"""
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1000, 820
STEPS = [  # (title, where it runs / model, what it does)
    ("1  Read", "Tesseract on CPU", "finds every word and where it is (plain, 2x, contrast, digits-only reads)"),
    ("2  Decide", "Muse Glimmer 30B, 4-bit, open weights, on our own GPU + pattern rules", "lists names, addresses, account, ID and card numbers, dates of birth, emails, phones"),
    ("3  Locate", "Tesseract words (+ a zoomed re-read)", "puts a box on every value Glimmer listed"),
    ("4  Faces", "SAM 3.1 on our own GPU", "covers each face (mask rectangle grown 15%)"),
    ("5  Count check", "Muse Glimmer", "Glimmer counts faces; more than SAM found = not sure"),
    ("6  Black out", "plain code", "solid black boxes; new PNG, no metadata"),
    ("7  Check the safe copy", "Tesseract + rules", "read it again; any private value still readable = not sure"),
    ("8  Send", "Muse Spark (Meta Model API)", "only the safe copy; SHA-256 of the sent bytes must equal the safe copy's"),
]


def build() -> str:
    x0, bw, bh, gap, y0 = 40, 600, 62, 24, 70
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">',
           '<title id="t">Picture guard pipeline</title>',
           '<desc id="d">A picture goes through eight steps. Any step that is not sure sends the whole picture to a black copy instead.</desc>',
           '<style>text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#1c1d1f}.b{fill:#ffffff;stroke:#9aa0a6;stroke-width:1.5}.t{font-size:17px;font-weight:600}'
           '.s{font-size:12.5px;fill:#5c6066}.m{font-size:13px;fill:#1f5eff;font-weight:600}.f{fill:#fdecea;stroke:#b3261e;stroke-width:2}.fr{font-size:15px;font-weight:700;fill:#b3261e}'
           '.fs{font-size:12.5px;fill:#7a1a14}.a{stroke:#5c6066;stroke-width:2;fill:none}.r{stroke:#b3261e;stroke-width:1.6;fill:none;stroke-dasharray:5 4}.g{fill:#e8f5ee;stroke:#16794a;stroke-width:2}</style>',
           f'<rect width="{W}" height="{H}" fill="#f7f7f4"/>',
           '<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5c6066"/></marker>'
           '<marker id="rr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#b3261e"/></marker></defs>',
           f'<text x="{x0}" y="40" class="t" style="font-size:22px">Picture guard: what happens to a picture</text>']
    ys = []
    for i, (title, where, what) in enumerate(STEPS):
        y = y0 + i * (bh + gap)
        ys.append(y)
        out += [f'<rect class="b" x="{x0}" y="{y}" width="{bw}" height="{bh}" rx="10"/>',
                f'<text class="t" x="{x0 + 16}" y="{y + 22}">{escape(title)}</text>',
                f'<text class="m" x="{x0 + 16}" y="{y + 40}">{escape(where)}</text>',
                f'<text class="s" x="{x0 + 16}" y="{y + 56}">{escape(what)}</text>']
        if i:
            out.append(f'<line class="a" x1="{x0 + bw / 2}" y1="{ys[i - 1] + bh}" x2="{x0 + bw / 2}" y2="{y - 2}" marker-end="url(#ar)"/>')
    last = ys[-1] + bh
    out += [f'<line class="a" x1="{x0 + bw / 2}" y1="{last}" x2="{x0 + bw / 2}" y2="{last + 22}" marker-end="url(#ar)"/>',
            f'<rect class="g" x="{x0}" y="{last + 24}" width="{bw}" height="36" rx="10"/>',
            f'<text class="t" x="{x0 + 16}" y="{last + 48}">Muse Spark answers your question about the safe copy</text>']
    # fail-safe box on the right
    fx, fw = 700, 270
    fy, fh = y0, 560
    out += [f'<rect class="f" x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="12"/>',
            f'<text class="fr" x="{fx + 16}" y="{fy + 30}">Whole picture black</text>',
            f'<text class="fs" x="{fx + 16}" y="{fy + 52}">(the fail-safe) when:</text>']
    rules = ["1  a value the AI saw has no", "    matching word on the picture", "2  the safe copy still shows a", "    private value when read again", "3  a step fails, times out, or the",
             "    picture can hardly be read", "4  the file is not one PNG or JPEG", "5  the AI counts more faces than", "    the face finder covered"]
    for i, r in enumerate(rules):
        out.append(f'<text class="fs" x="{fx + 16}" y="{fy + 84 + i * 20}">{escape(r)}</text>')
    out.append(f'<text class="fs" x="{fx + 16}" y="{fy + 84 + len(rules) * 20 + 14}">Any "not sure" = black.</text>')
    out.append(f'<text class="fs" x="{fx + 16}" y="{fy + 84 + len(rules) * 20 + 34}">Anything not found = not covered:</text>')
    out.append(f'<text class="fs" x="{fx + 16}" y="{fy + 84 + len(rules) * 20 + 52}">see LIMITS.md.</text>')
    for i in (0, 1, 2, 3, 4, 6):  # steps that can raise the fail-safe
        y = ys[i] + bh / 2
        out.append(f'<path class="r" d="M{x0 + bw} {y} L{fx} {y}" marker-end="url(#rr)"/>')
    out.append(f'<text class="s" x="{x0}" y="{H - 16}">Steps 1 to 7 run before anything leaves our own servers. The original goes only to our own GPU, never to Meta.</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    p = Path(__file__).resolve().parent.parent / "docs" / "pipeline.svg"
    p.write_text(build())
    print("wrote", p)
