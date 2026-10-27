"""pg protect <in> --out <safe.png> --report <report.json>   |   pg eval --set <testset|faces|faces_hard> --split dev"""
from __future__ import annotations

import argparse
import sys

from picture_guard.imaging import NotAPictureError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pg", description="Cover private values and faces in a picture, or black out the whole picture.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("protect", help="write a safe copy and a report")
    p.add_argument("input")
    p.add_argument("--out", required=True, help="safe copy (PNG, no metadata)")
    p.add_argument("--report", required=True, help="report.json")
    e = sub.add_parser("eval", help="run pg protect on a test set and measure the safe copies")
    e.add_argument("--set", dest="set_name", required=True, choices=["testset", "faces", "faces_hard"])
    e.add_argument("--split", required=True, help="dev only until day 9; the hold-out is refused")
    e.add_argument("--limit", type=int, default=0, help="first N pictures only (testing the harness)")
    e.add_argument("--results-dir", default=None, help="where the raw JSON and table go (default results/pg4)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "protect":
            from picture_guard.pipeline import protect
            rep = protect(a.input, a.out, a.report)
            fs = rep["fail_safe"]
            print(f"wrote {a.out} ({'whole picture black' if fs['whole_black'] else str(rep['output']['boxes_filled']) + ' boxes'}; "
                  f"{len(fs['reasons'])} reasons) and {a.report}")
            return 0
        from picture_guard.evaluate import run_eval
        return run_eval(a.set_name, a.split, a.limit, a.results_dir)
    except NotAPictureError as ex:
        print(f"pg: error: {ex}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as ex:
        print(f"pg: error: {ex}", file=sys.stderr)
        return 2
