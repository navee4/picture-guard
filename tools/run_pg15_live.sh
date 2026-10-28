#!/bin/sh
# PG-15 part 1: the product LIVE (fresh Glimmer and SAM calls, temperature 0, seed 1234) on the three dev sets, one process (one GPU app) per set.
# Usage: sh tools/run_pg15_live.sh run1   -> results/pg15/run1
cd "$(dirname "$0")/.." || exit 1
export OMP_THREAD_LIMIT=1 PG_SPEND_CAP_USD=${PG_SPEND_CAP_USD:-24.4}
d=results/pg15/$1; mkdir -p $d
for s in testset faces faces_hard; do
  .venv/bin/pg eval --set $s --split dev --fallback zoom --results-dir $d > $d/log-$s.txt 2>&1 &
done
wait
