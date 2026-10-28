## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 42 of 150 (28.0%) | 0 / 830 | 2 of 31 | 1213 of 2192 (1732) | 0 | 11.746 / 18.5123 / 30.2583 |
| chat | 37 | 16 of 37 (43.2%) | 0 / 115 | none planted | 123 of 434 (291) | 0 | 9.1248 / 19.8524 / 28.9772 |
| id_card | 38 | 7 of 38 (18.4%) | 0 / 217 | 2 of 31 | 126 of 372 (237) | 0 | 6.8935 / 17.4268 / 24.3204 |
| letter | 37 | 12 of 37 (32.4%) | 0 / 250 | none planted | 184 of 425 (329) | 0 | 17.1151 / 22.3105 / 39.4256 |
| payslip | 38 | 7 of 38 (18.4%) | 0 / 248 | none planted | 780 of 961 (875) | 0 | 13.9229 / 14.5945 / 28.5174 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 38,
"rule 2: the safe copy still shows a private value (check_safe)": 4
}
First not-sure or failing stage: {'None': 108, 'decide': 38, 'check_safe': 4} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 19, by line cover 0; no clear frame in 28 pictures. Frames chosen: {'None': 28, 'px': 3, 'norm1000': 10}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 58 | 0 | 83 (100.0%) | 0 |
| address | 241 | 182 | 0 | 241 (100.0%) | 0 |
| card_number | 35 | 22 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 68 | 0 | 85 (100.0%) | 0 |
| email | 43 | 28 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 29 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 41 | 0 | 56 (100.0%) | 0 |
| name | 276 | 196 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 34 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 26 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 87 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 59 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
