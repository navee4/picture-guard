## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 42 of 150 (28.0%) | 0 / 831 | 2 of 33 | 1342 of 2165 (1723) | 0 | 9.315 / 18.5123 / 27.8273 |
| chat | 37 | 17 of 37 (45.9%) | 0 / 110 | none planted | 160 of 414 (278) | 0 | 6.7348 / 19.8524 / 26.5873 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 2 of 33 | 183 of 396 (250) | 0 | 5.9087 / 17.4268 / 23.3356 |
| letter | 37 | 12 of 37 (32.4%) | 0 / 250 | none planted | 222 of 425 (329) | 0 | 13.188 / 22.3105 / 35.4985 |
| payslip | 38 | 8 of 38 (21.1%) | 0 / 240 | none planted | 777 of 930 (866) | 0 | 11.4626 / 14.5945 / 26.057 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 40,
"rule 2: the safe copy still shows a private value (check_safe)": 2
}
First not-sure or failing stage: {'None': 108, 'decide': 40, 'check_safe': 2} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 2, by line cover 0; no clear frame in 38 pictures. Frames chosen: {'None': 38, 'norm1000': 3}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 57 | 0 | 82 (98.8%) | 0 |
| address | 241 | 184 | 0 | 239 (99.2%) | 0 |
| card_number | 35 | 21 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 68 | 0 | 84 (98.8%) | 0 |
| email | 43 | 27 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 29 | 0 | 40 (95.2%) | 0 |
| id_number | 56 | 43 | 0 | 54 (96.4%) | 0 |
| name | 276 | 198 | 0 | 275 (99.6%) | 0 |
| ni_number | 46 | 33 | 0 | 45 (97.8%) | 0 |
| phone | 41 | 25 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 88 | 0 | 111 (98.2%) | 0 |
| sort_code | 84 | 58 | 0 | 83 (98.8%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
