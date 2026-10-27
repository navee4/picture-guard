## faces_hard, split dev, mode: product (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 32.0 s (both models loaded); container {'glimmer_load_seconds': 9.1, 'sam_load_seconds': 14.7, 'load_seconds': 23.8, 'gpu': 'NVIDIA L40S', 'peak_mib': 21217}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 4 of 60 (6.7%) | 0 / 0 | 114 of 114 | 9 of 56 (8) | 0 | 9.0737 / 4.4368 / 13.5106 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 6.7491 / 4.1467 / 10.8958 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 8.7521 / 5.002 / 13.7541 |
| scene | 15 | 0 of 15 (0.0%) | 0 / 0 | 31 of 31 | 1 of 15 (1) | 0 | 11.7255 / 4.5973 / 16.3229 |
| side_view | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 4 of 13 (4) | 0 | 9.0681 / 4.0013 / 13.0695 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 4
}
First not-sure or failing stage: {'None': 56, 'read': 4} (None = no stage failed).
The day-2 word list would have refused 56 of 56 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
