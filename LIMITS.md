# Limits: what Picture guard does not do, or has not been tested on

Every number here is from the **dev set** (150 made-up text pictures, 55 + 60 made-up face pictures) until the sealed hold-out run replaces it. See `README.md`.

## What was tested

- **Made-up pictures only.** Payslips, letters, ID-style cards and chat screenshots drawn by code (`testset/`), plus pictures with AI-made faces placed on cards and chat screenshots (`faces/`, `faces_hard/`). No real documents, no real people, no phone photos of real paper.
- **AI-made faces only.** No real photographs of people were used. How well SAM 3.1 finds real faces in real photos is **unknown**.
- **English and UK formats only.** UK postcodes, sort codes, National Insurance numbers, IBANs, UK-style phone numbers. Other countries' formats are not covered by the pattern rules (Muse Glimmer may still list them).
- **Single pictures only.** One PNG or JPEG per request. PDF, Word, multi-page, animated or multi-frame files are not handled: they go whole black.

## What it does not do

- **A value that no step finds is not covered.** If Tesseract and Muse Glimmer both miss a value (for example a very small or very blurred one), no box is drawn on it. The checks below catch only what a reader can still read.
- **Drawn faces on our test ID cards are not detected** (0 of 33 face boxes on the text test pictures; SAM and Glimmer do not treat the drawn placeholders as faces). This is a limit of the test pictures, not shown on real photos. The demo uses an AI-made face that SAM does cover.
- **About a quarter of text pictures still go whole black.** On the dev set: 41 of 150 (27%); chats 16 of 37, letters 12 of 37, payslips 7 of 38, ID cards 6 of 38. The usual cause is a value that Glimmer lists but Tesseract cannot read well enough to place a box (small, noisy or blurred text). Going black is the safe failure, not an error.
- **Partly covered values.** With the current box margin, 1 of 837 planted values in kept dev text pictures is covered under 90% by pixels (none under 50%). Before the margin was widened it was 22; most of those were short at the top or bottom edge of the key's box, which can be empty space above the letters (inferred). A wider margin also covers more ordinary text: about 55% of ordinary text stays readable in kept text pictures (66% with the old margin).
- **Hidden text the models cannot see** (white text on white, text inside a QR code, a barcode, very low contrast) is not found.
- **Not a legal or compliance product.** It reduces what leaves your machine; it is not a guarantee, and nothing here is legal advice.

## Speed

- Cold start: the first picture after a quiet spell took about **60 seconds** on the hosted demo (the GPU loads two models). A warm picture took about **20 to 30 seconds** (reading about 4 to 10 s on a small CPU, the AI step about 10 to 15 s, the re-read of the safe copy 3 to 5 s). Measured on the deployed demo and in replays; not a load test.

## Privacy in the hosted demo

- **The original picture goes to our own GPU** (Modal) so that Muse Glimmer and SAM can look at it. It is processed in memory and not stored or logged. **It never goes to Meta's API.** Only the safe copy can be sent to Muse Spark, and the page shows the SHA-256 of the bytes sent next to the safe copy's.
- Use made-up pictures in the demo.
- The Meta Model API's retention of images is **not stated** in Meta's developer docs (the legal terms were not read). The code uses a Standard-mode model only, never a "Contributor" one.

## What a leak check can and cannot prove

- Three checks run on every dev result: Tesseract read-back, a stricter read-back (plain + inverted-dark + local-contrast reads), and a pixel check against the planted boxes. They show that **planted values were not readable** in the pictures that were kept. They cannot show that every real value in an unseen picture is covered.
