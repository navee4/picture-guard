#!/bin/sh
# Secret scan: detect-secrets over the working tree and over `git log -p` (the whole history).
# Hex "High Entropy" hits that are SHA-256 hashes of made-up pictures (or the git commit hash in results/final/ran-*.json) are expected; the script prints any hit that is not a plain hash line.
set -e
cd "$(dirname "$0")/.."
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
.venv/bin/detect-secrets scan --all-files --exclude-files '(^|/)\.venv/|\.egg-info/|\.git/' > "$TMP/tree.json"
git log -p --all > "$TMP/history.txt"
( cd "$TMP" && "$OLDPWD/.venv/bin/detect-secrets" scan --all-files history.txt > hist.json )
.venv/bin/python - "$TMP" <<'PY'
import collections, json, re, sys
tmp = sys.argv[1]
plain = re.compile(r'(?:"[^"]*":\s*)?"[0-9a-f]{32,64}",?|.*"[a-z_0-9]*sha256[a-z_0-9]*":\s*"[0-9a-f]{32,64}",?|\+?\{"set": "[a-z_]+", "unix_time": \d+, "commit": "[0-9a-f]{40}", "pictures_scored": \d+\}')
def check(name, path, text_of):
    d = json.load(open(path)); types = collections.Counter(); odd = []
    for f, hits in d["results"].items():
        lines = text_of(f)
        for h in hits:
            types[h["type"]] += 1
            if not plain.fullmatch(lines[h["line_number"] - 1].lstrip("+- ").strip()): odd.append((f, h["line_number"], h["type"]))
    print(f"{name}: {sum(types.values())} findings {dict(types)}; not plain hash lines: {len(odd)} {odd[:5]}")
check("working tree", tmp + "/tree.json", lambda f: open(f).read().split("\n"))
check("git history", tmp + "/hist.json", lambda f: open(tmp + "/history.txt").read().split("\n"))
PY
echo "token-shaped strings (hf_, sk-, AKIA, ghp_, xox, private keys) in tree:"; grep -rIEn "hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|BEGIN [A-Z ]*PRIVATE KEY" --exclude-dir=.venv --exclude-dir=.git --exclude=secret_scan.sh . | wc -l
echo "token-shaped strings in history:"; grep -cE "hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|BEGIN [A-Z ]*PRIVATE KEY" "$TMP/history.txt" || true
