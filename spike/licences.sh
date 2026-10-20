#!/bin/sh
# Step 1 of the spike: fetch the licence files and model-repo metadata (text only, no weights).
# Writes to spike/out/lic/ and prints SHA-256 of each file. Needs no login for the Glimmer repos.
set -e
OUT="$(dirname "$0")/out/lic"; mkdir -p "$OUT"
for f in meta-models/Muse-Glimmer-30B/LICENSE meta-models/Muse-Glimmer-30B/USAGE_POLICY.md \
         meta-models/Muse-Glimmer-30B-GGUF/LICENSE meta-models/Muse-Glimmer-30B-GGUF/USAGE_POLICY.md \
         facebook/sam3.1/LICENSE; do
  curl -sfL -o "$OUT/$(echo "$f" | tr / _)" "https://huggingface.co/$(dirname "$f")/resolve/main/$(basename "$f")"
done
shasum -a 256 "$OUT"/*LICENSE "$OUT"/*USAGE_POLICY.md
for r in meta-models/Muse-Glimmer-30B meta-models/Muse-Glimmer-30B-GGUF facebook/sam3.1; do
  echo "== $r"
  curl -s "https://huggingface.co/api/models/$r" | python3 -c "import sys,json;d=json.load(sys.stdin);print('gated:',d.get('gated'),'| license tag:',[t for t in d['tags'] if t.startswith('license:')])"
  curl -s "https://huggingface.co/api/models/$r/tree/main?recursive=1" | python3 -c "import sys,json;[print(f['path'],f.get('size','')) for f in json.load(sys.stdin) if f['type']=='file' and f.get('size',0)>1e8]"
done
