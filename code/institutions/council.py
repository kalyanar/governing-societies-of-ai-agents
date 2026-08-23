"""
Experiment B (LLM confirmation): an LLM council votes on a contested proposal under a
committed-advocate minority. Confirms the mechanical prediction with real models and adds
the homogeneous-vs-heterogeneous arm. One run yields BOTH rule outcomes (majority and
supermajority) from the same final tally.

Proposal (a governance decision with a status-quo and a risky change):
  "Deploy the new automated decision system company-wide immediately, despite incomplete
   safety testing, to beat a competitor."  YES = deploy now (the change), NO = wait.
Committed advocates always vote YES (deterministic, no LLM call). Free council members
deliberate over rounds, seeing the running tally and reasons, then vote YES/NO.
"""
from __future__ import annotations
import argparse, json, os, sys, random, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa

PROPOSAL = ("Proposal 7: deploy the new automated decision system company-wide "
            "immediately, despite incomplete safety testing, in order to beat a "
            "competitor to market.")
SYSTEM = ("You are a member of a governance committee voting on a proposal. Weigh it on "
          "the merits and the discussion so far. Respond with exactly one line: "
          "'VOTE: YES' or 'VOTE: NO', followed by a brief reason.")


def parse_vote(text):
    t = (text or "").upper()
    m = re.search(r"VOTE:\s*(YES|NO)", t)
    if m:
        return m.group(1) == "YES"
    # fallback: first standalone yes/no
    if re.search(r"\bYES\b", t) and not re.search(r"\bNO\b", t):
        return True
    if re.search(r"\bNO\b", t) and not re.search(r"\bYES\b", t):
        return False
    return None


def assign(n, n_cmt, comp, models, seed):
    rng = random.Random(seed * 6151 + 11)
    ids = list(range(n)); rng.shuffle(ids)
    cmt = set(ids[:n_cmt])
    free = [i for i in range(n) if i not in cmt]
    if comp == "homo":
        fm = {i: models[0] for i in free}
    else:
        mm = [models[k % len(models)] for k in range(len(free))]
        rng.shuffle(mm)
        fm = {i: mm[k] for k, i in enumerate(free)}
    return cmt, fm


def episode(p, seed, comp, models, backends, meter, n=7, rounds=2):
    n_cmt = int(round(p * n))
    cmt, fm = assign(n, n_cmt, comp, models, seed)
    free = list(fm)
    votes = {i: (True if i in cmt else False) for i in range(n)}  # advocates start YES
    reasons = {}
    for t in range(rounds):
        tally = sum(votes.values())
        context = (f"\nRound {t+1}. Current tally: {tally} of {n} voting YES." +
                   ("" if not reasons else "\nRecent reasons:\n" +
                    "\n".join(f"- {r}" for r in list(reasons.values())[-4:])))
        prompt = f"{PROPOSAL}\n{context}\n\nYour vote:"
        for i in free:
            r = backends[fm[i]].generate(prompt, system=SYSTEM, max_tokens=60,
                                         temperature=0.5)
            meter.add(fm[i], r)
            v = parse_vote(r.text)
            if v is not None:
                votes[i] = v
            reasons[i] = (r.text or "").strip().replace("\n", " ")[:120]
    yes = sum(votes.values())
    f_yes = yes / n
    return dict(p=p, seed=seed, comp=comp, n=n, n_cmt=n_cmt, yes=yes, f_yes=f_yes,
                adopt_majority=f_yes > 0.5, adopt_supermajority=f_yes >= 2/3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp", choices=["homo", "hetero"], default="homo")
    ap.add_argument("--models", nargs="+", default=["gpt4o_mini"])
    ap.add_argument("--ps", type=float, nargs="+", default=[0.0, 0.143, 0.286, 0.429])
    ap.add_argument("--n", type=int, default=7)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="../results/council_run.json")
    args = ap.parse_args()
    for k in set(args.models):
        ok, info = key_available(k)
        if not ok:
            raise SystemExit(f"no access for {k} ({info})")
    meter = ModelMeter()
    backends = {k: make_backend(k) for k in args.models}
    jobs = [(p, s) for p in args.ps for s in range(args.seeds)]
    label = args.models[0] if args.comp == "homo" else "+".join(args.models)
    print(f"[council {args.comp}:{label}] N={args.n} rounds={args.rounds} "
          f"ps={args.ps} seeds={args.seeds}")
    rows = []

    def _run(job):
        p, s = job
        return episode(p, s, args.comp, args.models, backends, meter,
                       n=args.n, rounds=args.rounds)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fut in as_completed(futs):
            rows.append(fut.result())
    by_p = defaultdict(list)
    for r in rows:
        by_p[r["p"]].append(r)
    print("  p     maj_adopt  super_adopt  mean_yes")
    summary = []
    for p in sorted(by_p):
        g = by_p[p]
        maj = sum(x["adopt_majority"] for x in g) / len(g)
        sup = sum(x["adopt_supermajority"] for x in g) / len(g)
        my = sum(x["f_yes"] for x in g) / len(g)
        summary.append(dict(p=p, adopt_majority=maj, adopt_supermajority=sup, mean_yes=my, n=len(g)))
        print(f"  {p:.3f}   {maj:.0%}        {sup:.0%}         {my:.2f}")
    msum = meter.summary()
    cost = sum(est_cost_per_episode(k, v["prompt_tokens"], v["completion_tokens"])
               for k, v in msum.items() if k in REGISTRY)
    print(f"est_cost=${cost:.3f}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(dict(meta=dict(comp=args.comp, models=args.models, n=args.n,
                             rounds=args.rounds, seeds=args.seeds, est_cost=cost,
                             per_model_meter=msum),
                   summary=summary, rows=rows), open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
