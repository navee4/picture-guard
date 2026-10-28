## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 44 of 150 (29.3%) | 0 / 814 | 1 of 32 | 1209 of 2136 (1681) | 0 | 11.7623 / 18.5123 / 30.2746 |
| chat | 37 | 17 of 37 (45.9%) | 0 / 110 | none planted | 127 of 414 (272) | 0 | 9.1789 / 19.8524 / 29.0315 |
| id_card | 38 | 6 of 38 (15.8%) | 0 / 224 | 1 of 32 | 146 of 384 (248) | 0 | 6.906 / 17.4268 / 24.3328 |
| letter | 37 | 13 of 37 (35.1%) | 0 / 240 | none planted | 181 of 408 (315) | 0 | 17.0846 / 22.3105 / 39.3951 |
| payslip | 38 | 8 of 38 (21.1%) | 0 / 240 | none planted | 755 of 930 (846) | 0 | 13.9519 / 14.5945 / 28.5464 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 38,
"rule 2: the safe copy still shows a private value (check_safe)": 6
}
First not-sure or failing stage: {'None': 106, 'decide': 38, 'check_safe': 6} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 19, by line cover 0; no clear frame in 28 pictures. Frames chosen: {'None': 28, 'px': 3, 'norm1000': 10}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 56 | 0 | 83 (100.0%) | 0 |
| address | 241 | 180 | 0 | 240 (99.6%) | 0 |
| card_number | 35 | 20 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 68 | 0 | 85 (100.0%) | 0 |
| email | 43 | 28 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 28 | 0 | 42 (100.0%) | 0 |
| id_number | 56 | 41 | 0 | 56 (100.0%) | 0 |
| name | 276 | 192 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 33 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 25 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 86 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 57 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
