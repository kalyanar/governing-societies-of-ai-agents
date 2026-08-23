"""
Sweep committed-defector fraction p for a given composition + adversary tier and
locate the cooperation-collapse tipping point. Per-model cost metering.

Examples
--------
python run_govsim.py --comp homo --models llama3b --adversary greedy \
       --ps 0.0 0.2 0.4 0.6 --seeds 3 --n 5 --max_months 12
python run_govsim.py --comp hetero --models llama3b qwen25_3b gemma2_2b \
       --adversary persuasive --ps 0.0 0.2 0.4 --seeds 3
"""
from __future__ import annotations
import argparse, json, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, est_cost_per_episode   # noqa: E402
from backends import ModelMeter                                      # noqa: E402

from gov_loop import homogeneous, heterogeneous, GovComposition, run_episode


def build_comp(args):
    if args.comp == "homo":
        return homogeneous(args.models[0], adversary=args.adversary)
    if args.comp == "hetero":
        return heterogeneous(args.models, adversary=args.adversary)
    if args.comp == "mixed":
        return GovComposition("mixed_competence", args.models, args.adversary,
                              "mixed:" + "+".join(args.models))
    raise ValueError(args.comp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero", "mixed"], default="homo")
    ap.add_argument("--models", nargs="+", default=["llama3b"])
    ap.add_argument("--adversary", choices=["greedy", "persuasive", "injected"],
                    default="greedy")
    ap.add_argument("--ps", type=float, nargs="+", default=[0.0, 0.2, 0.4, 0.6])
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--max_months", type=int, default=12)
    ap.add_argument("--no_discussion", action="store_true")
    ap.add_argument("--monitoring", action="store_true",
                    help="reveal last month's per-agent catches (Ostrom principle 4)")
    ap.add_argument("--steward", action="store_true",
                    help="stewardship objective instead of the published "
                         "self-interested 'maximize YOUR catch' framing")
    ap.add_argument("--sanction", action="store_true",
                    help="reclaim an over-harvester's excess before regeneration "
                         "(principle 5 / restitution)")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--out", default="../results/govsim_run.json")
    args = ap.parse_args()

    comp = build_comp(args)
    for k in set(args.models):
        if k not in REGISTRY:
            raise SystemExit(f"unknown model '{k}'")
        ok, info = key_available(k)
        if not ok:
            raise SystemExit(f"no access for {k} ({info})")

    meter = ModelMeter()
    print(f"[GovSim {comp.label} adv={args.adversary}] N={args.n} ps={args.ps} "
          f"seeds={args.seeds} months={args.max_months} "
          f"discussion={not args.no_discussion}")
    t0 = time.time()
    jobs = [(p, s) for p in args.ps for s in range(args.seeds)]

    def _run(job):
        p, s = job
        te = time.time()
        m = run_episode(args.n, p, s, comp, meter, max_months=args.max_months,
                        monitoring=args.monitoring, sanction=args.sanction,
                        steward=args.steward,
                        discussion=not args.no_discussion, temperature=args.temperature)
        m.update(p=p, seed=s, episode_s=round(time.time() - te, 1))
        return m

    from concurrent.futures import ThreadPoolExecutor, as_completed
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fut in as_completed(futs):
            m = fut.result(); rows.append(m); done += 1
            print(f"  [{done}/{len(jobs)}] p={m['p']:.2f} s={m['seed']}: "
                  f"survival={m['survival_months']:2d}mo collapsed={m['collapsed']!s:5} "
                  f"yield={m['total_caught']:.0f}  {m['episode_s']}s")
    rows.sort(key=lambda m: (m["p"], m["seed"]))
    dt = time.time() - t0

    msum = meter.summary()
    total_cost = sum(est_cost_per_episode(mk, v["prompt_tokens"], v["completion_tokens"])
                     for mk, v in msum.items())
    bad_total = sum(r.get("n_failed", 0) + r.get("n_unparsed", 0) for r in rows)
    dec_total = sum(r.get("n_decisions", 0) for r in rows)
    if bad_total:
        print(f"\n!! DATA QUALITY: {bad_total}/{dec_total} decisions defaulted to the "
              f"sustainable harvest ({bad_total/max(dec_total,1):.1%}) -- these bias "
              f"TOWARD cooperation; check before trusting survival numbers.")
    else:
        print(f"\ndata quality: 0/{dec_total} defaulted decisions (clean)")
    print("\n--- PER-MODEL METER ---")
    for mk, v in msum.items():
        print(f"  {mk}: calls={v['calls']} in={v['prompt_tokens']} "
              f"out={v['completion_tokens']} fails={v['failures']}")
    print(f"  wall={dt:.1f}s  est_api_cost=${total_cost:.4f} "
          f"(${total_cost/max(len(rows),1):.4f}/episode)")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(composition=comp.label, kind=comp.kind,
                                 adversary=args.adversary, models=args.models,
                                 n=args.n, seeds=args.seeds,
                                 max_months=args.max_months,
                                 discussion=not args.no_discussion,
                                 wall_s=dt, per_model_meter=msum,
                                 est_api_cost=total_cost), rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
