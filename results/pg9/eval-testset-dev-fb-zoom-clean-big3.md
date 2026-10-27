## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 52 of 150 (34.7%) | 0 / 761 | 0 of 33 | 1406 of 1974 (1660) | 0 | 10.2819 / 19.8202 / 30.102 |
| chat | 37 | 25 of 37 (67.6%) | 0 / 62 | none planted | 132 of 243 (189) | 0 | 7.6009 / 23.4786 / 31.0795 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 0 of 33 | 201 of 396 (250) | 0 | 5.3101 / 17.4268 / 22.7368 |
| letter | 37 | 15 of 37 (40.5%) | 0 / 220 | none planted | 215 of 374 (323) | 0 | 18.9027 / 22.833 / 41.7356 |
| payslip | 38 | 7 of 38 (18.4%) | 0 / 248 | none planted | 858 of 961 (898) | 0 | 9.4701 / 15.7179 / 25.1879 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 51,
"rule 3: a stage failed, timed out or read almost nothing (read error)": 1
}
First not-sure or failing stage: {'None': 98, 'decide': 51, 'read': 1} (None = no stage failed).
The day-2 word list would have refused 149 of 149 pictures that reached `decide`.
Fallback (zoom): tried on 56 pictures, 184 values; placed by zoom 59, by line cover 0; no clear frame in 38 pictures. Frames chosen: {'norm1000': 14, 'None': 38, 'px': 4}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 48 | 0 | 82 (98.8%) | 0 |
| address | 241 | 175 | 0 | 235 (97.5%) | 0 |
| card_number | 35 | 18 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 68 | 0 | 84 (98.8%) | 0 |
| email | 43 | 22 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 23 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 39 | 0 | 54 (96.4%) | 0 |
| name | 276 | 181 | 0 | 272 (98.6%) | 0 |
| ni_number | 46 | 32 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 20 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 86 | 0 | 111 (98.2%) | 0 |
| sort_code | 84 | 49 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
