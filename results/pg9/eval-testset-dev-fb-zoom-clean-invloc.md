## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 48 of 150 (32.0%) | 0 / 794 | 0 of 33 | 1428 of 2060 (1681) | 0 | 9.0724 / 19.3402 / 28.4126 |
| chat | 37 | 24 of 37 (64.9%) | 0 / 67 | none planted | 149 of 264 (210) | 0 | 7.4396 / 23.2089 / 30.6485 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 0 of 33 | 200 of 396 (250) | 0 | 5.5539 / 17.4268 / 22.9807 |
| letter | 37 | 13 of 37 (35.1%) | 0 / 240 | none planted | 218 of 408 (315) | 0 | 14.4055 / 22.3105 / 36.716 |
| payslip | 38 | 6 of 38 (15.8%) | 0 / 256 | none planted | 861 of 992 (906) | 0 | 8.9881 / 14.5945 / 23.5825 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 46,
"rule 2: the safe copy still shows a private value (check_safe)": 2
}
First not-sure or failing stage: {'None': 102, 'decide': 46, 'check_safe': 2} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 50 pictures, 123 values; placed by zoom 20, by line cover 0; no clear frame in 34 pictures. Frames chosen: {'None': 34, 'px': 3, 'norm1000': 13}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 50 | 0 | 83 (100.0%) | 0 |
| address | 241 | 182 | 0 | 235 (97.5%) | 0 |
| card_number | 35 | 19 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 69 | 0 | 84 (98.8%) | 0 |
| email | 43 | 25 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 25 | 0 | 42 (100.0%) | 0 |
| id_number | 56 | 39 | 0 | 54 (96.4%) | 0 |
| name | 276 | 190 | 0 | 272 (98.6%) | 0 |
| ni_number | 46 | 33 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 22 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 89 | 0 | 110 (97.3%) | 0 |
| sort_code | 84 | 51 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
