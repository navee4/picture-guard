# Model spike (Modal)

Question: can Meta's open-weights models do the "find" step (Muse Glimmer 30B) and the "mask" step
(SAM 3.1), how fast, in how much memory, under which licence? Research only, no product pipeline.

Rules: models run on Modal only (never on the Mac); ephemeral apps (`modal run`), never `modal deploy`;
spend cap $25 (ledger `results/spend.jsonl`, checked before each GPU run); the hold-out is never run
(`prepare_dev.py` stages dev pictures only, so hold-out pictures never leave the Mac).

Needs: `.venv/bin/modal setup` done once by the builder (no token is ever typed into this repo or a chat);
for SAM 3.1 (gated repo): accept the terms at huggingface.co/facebook/sam3.1 and create the Modal secret
`huggingface` holding `HF_TOKEN` (`modal secret create huggingface HF_TOKEN=...`, typed by the builder).

    .venv/bin/python spike/prepare_dev.py
    sh spike/licences.sh                                           # step 1
    .venv/bin/modal run spike/modal_app.py::download_glimmer       # weights -> Volume pg1-models
    .venv/bin/modal run spike/modal_app.py::glimmer                # steps 2+3 (20 dev pictures, L40S)
    .venv/bin/modal run spike/modal_app.py::tesseract              # step 6 (CPU)
    .venv/bin/modal run spike/modal_app.py::download_sam           # needs secret `huggingface`
    .venv/bin/modal run spike/modal_app.py::sam                    # step 5

Raw outputs: `results/*.json`. Scoring definitions: top of `common.py`.
SAM 3.1 ships as a video checkpoint (`sam3.1_multiplex.pt`, no Transformers port), so single pictures
go through the video predictor as one-frame "videos" (`build_sam3_predictor(version="sam3.1")`).
