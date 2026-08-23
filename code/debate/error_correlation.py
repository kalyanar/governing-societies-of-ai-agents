"""
The mechanistic heart of RQ1: among EQUALLY-COMPETENT models, are their errors
DECORRELATED? Heterogeneity only helps a deliberating panel if different models
fail on DIFFERENT questions (low error correlation). If matched-accuracy models
make the SAME mistakes (high rho), diversity buys nothing.

Takes homogeneous run files (one per model, same question set) and computes:
  - per-model accuracy (the competence to match on)
  - pairwise error correlation rho (do they fail together?)
  - effective independent voters N_eff = N / (1 + (N-1) * mean_rho)
    (same decorrelation framework as the naming-game N_eff)

Usage: python error_correlation.py model1.json model2.json ...
"""
import json, sys, itertools
from collections import defaultdict
import numpy as np


def model_correctness(path):
    """Return (label, {question_id: mean correctness over seeds})."""
    d = json.load(open(path))
    label = d["meta"]["models"][0] if d["meta"].get("models") else path
    by_q = defaultdict(list)
    for r in d["rows"]:
        if r.get("p", 0.0) == 0.0:                 # clean (no adversary)
            by_q[r["question_id"]].append(1.0 if r["honest_correct"] else 0.0)
    return label, {q: float(np.mean(v)) for q, v in by_q.items()}


def main():
    models = [model_correctness(p) for p in sys.argv[1:]]
    # common question set
    qs = set.intersection(*[set(m[1]) for m in models]) if models else set()
    qs = sorted(qs)
    if not qs:
        print("no common questions across the given files"); return
    labels = [m[0] for m in models]
    M = np.array([[m[1][q] for q in qs] for m in models])   # models x questions (acc)
    acc = M.mean(axis=1)

    print(f"Common questions: {len(qs)}   models: {len(models)}\n")
    print("Per-model accuracy (the competence to match on):")
    for l, a in zip(labels, acc):
        print(f"  {l:16} {a:.0%}")

    # error vectors (1 = wrong) and pairwise correlation
    E = 1.0 - M
    print("\nPairwise ERROR correlation rho (low = decorrelated = diversity helps):")
    rhos = []
    for i, j in itertools.combinations(range(len(models)), 2):
        a, b = E[i], E[j]
        if a.std() < 1e-9 or b.std() < 1e-9:
            r = float("nan")
        else:
            r = float(np.corrcoef(a, b)[0, 1])
        rhos.append(r)
        print(f"  {labels[i]:14} vs {labels[j]:14} rho={r:+.2f}")
    valid = [r for r in rhos if r == r]
    mean_rho = float(np.mean(valid)) if valid else float("nan")
    N = len(models)
    n_eff = N / (1 + (N - 1) * mean_rho) if mean_rho == mean_rho else float("nan")
    print(f"\nmean error-correlation rho = {mean_rho:+.2f}")
    print(f"effective independent voters N_eff = {n_eff:.2f} of {N}  "
          f"(N_eff -> N as errors decorrelate)")
    # how often is at least one model right (diversity ceiling) vs all-wrong (shared blind spot)
    any_right = (M.max(axis=0) > 0.5).mean()
    all_wrong = (M.max(axis=0) <= 0.5).mean()
    best_single = acc.max()
    print(f"\nat-least-one-model-right: {any_right:.0%}  (diversity ceiling)")
    print(f"best single model:        {best_single:.0%}")
    print(f"-> headroom diversity could capture: {any_right - best_single:+.0%} "
          f"(all-models-wrong shared blind spots: {all_wrong:.0%})")


if __name__ == "__main__":
    main()
