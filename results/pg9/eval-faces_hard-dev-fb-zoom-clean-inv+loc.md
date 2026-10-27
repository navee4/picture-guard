## faces_hard, split dev, mode: product (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 37.3 s (both models loaded); container {'glimmer_load_seconds': 10.5, 'sam_load_seconds': 15.1, 'load_seconds': 25.5, 'gpu': 'NVIDIA L40S', 'peak_mib': 21477}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 5 of 60 (8.3%) | 0 / 0 | 113 of 113 | 9 of 55 (8) | 0 | 6.6894 / 4.3222 / 11.0115 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 5.0591 / 4.1467 / 9.2057 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 6.1805 / 5.002 / 11.1825 |
| scene | 15 | 0 of 15 (0.0%) | 0 / 0 | 31 of 31 | 1 of 15 (1) | 0 | 8.2709 / 4.5973 / 12.8683 |
| side_view | 15 | 3 of 15 (20.0%) | 0 / 0 | 12 of 12 | 4 of 12 (4) | 0 | 7.2471 / 3.5427 / 10.7897 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 5
}
First not-sure or failing stage: {'None': 55, 'read': 5} (None = no stage failed).
The day-2 word list would have refused 55 of 55 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
