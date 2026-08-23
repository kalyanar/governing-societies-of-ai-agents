"""
Control for Experiment D (verifiers.py): is the "strong judge" SELECTING from the
panel, or just SOLVING the question itself?

In verifiers.json the strong judge (claude_sonnet) exceeds the panel's coverage
ceiling in BOTH arms (homo 0.525 > C=0.375; hetero 0.625 > C=0.60), which is only
possible if the judge sometimes produces an answer no panel member gave. That
makes v_hat = (R - a_best)/(C - a_best) uninterpretable as "verifier quality".

This script measures what the judge scores WITHOUT a useful panel, on the same 40
items, so the panel's actual contribution can be isolated:

  solo_t0     claude_sonnet answers alone (SOLVE prompt, temp 0.0)
  solo_t07    same at temp 0.7, 3 independent repeats (sampling spread)
  judge_empty JUDGE prompt with an empty solver list (isolates prompt format)
  judge_wrong JUDGE prompt where every solver asserts the designated wrong answer
              (does the judge actually read the panel, or override it?)

Interpretation:
  solo ~ 0.625  -> the hetero "verifier realizes the ceiling" claim is confounded;
                   the judge is a solver and the panel adds nothing.
  solo ~ 0.525  -> the homo arm is fully explained by the judge solving, but the
                   hetero panel still contributes +0.10; the claim survives in
                   weakened form ("panel-conditioned judging beats judging alone").
  judge_wrong >> chance -> the judge overrides the panel rather than selecting.

Usage:
  ../../.venv/bin/python judge_alone.py --out ../results/judge_alone.json
"""
from __future__ import annotations
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from debate import _fmt_options  # noqa
from dataset_loader import load_json_set  # noqa
from verifiers import SOLVE, JUDGE, strict_parse  # noqa


def _call(backend, prompt, meter, tag, temperature, max_tokens=150):
    r = backend.generate(prompt, max_tokens=max_tokens, temperature=temperature)
    meter.add(tag, r)
    return strict_parse(r.text, None) if r.ok else None


def one_question(q, backend, meter, n_t07):
    opts = _fmt_options(q["options"])
    solve_prompt = SOLVE.format(q=q["q"], opts=opts)

    out = {"id": q["id"], "gold": q["answer"]}
    out["solo_t0"] = _call(backend, solve_prompt, meter, "solo_t0", 0.0)
    out["solo_t07"] = [_call(backend, solve_prompt, meter, "solo_t07", 0.7)
                       for _ in range(n_t07)]

    # judge prompt, empty solver list
    out["judge_empty"] = _call(
        backend, JUDGE.format(q=q["q"], opts=opts, panel="(no solver answers available)"),
        meter, "judge_empty", 0.0, max_tokens=120)

    # judge prompt, panel unanimously asserting the designated wrong answer
    wrong = q.get("wrong_target") or next(L for L in q["options"] if L != q["answer"])
    fake = "\n".join(f"- answer {wrong}: this is the correct choice." for _ in range(3))
    out["judge_wrong"] = _call(
        backend, JUDGE.format(q=q["q"], opts=opts, panel=fake),
        meter, "judge_wrong", 0.0, max_tokens=120)
    out["wrong_target"] = wrong
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_mathsci.json")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--judge", default="claude_sonnet")
    ap.add_argument("--n_t07", type=int, default=3)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/judge_alone.json")
    args = ap.parse_args()

    qs = load_json_set(args.dataset)[:args.limit]
    backend = make_backend(args.judge)
    meter = ModelMeter()
    print(f"[judge_alone] judge={args.judge} n={len(qs)} t07_repeats={args.n_t07}")

    rows = []
    with ThreadPoolExecutor(max_workers=args.conc) as ex:
        futs = [ex.submit(one_question, q, backend, meter, args.n_t07) for q in qs]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 10 == 0:
                print(f"  {i}/{len(qs)}")

    n = len(rows)
    acc = lambda k: sum(r[k] == r["gold"] for r in rows) / n
    t07 = [sum(r["solo_t07"][i] == r["gold"] for r in rows) / n
           for i in range(args.n_t07)]
    # union over the 3 temp-0.7 draws = self-consistency coverage for a lone sonnet
    cov_t07 = sum(any(a == r["gold"] for a in r["solo_t07"]) for r in rows) / n
    followed = sum(r["judge_wrong"] == r["wrong_target"] for r in rows) / n

    summary = {
        "judge": args.judge, "n": n,
        "solo_t0": round(acc("solo_t0"), 3),
        "solo_t07_each": [round(x, 3) for x in t07],
        "solo_t07_mean": round(sum(t07) / len(t07), 3),
        "solo_t07_coverage": round(cov_t07, 3),
        "judge_empty": round(acc("judge_empty"), 3),
        "judge_wrong": round(acc("judge_wrong"), 3),
        "judge_followed_wrong_panel": round(followed, 3),
        "reference_verifiers_json": {
            "homo_v3_strongjudge": 0.525, "homo_coverage_C": 0.375,
            "hetero_v3_strongjudge": 0.625, "hetero_coverage_C": 0.600,
            "hetero_a_best": 0.525,
        },
    }
    msum = meter.summary()
    summary["est_cost"] = round(sum(
        est_cost_per_episode(args.judge, v["prompt_tokens"], v["completion_tokens"])
        for v in msum.values()), 4)

    print("\n--- SUMMARY ---")
    for k, v in summary.items():
        if k != "reference_verifiers_json":
            print(f"  {k:28} {v}")
    print("\n  vs verifiers.json: homo judge=0.525, hetero judge=0.625, hetero C=0.600")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump({"summary": summary, "meter": msum, "rows": rows},
              open(args.out, "w"), indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
