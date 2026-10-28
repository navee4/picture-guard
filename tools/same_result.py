"""The same-result guard (PG-14): replay the dev sets and write the SHA-256 of every safe copy, so a speed change can be compared byte for byte.
Usage: python tools/same_result.py LABEL [sets...]   -> results/pg14/manifest-LABEL.json
       python tools/same_result.py --compare A B     -> lists every picture whose safe copy (or whole-black flag) differs
Replay only: saved Glimmer/SAM answers, no Modal call (a picture with no saved answer is reported, not run)."""
import json
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
sys.path.insert(0, str(ROOT))


def run_chunk(args):
    set_name, files = args
    from picture_guard import imaging
    from picture_guard.evaluate import SETS, _replay_guard
    from picture_guard.pipeline import protect
    base = SETS[set_name]
    key = json.loads((base / "key.json").read_text())
    entries = [e for e in key["images"] if e["split"] == "dev" and e["file"] in files]
    out = {}
    scratch = Path(tempfile.mkdtemp(prefix="pg-same-"))
    (scratch / "debug").mkdir()
    src = ROOT / "results" / "pg11" / "final" / "debug" / f"boxes-{set_name}.jsonl"
    if src.exists():  # only the sets that needed the zoom fallback have a box cache
        (scratch / "debug" / src.name).write_text(src.read_text())
    guard = _replay_guard(set_name, entries, base, scratch, "same-result")
    guard.offline = True  # replay only: never start Modal
    with guard as g:
        for e in entries:
            safe, rep = scratch / "s.png", scratch / "r.json"
            report = protect(base / "images" / e["file"], safe, rep, guard=g, options={"fallback": "zoom"})
            out[e["file"]] = {"sha256": imaging.sha256_file(safe), "whole_black": report["fail_safe"]["whole_black"],
                              "reasons": [r.split(":")[0] + ":" + r.split(":")[1] for r in report["fail_safe"]["reasons"]],
                              "live_calls": getattr(g, "live_calls", 0)}
    return set_name, out


def main(label, sets, workers=14):
    from picture_guard.evaluate import SETS
    jobs = []
    for s in sets:
        key = json.loads((SETS[s] / "key.json").read_text())
        files = [e["file"] for e in key["images"] if e["split"] == "dev"]
        n = max(1, len(files) // (workers * 2 // len(sets) or 1))
        jobs += [(s, files[i:i + n]) for i in range(0, len(files), n)]
    res = {s: {} for s in sets}
    with ProcessPoolExecutor(workers) as ex:
        for s, out in ex.map(run_chunk, jobs):
            res[s].update(out)
    live = sum(v["live_calls"] for s in res.values() for v in s.values())
    d = ROOT / "results" / "pg14"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"manifest-{label}.json").write_text(json.dumps({"label": label, "sets": res}, indent=1, sort_keys=True))
    print(label, {s: len(v) for s, v in res.items()}, "whole black:", {s: sum(x["whole_black"] for x in v.values()) for s, v in res.items()}, "live calls:", live)


def compare(a, b):
    A, B = (json.loads((ROOT / "results" / "pg14" / f"manifest-{x}.json").read_text())["sets"] for x in (a, b))
    diffs = [(s, f) for s in A for f in A[s] if A[s][f]["sha256"] != B.get(s, {}).get(f, {}).get("sha256") or A[s][f]["whole_black"] != B.get(s, {}).get(f, {}).get("whole_black")]
    n = sum(len(v) for v in A.values())
    print(f"{n} pictures compared; {len(diffs)} differ" + (": " + ", ".join(f"{s}/{f}" for s, f in diffs[:20]) if diffs else " (byte-identical)"))
    return 1 if diffs else 0


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    main(sys.argv[1], sys.argv[2:] or ["testset", "faces", "faces_hard"])
