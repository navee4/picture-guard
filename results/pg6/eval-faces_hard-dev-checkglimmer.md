## faces_hard, split dev, mode: product, second Glimmer check on the safe copy ON (60 of 60 pictures scored, version 0.1.0-day1)

Modal: cold start 40.7 s (both models loaded); container {'glimmer_load_seconds': 10.7, 'sam_load_seconds': 16.2, 'load_seconds': 26.9, 'gpu': 'NVIDIA L40S', 'peak_mib': 21926}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 60 | 6 of 60 (10.0%) | 0 / 0 | 112 of 112 | 9 of 54 (8) | 0 | 2.9118 / 9.03 / 11.9418 |
| accessory | 15 | 2 of 15 (13.3%) | 0 / 0 | 13 of 13 | 2 of 13 (3) | 0 | 2.3277 / 8.2293 / 10.5572 |
| group | 15 | 0 of 15 (0.0%) | 0 / 0 | 57 of 57 | 2 of 15 (0) | 0 | 3.033 / 10.68 / 13.713 |
| scene | 15 | 0 of 15 (0.0%) | 0 / 0 | 31 of 31 | 1 of 15 (1) | 0 | 4.2081 / 9.7693 / 13.9774 |
| side_view | 15 | 4 of 15 (26.7%) | 0 / 0 | 11 of 11 | 4 of 11 (4) | 0 | 2.0784 / 7.4413 / 9.5197 |

Why pictures went whole black: {
"rule 3: a stage failed, timed out or read almost nothing (read)": 6
}
First not-sure or failing stage: {'None': 54, 'read': 6} (None = no stage failed).
The day-2 word list would have refused 54 of 54 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
