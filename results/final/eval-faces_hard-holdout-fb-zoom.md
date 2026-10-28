## faces_hard, split holdout, mode: product (20 of 20 pictures scored, version 0.1.0-day1)

Modal: cold start 82.3 s (both models loaded); container {'glimmer_load_seconds': 23.8, 'sam_load_seconds': 23.6, 'load_seconds': 23.8, 'gpu': 'NVIDIA L40S', 'peak_mib': 22383}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 20 | 1 of 20 (5.0%) | 0 / 0 | 33 of 34 | 3 of 19 (4) | 0 | 0.5476 / 4.739 / 5.2867 |
| accessory | 5 | 0 of 5 (0.0%) | 0 / 0 | 4 of 5 | 2 of 5 (3) | 0 | 0.411 / 4.222 / 4.633 |
| group | 5 | 0 of 5 (0.0%) | 0 / 0 | 13 of 13 | 0 of 5 (0) | 0 | 0.5554 / 5.084 / 5.6394 |
| scene | 5 | 0 of 5 (0.0%) | 0 / 0 | 12 of 12 | 1 of 5 (1) | 0 | 0.7326 / 4.76 / 5.4928 |
| side_view | 5 | 1 of 5 (20.0%) | 0 / 0 | 4 of 4 | 0 of 4 (0) | 0 | 0.4916 / 4.89 / 5.3816 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 1
}
First not-sure or failing stage: {'read': 1, 'None': 19} (None = no stage failed).
The day-2 word list would have refused 19 of 19 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
