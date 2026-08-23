#!/usr/bin/env bash
# N=64 re-run of the cross-lineage naming-game tipping point.
#
# Why: the published xlin_* runs used N=16 with p in {0, 0.1, 0.2, 0.3, 0.4}. At
# N=16 the realizable committed counts are multiples of 1/16=0.0625, and the ENTIRE
# transition falls between the first two grid points (order parameter 1.00 -> ~0.4
# -> ~0.0). The fitted p_c is therefore a monotone re-encoding of the single mean at
# p=0.1, not a resolved threshold.
#
# Fix: N=64 (granularity 1/64 = 0.0156) with the p grid placed on EXACT multiples of
# 1/64 so round(p*N) never collides, densely bracketing the analytic 0.0979:
#   0/64=0.0000  3/64=0.0469  4/64=0.0625  5/64=0.0781  6/64=0.0938
#   7/64=0.1094  8/64=0.1250  10/64=0.1562 12/64=0.1875
# p=0 is retained because analysis.py estimates the intrinsic-bias term h from the
# p=0 drift. Seeds 3 -> 5; push=both keeps the counterbalancing.
#
# 90 episodes/lineage (2 pushes x 9 p x 5 seeds), t_max_units=30 (6.7x the steps per
# episode vs the N=16 runs). Episodes stop early on consensus or on a settled
# metastable plateau, so most do not reach the horizon.
#
# Run as three provider-grouped streams so the three HF-routed models do not
# contend for the same rate limit:
#   ./run_n64.sh anthropic   # claude_haiku
#   ./run_n64.sh openai      # gpt4o_mini
#   ./run_n64.sh hf          # deepseekv3, llama70b, qwen72b (sequential)
set -u
cd "$(dirname "$0")"
PY=../../.venv/bin/python

N=64
SEEDS=5
TMAX=30
CONC=16
PS="0.0 0.0469 0.0625 0.0781 0.0938 0.1094 0.125 0.1562 0.1875"

R(){
  local key="$1"
  echo "=== $(date -Is) START $key ==="
  $PY run_society.py --comp homo --models "$key" --n $N --ps $PS \
      --seeds $SEEDS --t_max_units $TMAX --push both --concurrency $CONC \
      --out "../results/n64_${key}.json"
  echo "=== $(date -Is) DONE $key (exit $?) ==="
}

case "${1:-all}" in
  anthropic) R claude_haiku ;;
  openai)    R gpt4o_mini ;;
  hf)        R deepseekv3; R llama70b; R qwen72b ;;
  all)       R claude_haiku; R gpt4o_mini; R deepseekv3; R llama70b; R qwen72b ;;
  *) echo "usage: $0 {anthropic|openai|hf|all}"; exit 2 ;;
esac
echo "N64_STREAM_DONE"
