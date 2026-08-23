"""
RQ2 capability gate: can a model execute the binary-agreement (Naming Game)
coordination primitive at all?

The paper reports rule-following accuracy by scale ("33-77% for 2-4B vs 100% at
70B+"), but no result file in results/ contains those numbers -- they were
produced ad hoc and never saved. This script measures the same quantity
reproducibly and writes an artifact.

VALIDITY NOTE: the probe imports `build_prompt` and `make_labels` from
llm_agent.py, so every agent sees byte-for-byte the prompt the live simulation
sends, with the same neutral randomized labels. Ground truth is
`model.mechanical_update`, i.e. Table I of Xie et al. (2011). We are therefore
measuring exactly the primitive the naming-game results depend on, not a proxy.

The rule has three cases; we probe each separately because they fail differently
(weak models tend to collapse to "both", which is case 2's answer -- so overall
accuracy alone hides the failure mode):

  agree    listener holds X, hears X       -> X      (drop the other, keep X)
  add      listener holds X, hears Y       -> both   (adopt the new word too)
  collapse listener holds both, hears X    -> X      (collapse onto what it heard)

Usage
-----
  ../../.venv/bin/python rule_probe.py --models or_ministral8b or_ministral14b \
      --trials 30 --out ../results/rule_probe_mistral.json
"""
from __future__ import annotations
import argparse, json, os, random, time
from concurrent.futures import ThreadPoolExecutor, as_completed

from model import A, B, AB, mechanical_update
from llm_agent import build_prompt, make_labels, _parse
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode
from backends import ModelMeter

# (case name, listener state, heard opinion)
CASES = [
    ("agree",    A,  A),
    ("add",      A,  B),
    ("collapse", AB, A),
]


def one_trial(backend, mk, meter, case, state, heard, rng_seed,
              temperature, max_tokens):
    rng = random.Random(rng_seed)
    labels = make_labels(rng)
    _, user = build_prompt(state, heard, labels, rule_guided=False)
    r = backend.generate(user, system=None, max_tokens=max_tokens,
                         temperature=temperature)
    meter.add(mk, r)
    if not r.ok:
        return dict(case=case, ok=False, parsed=None, correct=False,
                    error=(r.error or "")[:120])
    parsed = _parse(r.text, labels)
    truth = mechanical_update(state, heard)
    return dict(case=case, ok=True, parsed=parsed, truth=truth,
                correct=(parsed == truth), unparseable=(parsed is None),
                reply=(r.text or "").strip()[:80], served_by=r.served_by)


def probe_model(mk, trials, temperature, max_tokens, conc):
    backend = make_backend(mk)
    meter = ModelMeter()
    jobs = [(c, s, h, i) for (c, s, h) in CASES for i in range(trials)]
    rows = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(one_trial, backend, mk, meter, c, s, h,
                          hash((mk, c, i)) & 0xFFFFFFFF, temperature, max_tokens)
                for (c, s, h, i) in jobs]
        for f in as_completed(futs):
            rows.append(f.result())

    by_case = {}
    for c, _, _ in CASES:
        sub = [r for r in rows if r["case"] == c]
        by_case[c] = dict(
            n=len(sub),
            acc=round(sum(r["correct"] for r in sub) / max(len(sub), 1), 3),
            unparseable=round(sum(r.get("unparseable", False) for r in sub)
                              / max(len(sub), 1), 3),
            errors=sum(not r["ok"] for r in sub),
        )
    overall = round(sum(r["correct"] for r in rows) / max(len(rows), 1), 3)
    # the characteristic weak-model failure: answering "both" regardless
    always_both = round(sum(r.get("parsed") == AB for r in rows) / max(len(rows), 1), 3)

    msum = meter.summary()
    m = msum.get(mk, {})
    cost = est_cost_per_episode(mk, m.get("prompt_tokens", 0),
                                m.get("completion_tokens", 0))
    e = REGISTRY[mk]
    return dict(
        key=mk, model=e["model"], scale_b=e.get("scale_b"),
        active_b=e.get("active_b"), family=e["family"],
        reasoning_model=e.get("reasoning"),
        overall_acc=overall, by_case=by_case, frac_answered_both=always_both,
        served_by=m.get("served_by", {}), calls=m.get("calls", 0),
        est_cost=round(cost, 4), rows=rows,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--trials", type=int, default=30, help="trials PER CASE")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="0.7 matches the live simulation")
    ap.add_argument("--max_tokens", type=int, default=16)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/rule_probe.json")
    args = ap.parse_args()

    for mk in args.models:
        if mk not in REGISTRY:
            raise SystemExit(f"unknown model '{mk}'")
        ok, info = key_available(mk)
        if not ok:
            raise SystemExit(f"no access for {mk} ({info})")

    print(f"[rule_probe] {len(args.models)} models x {args.trials} trials x "
          f"{len(CASES)} cases, temp={args.temperature}")
    t0 = time.time()
    out = []
    for mk in args.models:
        res = probe_model(mk, args.trials, args.temperature, args.max_tokens,
                          args.conc)
        out.append(res)
        sb = ",".join(res["served_by"]) or "-"
        print(f"  {mk:22s} {str(res['scale_b'])+'B':>6}  overall={res['overall_acc']:.2f}  "
              f"agree={res['by_case']['agree']['acc']:.2f} "
              f"add={res['by_case']['add']['acc']:.2f} "
              f"collapse={res['by_case']['collapse']['acc']:.2f}  "
              f"both%={res['frac_answered_both']:.2f}  via={sb}  ${res['est_cost']:.4f}")

    total = sum(r["est_cost"] for r in out)
    print(f"\nwall={time.time()-t0:.0f}s  est_cost=${total:.4f}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(dict(meta=dict(trials=args.trials, temperature=args.temperature,
                             cases=[c for c, _, _ in CASES],
                             est_cost=total), models=out),
              open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
