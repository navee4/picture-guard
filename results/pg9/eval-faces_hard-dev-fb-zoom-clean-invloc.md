## faces_hard, split dev, mode: product (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 53.5 s (both models loaded); container {'glimmer_load_seconds': 10.3, 'sam_load_seconds': 15.1, 'load_seconds': 25.4, 'gpu': 'NVIDIA L40S', 'peak_mib': 20901}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 3 of 60 (5.0%) | 0 / 0 | 115 of 115 | 9 of 57 (8) | 0 | 5.7237 / 4.4358 / 10.1595 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 3.9845 / 4.1467 / 8.1311 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 4.8722 / 5.002 / 9.8742 |
| scene | 15 | 0 of 15 (0.0%) | 0 / 0 | 31 of 31 | 1 of 15 (1) | 0 | 6.447 / 4.5973 / 11.0443 |
| side_view | 15 | 1 of 15 (6.7%) | 0 / 0 | 14 of 14 | 4 of 14 (4) | 0 | 7.5912 / 3.9973 / 11.5885 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 3
}
First not-sure or failing stage: {'None': 57, 'read': 3} (None = no stage failed).
The day-2 word list would have refused 57 of 57 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
