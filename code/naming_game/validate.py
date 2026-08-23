"""
Validate the mechanical binary-agreement harness against Xie 2011.

Finite-N signature of the tipping point p_c (the paper, Fig. 1a / Fig. 3):
  - For a FIXED time horizon T_max:
      * p < p_c : system stays in the ACTIVE metastable state, n_B ~ 0.65
                  (escape time ~ exp(alpha*N) exceeds the horizon).
      * p > p_c : system collapses to A-consensus quickly, n_B -> 0.
    So n_B(T_max) vs p drops sharply from ~0.65 to 0 at p_c.
  - Consensus time T_c grows sharply as p decreases toward p_c (exp(N) below).

We reproduce both and estimate p_c from the n_B drop, comparing to 0.0979.
"""
from __future__ import annotations
import argparse, json, os, time
from model import Population


def metastable_nB(n, p, seed, t_max_units, sample_from=0.5):
    """Run for t_max_units; return time-averaged n_B over the tail of the run
    (averaging suppresses fluctuations). Stops early only if consensus reached
    (n_B then = 0 for the rest)."""
    pop = Population(n=n, p_committed=p, seed=seed)
    max_steps = int(t_max_units * n)
    start_avg = int(sample_from * max_steps)
    acc = 0.0
    cnt = 0
    steps = 0
    reached_at = None
    while steps < max_steps:
        pop.step()
        steps += 1
        if steps % n == 0:                      # sample once per time unit
            nb = pop.n_B()
            if steps >= start_avg:
                acc += nb
                cnt += 1
            if pop.consensus_A() and reached_at is None:
                reached_at = steps / n
                # consensus is absorbing: n_B stays 0 -> fill remaining samples
                remaining = (max_steps - steps) // n
                cnt += remaining            # contributes 0 to acc
                break
    mean_nb = acc / cnt if cnt else pop.n_B()
    return mean_nb, reached_at


def consensus_time(n, p, seed, max_time_units):
    pop = Population(n=n, p_committed=p, seed=seed)
    max_steps = int(max_time_units * n)
    steps = 0
    while steps < max_steps:
        pop.step()
        steps += 1
        if steps % n == 0 and pop.consensus_A():
            return steps / n
    return float("inf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--pmin", type=float, default=0.04)
    ap.add_argument("--pmax", type=float, default=0.14)
    ap.add_argument("--pstep", type=float, default=0.01)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--t_max_units", type=float, default=80.0,
                    help="fixed horizon for the metastable n_B measurement")
    ap.add_argument("--out", type=str, default="../results/validation.json")
    args = ap.parse_args()

    p_values = [round(args.pmin + i * args.pstep, 4)
                for i in range(int(round((args.pmax - args.pmin) / args.pstep)) + 1)]
    seeds = list(range(args.seeds))

    print(f"Validation: N={args.n}, horizon={args.t_max_units} time units, "
          f"{args.seeds} seeds")
    print(f"{'p':>7} {'n_B(plateau)':>13} {'frac_consensus':>15} {'<T_c>':>10}")
    t0 = time.time()
    rows = []
    for p in p_values:
        nbs, reached_flags, tcs = [], [], []
        for s in seeds:
            nb, reached_at = metastable_nB(args.n, p, s, args.t_max_units)
            nbs.append(nb)
            reached_flags.append(reached_at is not None)
            tcs.append(reached_at if reached_at is not None else float("inf"))
        mean_nb = sum(nbs) / len(nbs)
        frac = sum(reached_flags) / len(seeds)
        finite_tc = [t for t in tcs if t != float("inf")]
        mean_tc = sum(finite_tc) / len(finite_tc) if finite_tc else float("inf")
        rows.append(dict(p=p, n=args.n, mean_n_B=mean_nb, frac_consensus=frac,
                         mean_t_consensus=mean_tc))
        tc_str = f"{mean_tc:10.1f}" if mean_tc != float('inf') else "       inf"
        print(f"{p:7.3f} {mean_nb:13.3f} {frac:15.0%} {tc_str}")

    # p_c estimate: steepest drop in n_B (midpoint of the largest single-step fall)
    rows_sorted = sorted(rows, key=lambda r: r["p"])
    best_drop, pc = -1.0, None
    for a, b in zip(rows_sorted, rows_sorted[1:]):
        d = a["mean_n_B"] - b["mean_n_B"]
        if d > best_drop:
            best_drop, pc = d, 0.5 * (a["p"] + b["p"])
    dt = time.time() - t0
    print(f"\nEstimated p_c (steepest n_B drop) ~ {pc:.4f}   "
          f"(analytic 0.0979)   [{dt:.1f}s]")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(n=args.n, t_max_units=args.t_max_units,
                                 seeds=args.seeds, analytic_pc=0.0979,
                                 estimated_pc=pc, wall_s=dt), rows=rows),
                  f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
