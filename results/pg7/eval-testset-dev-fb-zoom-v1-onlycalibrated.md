## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

Modal: cold start 38.2 s (both models loaded); container {'glimmer_load_seconds': 10.0, 'sam_load_seconds': 15.1, 'load_seconds': 25.1, 'gpu': 'NVIDIA L40S', 'peak_mib': 20901}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 56 of 150 (37.3%) | 0 / 729 | 0 of 33 | 1335 of 1873 (1599) | 0 | 4.1582 / 20.205 / 24.3632 |
| chat | 37 | 26 of 37 (70.3%) | 0 / 56 | none planted | 125 of 221 (183) | 0 | 2.7189 / 23.4786 / 26.1976 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 0 of 33 | 201 of 396 (250) | 0 | 2.9363 / 17.4268 / 20.3632 |
| letter | 37 | 16 of 37 (43.2%) | 0 / 210 | none planted | 211 of 357 (307) | 0 | 5.525 / 24.393 / 29.918 |
| payslip | 38 | 9 of 38 (23.7%) | 0 / 232 | none planted | 798 of 899 (859) | 0 | 5.4505 / 15.7179 / 21.1684 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 56
}
First not-sure or failing stage: {'None': 94, 'decide': 56} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 58 pictures, 197 values; placed by zoom 4, by line cover 0; no clear frame in 41 pictures. Frames chosen: {'norm1000': 14, 'None': 41, 'px': 3}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 45 | 0 | 82 (98.8%) | 0 |
| address | 241 | 169 | 0 | 235 (97.5%) | 0 |
| card_number | 35 | 17 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 66 | 0 | 84 (98.8%) | 0 |
| email | 43 | 20 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 21 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 39 | 0 | 54 (96.4%) | 0 |
| name | 276 | 175 | 0 | 273 (98.9%) | 0 |
| ni_number | 46 | 30 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 18 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 83 | 0 | 111 (98.2%) | 0 |
| sort_code | 84 | 46 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
