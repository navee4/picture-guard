#!/bin/sh
# Day 9, second round: ink-aware box with the day-8 vertical margin (alone, and with widen on re-read).
cd "$(dirname "$0")/.." || exit 1
export OMP_THREAD_LIMIT=1
run() {  # name, json, extra args
  for s in testset faces faces_hard; do
    d=results/pg12/$1; mkdir -p $d/debug; cp results/pg11/final/debug/boxes-$s.jsonl $d/debug/
    .venv/bin/pg eval --set $s --split dev --replay --fallback zoom --smart "$2" $3 --results-dir $d > $d/log-$s.txt 2>&1 &
  done
}
run inkv '{"ink":{"gap_frac":1.0}}' "--margin 0.25,3,1.0,8"
run inkv_widen '{"ink":{"gap_frac":1.0},"widen":true,"levels":[[0.25,3,1.0,8],[0.5,5,1.0,8],[0.75,6,1.0,8],[1.0,8,1.0,8]]}' ""
wait
