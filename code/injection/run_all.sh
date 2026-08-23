#!/usr/bin/env bash
# Experiment A (injection propagation) + C (frontier arm). Chain topology, n=6, 8 seeds.
set -u
cd "$(dirname "$0")"
PY=../../.venv/bin/python
S=8; N=6
R(){ echo "=== $* ==="; timeout 1200 $PY run_inject.py "$@" --n $N --seeds $S --topology chain; }

# --- A: open/mid monocultures (undefended) ---
R --comp homo --models gpt4o_mini   --out ../results/inj_homo_gpt4omini.json
R --comp homo --models claude_haiku  --out ../results/inj_homo_haiku.json
R --comp homo --models qwen72b       --out ../results/inj_homo_qwen72b.json
R --comp homo --models llama70b      --out ../results/inj_homo_llama70b.json
R --comp homo --models deepseekv3    --out ../results/inj_homo_deepseekv3.json
# --- A: heterogeneous (undefended); contains the immune claude_haiku link ---
R --comp hetero --models claude_haiku gpt4o_mini qwen72b llama70b deepseekv3 \
     --out ../results/inj_hetero.json

# --- C: frontier monocultures + frontier diverse (undefended) ---
R --comp homo --models gpt4o          --out ../results/inj_homo_gpt4o.json
R --comp homo --models claude_sonnet  --out ../results/inj_homo_sonnet.json
R --comp hetero --models claude_sonnet gpt4o deepseekv3 qwen235b gptoss120b \
     --out ../results/inj_hetero_frontier.json

# --- defended (hardening): works for strong models, fails for robustly-susceptible ---
R --comp homo --models gpt4o_mini --defended --out ../results/inj_homo_gpt4omini_def.json
R --comp homo --models deepseekv3 --defended --out ../results/inj_homo_deepseekv3_def.json
R --comp hetero --models claude_haiku gpt4o_mini qwen72b llama70b deepseekv3 --defended \
     --out ../results/inj_hetero_def.json

echo "INJECT_ALL_DONE"
