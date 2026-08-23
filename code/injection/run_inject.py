"""
Run the injection-propagation study: homogeneous (monoculture) vs heterogeneous panels.

Examples
--------
# one homogeneous panel (6x a single model)
python run_inject.py --comp homo --models llama70b_local --n 6 --rounds 4 --seeds 5
# a heterogeneous panel (round-robin across the listed models)
python run_inject.py --comp hetero --models llama70b_local qwen32b gpt4o_mini claude_haiku \
       --n 6 --rounds 4 --seeds 5
"""
from __future__ import annotations
import argparse, json, os, sys, time, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from inject import run_propagation, run_chain  # noqa


def assign(n, comp, models, seed):
    """agent 0 = patient zero. Homogeneous: all agents one model. Heterogeneous:
    patient zero is models[0]; the rest round-robin across all models (shuffled)."""
    rng = random.Random(seed * 6151 + 11)
    if comp == "homo":
        return [models[0]] * n
    out = [models[0]]
    rest = [models[k % len(models)] for k in range(n - 1)]
    rng.shuffle(rest)
    return out + rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero"], default="homo")
    ap.add_argument("--models", nargs="+", default=["llama70b_local"])
    ap.add_argument("--topology", choices=["chain", "broadcast"], default="chain")
    ap.add_argument("--defended", action="store_true",
                    help="harden agents (tell them notes are untrusted)")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--out", default="../results/inject_run.json")
    args = ap.parse_args()

    for k in set(args.models):
        if k not in REGISTRY:
            raise SystemExit(f"unknown model '{k}'")
        ok, info = key_available(k)
        if not ok:
            raise SystemExit(f"no access for {k} ({info})")

    meter = ModelMeter()
    backends = {k: make_backend(k) for k in args.models}
    jobs = list(range(args.seeds))
    label = args.models[0] if args.comp == "homo" else "+".join(args.models)
    print(f"[inject {args.comp}:{label}] N={args.n} rounds={args.rounds} "
          f"seeds={args.seeds} concurrency={args.concurrency}")
    t0 = time.time()
    rows = []

    def _run(seed):
        mk = assign(args.n, args.comp, args.models, seed)
        if args.topology == "chain":
            return run_chain(mk, backends, meter, seed=seed, defended=args.defended)
        return run_propagation(mk, backends, meter, rounds=args.rounds, seed=seed,
                               defended=args.defended)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, s): s for s in jobs}
        for fut in as_completed(futs):
            r = fut.result(); rows.append(r)
            extra = (f"depth={r['depth']}/{r['n_free']} reached_end={r['reached_end']}"
                     if args.topology == "chain"
                     else f"curve={[round(x,2) for x in r['per_round_frac']]}")
            print(f"  seed={r['seed']}: final_infected={r['final_infected_frac']:.0%} "
                  f"spread={r['spread_beyond_zero']} {extra}")
    dt = time.time() - t0

    # aggregate
    final = [r["final_infected_frac"] for r in rows]
    spread = [r["spread_beyond_zero"] for r in rows]
    mean_final = sum(final) / len(final)
    spread_rate = sum(spread) / len(spread)
    print(f"\n--- {args.comp}:{label} [{args.topology}{'/defended' if args.defended else ''}] ---")
    print(f"mean final-infected fraction = {mean_final:.0%}")
    print(f"spread-beyond-patient-zero rate = {spread_rate:.0%}")
    if args.topology == "chain":
        mean_depth = sum(r["depth"] for r in rows) / len(rows)
        reach = sum(r["reached_end"] for r in rows) / len(rows)
        curve = None
        print(f"mean propagation depth = {mean_depth:.2f}/{rows[0]['n_free']}  "
              f"reached-end rate = {reach:.0%}")
    else:
        R = max(len(r["per_round_frac"]) for r in rows)
        curve = [sum(r["per_round_frac"][t] for r in rows) / len(rows) for t in range(R)]
        print(f"mean infection curve by round = {[round(x,2) for x in curve]}")

    msum = meter.summary()
    cost = sum(est_cost_per_episode(mk, v["prompt_tokens"], v["completion_tokens"])
               for mk, v in msum.items() if mk in REGISTRY)
    print(f"wall={dt:.0f}s est_cost=${cost:.3f} calls={ {k: v['calls'] for k,v in msum.items()} }")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(comp=args.comp, models=args.models, n=args.n,
                                 topology=args.topology, defended=args.defended,
                                 rounds=args.rounds, seeds=args.seeds, wall_s=dt,
                                 est_cost=cost, mean_final=mean_final,
                                 spread_rate=spread_rate, curve=curve,
                                 per_model_meter=msum),
                       rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
