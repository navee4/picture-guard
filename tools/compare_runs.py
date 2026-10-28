"""Compare two live eval result directories: safe-copy hashes and headline numbers.

    .venv/bin/python tools/compare_runs.py results/pg15/run1 results/pg15/run2
"""
import glob
import json
import os
import sys


def load(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, "eval-*.json"))):
        j = json.load(open(p))
        out[j["set"]] = j
    return out


def main(a, b):
    A, B = load(a), load(b)
    same = diff = 0
    for s in sorted(A):
        pa = {p["file"]: p for p in A[s]["pictures"]}
        pb = {p["file"]: p for p in B[s]["pictures"]}
        bad = [f for f in pa if pa[f].get("safe_sha256") != pb.get(f, {}).get("safe_sha256")]
        same += len(pa) - len(bad)
        diff += len(bad)
        print(s, "pictures", len(pa), "differ", len(bad), bad[:10])
    print("byte-identical", same, "of", same + diff)
    for name, R in (("A", A), ("B", B)):
        for s in sorted(R):
            k = R[s]["summary"]["all"]["kept"]
            print(name, s, "black", R[s]["summary"]["all"]["whole_black_pixels"], "leaks", k["values_left_readable"],
                  "strict", k["values_left_readable_strict"], "under90", k["value_boxes"] - k["value_boxes_90_black"],
                  "faces", k["face_boxes_90_black"], "/", k["face_boxes"], "readable", k["plain_readable"], "/", k["plain_readable_on_original"])


main(*sys.argv[1:3])
