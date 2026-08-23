#!/usr/bin/env bash
# Experiment B (LLM council confirmation): homo vs hetero, capture vs committed fraction.
set -u
cd "$(dirname "$0")"
PY=../../.venv/bin/python
PS="0.0 0.143 0.286 0.429 0.571"; S=5
R(){ echo "=== $* ==="; timeout 1800 $PY council.py "$@" --ps $PS --seeds $S; }

R --comp homo   --models gpt4o_mini  --out ../results/council_homo_gpt4omini.json
R --comp homo   --models claude_haiku --out ../results/council_homo_haiku.json
R --comp hetero --models gpt4o_mini claude_haiku qwen72b llama70b \
     --out ../results/council_hetero.json
echo "COUNCIL_ALL_DONE"
