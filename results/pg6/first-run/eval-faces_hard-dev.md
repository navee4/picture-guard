## faces_hard, split dev, mode: product (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 36.1 s (both models loaded); container {'glimmer_load_seconds': 10.0, 'sam_load_seconds': 15.1, 'load_seconds': 25.0, 'gpu': 'NVIDIA L40S', 'peak_mib': 21617}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 16 of 60 (26.7%) | 0 / 0 | 100 of 100 | 6 of 44 (6) | 0 | 1.6179 / 3.9635 / 5.5814 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 1.3366 / 3.304 / 4.6407 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 1.7787 / 4.29 / 6.0687 |
| scene | 15 | 3 of 15 (20.0%) | 0 / 0 | 26 of 26 | 1 of 12 (1) | 0 | 2.2853 / 4.1267 / 6.412 |
| side_view | 15 | 11 of 15 (73.3%) | 0 / 0 | 4 of 4 | 1 of 4 (2) | 0 | 1.0711 / 4.1333 / 5.2043 |

Why pictures went whole black: {
"rule 2: the safe copy still shows a private value (check_safe)": 6,
"rule 3: a stage failed, timed out or read almost nothing (read)": 10
}
First not-sure or failing stage: {'check_safe': 6, 'None': 44, 'read': 10} (None = no stage failed).
The day-2 word list would have refused 50 of 50 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
