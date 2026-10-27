# Picture guard

Finds names, addresses, account and ID numbers and faces in a picture, covers each with a black box, and sends only
the cleaned copy to an AI. If it is not sure, it blacks out the whole picture.

## The entry (`picture_guard/`), written from 27 Oct 2026

    uv pip install --python .venv/bin/python -e .      # installs the `pg` command
    brew install tesseract                              # the reader (a separate program)
    .venv/bin/pg protect in.png --out safe.png --report report.json
    .venv/bin/pg eval --set testset --split dev         # measure on made-up test pictures (dev split only)
    .venv/bin/python -m unittest discover -s tests -t .

Status (day 2): reader (Tesseract), pattern rules with check digits, locating and black-out are built. Faces,
the face-count check, the check of the safe copy and the AI step are not, so the product answer is still
"black out the whole picture" whenever a stage is not sure. `--ablation` switches the unbuilt stages off for
measurement only; it is **not a product result**. See `BUILT-BEFORE-HACKATHON.md` and `LICENCES.md`.

## The live demo (`picture_guard/demo/`)

A web page over the same pipeline as `pg protect`: pick a made-up sample or upload a PNG/JPEG, see the original beside the safe copy, what was covered (types and counts only), progress per stage, then ask Muse Spark a question about the safe copy. A panel shows the SHA-256 of the original, of the safe copy and of the image bytes in the request to Muse Spark (they must match the safe copy and never the original).

- Deploy (Modal, scales to zero, one container each for the web part and the GPU part): `.venv/bin/python tools/deploy_demo.py`. The Muse Spark call uses the Modal secret `meta-model-api` (key `META_MODEL_API_KEY`) if it exists; otherwise the page says "not connected yet" and nothing is sent.
- Limits: 5 MB, 16 megapixels, 8 pictures and 12 questions per visitor per 10 minutes, 200 pictures a day, one picture at a time, 240 s per request.
- Pictures are processed in memory-backed temporary files that are deleted at once. Nothing is stored or logged.
- Tests: `.venv/bin/python -m unittest tests.test_demo`; end to end in a real browser against a deployed demo: `PG_DEMO_URL=... .venv/bin/python -m unittest tests.e2e.test_demo_e2e` (needs `uv pip install -e '.[demo-test]'` and `playwright install chromium`).

## Licence

Our code is licensed under Apache-2.0 (see `LICENSE`). That covers our code only; the models and programs it uses have their own licences, listed in `LICENCES.md`.

---

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

See `spike/README.md`.
