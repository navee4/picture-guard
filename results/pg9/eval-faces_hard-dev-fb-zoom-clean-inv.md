## faces_hard, split dev, mode: product (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 32.3 s (both models loaded); container {'glimmer_load_seconds': 8.6, 'sam_load_seconds': 13.5, 'load_seconds': 22.1, 'gpu': 'NVIDIA L40S', 'peak_mib': 22384}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 5 of 60 (8.3%) | 0 / 0 | 113 of 113 | 9 of 55 (8) | 0 | 5.3117 / 4.322 / 9.6338 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 3.7959 / 4.1467 / 7.9426 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 4.9971 / 5.002 / 9.9992 |
| scene | 15 | 0 of 15 (0.0%) | 0 / 0 | 31 of 31 | 1 of 15 (1) | 0 | 6.1977 / 4.5973 / 10.795 |
| side_view | 15 | 3 of 15 (20.0%) | 0 / 0 | 12 of 12 | 4 of 12 (4) | 0 | 6.2562 / 3.542 / 9.7983 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 5
}
First not-sure or failing stage: {'None': 55, 'read': 5} (None = no stage failed).
The day-2 word list would have refused 55 of 55 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
