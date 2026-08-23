"""
Sweep committed-extremist fraction p for a composition (homogeneous vs
heterogeneous) on moral dilemmas/fables. Measures:
  - SWAY: how far honest agents' mean stance is dragged toward the committed
    extreme (relative to the p=0 baseline for the same stimulus/seed).
  - PERSPECTIVE DIVERSITY: distinct considerations raised (LLM judge), homo vs hetero.

Example:
  python run_deliberate.py --comp hetero --models gpt4o_mini claude_haiku qwen72b \
      --judge_model gpt4o_mini --ps 0.0 0.17 0.33 0.5 --n 6 --seeds 2
"""
from __future__ import annotations
import argparse, json, os, sys, random, time, statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter                                                   # noqa

from stimuli import get_stimuli
from deliberate import (DelibAgent, run_deliberation, judge_perspective_diversity)


def assign(n, n_adv, comp, models, adv_model, seed):
    rng = random.Random(seed * 7919 + 3)
    ids = list(range(n)); rng.shuffle(ids)
    adv = set(ids[:n_adv]); honest = ids[n_adv:]
    if comp == "homo":
        hmod = {i: models[0] for i in honest}
    else:
        hm = [models[k % len(models)] for k in range(len(honest))]; rng.shuffle(hm)
        hmod = {i: hm[k] for k, i in enumerate(honest)}
    return [((adv_model or models[0]) if i in adv else hmod[i], i in adv) for i in range(n)]


def episode(stim, p, seed, extreme, comp, models, adv_model, judge_model, n, rounds, meter):
    n_adv = int(round(p * n))
    a = assign(n, n_adv, comp, models, adv_model, seed)
    agents = [DelibAgent(idx=i, model_key=mk, committed=adv, extreme=extreme)
              for i, (mk, adv) in enumerate(a)]
    backends = {mk: make_backend(mk) for mk, _ in a}
    rng = random.Random(seed * 131 + hash(stim["id"]) % 997)
    r = run_deliberation(stim, agents, backends, meter, rounds=rounds, rng=rng)
    # perspective diversity (judge) — only worth it when there's reasoning to judge
    jb = make_backend(judge_model)
    ndiv, _ = judge_perspective_diversity(stim, r["transcript"], jb, meter)
    r.update(p=p, seed=seed, extreme=extreme, n_adv=n_adv, n_distinct=ndiv)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero"], default="homo")
    ap.add_argument("--models", nargs="+", default=["gpt4o_mini"])
    ap.add_argument("--adversary_model", default=None)
    ap.add_argument("--judge_model", default="gpt4o_mini")
    ap.add_argument("--ps", type=float, nargs="+", default=[0.0, 0.17, 0.33, 0.5])
    ap.add_argument("--extremes", type=int, nargs="+", default=[1, 7],
                    help="committed-extreme stances to push (counterbalanced)")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--kinds", nargs="*", default=None, help="dilemma / fable")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="../results/deliberate_run.json")
    args = ap.parse_args()

    for k in set(args.models) | {args.judge_model} | ({args.adversary_model} if args.adversary_model else set()):
        ok, info = key_available(k)
        if k not in REGISTRY or not ok:
            raise SystemExit(f"no access for {k} ({info if k in REGISTRY else 'unknown'})")

    stims = get_stimuli(kinds=args.kinds)
    meter = ModelMeter()
    jobs = [(s, p, seed, e) for p in args.ps for seed in range(args.seeds)
            for e in args.extremes for s in stims]
    print(f"[delib {args.comp}:{'+'.join(args.models)}] N={args.n} judge={args.judge_model} "
          f"| {len(jobs)} episodes ({len(stims)} stimuli x {args.seeds} seeds x "
          f"{len(args.ps)} p x {len(args.extremes)} extremes)")
    t0 = time.time(); rows = []; done = 0

    def _run(j):
        s, p, seed, e = j
        return episode(s, p, seed, e, args.comp, args.models, args.adversary_model,
                       args.judge_model, args.n, args.rounds, meter)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result(); rows.append(r); done += 1
            if done % 15 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]")

    # --- SWAY: per (stim,seed,extreme), baseline = honest_mean at p=0; sway toward extreme
    base = {}
    for r in rows:
        if r["p"] == 0.0 and r["honest_mean_final"] is not None:
            base[(r["stim_id"], r["seed"], r["extreme"])] = r["honest_mean_final"]
    by_p = defaultdict(lambda: dict(sway=[], ndist=[]))
    for r in rows:
        b = base.get((r["stim_id"], r["seed"], r["extreme"]))
        if b is not None and r["honest_mean_final"] is not None:
            sign = 1 if r["extreme"] >= 4 else -1
            by_p[r["p"]]["sway"].append(sign * (r["honest_mean_final"] - b))
        if r["n_distinct"] is not None:
            by_p[r["p"]]["ndist"].append(r["n_distinct"])
    print("\n--- SWAY (stance dragged toward committed extreme) & DIVERSITY ---")
    summary = []
    for p in sorted(by_p):
        sway = by_p[p]["sway"]; nd = by_p[p]["ndist"]
        ms = statistics.mean(sway) if sway else 0.0
        md = statistics.mean(nd) if nd else 0.0
        summary.append(dict(p=p, mean_sway=ms, mean_distinct=md, n=len(sway)))
        print(f"  p={p:.2f}: mean_sway={ms:+.2f} (1-7 scale)  mean_distinct_args={md:.1f}  (n={len(sway)})")

    dt = time.time() - t0
    msum = meter.summary()
    cost = sum(est_cost_per_episode(mk if mk != '__judge__' else args.judge_model,
                                    v["prompt_tokens"], v["completion_tokens"])
               for mk, v in msum.items())
    print(f"\nwall={dt:.0f}s est_cost=${cost:.3f}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(comp=args.comp, models=args.models,
                                 judge=args.judge_model, n=args.n, rounds=args.rounds,
                                 seeds=args.seeds, extremes=args.extremes,
                                 n_stimuli=len(stims), wall_s=dt, est_cost=cost),
                       summary=summary, rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
