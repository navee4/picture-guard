## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 41 of 150 (27.3%) | 0 / 837 | 1 of 33 | 1266 of 2210 (1744) | 0 | 9.7954 / 18.5123 / 28.3077 |
| chat | 37 | 17 of 37 (45.9%) | 0 / 110 | none planted | 127 of 414 (272) | 0 | 7.7048 / 19.8524 / 27.5572 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 1 of 33 | 146 of 396 (250) | 0 | 5.3469 / 17.4268 / 22.7737 |
| letter | 37 | 13 of 37 (35.1%) | 0 / 240 | none planted | 181 of 408 (315) | 0 | 14.6514 / 22.3105 / 36.9619 |
| payslip | 38 | 6 of 38 (15.8%) | 0 / 256 | none planted | 812 of 992 (907) | 0 | 11.5514 / 14.5945 / 26.1459 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 38,
"rule 2: the safe copy still shows a private value (check_safe)": 3
}
First not-sure or failing stage: {'None': 109, 'decide': 38, 'check_safe': 3} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 19, by line cover 0; no clear frame in 28 pictures. Frames chosen: {'None': 28, 'px': 3, 'norm1000': 10}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 58 | 0 | 83 (100.0%) | 0 |
| address | 241 | 186 | 0 | 240 (99.6%) | 0 |
| card_number | 35 | 20 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 71 | 0 | 85 (100.0%) | 0 |
| email | 43 | 28 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 28 | 0 | 42 (100.0%) | 0 |
| id_number | 56 | 42 | 0 | 56 (100.0%) | 0 |
| name | 276 | 196 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 35 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 25 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 89 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 59 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
