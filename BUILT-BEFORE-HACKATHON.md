# Built before the hackathon

The Meta Global AI Developer Hackathon started on Monday 26 October 2026. This file says what was made **before**
that, so the judges can tell old work from new work.

## The last commit before hackathon work

Git tag `pre-hackathon` points at commit `0013a9deca609a6c3786d20ea43a5ca2c8ffa477`
("Run SAM 3.1 and Glimmer 4-bit on 60 dev harder-face pictures; scoring, contact sheet", 21 Oct 2026, 07:43 +0100).
Everything up to and including that commit was made before the hackathon. List it with:

    git log --format='%h %ad %s' --date=iso pre-hackathon

## What is in that range (10 commits, 20 to 21 October 2026)

| Folder | What it is | Dates (commits) |
|---|---|---|
| `testset/` | Generator, key and self-check for 200 made-up pictures (payslips, letters, ID-style cards, chat screenshots) with planted values | 20 Oct 2026 (`9d4031a`, `285aca0`) |
| `spike/` | Scripts that tried Muse Glimmer, SAM 3.1 and Tesseract on the test pictures, on Modal; scoring and a spend ledger | 20 Oct 2026 (`d5bb347` to `8cdcdfb`) |
| `faces/` | Made-up face pictures (AI-generated portraits placed on cards and chat screenshots), key, self-check, and a run of SAM and Glimmer on them | 20 Oct 2026 (`4e6574e`, `e8fdd7d`) |
| `faces_hard/` | Harder made-up face pictures (side views, hats, masks, groups, small faces), key, self-check, and a run of SAM and Glimmer on them | 21 Oct 2026 (`acc634b`, `0013a9d`) |

The repo also had a `README.md`, `requirements.txt` and `.gitignore` from 20 October.

## What these folders are

They are **test tools and test data**. They are not the entry. They measure models on made-up pictures so that
design choices can be made with numbers. All pictures are made up; none shows a real person or real data.

## What is the entry

The entry is the folder `picture_guard/` (with its tests in `tests/`), written from 27 October 2026, after the
hackathon started. It does not import anything from `spike/`, `testset/`, `faces/` or `faces_hard/`.
The test and results tool `pg eval` only **reads** the test sets' `key.json` and picture folders.

Commits after the tag are hackathon work:

    git log --format='%h %ad %s' --date=iso pre-hackathon..HEAD

## Outside code

No code was copied from any other project. Third-party programs and models are listed in `LICENCES.md`.
