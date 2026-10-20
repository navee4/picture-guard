"""Self-check for the test set. Fails loudly (non-zero exit) on any miss.

    python testset/check.py            # checks testset/images + testset/key.json

What it proves:
  1. counts by type and split are right (4 types x 50; 150 dev / 50 hold-out);
  2. every span box is inside its picture and the saved picture has the size the key says;
  3. every planted value is drawn: the picture is re-rendered with that one span left out, and
     the pixels change inside the span's box and nowhere outside it;
  4. planted values are valid: Luhn cards, IBAN mod-97, NI format, published test cards only;
  5. the key matches a fresh rebuild from the seed, and two fresh generations give identical SHA-256.
"""
import hashlib
import json
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from draw import encode, final_boxes, render  # noqa: E402
from generate import HOLDOUT, PER_TYPE, TYPES, build_specs, key_entry  # noqa: E402
from values import FICTIONAL_BANK_CODE, TEST_CARDS, iban_ok, luhn_ok, ni_format_ok  # noqa: E402

HERE = Path(__file__).resolve().parent
errors = []


def fail(msg):
    errors.append(msg)


def digits(s):
    return "".join(ch for ch in s if ch.isdigit())


def check_one(args):
    e, (t, split, spec) = args
    errs, counts = [], Counter()

    def fail(msg):
        errs.append(msg)

    name = e["file"]
    # 5a. key matches rebuild
    if key_entry(name, t, split, spec) != e: fail(f"{name}: key entry differs from a fresh rebuild")
    # 2. boxes + saved size
    path = HERE / "images" / name
    if not path.exists():
        return [f"{name}: picture file missing (run generate.py)"], counts
    with Image.open(path) as im:
        if im.size != (e["width"], e["height"]): fail(f"{name}: size {im.size} != key")
    for s in e["spans"]:
        x0, y0, x1, y1 = s["box"]
        if not (0 <= x0 < x1 <= e["width"] and 0 <= y0 < y1 <= e["height"]):
            fail(f"{name}: box {s['box']} outside {e['width']}x{e['height']} ({s['text']!r})")
    if "SYNTHETIC TEST DATA" not in [s["text"] for s in e["spans"]]: fail(f"{name}: no SYNTHETIC TEST DATA label")
    # 3. every span drawn
    full = np.asarray(render(spec), dtype=np.int16)
    for i, s in enumerate(e["spans"]):
        part = np.asarray(render(spec, omit=i), dtype=np.int16)
        diff = np.abs(full - part).max(axis=2)
        ys, xs = np.nonzero(diff > 0)
        x0, y0, x1, y1 = s["box"]
        if len(xs) < 5:
            fail(f"{name}: span {i} {s['text']!r} ({s['pii_type']}) is not drawn (only {len(xs)} pixels differ)")
            continue
        if xs.min() < x0 or xs.max() >= x1 or ys.min() < y0 or ys.max() >= y1:
            fail(f"{name}: span {i} {s['text']!r} changes pixels outside its box {s['box']}: "
                 f"[{xs.min()},{ys.min()},{xs.max() + 1},{ys.max() + 1}]")
        elif diff.max() < 8:
            fail(f"{name}: span {i} {s['text']!r} is almost invisible (max pixel change {diff.max()})")
    # 4. value validity
    for s in e["spans"]:
        pt = s["pii_type"]
        if s["kind"] == "personal": counts[pt] += 1
        if pt == "card_number" and not (luhn_ok(digits(s["text"])) and digits(s["text"]) in TEST_CARDS):
            fail(f"{name}: card {s['text']!r} is not a Luhn-valid published test number")
        if pt == "iban" and not (iban_ok(s["text"]) and s["text"].replace(" ", "")[4:8] == FICTIONAL_BANK_CODE):
            fail(f"{name}: IBAN {s['text']!r} is not valid")
        if pt == "ni_number" and not ni_format_ok(s["text"]): fail(f"{name}: NI {s['text']!r} bad format")
        if pt == "sort_code" and len(digits(s["text"])) != 6: fail(f"{name}: sort code {s['text']!r}")
        if pt == "account_number" and len(s["text"]) != 8: fail(f"{name}: account {s['text']!r}")
        if (s["kind"] == "personal") != (pt is not None): fail(f"{name}: kind/pii_type mismatch {s}")
    return errs, counts


def main():
    key = json.loads((HERE / "key.json").read_text())
    imgs = key["images"]

    # 1. counts
    by_type = Counter(e["type"] for e in imgs)
    by_split = Counter(e["split"] for e in imgs)
    by_ts = Counter((e["type"], e["split"]) for e in imgs)
    if len(imgs) != 200: fail(f"expected 200 pictures, found {len(imgs)}")
    for t in TYPES:
        if by_type[t] != PER_TYPE: fail(f"type {t}: {by_type[t]} != {PER_TYPE}")
        if by_ts[(t, "holdout")] != HOLDOUT[t]: fail(f"type {t}: holdout {by_ts[(t, 'holdout')]} != {HOLDOUT[t]}")
    if by_split["dev"] != 150 or by_split["holdout"] != 50: fail(f"split counts {dict(by_split)}")
    if len({e["file"] for e in imgs}) != 200: fail("file names are not unique")

    # fresh rebuild from the seed; per-picture checks run in parallel
    specs = {n: (t, s, sp) for n, t, s, sp in build_specs(key["seed"])}
    pii_counts = Counter()
    with Pool() as pool:
        for errs, counts in pool.imap_unordered(check_one, [(e, specs[e["file"]]) for e in imgs]):
            errors.extend(errs)
            pii_counts.update(counts)
    for t in ("name", "address", "postcode", "sort_code", "account_number", "ni_number", "card_number",
              "iban", "id_number", "dob", "email", "phone", "face"):
        if pii_counts[t] == 0: fail(f"no planted values of type {t}")

    # 5b. same seed, same bytes (two fresh generations vs each other, key.json and the files on disk)
    runs = []
    for _ in (1, 2):
        runs.append({name: hashlib.sha256(encode(render(spec), spec["variety"])).hexdigest()
                     for name, t, sp, spec in build_specs(key["seed"])})
    for name, h in runs[0].items():
        if runs[1][name] != h: fail(f"{name}: two generations differ")
        if key["sha256"].get(name) != h: fail(f"{name}: SHA-256 differs from key.json")
        disk = HERE / "images" / name
        if disk.exists() and hashlib.sha256(disk.read_bytes()).hexdigest() != h:
            fail(f"{name}: file on disk differs from a fresh generation")

    print(f"pictures {len(imgs)}  by type {dict(by_type)}  by split {dict(by_split)}")
    print(f"planted personal spans by type {dict(sorted(pii_counts.items()))}")
    print("other spans", sum(1 for e in imgs for s in e["spans"] if s["kind"] == "other"))
    if errors:
        print(f"\nCHECK FAILED: {len(errors)} problem(s)")
        for m in errors[:40]: print(" -", m)
        sys.exit(1)
    print("CHECK PASSED")


if __name__ == "__main__":
    main()
