# Licences

What the entry uses, and under which licence. Each line says how I know: **read** (I read the licence file or the
installed package metadata on 27 Oct 2026), or **from memory** (not read; check before relying on it).
This file is not legal advice. A lawyer has not read any of it.

## The entry itself (`picture_guard/`)

Written new from 27 October 2026. No code copied from any other project. **No licence file for our own code yet**:
the builder has to choose one before the repository is made public (open question in the PG-5 results).

## What the entry needs to run

| Item | Version | Licence | How I know |
|---|---|---|---|
| Tesseract OCR (program, called as a separate process) | 5.5.3 (Homebrew) | Apache-2.0 | read: `/opt/homebrew/Cellar/tesseract/5.5.3/LICENSE` and `brew info` |
| Tesseract language data `eng`, `osd` (installed with it) | with 5.5.3 | Apache-2.0 | from memory |
| Pillow | 13.0.0 | MIT-CMU (HPND style) | read: package metadata |
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | read: package metadata |
| Python | 3.12 | PSF licence | from memory |

## Models the entry will call (not built in yet)

| Model | Licence | How I know |
|---|---|---|
| Muse Glimmer 30B (GGUF 4-bit build, run with llama.cpp) | Apache-2.0, plus a separate `USAGE_POLICY.md`. Whether the policy binds on top of Apache-2.0 is **unknown**. Item 1.5 bars processing private information about individuals "unless you have obtained the right to do so in accordance with applicable law". Picture guard hides personal data; that reading is **inferred**, not checked by a lawyer | read in PG-1 (`PG1-RESULTS-prep-1020.md`, `sh spike/licences.sh`) |
| SAM 3.1 (Meta; "SAM License", 19 Nov 2025; gated, access granted) | Custom licence. Royalty-free limited licence to use, copy, modify and distribute; follow privacy and data-protection law; no weapons or military use; credit SAM in published research; terms may change | read in PG-1 |
| Muse Spark through the Meta Model API | **Unknown.** Not read; not used yet (day 3 or later) | unknown |
| llama.cpp (runs Glimmer on Modal) | MIT | from memory |

## Test tools and test data (`spike/`, `testset/`, `faces/`, `faces_hard/`; made before the hackathon; not the entry)

| Item | Licence | How I know |
|---|---|---|
| Stable Diffusion XL base 1.0 (made the test portraits; the portraits are made-up faces, not real people) | CreativeML Open RAIL++-M. Output use allowed; Attachment A bans uses such as harming minors and harassment, which must be passed on if the model is redistributed. We do not redistribute the model | read in PG-2 (`LICENSE.md`, 14,109 bytes, SHA-256 starts `19b6998b569b53ac`) |
| OpenCV YuNet face detector (`face_detection_yunet_2023mar.onnx`, made the face boxes) | MIT | PG-2 results say MIT; **not re-read today** |
| OpenCV (`opencv-python-headless`), PyTorch, diffusers, transformers, accelerate, safetensors, huggingface_hub, einops, pycocotools, psutil, requests (installed on Modal only, for the test tools) | Apache-2.0 or BSD-style | from memory, **not read** |
| Faker (makes made-up names and numbers for the test set) | MIT | read: package metadata |
| Modal client (runs the test tools on Modal) | Apache-2.0 | read: package metadata |
| The test pictures and keys (`testset/key.json`, `faces/key.json`, `faces_hard/key.json`) | Made by us from made-up data. Cards are published test numbers, phones are Ofcom's drama range, emails use reserved example domains. Picture files are git-ignored and rebuilt with the generators | measured in PG-1 to PG-3 |

## Development tools (not shipped)

| Item | Licence | How I know |
|---|---|---|
| detect-secrets 1.5.0 (secret scan) | Apache Software License | read: package metadata |
| uv (installs packages), setuptools (builds the package) | MIT / Apache-2.0 | from memory |

## Every Python package in the Mac `.venv` on 27 Oct 2026 (read from installed metadata)

Command: `.venv/bin/python -c "import importlib.metadata as m; ..."` (the loop is in the PG-5 results file).
`picture_guard/` imports only `pillow` and `numpy`. The rest belong to the test tools and the Modal client.

| Package | Version | Licence stated in metadata |
|---|---|---|
| aiohappyeyeballs | 2.7.1 | Python Software Foundation License |
| aiohttp | 3.14.5 | Apache-2.0 AND MIT |
| aiosignal | 1.4.0 | Apache Software License |
| anyio | 4.15.1 | MIT |
| attrs | 26.1.0 | MIT |
| cbor2 | 6.1.5 | MIT |
| certifi | 2026.10.19 | Mozilla Public License 2.0 (MPL 2.0) |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| detect-secrets | 1.5.0 | Apache Software License |
| Faker | 40.43.0 | MIT License |
| frozenlist | 1.8.0 | Apache-2.0 |
| grpclib | 0.4.9 | BSD License |
| h2 | 4.4.1 | MIT |
| hpack | 4.2.0 | MIT |
| hyperframe | 6.1.0 | MIT License |
| idna | 3.20 | BSD-3-Clause |
| markdown-it-py | 4.2.0 | MIT License |
| mdurl | 0.1.2 | MIT License |
| modal | 1.6.2 | Apache-2.0 |
| multidict | 7.1.0 | Apache-2.0 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pillow | 13.0.0 | MIT-CMU |
| propcache | 0.5.4 | Apache-2.0 |
| protobuf | 7.36.2 | 3-Clause BSD License |
| Pygments | 2.21.0 | BSD-2-Clause |
| PyYAML | 6.0.3 | MIT License |
| requests | 2.34.2 | Apache Software License |
| rich | 15.0.0 | MIT License |
| synchronicity | 0.12.6 | Apache Software License |
| toml | 0.10.2 | MIT License |
| types-certifi | 2021.10.8.3 | Apache Software License |
| types-toml | 0.10.8.20260518 | Apache-2.0 |
| typing_extensions | 4.16.0 | PSF-2.0 |
| urllib3 | 2.8.0 | MIT |
| watchfiles | 1.3.0 | MIT License |
| yarl | 1.25.1 | Apache-2.0 |

A package marked NOT STATED has no licence field in its metadata; none of the packages above is in that state except our own `picture-guard`.
