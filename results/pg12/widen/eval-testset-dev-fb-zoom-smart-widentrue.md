## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 45 of 150 (30.0%) | 0 / 803 | 1 of 32 | 1340 of 2094 (1653) | 0 | 13.4056 / 18.5123 / 31.9179 |
| chat | 37 | 16 of 37 (43.2%) | 0 / 115 | none planted | 189 of 434 (291) | 0 | 9.6562 / 19.8524 / 29.5085 |
| id_card | 38 | 6 of 38 (15.8%) | 0 / 224 | 1 of 32 | 191 of 384 (239) | 0 | 9.08 / 17.4268 / 26.5069 |
| letter | 37 | 13 of 37 (35.1%) | 0 / 240 | none planted | 217 of 408 (315) | 0 | 16.7268 / 22.3105 / 39.0374 |
| payslip | 38 | 10 of 38 (26.3%) | 0 / 224 | none planted | 743 of 868 (808) | 0 | 18.1483 / 14.5945 / 32.7428 |

Why pictures went whole black: {
"rule 2: the safe copy still shows a private value (black_out)": 1,
"rule 1: a private value has no word box (decide)": 40,
"rule 3: a stage failed, timed out or read almost nothing (black_out timeout)": 2,
"rule 2: the safe copy still shows a private value (check_safe)": 2
}
First not-sure or failing stage: {'None': 105, 'black_out': 3, 'decide': 40, 'check_safe': 2} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 2, by line cover 0; no clear frame in 38 pictures. Frames chosen: {'None': 38, 'norm1000': 3}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 54 | 0 | 82 (98.8%) | 0 |
| address | 241 | 176 | 0 | 234 (97.1%) | 0 |
| card_number | 35 | 21 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 66 | 0 | 84 (98.8%) | 0 |
| email | 43 | 28 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 28 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 42 | 0 | 53 (94.6%) | 0 |
| name | 276 | 192 | 0 | 273 (98.9%) | 0 |
| ni_number | 46 | 31 | 0 | 45 (97.8%) | 0 |
| phone | 41 | 26 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 84 | 0 | 110 (97.3%) | 0 |
| sort_code | 84 | 55 | 0 | 83 (98.8%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
