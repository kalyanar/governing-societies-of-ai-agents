"""
Run LLM-backed binary-agreement episodes and sweep committed fraction p.
Meters tokens + latency for cost projection. Pilot-scale by default.
"""
from __future__ import annotations
import argparse, json, os, time
from model import Population
from llm_agent import make_llm_update, Meter, ping


def run_episode(n, p, seed, model, t_max_units, meter, rule_guided=False,
                temperature=0.7):
    pop = Population(n=n, p_committed=p, seed=seed)
    update_fn = make_llm_update(model, meter, rule_guided=rule_guided,
                                temperature=temperature)
    max_steps = int(t_max_units * n)
    steps, reached_at, outcome = 0, None, None
    traj = []
    while steps < max_steps:
        pop.step(update_fn=update_fn)
        steps += 1
        if steps % n == 0:
            traj.append(round(pop.n_B_total(), 3))
            c = pop.consensus()
            if c is not None:
                reached_at, outcome = steps / n, c
                break
    return dict(reached=outcome == "A",            # tipped to committed opinion
                consensus=outcome,                  # 'A','B', or None (no consensus)
                t_consensus=reached_at,
                final_n_B=pop.n_B_total(), steps=steps, traj=traj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--model", type=str, default="llama3.2:3b")
    ap.add_argument("--ps", type=float, nargs="+",
                    default=[0.0, 0.10, 0.20, 0.30])
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--t_max_units", type=float, default=40.0)
    ap.add_argument("--rule_guided", action="store_true")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out", type=str, default="../results/llm_pilot.json")
    args = ap.parse_args()

    if not ping(args.model):
        raise SystemExit(f"ollama model {args.model} not reachable")

    meter = Meter()
    seeds = list(range(args.seeds))
    print(f"LLM pilot: model={args.model} N={args.n} horizon={args.t_max_units} "
          f"ps={args.ps} seeds={args.seeds} rule_guided={args.rule_guided}")
    t0 = time.time()
    rows = []
    for p in args.ps:
        for s in seeds:
            te = time.time()
            r = run_episode(args.n, p, s, args.model, args.t_max_units, meter,
                            args.rule_guided, args.temperature)
            r.update(p=p, seed=s, episode_s=round(time.time() - te, 1))
            rows.append(r)
            oc = r["consensus"] or "none"
            tc = f"@{r['t_consensus']:.1f}" if r["t_consensus"] else ""
            print(f"  p={p:.2f} seed={s}: consensus={oc:>4}{tc:>6}  "
                  f"final_n_B={r['final_n_B']:.2f}  steps={r['steps']}  "
                  f"{r['episode_s']}s")
    dt = time.time() - t0
    msum = meter.summary()
    print("\n--- METER ---")
    for k, v in msum.items():
        print(f"  {k}: {v}")
    print(f"  wall_clock_s: {dt:.1f}")
    if msum["calls"]:
        print(f"  tokens/episode: {msum['total_tokens']/len(rows):.0f}")
        print(f"  seconds/episode: {dt/len(rows):.1f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(model=args.model, n=args.n,
                                 t_max_units=args.t_max_units, seeds=args.seeds,
                                 rule_guided=args.rule_guided, wall_s=dt,
                                 meter=msum), rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
