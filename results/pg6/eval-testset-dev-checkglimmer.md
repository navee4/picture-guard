## testset, split dev, mode: product, second Glimmer check on the safe copy ON (150 of 150 pictures scored, version 0.1.0-day1)

Modal: cold start 50.9 s (both models loaded); container {'glimmer_load_seconds': 14.7, 'sam_load_seconds': 15.8, 'load_seconds': 30.5, 'gpu': 'NVIDIA L40S', 'peak_mib': 20896}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 60 of 150 (40.0%) | 0 / 710 | 0 of 33 | 1266 of 1778 (1519) | 0 | 3.705 / 17.7328 / 21.4378 |
| chat | 37 | 30 of 37 (81.1%) | 0 / 35 | none planted | 86 of 140 (124) | 0 | 2.1999 / 13.7114 / 15.9112 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 0 of 33 | 201 of 396 (250) | 0 | 2.7007 / 19.9676 / 22.6684 |
| letter | 37 | 15 of 37 (40.5%) | 0 / 220 | none planted | 212 of 374 (317) | 0 | 5.8814 / 20.3438 / 26.2253 |
| payslip | 38 | 10 of 38 (26.3%) | 0 / 224 | none planted | 767 of 868 (828) | 0 | 4.0556 / 16.8713 / 20.9268 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 57,
"rule 2: the safe copy still shows a private value (check_safe)": 3
}
First not-sure or failing stage: {'None': 90, 'decide': 57, 'check_safe': 3} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 43 | 0 | 82 (98.8%) | 0 |
| address | 241 | 169 | 0 | 235 (97.5%) | 0 |
| card_number | 35 | 16 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 65 | 0 | 84 (98.8%) | 0 |
| email | 43 | 20 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 21 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 36 | 0 | 54 (96.4%) | 0 |
| name | 276 | 170 | 0 | 273 (98.9%) | 0 |
| ni_number | 46 | 28 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 14 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 83 | 0 | 111 (98.2%) | 0 |
| sort_code | 84 | 45 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
