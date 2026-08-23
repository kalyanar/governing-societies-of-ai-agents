"""
Finite-size scaling check: the measured transition midpoint p_c(N) should
converge UP toward the analytic 0.0979 as N grows. Also reports the
active-state plateau n_B (total) which the paper places at ~0.6504.
"""
from __future__ import annotations
import argparse, json, os, time
from model import Population


def run(n, p, seed, t_max_units):
    pop = Population(n=n, p_committed=p, seed=seed)
    max_steps = int(t_max_units * n)
    start_avg = max_steps // 2
    acc_tot, cnt = 0.0, 0
    steps, reached = 0, None
    while steps < max_steps:
        pop.step(); steps += 1
        if steps % n == 0:
            if steps >= start_avg:
                acc_tot += pop.n_B_total(); cnt += 1
            if pop.consensus_A() and reached is None:
                reached = steps / n
                cnt += (max_steps - steps) // n
                break
    return (acc_tot / cnt if cnt else pop.n_B_total()), (reached is not None)


def midpoint_pc(ps, fracs):
    """interpolate p where frac_consensus crosses 0.5"""
    for (p0, f0), (p1, f1) in zip(zip(ps, fracs), zip(ps[1:], fracs[1:])):
        if f0 < 0.5 <= f1:
            if f1 == f0:
                return 0.5 * (p0 + p1)
            return p0 + (0.5 - f0) * (p1 - p0) / (f1 - f0)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[200, 500, 1000, 2000])
    ap.add_argument("--pmin", type=float, default=0.06)
    ap.add_argument("--pmax", type=float, default=0.12)
    ap.add_argument("--pstep", type=float, default=0.005)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--t_max_units", type=float, default=100.0)
    ap.add_argument("--out", type=str, default="../results/finite_size.json")
    args = ap.parse_args()

    p_values = [round(args.pmin + i * args.pstep, 4)
                for i in range(int(round((args.pmax - args.pmin) / args.pstep)) + 1)]
    seeds = list(range(args.seeds))
    t0 = time.time()
    result = {}
    print(f"horizon={args.t_max_units} units, seeds={args.seeds}, "
          f"p grid {p_values[0]}..{p_values[-1]}")
    for n in args.ns:
        fracs, plateaus = [], []
        for p in p_values:
            rs = [run(n, p, s, args.t_max_units) for s in seeds]
            plateaus.append(sum(r[0] for r in rs) / len(rs))
            fracs.append(sum(r[1] for r in rs) / len(seeds))
        pc = midpoint_pc(p_values, fracs)
        # active plateau = mean n_B over sub-critical p (frac_consensus==0)
        sub = [pl for pl, fr in zip(plateaus, fracs) if fr == 0.0]
        plateau = max(plateaus) if not sub else sum(sub) / len(sub)
        result[n] = dict(p=p_values, frac=fracs, plateau=plateaus,
                         pc_midpoint=pc, active_plateau=plateau)
        print(f"  N={n:5d}  p_c(midpoint)={pc if pc is None else round(pc,4)}  "
              f"active n_B plateau~{plateau:.3f}")
    dt = time.time() - t0
    print(f"\nanalytic p_c=0.0979, active n_B=0.6504   [{dt:.1f}s]")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(seeds=args.seeds, t_max_units=args.t_max_units,
                                 wall_s=dt), by_N=result), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
