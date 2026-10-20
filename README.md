# Picture guard — prep (test set + model spike)

Entry for the Meta Global AI Developer Hackathon (starts 26 Oct 2026). Picture guard finds personal
values in a picture, covers each with a black box and sends only the cleaned copy to an AI.
This repo is **prep only**: a made-up test set and a model spike. No product pipeline yet.

All data here is **made up** (every picture says "SYNTHETIC TEST DATA"). Fictional issuers, banks,
employers and chat apps. Cards are published test numbers, phone numbers are Ofcom's drama range,
emails use reserved example domains, IBANs use a fictional bank code. Faces are drawn placeholders.

## Set up

    uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt

No model weights or model runs on the Mac. Models run on Modal only (`modal profile current` must work).

## Test set (`testset/`)

    .venv/bin/python testset/generate.py     # 200 pictures -> testset/images/ (git-ignored) + testset/key.json
    .venv/bin/python testset/check.py        # self-check; exits non-zero on any miss

- 200 pictures, fixed seed 20261020: 50 payslips, 50 letters, 50 ID-style cards, 50 chat screenshots.
- Split in `key.json`: 150 `dev`, 50 `holdout`. **Nothing is tuned on the hold-out.**
- `key.json` lists, per picture: file, type, split, variety tags, and spans
  `{text, kind: personal|other, pii_type, box: [x0,y0,x1,y1]}` (pixels, in the saved picture;
  rotated pictures use the axis-aligned box around the rotated text).
- `other` spans are non-personal text (titles, labels, amounts, body text) used to measure false alarms
  and how much of a picture stays readable.
- Variety: 6 fonts, sizes, small rotations, PNG/JPEG, scan noise, low contrast, phone-photo blur, dark chat theme.
- Same seed gives the same SHA-256 for every file **on the same machine**. The generator uses macOS
  system fonts (`/System/Library/Fonts/Supplemental`), so another OS gives other bytes. `key.json`
  stores the SHA-256 of each file and `check.py` verifies them.

## Spike (`spike/`)

See `spike/README.md`. Results go to the events folder (see the task brief), not into this repo.
