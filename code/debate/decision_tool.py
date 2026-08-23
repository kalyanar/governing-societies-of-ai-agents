"""
Decision tool: cheap heterogeneous panel vs. one expensive model.

Given the accuracies of cheaper models on a sample of similar questions, their error
correlation rho, the expensive model's accuracy, a verifier quality v in [0,1], and
per-call costs, project the panel's accuracy and recommend a choice.

Theory
------
- Effective independent voters:        N_eff = N / (1 + (N-1)*rho)
- Coverage ceiling (>=1 correct):       C = 1 - (1 - a_bar)^N_eff
  (exchangeable approximation: N models with mean accuracy a_bar behave like N_eff
   independent voters; the chance all are wrong is (1-a_bar)^N_eff)
- Realized panel accuracy with a verifier of quality v (0 = blind majority,
  1 = oracle that always picks a present-correct answer):
      R = a_best + v * (C - a_best)
  v=0 reproduces "majority ~ best single cheap model"; v=1 reaches the coverage ceiling.
- Costs: panel = N * rounds * c_cheap + c_verify ; single = c_expensive.

Recommend the cheap panel iff R >= a_expensive - tol AND cost_panel < cost_expensive.
"""
from __future__ import annotations
import argparse


def coverage_ceiling(accs, rho):
    n = len(accs)
    a_bar = sum(accs) / n
    n_eff = n / (1 + (n - 1) * rho)
    return 1 - (1 - a_bar) ** n_eff, n_eff


def project(accs, rho, v, a_expensive,
            c_cheap=1.0, c_expensive=50.0, rounds=1, c_verify=1.0, tol=0.0):
    a_best = max(accs)
    C, n_eff = coverage_ceiling(accs, rho)
    R = a_best + v * (C - a_best)
    cost_panel = len(accs) * rounds * c_cheap + c_verify
    use_panel = (R >= a_expensive - tol) and (cost_panel < c_expensive)
    return dict(coverage=C, n_eff=n_eff, a_best=a_best, projected_panel=R,
                cost_panel=cost_panel, cost_expensive=c_expensive,
                recommend="cheap panel" if use_panel else "expensive single",
                reason=(f"panel ~{R:.0%} {'>=' if R>=a_expensive-tol else '<'} "
                        f"expensive {a_expensive:.0%}; "
                        f"cost {cost_panel:.0f} {'<' if cost_panel<c_expensive else '>='} "
                        f"{c_expensive:.0f}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accs", type=float, nargs="+", required=True,
                    help="cheap models' accuracies on similar questions, e.g. 0.66 0.65 0.75")
    ap.add_argument("--rho", type=float, default=0.5, help="error correlation")
    ap.add_argument("--v", type=float, default=0.0,
                    help="verifier quality 0..1 (0=blind majority, 1=oracle/strong checker)")
    ap.add_argument("--expensive", type=float, required=True, help="expensive model accuracy")
    ap.add_argument("--c_cheap", type=float, default=1.0)
    ap.add_argument("--c_expensive", type=float, default=50.0)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--tol", type=float, default=0.0)
    a = ap.parse_args()
    r = project(a.accs, a.rho, a.v, a.expensive, a.c_cheap, a.c_expensive, a.rounds,
                tol=a.tol)
    print(f"cheap models: {[f'{x:.0%}' for x in a.accs]}  rho={a.rho}  verifier v={a.v}")
    print(f"  coverage ceiling      : {r['coverage']:.0%}  (N_eff={r['n_eff']:.2f})")
    print(f"  best single cheap     : {r['a_best']:.0%}")
    print(f"  projected panel acc   : {r['projected_panel']:.0%}")
    print(f"  expensive single acc  : {a.expensive:.0%}")
    print(f"  cost: panel {r['cost_panel']:.0f} vs expensive {r['cost_expensive']:.0f}")
    print(f"  >>> RECOMMEND: {r['recommend']}  ({r['reason']})")


if __name__ == "__main__":
    main()
