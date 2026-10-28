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
    p.add_argument("--no-models", action="store_true", help="do not start the Modal app: names and addresses cannot be judged, so the whole picture goes black")
    p.add_argument("--fallback", default="zoom", choices=["none", "zoom", "line", "zoom+line"], help="place values Tesseract cannot find (see `pg eval --help`)")
    p.add_argument("--ablation", action="store_true", help="MEASUREMENT ONLY, NOT A PRODUCT RESULT: unbuilt stages answer 'nothing found'")
    e = sub.add_parser("eval", help="run pg protect on a test set and measure the safe copies")
    e.add_argument("--set", dest="set_name", required=True, choices=["testset", "faces", "faces_hard"])
    e.add_argument("--split", required=True, help="dev only until day 9; the hold-out is refused")
    e.add_argument("--ablation", action="store_true", help="MEASUREMENT ONLY, NOT A PRODUCT RESULT: unbuilt stages answer 'nothing found'")
    e.add_argument("--check-glimmer", action="store_true", help="also ask Glimmer about the safe copy (extra Glimmer call; off by default)")
    e.add_argument("--fallback", default="zoom", choices=["none", "zoom", "line", "zoom+line"], help="place values Tesseract cannot find: zoom read, line cover, or both in order")
    e.add_argument("--replay", action="store_true", help="reuse the saved day-3 Glimmer/SAM answers (dev pictures); only new calls go to Modal")
    e.add_argument("--cleanups", default=None, help="reader clean-ups to add, comma list of inv,loc,big3,invloc or 'none' (default: the built-in default)")
    e.add_argument("--margin", default=None, help="box margin as FRAC,PX or HFRAC,HPX,VFRAC,VPX (fractions of the text height, minimums in pixels); default is the built-in one")
    e.add_argument("--smart", default=None, help='smart margin as JSON, e.g. {"ink": {"gap_frac": 0.5}, "widen": true} (day 9)')
    e.add_argument("--limit", type=int, default=0, help="first N pictures only (testing the harness)")
    e.add_argument("--results-dir", default=None, help="where the raw JSON and table go (default results/pg6)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "protect":
            from picture_guard.pipeline import protect
            from picture_guard.pipeline import preflight
            preflight(a.input, a.out, a.report)
            if a.ablation or a.no_models:
                rep = protect(a.input, a.out, a.report, ablation=a.ablation)
            else:
                from picture_guard.remote.client import ModalGuard
                with ModalGuard("protect") as guard:
                    print(f"models ready after {guard.cold_start_seconds} s (cold start)", file=sys.stderr)
                    rep = protect(a.input, a.out, a.report, guard=guard, options={"fallback": a.fallback})
            fs = rep["fail_safe"]
            print(f"wrote {a.out} ({'whole picture black' if fs['whole_black'] else str(rep['output']['boxes_filled']) + ' boxes'}; "
                  f"{len(fs['reasons'])} reasons) and {a.report}")
            return 0
        from picture_guard.evaluate import run_eval
        return run_eval(a.set_name, a.split, a.limit, a.results_dir, a.ablation, a.check_glimmer, a.fallback, a.replay, None if a.cleanups is None else tuple(c for c in a.cleanups.split(',') if c and c != 'none'), None if a.margin is None else tuple(float(x) if i % 2 == 0 else int(x) for i, x in enumerate(a.margin.split(','))), None if a.smart is None else __import__('json').loads(a.smart))
    except NotAPictureError as ex:
        print(f"pg: error: {ex}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as ex:
        print(f"pg: error: {ex}", file=sys.stderr)
        return 2
