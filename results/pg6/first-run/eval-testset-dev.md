## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

Modal: cold start 31.8 s (both models loaded); container {'glimmer_load_seconds': 9.2, 'sam_load_seconds': 15.1, 'load_seconds': 24.4, 'gpu': 'NVIDIA L40S', 'peak_mib': 21101}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 76 of 150 (50.7%) | 0 / 582 | 0 of 21 | 1120 of 1530 (1368) | 0 | 1.7641 / 13.6206 / 15.3848 |
| chat | 37 | 28 of 37 (75.7%) | 0 / 45 | none planted | 104 of 180 (155) | 0 | 1.1082 / 11.6022 / 12.7105 |
| id_card | 38 | 17 of 38 (44.7%) | 0 / 147 | 0 of 21 | 116 of 252 (164) | 0 | 1.4279 / 15.3384 / 16.7664 |
| letter | 37 | 18 of 37 (48.6%) | 0 / 190 | none planted | 203 of 323 (290) | 0 | 2.3248 / 15.9811 / 18.3059 |
| payslip | 38 | 13 of 38 (34.2%) | 0 / 200 | none planted | 697 of 775 (759) | 0 | 2.1931 / 11.5697 / 13.7628 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 63,
"rule 2: the safe copy still shows a private value (check_safe)": 13
}
First not-sure or failing stage: {'None': 74, 'decide': 63, 'check_safe': 13} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 38 | 0 | 83 (100.0%) | 0 |
| address | 241 | 133 | 0 | 238 (98.8%) | 0 |
| card_number | 35 | 16 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 50 | 0 | 85 (100.0%) | 0 |
| email | 43 | 18 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 20 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 26 | 0 | 55 (98.2%) | 0 |
| name | 276 | 137 | 0 | 274 (99.3%) | 0 |
| ni_number | 46 | 26 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 14 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 65 | 0 | 112 (99.1%) | 0 |
| sort_code | 84 | 39 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
