## testset, split dev, mode: product (150 of 150 pictures scored, version 0.1.0-day1)

Modal: cold start 30.0 s (both models loaded); container {'glimmer_load_seconds': 8.5, 'sam_load_seconds': 13.8, 'load_seconds': 22.4, 'gpu': 'NVIDIA L40S', 'peak_mib': 20903}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 150 | 58 of 150 (38.7%) | 0 / 715 | 0 of 33 | 1297 of 1821 (1555) | 0 | 3.7752 / 14.2757 / 18.0509 |
| chat | 37 | 27 of 37 (73.0%) | 0 / 50 | none planted | 118 of 200 (170) | 0 | 2.5787 / 12.1219 / 14.7005 |
| id_card | 38 | 5 of 38 (13.2%) | 0 / 231 | 0 of 33 | 201 of 396 (250) | 0 | 2.8872 / 15.7326 / 18.6198 |
| letter | 37 | 16 of 37 (43.2%) | 0 / 210 | none planted | 211 of 357 (307) | 0 | 5.5843 / 17.2592 / 22.8435 |
| payslip | 38 | 10 of 38 (26.3%) | 0 / 224 | none planted | 767 of 868 (828) | 0 | 4.0669 / 12.0111 / 16.0779 |

Why pictures went whole black: {
"rule 1: a private value has no word box (decide)": 58
}
First not-sure or failing stage: {'None': 92, 'decide': 58} (None = no stage failed).
The day-2 word list would have refused 150 of 150 pictures that reached `decide`.

| Value type | Planted | Pictures not black: planted | ...of those left readable | Box 90%+ black (all pictures) | Left readable (all pictures) |
|---|---|---|---|---|---|
| account_number | 83 | 43 | 0 | 82 (98.8%) | 0 |
| address | 241 | 167 | 0 | 235 (97.5%) | 0 |
| card_number | 35 | 17 | 0 | 35 (100.0%) | 0 |
| dob | 85 | 65 | 0 | 84 (98.8%) | 0 |
| email | 43 | 20 | 0 | 43 (100.0%) | 0 |
| iban | 42 | 20 | 0 | 41 (97.6%) | 0 |
| id_number | 56 | 39 | 0 | 54 (96.4%) | 0 |
| name | 276 | 172 | 0 | 273 (98.9%) | 0 |
| ni_number | 46 | 29 | 0 | 46 (100.0%) | 0 |
| phone | 41 | 17 | 0 | 41 (100.0%) | 0 |
| postcode | 113 | 82 | 0 | 111 (98.2%) | 0 |
| sort_code | 84 | 44 | 0 | 84 (100.0%) | 0 |

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
