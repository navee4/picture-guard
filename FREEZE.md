# Freeze 1 (28 Oct 2026)

From the commit tagged `freeze-1`, the pipeline does not change. Only docs, the demo page text and tests may change.
The sealed hold-out was run once on this exact commit (see `README.md` and `LIMITS.md` for the numbers).

## Frozen settings

| Item | Setting |
|---|---|
| Answer step for the cleaned copy | Muse Spark Standard `muse-spark-1.3` (never a Contributor model); only the cleaned copy is sent |
| Model that finds boxes and faces | Muse Glimmer 30B, GGUF `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` with `mmproj-Muse-Glimmer-30B-Q4_K_M.gguf`, run by llama.cpp (`llama-server`) on a Modal L40S |
| Glimmer sampling | **temperature 0.0, seed 1234** on every request (decide / face count, zoom boxes), set in `SAMPLING` in `picture_guard/remote/container_impl.py`. The server's own start-up flags (`--temp 1.0 --top-p 0.95 --top-k 64`) are only defaults that each request overrides |
| Glimmer other settings | context 32768, 1 slot, `--image-max-tokens 4096`, reasoning strength "low", `max_tokens` 6000 |
| Segmentation | SAM 3.1 (`sam3.1`), same container |
| Reader | Tesseract 5.5.3, page-segmentation modes 6 and 11, reads at 1x, 2x and 2x cleaned (six passes), read in parallel (`PG_OCR_WORKERS`, one thread per read) |
| Box margin | 1.0 x text height, at least 8 px, on all four sides (`MARGIN` in `picture_guard/stages/locate.py`); widen-on-re-read is off by default |
| Fallback for a value with no box | zoom (crop, enlarge, read again) |
| Fail-safe | any "not sure" gives a whole black picture; five rules (see `README.md`); a failing model call is also "not sure" |
| Tool version | `0.1.0-day1` |

## What is not pinned (stated plainly)

- llama.cpp and the SAM 3 code are cloned from their default branches when the Modal image is built (`picture_guard/remote/service.py`). The image Modal built is cached, so the frozen run and the deployed demo use the image built before this commit. If the image is rebuilt, those two could move. (measured: the two live dev runs before the freeze gave byte-identical safe copies; **unknown**: what a rebuilt image would give)
- Same-seed repeatability was measured on this GPU type only (L40S).

## How it was checked before the freeze

Two live runs of the three dev sets at temperature 0: 265 of 265 safe copies byte-identical (`tools/compare_runs.py results/pg15/run1 results/pg15/run2`).
