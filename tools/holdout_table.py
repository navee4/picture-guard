"""Print the hold-out headline table from the saved result files (results/final/eval-*-holdout-*.json). Needs no models and no secret.

    .venv/bin/python tools/holdout_table.py
"""
import glob
import json
import os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "final")


def main():
    for path in sorted(glob.glob(os.path.join(D, "eval-*-holdout-*.json"))):
        j = json.load(open(path))
        print(f"\n{j['set']} (split {j['split']}, {j['pictures_scored']} pictures, tool {j['tool_version']}, {os.path.basename(path)})")
        print("type | pictures | whole black | leaks plain/strict/under50% (planted) | under 90% | faces 90%+ | ordinary text readable (kept)")
        for t, s in j["summary"].items():
            k = s["kept"]
            print(f"{t} | {s['pictures']} | {s['whole_black_pixels']} | {k['values_left_readable']}/{k['values_left_readable_strict']}/{k['values_under_50_pixels']} ({k['planted_values']}) | "
                  f"{k['value_boxes'] - k['value_boxes_90_black']} | {k['face_boxes_90_black']} of {k['face_boxes']} | {k['plain_readable']} of {k['plain_spans']}")


main()
