## faces, split dev, mode: product (55 of 55 pictures scored, version 0.1.0-day1)

Modal: cold start 28.5 s (both models loaded); container {'glimmer_load_seconds': 9.2, 'sam_load_seconds': 13.1, 'load_seconds': 22.4, 'gpu': 'NVIDIA L40S', 'peak_mib': 20897}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 55 | 6 of 55 (10.9%) | 0 / 0 | 105 of 105 | 42 of 49 (21) | 0 | 1.2333 / 8.34 / 9.5733 |
| chat | 18 | 3 of 18 (16.7%) | 0 / 0 | 71 of 71 | 14 of 15 (15) | 0 | 1.349 / 7.9939 / 9.343 |
| id_card | 37 | 3 of 37 (8.1%) | 0 / 0 | 34 of 34 | 28 of 34 (6) | 0 | 1.177 / 8.5084 / 9.6853 |

Why pictures went whole black: {
"rule 2: the safe copy still shows a private value (check_safe)": 6
}
First not-sure or failing stage: {'None': 49, 'check_safe': 6} (None = no stage failed).
The day-2 word list would have refused 55 of 55 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
