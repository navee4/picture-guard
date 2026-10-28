# Picture guard

**Built for the Meta Global AI Developer Hackathon (Startup track).** Demo: link added at submission.

## The problem

People paste screenshots, payslips, letters and photos of ID cards into AI chatbots all the time. Text tools that look for private data cannot see text inside a picture. So names, addresses, account numbers and faces go straight to the AI.

## What Picture guard does

It finds names, addresses, account numbers, ID numbers and faces in a picture. It covers each one with a black box, and sends only that cleaned copy to the AI. If it is not sure, it blacks out the whole picture.

![The pipeline](docs/pipeline.svg)

## How it works (and where Meta's models are used)

1. **Read.** Tesseract (on CPU) finds every word and where it is.
2. **Decide.** Pattern rules with check digits (card numbers, IBANs, NI numbers, sort codes) plus **Muse Glimmer** (open weights, 4-bit, on our own GPU) decide what is private, including names, addresses and ID numbers.
3. **Locate.** Each private value gets a box from the words Tesseract found (with a zoomed re-read for hard ones).
4. **Faces.** **SAM 3.1** (on our own GPU) finds faces; Glimmer's face count is a second check.
5. **Black out.** Solid black boxes, written to a new PNG with no metadata.
6. **Check the safe copy.** The cleaned picture is read again; any private value still readable means "not sure".
7. **Ask.** **Muse Spark** (Meta Model API) answers questions about the **safe copy only**. The step is built and unit-tested; the hosted demo switches it on with the Meta Model API key.

The original picture goes only to our own GPU (Modal), never to Meta's API.

## The safety rules

Any "not sure" gives a whole black picture. The five fail-safe rules:

1. A value the AI saw has no matching word on the picture, so it cannot be covered safely.
2. After covering, a private value can still be read on the safe copy.
3. A step fails, times out, or the picture can hardly be read.
4. The file is not one PNG or JPEG picture.
5. The AI counts more faces than the face finder covered.

**The proof.** The page and the code check, before anything is sent, that the SHA-256 of the image in the request equals the SHA-256 of the safe copy and never the original's (unit tests refuse the original, a second image, an image URL and a file id). Three leak checks run on every test result: a plain Tesseract read of the safe copy, a stricter read (plain, dark areas inverted, local contrast), and a pixel check of every planted box.

## Results (dev set, 28 Oct 2026)

Made-up test pictures only. Measured on the **dev** split (150 text pictures, 55 + 60 face pictures); the final numbers will come from a sealed **hold-out** set, run once at the end. Details: `LIMITS.md`.

| Dev set | Pictures | Whole picture black | Planted values left readable (kept pictures) | Faces covered ≥90% (kept pictures) |
|---|---|---|---|---|
| Text pictures (payslips, letters, ID-style cards, chats) | 150 | 41 (27%): chats 16 of 37, letters 12 of 37, payslips 7 of 38, ID cards 6 of 38 | 0 by plain Tesseract, 0 by the strict read, 0 under 50% covered by pixels, 1 under 90% (of 837) | drawn placeholder faces not detected (a test-picture limit) |
| Faces on cards and chats (AI-made faces) | 55 | 1 (2%) | no values planted | 117 of 117 |
| Harder faces (side views, hats, masks, groups) | 60 | 6 (10%) | no values planted | 112 of 112 |

Reading the table: a black picture is the safe failure, not a leak. "Kept" means the picture was not blacked out whole. About 55% of the ordinary (not private) text stays readable in kept text pictures.

## Run it

    uv pip install --python .venv/bin/python -e .      # installs the `pg` command
    brew install tesseract                              # the reader (a separate program)
    .venv/bin/pg protect in.png --out safe.png --report report.json    # needs the Modal app (see below)
    .venv/bin/pg eval --set testset --split dev         # measure on made-up test pictures (dev split only)
    .venv/bin/python -m unittest discover -s tests -t .

The models run on Modal only (never on your computer): `pg protect` and `pg eval` start the Modal app for the length of the run. `pg protect --no-models` runs without models; it then blacks out whole pictures whenever names and addresses would need judging.

### The live demo (`picture_guard/demo/`)

A web page over the same pipeline as `pg protect`: pick a made-up sample or upload a PNG/JPEG, see the original beside the safe copy, what was covered (types and counts only), progress per stage, then ask Muse Spark a question about the safe copy. A panel shows the SHA-256 of the original, of the safe copy and of the image bytes in the request to Muse Spark.

- Deploy (Modal, scales to zero; one container each for the web part and the GPU part): `.venv/bin/python tools/deploy_demo.py`. The Muse Spark call uses the Modal secret `meta-model-api` (key `META_MODEL_API_KEY`) if it exists; otherwise the page says "not connected yet" and nothing is sent.
- Limits: 5 MB, 16 megapixels, 8 pictures and 12 questions per visitor per 10 minutes, 200 pictures a day, one picture at a time, 240 s per request.
- Pictures are processed in memory-backed temporary files that are deleted at once. Nothing is stored or logged.
- End to end in a real browser against a deployed demo: `PG_DEMO_URL=... .venv/bin/python -m unittest tests.e2e.test_demo_e2e tests.e2e.test_demo_samples` (needs `uv pip install -e '.[demo-test]'` and `playwright install chromium`).

### Tests

    .venv/bin/python -m unittest discover -s tests -t .     # 120+ tests; the model calls are faked, Tesseract is real
    sh tools/secret_scan.sh                                 # looks for keys and tokens before every commit

## What was built during the hackathon

The hackathon started on 26 Oct 2026. Everything in `picture_guard/`, `tests/`, `tools/` and `docs/` was written from 27 Oct. The made-up test pictures and model spike (`testset/`, `spike/`, `faces/`, `faces_hard/`) were made before it; see `BUILT-BEFORE-HACKATHON.md` and the git tag `pre-hackathon`.

## Test data

All pictures are **made up** (each says "SYNTHETIC TEST DATA"): fictional issuers, banks and employers; published test card numbers; Ofcom's drama phone range; reserved example email domains; a fictional IBAN bank code; AI-made or drawn faces. `testset/` has 200 pictures (150 dev, 50 hold-out) with a key of every planted value and its box; `faces/` and `faces_hard/` hold face pictures. The hold-out is not used until the final run.

## Limits

An honest list is in `LIMITS.md`.

## Built by

Built by navee4 (solo builder). AI coding tools (Claude) helped write the code.

## Licence

Our code is licensed under Apache-2.0 (see `LICENSE`). That covers our code only; the models and programs it uses have their own licences, listed in `LICENCES.md`.
