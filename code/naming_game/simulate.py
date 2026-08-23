"""
Driver for the binary-agreement model: run to consensus, sweep committed
fraction p, locate the tipping point p_c, and check consensus-time scaling.

Mechanical (deterministic) backend only here — this is the validation harness
that must reproduce the analytic p_c ~ 0.0979 before any LLM is plugged in.
"""
from __future__ import annotations
import argparse, json, math, time
from dataclasses import dataclass
from typing import Optional

from model import Population, A

# unit of time in the paper = N speaker-listener interactions (one per agent on avg)
def run_to_consensus(n: int, p: float, seed: int,
                     max_time_units: float = 5000.0,
                     adjacency: Optional[list] = None,
                     update_fn=None):
    """Run until all agents hold A, or until max_time_units * N steps elapse.

    Returns dict: reached (bool), t_consensus (in time units = steps/N),
    final n_B, steps.
    """
    pop = Population(n=n, p_committed=p, seed=seed, adjacency=adjacency)
    # If committed fraction already forces it, or no uncommitted agents:
    max_steps = int(max_time_units * n)
    steps = 0
    while steps < max_steps:
        pop.step(update_fn=update_fn)
        steps += 1
        # check consensus every N steps (one time unit) to keep it cheap
        if steps % n == 0:
            if pop.consensus_A():
                return dict(reached=True, t_consensus=steps / n,
                            n_B=pop.n_B(), steps=steps)
    return dict(reached=False, t_consensus=float("inf"),
                n_B=pop.n_B(), steps=steps)


def sweep_p(n: int, p_values, seeds, max_time_units=5000.0, adjacency=None,
            update_fn=None, verbose=True):
    """For each p, run `seeds` trials; report fraction reaching A-consensus and
    mean consensus time among those that reached it."""
    rows = []
    for p in p_values:
        reached = 0
        times = []
        nb = []
        for s in seeds:
            r = run_to_consensus(n, p, s, max_time_units, adjacency, update_fn)
            reached += int(r["reached"])
            if r["reached"]:
                times.append(r["t_consensus"])
            nb.append(r["n_B"])
        frac = reached / len(seeds)
        mean_t = sum(times) / len(times) if times else float("inf")
        mean_nb = sum(nb) / len(nb)
        rows.append(dict(p=p, n=n, frac_consensus=frac, mean_t_consensus=mean_t,
                         mean_n_B=mean_nb, n_seeds=len(seeds)))
        if verbose:
            print(f"  p={p:.3f}  consensus={frac:5.0%}  "
                  f"<T_c>={mean_t:8.2f}  <n_B>={mean_nb:.3f}")
    return rows


def estimate_pc(rows):
    """Crude p_c estimate: midpoint between the largest p with frac<0.5 and the
    smallest p with frac>=0.5. (Real analysis uses change-point / FSS later.)"""
    rows = sorted(rows, key=lambda r: r["p"])
    below = [r for r in rows if r["frac_consensus"] < 0.5]
    above = [r for r in rows if r["frac_consensus"] >= 0.5]
    if not below or not above:
        return None
    return 0.5 * (below[-1]["p"] + above[0]["p"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--pmin", type=float, default=0.02)
    ap.add_argument("--pmax", type=float, default=0.16)
    ap.add_argument("--pstep", type=float, default=0.01)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--max_time_units", type=float, default=3000.0)
    ap.add_argument("--out", type=str, default="../results/mechanical_sweep.json")
    args = ap.parse_args()

    p_values = [round(args.pmin + i * args.pstep, 4)
                for i in range(int(round((args.pmax - args.pmin) / args.pstep)) + 1)]
    seeds = list(range(args.seeds))

    print(f"Binary-agreement mechanical sweep: N={args.n}, "
          f"p in [{args.pmin},{args.pmax}] step {args.pstep}, {args.seeds} seeds")
    t0 = time.time()
    rows = sweep_p(args.n, p_values, seeds, args.max_time_units)
    dt = time.time() - t0
    pc = estimate_pc(rows)
    print(f"\nEstimated p_c ~ {pc}   (analytic 0.0979)   [{dt:.1f}s]")

    out = dict(meta=dict(n=args.n, seeds=args.seeds,
                         max_time_units=args.max_time_units,
                         analytic_pc=0.0979, estimated_pc=pc, wall_s=dt),
               rows=rows)
    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
