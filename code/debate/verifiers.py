"""
Experiment D: calibrated verifiers realize the coverage ceiling (validates the
competence-band law R = a_best + v*(C - a_best)).

A panel answers verifiable STEM questions. We then aggregate with verifiers of INCREASING
quality v and measure realized accuracy R:
  v0  blind majority vote          (v ~ 0)
  v1  self-verification + majority  (each agent re-checks its own answer)
  v2  weak cross-judge              (a cheap model picks among the panel's answers)
  v3  strong judge                  (a strong model picks among the panel's answers)
  oracle  coverage ceiling C = P(>=1 panel answer correct)   (v = 1, upper bound)

Run for a HOMOGENEOUS panel (N samples of one cheap model = self-consistency) and a
HETEROGENEOUS panel (N different cheap models). Heterogeneity lowers error correlation,
raising C; a good verifier should therefore extract MORE from the hetero panel. The
empirical verifier quality at each level is v_hat = (R - a_best)/(C - a_best).
"""
from __future__ import annotations
import argparse, json, os, sys, re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from debate import _fmt_options, parse_answer  # noqa
from dataset_loader import load_json_set  # noqa

SOLVE = ("Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
         "Reply MUST begin with 'ANSWER: <letter>' then one short sentence.")
RECHECK = ("Question: {q}\nOptions:\n{opts}\n\nA solver answered {ans}. Re-examine "
           "carefully and give your best final answer. Reply 'ANSWER: <letter>' then "
           "one short sentence.")
JUDGE = ("Select the best answer to this question by weighing several solvers and your "
         "own judgement.\n\nQuestion: {q}\nOptions:\n{opts}\n\nSolvers:\n{panel}\n\n"
         "Respond with EXACTLY one line and nothing else, in the form: ANSWER: <letter>")


def strict_parse(text, options=None):
    """Parse an option letter WITHOUT the bare-standalone-letter fallback (which spuriously
    matches prose words like 'I' or 'A'). Returns None if no explicit marker is present."""
    m = re.search(r"ANSWER:\s*\(?([A-J])\)?", text or "", re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"\boption\s+([A-J])\b|\(([A-J])\)", text or "", re.I)
    if m:
        return (m.group(1) or m.group(2)).upper()
    if options:
        tl = (text or "").lower()
        hits = [L for L, t in options.items() if t and len(t) > 2 and t.lower() in tl]
        if len(hits) == 1:
            return hits[0]
    return None


def solo(backend, q, meter, mk, temperature=0.7):
    r = backend.generate(SOLVE.format(q=q["q"], opts=_fmt_options(q["options"])),
                         max_tokens=150, temperature=temperature)
    meter.add(mk, r)
    return parse_answer(r.text, q["options"]) if r.ok else None, (r.text or "")[:160]


def recheck(backend, q, ans, meter, mk):
    r = backend.generate(RECHECK.format(q=q["q"], opts=_fmt_options(q["options"]), ans=ans),
                         max_tokens=150, temperature=0.0)
    meter.add(mk, r)
    return parse_answer(r.text, q["options"]) if r.ok else ans


def judge(backend, q, panel, meter, mk):
    txt = "\n".join(f"- answer {a}: {why[:120]}" for a, why in panel if a)
    r = backend.generate(JUDGE.format(q=q["q"], opts=_fmt_options(q["options"]), panel=txt),
                         max_tokens=120, temperature=0.0)
    meter.add(mk + ":judge", r)
    return strict_parse(r.text, q["options"]) if r.ok else None


def majority(ans):
    c = Counter(a for a in ans if a)
    if not c:
        return None
    top, n = c.most_common(1)[0]
    return None if list(c.values()).count(n) > 1 else top


def per_question(q, panel_models, backends, meter, weak_judge, strong_judge):
    gold = q["answer"]
    # 1) solo answers (one independent sample per panel slot)
    solos = [solo(backends[mk], q, meter, mk) for mk in panel_models]
    ans = [a for a, _ in solos]
    best_each = ans                                   # per-slot correctness handled by caller
    # 2) self-verify
    sv = [recheck(backends[mk], q, a, meter, mk) if a else a
          for mk, (a, _) in zip(panel_models, solos)]
    # 3) judges weigh the solo panel
    wj = judge(backends[weak_judge], q, solos, meter, weak_judge)
    sj = judge(backends[strong_judge], q, solos, meter, strong_judge)
    return dict(
        gold=gold, solo=ans,
        v0_majority=majority(ans),
        v1_selfverify=majority(sv),
        v2_weakjudge=wj,
        v3_strongjudge=sj,
        coverage=any(a == gold for a in ans),         # >=1 correct (oracle ceiling)
        best_slot=[a == gold for a in ans],
    )


def run_panel(name, panel_models, questions, weak_judge, strong_judge, conc=8):
    meter = ModelMeter()
    backends = {mk: make_backend(mk) for mk in set(panel_models + [weak_judge, strong_judge])}
    rows = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(per_question, q, panel_models, backends, meter,
                          weak_judge, strong_judge) for q in questions]
        for f in as_completed(futs):
            rows.append(f.result())
    n = len(rows)
    acc = lambda key: sum(r[key] == r["gold"] for r in rows) / n
    C = sum(r["coverage"] for r in rows) / n
    # best single slot accuracy (max over panel positions)
    nslot = len(panel_models)
    a_best = max(sum(r["best_slot"][i] for r in rows) / n for i in range(nslot))
    levels = {"v0_majority": acc("v0_majority"), "v1_selfverify": acc("v1_selfverify"),
              "v2_weakjudge": acc("v2_weakjudge"), "v3_strongjudge": acc("v3_strongjudge"),
              "oracle_C": C}
    vhat = {k: (None if C <= a_best else round((R - a_best) / (C - a_best), 2))
            for k, R in levels.items()}
    msum = meter.summary()
    cost = sum(est_cost_per_episode(k.split(":")[0], v["prompt_tokens"], v["completion_tokens"])
               for k, v in msum.items() if k.split(":")[0] in REGISTRY)
    return dict(name=name, panel=panel_models, n=n, a_best=round(a_best, 3),
                coverage_C=round(C, 3), levels={k: round(v, 3) for k, v in levels.items()},
                v_hat=vhat, est_cost=round(cost, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_mathsci.json")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--homo_model", default="gpt4o_mini")
    ap.add_argument("--hetero", nargs="+", default=["gpt4o_mini", "qwen72b", "llama70b"])
    ap.add_argument("--weak_judge", default="gpt4o_mini")
    ap.add_argument("--strong_judge", default="claude_sonnet")
    ap.add_argument("--out", default="../results/verifiers.json")
    args = ap.parse_args()
    qs = load_json_set(args.dataset)[:args.limit]
    homo_panel = [args.homo_model] * len(args.hetero)
    print(f"[verifiers] {len(qs)} Qs | homo={homo_panel} hetero={args.hetero} "
          f"judges weak={args.weak_judge} strong={args.strong_judge}")
    out = {}
    for name, panel in [("homo", homo_panel), ("hetero", args.hetero)]:
        res = run_panel(name, panel, qs, args.weak_judge, args.strong_judge)
        out[name] = res
        print(f"\n--- {name}: {panel} ---")
        print(f"  a_best={res['a_best']}  coverage_C={res['coverage_C']}  cost=${res['est_cost']}")
        for k in ["v0_majority", "v1_selfverify", "v2_weakjudge", "v3_strongjudge", "oracle_C"]:
            print(f"  {k:16} R={res['levels'][k]:.3f}  v_hat={res['v_hat'][k]}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
