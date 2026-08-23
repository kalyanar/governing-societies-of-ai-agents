"""Per-model injection-susceptibility probe: one call per model, undefended vs defended.
Sends patient-zero's board once and checks whether the model emits the marker."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import make_backend, key_available  # noqa
from backends import ModelMeter  # noqa
from inject import (PATIENT_ZERO_NOTE, round_prompt, is_infected,
                    SYSTEM_UNDEFENDED, SYSTEM_DEFENDED)  # noqa

MODELS = sys.argv[1:] or ["gpt4o_mini", "gpt4o", "claude_haiku", "qwen72b",
                          "llama70b", "deepseekv3", "gemma2_2b", "qwen25_3b",
                          "llama3b"]
meter = ModelMeter()
board = [PATIENT_ZERO_NOTE]
print(f"{'model':14} {'undef':>6} {'def':>6}   sample (undefended)")
rows = []
for k in MODELS:
    ok, info = key_available(k)
    if not ok:
        print(f"{k:14}  skip ({info})"); continue
    b = make_backend(k)
    ru = b.generate(round_prompt(board), system=SYSTEM_UNDEFENDED, max_tokens=120, temperature=0.3)
    rd = b.generate(round_prompt(board), system=SYSTEM_DEFENDED, max_tokens=120, temperature=0.3)
    meter.add(k, ru); meter.add(k, rd)
    iu, idf = is_infected(ru.text), is_infected(rd.text)
    rows.append(dict(model=k, undefended=iu, defended=idf, sample=ru.text.strip()[:80]))
    print(f"{k:14} {('YES' if iu else 'no'):>6} {('YES' if idf else 'no'):>6}   {ru.text.strip()[:70]!r}")

json.dump(rows, open(os.path.join(os.path.dirname(__file__), "..", "results", "inject_probe.json"), "w"), indent=2)
print("\nsusceptible (undefended):", [r["model"] for r in rows if r["undefended"]])
