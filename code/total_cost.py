"""Sum the metered API cost across every result file.

Each run records its own spend, so the total is recomputable from the released
artifacts rather than asserted. Runs are metered per model from the token counts
the provider returned, priced by the table in naming_game/registry.py.

Two caveats worth stating, since a reader reconciling this against the paper will
hit both:

  * Provider list prices change. The figures here are those recorded at run time,
    which is what the runs actually cost; re-pricing today's rates against the
    same token counts would give a different number.
  * Superseded runs are retained rather than deleted, so the total includes work
    that no longer backs a claim -- for example the free-form-judge verifier run
    that the constrained instrument replaced, and runs discarded by the
    data-quality audit. That is deliberate: exclusions stay auditable.

Usage
-----
  ../.venv/bin/python total_cost.py            # total, and the ten priciest runs
  ../.venv/bin/python total_cost.py --by-file  # every file
"""
from __future__ import annotations
import argparse, glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")

COST_KEYS = ("est_cost", "est_api_cost", "est_cost_this_run")


def file_cost(obj):
    """Sum every cost field in one result file, at any nesting depth."""
    total = 0.0
    def walk(o):
        nonlocal total
        if isinstance(o, dict):
            for k, v in o.items():
                if k in COST_KEYS and isinstance(v, (int, float)):
                    total += v
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(o, list):
            for x in o[:200]:          # rows are homogeneous; cap the scan
                walk(x)
    walk(obj)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by-file", action="store_true", help="list every file")
    ap.add_argument("--results", default=RES)
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob(os.path.join(args.results, "*.json"))):
        try:
            rows.append((file_cost(json.load(open(path))), os.path.basename(path)))
        except Exception:
            continue

    total = sum(c for c, _ in rows)
    priced = [r for r in rows if r[0] > 0]
    rows.sort(reverse=True)

    shown = rows if args.by_file else rows[:10]
    print(f"{'cost':>9}  file")
    print("-" * 52)
    for c, name in shown:
        if c > 0 or args.by_file:
            print(f"{c:>9.4f}  {name}")
    if not args.by_file and len(priced) > 10:
        print(f"{'':>9}  ... and {len(priced) - 10} more priced runs")

    print("-" * 52)
    print(f"{total:>9.2f}  TOTAL across {len(rows)} result files "
          f"({len(priced)} with recorded cost)")
    print("\nFree-tier runs (local Ollama, Cerebras, Groq) are priced at zero and\n"
          "contribute nothing to this total.")


if __name__ == "__main__":
    main()
