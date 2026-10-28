## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 41 of 150 (27.3%) | 0 / 834 | 1 of 33 | 1377 of 2199 (1731) | 0 | 11.2327 / 18.5123 / 29.745 |
| chat | 37 | 16 of 37 (43.2%) | 0 / 115 | none planted | 173 of 434 (291) | 0 | 8.4529 / 19.8524 / 28.3054 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 1 of 33 | 178 of 396 (250) | 0 | 6.0879 / 17.4268 / 23.5148 |
| letter | 37 | 13 of 37 (35.1%) | 0 / 240 | none planted | 214 of 408 (315) | 0 | 16.0334 / 22.3105 / 38.344 |
| payslip | 38 | 7 of 38 (18.4%) | 0 / 248 | none planted | 812 of 961 (875) | 0 | 14.4096 / 14.5945 / 29.0041 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 38,
"rule 2: the safe copy still shows a private value (check_safe)": 3
}
First not-sure or failing stage: {'None': 109, 'decide': 38, 'check_safe': 3} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 19, by line cover 0; no clear frame in 28 pictures. Frames chosen: {'None': 28, 'px': 3, 'norm1000': 10}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 57 | 0 | 83 (100.0%) | 0 |
| address | 241 | 184 | 0 | 239 (99.2%) | 0 |
| card_number | 35 | 21 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 70 | 0 | 85 (100.0%) | 0 |
| email | 43 | 28 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 28 | 0 | 42 (100.0%) | 0 |
| id_number | 56 | 43 | 0 | 56 (100.0%) | 0 |
| name | 276 | 197 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 34 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 26 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 88 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 58 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
