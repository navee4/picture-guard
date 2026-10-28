#!/bin/sh
# Day 9: replay the dev sets with each smart-margin setting, one process per (setting, set). Usage: sh tools/run_pg12.sh
cd "$(dirname "$0")/.." || exit 1
export OMP_THREAD_LIMIT=1
run() {  # name, json
  for s in testset faces faces_hard; do
    d=results/pg12/$1; mkdir -p $d/debug; cp results/pg11/final/debug/boxes-$s.jsonl $d/debug/
    .venv/bin/pg eval --set $s --split dev --replay --fallback zoom --smart "$2" --results-dir $d > $d/log-$s.txt 2>&1 &
  done
}
run ink025 '{"ink":{"gap_frac":0.25}}'
run ink05 '{"ink":{"gap_frac":0.5}}'
run ink10 '{"ink":{"gap_frac":1.0}}'
run widen '{"widen":true}'
wait
