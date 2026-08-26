"""
Unified runner: sweep committed fraction p for a given COMPOSITION (homogeneous /
heterogeneous / mixed-competence) and locate the LLM tipping point p_c.
Per-model token/cost metering across all providers.

Examples
--------
# homogeneous local pilot
python run_society.py --comp homo --models llama3b --n 24 \
       --ps 0.0 0.1 0.2 0.3 0.4 --seeds 2 --t_max_units 35

# heterogeneous: mix two local families
python run_society.py --comp hetero --models llama3b qwen4b --n 24 \
       --ps 0.1 0.2 0.3 --seeds 2

# scale the ATTACKER independently (committed minority on a bigger model)
python run_society.py --comp homo --models llama3b --committed_model qwen32b ...
"""
from __future__ import annotations
import argparse, json, os, time
import random
from model import Population
from society import homogeneous, heterogeneous, mixed_competence, build_population, composition_report
from llm_agent import make_society_update_fn, make_labels
from backends import ModelMeter
from registry import REGISTRY, key_available, est_cost_per_episode


def run_episode(n, p, seed, comp, t_max_units, meter, rule_guided=False,
                temperature=0.7, adjacency=None, committed_opinion="A",
                settle_window=12, settle_eps=0.05):
    pop, backend_map = build_population(n, p, seed, comp, adjacency,
                                        committed_opinion=committed_opinion)
    # neutral, randomized label mapping for THIS episode (controls token bias)
    label_rng = random.Random(hash((seed, committed_opinion, p)) & 0xFFFFFFFF)
    labels = make_labels(label_rng)
    update_fn = make_society_update_fn(backend_map, meter, labels, rule_guided,
                                       temperature)
    max_steps = int(t_max_units * n)
    steps, reached_at, outcome, stop_reason = 0, None, None, "horizon"
    traj = []
    while steps < max_steps:
        pop.step(update_fn=update_fn)
        steps += 1
        if steps % n == 0:
            traj.append(round(pop.n_resist(), 3))
            c = pop.consensus()
            if c is not None:                       # tipped or fully resisted
                reached_at, outcome, stop_reason = steps / n, c, "consensus"
                break
            # early stop: metastable plateau settled (order parameter flat)
            if len(traj) >= settle_window:
                w = traj[-settle_window:]
                if max(w) - min(w) < settle_eps:
                    stop_reason = "settled"
                    break
    tipped = (outcome == committed_opinion)
    return dict(reached=tipped, consensus=outcome, t_consensus=reached_at,
                stop_reason=stop_reason,
                committed_opinion=committed_opinion,
                labels={"committed": labels[committed_opinion],
                        "resist": labels[pop.resist_opinion]},
                final_n_resist=pop.n_resist(), final_n_B=pop.n_B_total(),
                steps=steps, traj=traj, composition=composition_report(pop))


def build_comp(args):
    if args.comp == "homo":
        return homogeneous(args.models[0], committed_model=args.committed_model)
    if args.comp == "hetero":
        return heterogeneous(args.models, committed_model=args.committed_model)
    if args.comp == "mixed":
        return mixed_competence(args.models[0], args.models[1],
                                weak_fraction=args.weak_fraction,
                                committed_model=args.committed_model)
    raise ValueError(args.comp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero", "mixed"], default="homo")
    ap.add_argument("--models", nargs="+", default=["llama3b"],
                    help="registry keys for uncommitted agents")
    ap.add_argument("--committed_model", default=None,
                    help="registry key for the committed minority (default=majority)")
    ap.add_argument("--weak_fraction", type=float, default=0.5)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--ps", type=float, nargs="+", default=[0.0, 0.1, 0.2, 0.3, 0.4])
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=0,
                    help="first seed index; lets a later pass add seeds "
                         "(--seed0 2 --seeds 3 gives seeds 2,3,4) and be merged "
                         "with an earlier one instead of re-running it.")
    ap.add_argument("--t_max_units", type=float, default=35.0)
    ap.add_argument("--rule_guided", action="store_true")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--push", choices=["A", "B", "both"], default="both",
                    help="which opinion the committed minority pushes; "
                         "'both' counterbalances to control intrinsic option bias")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="episodes to run in parallel (API/HF are I/O-bound)")
    ap.add_argument("--content", default="neutral",
                    help="content condition for the two conventions "
                         "(neutral|coop_sym|coop_asym); see norm_content.py. "
                         "Only the words and framing change -- the update rule, "
                         "population and estimator are identical.")
    ap.add_argument("--out", default="../results/society_run.json")
    args = ap.parse_args()

    # Content condition must be installed BEFORE any episode builds its labels.
    import norm_content
    _cond = norm_content.install(args.content)
    print(f"[content] condition={args.content} asymmetric={_cond['asymmetric']}")

    comp = build_comp(args)
    # preflight: check every model used is available
    used = set(args.models) | ({args.committed_model} if args.committed_model else set())
    missing = []
    for k in used:
        if k not in REGISTRY:
            raise SystemExit(f"unknown model '{k}'")
        ok, info = key_available(k)
        if not ok:
            missing.append(f"{k} ({info})")
    if missing:
        raise SystemExit("missing access for: " + ", ".join(missing) +
                         "\nSet the API key(s) and retry.")

    meter = ModelMeter()
    seeds = list(range(args.seed0, args.seed0 + args.seeds))
    pushes = ["A", "B"] if args.push == "both" else [args.push]
    jobs = [(push, p, s) for push in pushes for p in args.ps for s in seeds]
    print(f"[{comp.label}] N={args.n} ps={args.ps} seeds={args.seeds} "
          f"push={args.push} committed_model={comp.committed_model} "
          f"| {len(jobs)} episodes, concurrency={args.concurrency}")
    t0 = time.time()

    def _run(job):
        push, p, s = job
        te = time.time()
        r = run_episode(args.n, p, s, comp, args.t_max_units, meter,
                        args.rule_guided, args.temperature, committed_opinion=push)
        r.update(p=p, seed=s, episode_s=round(time.time() - te, 1))
        return r

    rows = []
    done = 0
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            done += 1
            oc = r["consensus"] or "none"
            print(f"  [{done}/{len(jobs)}] push={r['committed_opinion']} "
                  f"p={r['p']:.2f} s={r['seed']}: {oc:>4}  "
                  f"n_resist={r['final_n_resist']:.2f}  {r['episode_s']}s")
    rows.sort(key=lambda r: (r["committed_opinion"], r["p"], r["seed"]))
    dt = time.time() - t0

    # cost projection from measured per-model usage
    msum = meter.summary()
    print("\n--- PER-MODEL METER ---")
    total_cost = 0.0
    for mk, m in msum.items():
        cost = est_cost_per_episode(mk, m["prompt_tokens"], m["completion_tokens"])
        total_cost += cost
        print(f"  {mk}: calls={m['calls']} tok_in={m['prompt_tokens']} "
              f"tok_out={m['completion_tokens']} fails={m['failures']} "
              f"est_cost_this_run=${cost:.4f}")
    print(f"  wall={dt:.1f}s  est_api_cost_this_run=${total_cost:.4f}  "
          f"(${total_cost/max(len(rows),1):.4f}/episode)")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(meta=dict(content=args.content, seed0=args.seed0, composition=comp.label, kind=comp.kind,
                                 models=args.models,
                                 committed_model=comp.committed_model,
                                 n=args.n, seeds=args.seeds,
                                 t_max_units=args.t_max_units, wall_s=dt,
                                 per_model_meter=msum,
                                 est_api_cost=total_cost), rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
