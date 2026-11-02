# Limits: what Picture guard does not do, or has not been tested on

The headline numbers are from the sealed **hold-out** (50 made-up text pictures, 20 + 20 made-up face pictures), run once on 28 Oct 2026 on the frozen pipeline (tag `freeze-1`); the full table is in `README.md`. Numbers marked "dev" are from the development set (150 text pictures, 55 + 60 face pictures), which the settings were tuned on.

## What was tested

- **Made-up pictures only.** Payslips, letters, ID-style cards and chat screenshots drawn by code (`testset/`), plus pictures with AI-made faces placed on cards and chat screenshots (`faces/`, `faces_hard/`). No real documents, no real people, no phone photos of real paper.
- **AI-made faces only.** No real photographs of people were used. How well SAM 3.1 finds real faces in real photos is **unknown**.
- **English and UK formats only.** UK postcodes, sort codes, National Insurance numbers, IBANs, UK-style phone numbers. Other countries' formats are not covered by the pattern rules (Muse Glimmer may still list them).
- **Single pictures only.** One PNG or JPEG per request. PDF, Word, multi-page, animated or multi-frame files are not handled: they go whole black.

## What it does not do

- **A value that no step finds is not covered.** If Tesseract and Muse Glimmer both miss a value (for example a very small or very blurred one), no box is drawn on it. The checks below catch only what a reader can still read.
- **Drawn faces on our test ID cards are not detected** (0 of 33 face boxes on the text test pictures; SAM and Glimmer do not treat the drawn placeholders as faces). This is a limit of the test pictures, not shown on real photos. The demo uses an AI-made face that SAM does cover.
- **About a quarter of text pictures still go whole black.** On the hold-out: 13 of 50 (26%); chats 5 of 13, letters 4 of 13, payslips 4 of 12, ID cards 0 of 12. On the dev set at the frozen settings: 40 of 150 (27%). The usual cause is a value that Glimmer lists but Tesseract cannot read well enough to place a box (small, noisy or blurred text). Going black is the safe failure, not an error.
- **Partly covered values.** With the current box margin, 1 of 281 planted values in kept hold-out text pictures is covered under 90% by pixels (about 90%, none under 50%); on the dev set 1 of 850. One face in the hard-face hold-out (an accessory picture) was covered 78%, not 90%. Before the margin was widened it was 22; most of those were short at the top or bottom edge of the key's box, which can be empty space above the letters (inferred). A wider margin also covers more ordinary text: about 50% of ordinary text stays readable in kept hold-out text pictures (57% on dev; 66% with the old margin).
- **Phone photos (2 Nov 2026).** Two phone photos of a printed made-up staff badge (5712 × 4284 pixels each) went whole black (safety rule 2: a pattern-rule value was still readable after the bars were drawn), so the badge is not a demo sample. The two phone photos of the printed payslip and letter passed (not whole black, no planted value readable by the plain or strict read-back; one photo each). We do not know which value the rule found.
- **Hidden text the models cannot see** (white text on white, text inside a QR code, a barcode, very low contrast) is not found.
- **Not a legal or compliance product.** It reduces what leaves your machine; it is not a guarantee, and nothing here is legal advice.

## Speed

- **First picture after a quiet spell: about 48 seconds** on the hosted demo (the GPU container starts and loads two models; the page says the wake-up alone takes about 40 seconds). **After that, 7 to 24 seconds** per picture. Measured on the deployed demo in the speed-up work (PG-14, 28 Oct 2026: one cold and several warm pictures per sample; the cold wake-up on our own test app was 31.1 s in one run, and the cold payslip's AI step on the demo took 39.5 s). A later deployed run on 29 Oct showed the same range (the AI step took 11.0 s on one payslip run and 33.5 s on another; one run each, so not a benchmark). Not a load test.

## Privacy in the hosted demo

- **The original picture goes to our own GPU** (Modal) so that Muse Glimmer and SAM can look at it. It is processed in memory and not stored or logged. **It never goes to Meta's API.** Only the safe copy can be sent to Muse Spark, and the page shows the SHA-256 of the bytes sent next to the safe copy's.
- Use made-up pictures in the demo.
- **Known gap (29 Oct 2026):** if the hash check ever failed, the server stops before sending anything to Meta, but the demo page shows a general error, not the plain sentence "The hashes do not match. Nothing was sent." Nothing is sent in either case. This has not happened in any test.
- **What goes to Meta:** only the safe copy and your question go to Meta's Model API. On free credits, Meta may use what is sent for product improvement (Meta's billing page, 28 Oct 2026).
- The Meta Model API's retention of images is **not stated** in Meta's developer docs (the legal terms were not read). The code uses a Standard-mode model only, never a "Contributor" one.

## What a leak check can and cannot prove

- Three checks run on every result: Tesseract read-back, a stricter read-back (plain + inverted-dark + local-contrast reads), and a pixel check against the planted boxes. They show that **planted values were not readable** in the pictures that were kept. They cannot show that every real value in an unseen picture is covered.
