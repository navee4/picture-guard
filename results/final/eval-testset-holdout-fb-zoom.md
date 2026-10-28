## testset, split holdout, mode: product (50 of 50 pictures scored, version 0.1.0-day1)

Modal: cold start 52.9 s (both models loaded); container {'glimmer_load_seconds': 37.3, 'sam_load_seconds': 35.9, 'load_seconds': 37.3, 'gpu': 'NVIDIA L40S', 'peak_mib': 22140}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 50 | 13 of 50 (26.0%) | 0 / 281 | 0 of 12 | 352 of 709 (579) | 0 | 1.8492 / 18.485 / 20.3341 |
| chat | 13 | 5 of 13 (38.5%) | 0 / 43 | none planted | 46 of 164 (102) | 0 | 1.371 / 18.3585 / 19.7295 |
| id_card | 12 | 0 of 12 (0.0%) | 0 / 84 | 0 of 12 | 35 of 144 (99) | 0 | 0.7909 / 16.5475 / 17.3384 |
| letter | 13 | 4 of 13 (30.8%) | 0 / 90 | none planted | 88 of 153 (133) | 0 | 2.9631 / 21.5292 / 24.4922 |
| payslip | 12 | 4 of 12 (33.3%) | 0 / 64 | none planted | 183 of 248 (245) | 0 | 2.2187 / 17.2617 / 19.4803 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 11,
"rule 2: the safe copy still shows a private value (check_safe)": 2
}
First not-sure or failing stage: {'decide': 11, 'None': 37, 'check_safe': 2} (None = no stage failed).
The day-2 word list would have refused 50 of 50 pictures that reached `decide`.
Fallback (zoom): tried on 12 pictures, 34 values; placed by zoom 13, by line cover 0; no clear frame in 8 pictures. Frames chosen: {'norm1000': 3, 'None': 8, 'px': 1}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 24 | 16 | 0 | 24 (100.0%) | 0 |
| address | 80 | 62 | 0 | 80 (100.0%) | 0 |
| card_number | 16 | 10 | 0 | 16 (100.0%) | 0 |
| dob | 28 | 22 | 0 | 28 (100.0%) | 0 |
| email | 14 | 8 | 0 | 13 (92.9%) | 0 |
| iban | 12 | 9 | 0 | 12 (100.0%) | 0 |
| id_number | 20 | 18 | 0 | 20 (100.0%) | 0 |
| name | 94 | 70 | 0 | 94 (100.0%) | 0 |
| ni_number | 14 | 9 | 0 | 14 (100.0%) | 0 |
| phone | 16 | 12 | 0 | 16 (100.0%) | 0 |
| postcode | 37 | 29 | 0 | 37 (100.0%) | 0 |
| sort_code | 24 | 16 | 0 | 24 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
