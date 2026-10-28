## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

Modal: cold start 22.2 s (both models loaded); container {'glimmer_load_seconds': 15.4, 'sam_load_seconds': 15.2, 'load_seconds': 15.4, 'gpu': 'NVIDIA L40S', 'peak_mib': 20661}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 40 of 150 (26.7%) | 0 / 850 | 2 of 31 | 1272 of 2250 (1782) | 0 | 1.2677 / 18.6349 / 19.9026 |
| chat | 37 | 17 of 37 (45.9%) | 0 / 109 | none planted | 119 of 413 (279) | 0 | 1.1014 / 20.2384 / 21.3398 |
| id_card | 38 | 7 of 38 (18.4%) | 0 / 217 | 2 of 31 | 121 of 372 (235) | 0 | 0.5675 / 16.6966 / 17.2641 |
| letter | 37 | 11 of 37 (29.7%) | 0 / 260 | none planted | 197 of 442 (332) | 0 | 2.1111 / 23.5295 / 25.6406 |
| payslip | 38 | 5 of 38 (13.2%) | 0 / 264 | none planted | 835 of 1023 (936) | 0 | 1.3084 / 14.2463 / 15.5547 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 37,
"rule 2: the safe copy still shows a private value (check_safe)": 3
}
First not-sure or failing stage: {'None': 110, 'decide': 37, 'check_safe': 3} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.
Fallback (zoom): tried on 41 pictures, 108 values; placed by zoom 15, by line cover 0; no clear frame in 27 pictures. Frames chosen: {'norm1000': 11, 'px': 3, 'None': 27}.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 59 | 0 | 83 (100.0%) | 0 |
| address | 241 | 187 | 0 | 241 (100.0%) | 0 |
| card_number | 35 | 21 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 70 | 0 | 85 (100.0%) | 0 |
| email | 43 | 29 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 30 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 40 | 0 | 56 (100.0%) | 0 |
| name | 276 | 200 | 0 | 276 (100.0%) | 0 |
| ni_number | 46 | 36 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 27 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 90 | 0 | 113 (100.0%) | 0 |
| sort_code | 84 | 61 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
