"""
Sweep adversarial fraction p for a composition (homogeneous vs heterogeneous) and
measure debate accuracy. Tests whether a DIVERSE honest pool resists a committed
wrong-answer minority better than a MONOCULTURE (error decorrelation).

Examples
--------
python run_debate.py --comp homo --models gpt4o_mini --ps 0.0 0.2 0.4 --n 6
python run_debate.py --comp hetero --models gpt4o_mini claude_haiku qwen72b \
       --adversary_model gpt4o_mini --ps 0.0 0.17 0.33 0.5 --n 6 --seeds 3
"""
from __future__ import annotations
import argparse, json, os, sys, random, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter                                                   # noqa

from questions import get_questions
from dataset_loader import load_json_set
from debate import DebateAgent, run_debate, judge_aggregate


def assign_models(n, n_adv, comp, models, adversary_model, seed):
    """Return per-agent (model_key, is_adversary). Adversaries are the LAST n_adv
    indices (shuffled), honest agents get the composition's models."""
    rng = random.Random(seed * 6151 + 11)
    ids = list(range(n))
    rng.shuffle(ids)
    adv_ids = set(ids[:n_adv])
    honest_ids = ids[n_adv:]
    # honest model assignment
    if comp == "homo":
        honest_models = {i: models[0] for i in honest_ids}
    else:  # hetero: round-robin across the model list
        hm = [models[k % len(models)] for k in range(len(honest_ids))]
        rng.shuffle(hm)
        honest_models = {i: hm[k] for k, i in enumerate(honest_ids)}
    out = []
    for i in range(n):
        if i in adv_ids:
            out.append((adversary_model or models[0], True))
        else:
            out.append((honest_models[i], False))
    return out


def episode(question, p, seed, comp, models, adversary_model, n, rounds, meter,
            judge_model=None):
    n_adv = int(round(p * n))
    assign = assign_models(n, n_adv, comp, models, adversary_model, seed)
    agents = [DebateAgent(idx=i, model_key=mk, adversary=adv,
                          wrong_target=question.get("wrong_target", "A"))
              for i, (mk, adv) in enumerate(assign)]
    backends = {mk: make_backend(mk) for mk, _ in assign}
    rng = random.Random(seed * 131 + hash(question["id"]) % 1000)
    r = run_debate(question, agents, backends, meter, rounds=rounds, rng=rng)
    # verify/select-style aggregator (captures coverage that majority misses)
    if judge_model:
        ja = judge_aggregate(question, agents, make_backend(judge_model), meter)
        r["judge_answer"] = ja
        r["judge_correct"] = (ja == question["answer"])
    r.update(p=p, seed=seed, n_adv=n_adv, source=question.get("source", "?"),
             n_models=len({mk for mk, a in assign if not a}))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero"], default="homo")
    ap.add_argument("--models", nargs="+", default=["gpt4o_mini"])
    ap.add_argument("--adversary_model", default=None,
                    help="model backing the adversaries (default: first honest model)")
    ap.add_argument("--ps", type=float, nargs="+", default=[0.0, 0.17, 0.33, 0.5])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--questions", nargs="*", default=None)
    ap.add_argument("--dataset", default=None,
                    help="path to a normalized question JSON (overrides builtin questions)")
    ap.add_argument("--judge_model", default=None,
                    help="if set, a judge weighs the panel's answers (verify-style aggregation)")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--out", default="../results/debate_run.json")
    args = ap.parse_args()

    for k in set(args.models) | ({args.adversary_model} if args.adversary_model else set()):
        if k not in REGISTRY:
            raise SystemExit(f"unknown model '{k}'")
        ok, info = key_available(k)
        if not ok:
            raise SystemExit(f"no access for {k} ({info})")

    qs = load_json_set(args.dataset) if args.dataset else get_questions(args.questions)
    meter = ModelMeter()
    jobs = [(q, p, s) for p in args.ps for s in range(args.seeds) for q in qs]
    print(f"[debate {args.comp}:{'+'.join(args.models)}] N={args.n} rounds={args.rounds} "
          f"adv={args.adversary_model or args.models[0]} | {len(jobs)} episodes "
          f"({len(qs)} questions x {args.seeds} seeds x {len(args.ps)} p), "
          f"concurrency={args.concurrency}")
    t0 = time.time()
    rows = []
    done = 0

    def _run(job):
        q, p, s = job
        return episode(q, p, s, args.comp, args.models, args.adversary_model,
                       args.n, args.rounds, meter, judge_model=args.judge_model)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result(); rows.append(r); done += 1
            if done % 10 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}] last: p={r['p']:.2f} q={r['question_id']} "
                      f"full_maj={r['full_majority']} correct={r['full_correct']}")
    dt = time.time() - t0

    # accuracy vs p (homo/hetero), honest and full
    from collections import defaultdict
    by_p = defaultdict(list)
    for r in rows:
        by_p[r["p"]].append(r)
    print("\n--- ACCURACY vs ADVERSARIAL FRACTION ---")
    summary = []
    for p in sorted(by_p):
        grp = by_p[p]
        full = sum(x["full_correct"] for x in grp) / len(grp)
        honest = sum(x["honest_correct"] for x in grp) / len(grp)
        jvals = [x["judge_correct"] for x in grp if "judge_correct" in x]
        judge = (sum(jvals) / len(jvals)) if jvals else None
        summary.append(dict(p=p, full_acc=full, honest_acc=honest,
                            judge_acc=judge, n=len(grp)))
        js = f"  judge_acc={judge:.0%}" if judge is not None else ""
        print(f"  p={p:.2f}: majority_acc={honest:.0%}{js}  (n={len(grp)})")

    msum = meter.summary()
    cost = sum(est_cost_per_episode(args.judge_model if mk == "__judge__" else mk,
                                    v["prompt_tokens"], v["completion_tokens"])
               for mk, v in msum.items()
               if mk in REGISTRY or mk == "__judge__")
    print(f"\nwall={dt:.0f}s  est_cost=${cost:.3f}  per_model={ {k:v['calls'] for k,v in msum.items()} }")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(comp=args.comp, models=args.models,
                                 adversary_model=args.adversary_model or args.models[0],
                                 n=args.n, rounds=args.rounds, seeds=args.seeds,
                                 n_questions=len(qs), wall_s=dt, est_cost=cost,
                                 per_model_meter=msum),
                       summary=summary, rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
