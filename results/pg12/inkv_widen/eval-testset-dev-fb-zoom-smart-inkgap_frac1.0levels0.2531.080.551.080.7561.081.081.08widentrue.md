## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 46 of 150 (30.7%) | 0 / 796 | 4 of 31 | 1156 of 2105 (1705) | 0 | 12.5623 / 18.5123 / 31.0745 |
| chat | 37 | 17 of 37 (45.9%) | 0 / 109 | none planted | 117 of 412 (283) | 0 | 8.3817 / 19.8524 / 28.2341 |
| id_card | 38 | 7 of 38 (18.4%) | 0 / 217 | 4 of 31 | 130 of 372 (241) | 0 | 8.9212 / 17.4268 / 26.348 |
| letter | 37 | 14 of 37 (37.8%) | 0 / 230 | none planted | 173 of 391 (313) | 0 | 16.238 / 22.3105 / 38.5485 |
| payslip | 38 | 8 of 38 (21.1%) | 0 / 240 | none planted | 736 of 930 (868) | 0 | 16.695 / 14.5945 / 31.2896 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 40,
"rule 3: a stage failed, timed out or read almost nothing (black_out timeout)": 3,
"rule 2: the safe copy still shows a private value (black_out)": 3
}
First not-sure or failing stage: {'None': 104, 'decide': 40, 'black_out': 6} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 110 values; placed by zoom 2, by line cover 0; no clear frame in 38 pictures. Frames chosen: {'None': 38, 'norm1000': 3}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 54 | 0 | 83 (100.0%) | 0 |
| address | 241 | 176 | 0 | 241 (100.0%) | 0 |
| card_number | 35 | 21 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 66 | 0 | 85 (100.0%) | 0 |
| email | 43 | 26 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 27 | 0 | 42 (100.0%) | 0 |
| id_number | 56 | 41 | 0 | 56 (100.0%) | 0 |
| name | 276 | 188 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 33 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 24 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 84 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 56 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
