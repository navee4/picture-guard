## faces, split dev, mode: product, second Glimmer check on the safe copy ON (55 of 55 pictures scored, version 0.1.0-day1)

Modal: cold start 40.1 s (both models loaded); container {'glimmer_load_seconds': 10.4, 'sam_load_seconds': 15.4, 'load_seconds': 25.8, 'gpu': 'NVIDIA L40S', 'peak_mib': 20901}.

| Type | Pictures | Whole picture black | Not black: values left readable / planted | Not black: face boxes 90%+ covered | Not black: ordinary spans readable (original) | Whole-black pictures: planted values left readable | s/picture Mac / Modal / total |
|---|---|---|---|---|---|---|---|
| all | 55 | 1 of 55 (1.8%) | 0 / 0 | 118 of 118 | 46 of 54 (23) | 0 | 2.0291 / 15.8071 / 17.8362 |
| chat | 18 | 1 of 18 (5.6%) | 0 / 0 | 81 of 81 | 16 of 17 (17) | 0 | 2.1863 / 16.0372 / 18.2236 |
| id_card | 37 | 0 of 37 (0.0%) | 0 / 0 | 37 of 37 | 30 of 37 (6) | 0 | 1.9526 / 15.6951 / 17.6477 |

Why pictures went whole black: {
"rule 2: the safe copy still shows a private value (check_safe)": 1
}
First not-sure or failing stage: {'None': 54, 'check_safe': 1} (None = no stage failed).
The day-2 word list would have refused 55 of 55 pictures that reached `decide`.

Report says whole-black but pixels disagree: 0. Safe copy wrong size: 0. Safe copies with metadata chunks: 0. Pictures that failed to run: 0.
