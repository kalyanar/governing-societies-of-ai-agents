"""
Experiment D-v2: a CONSTRAINED verifier that may only SELECT from the panel.

Why this replaces the original verifiers.py judge
-------------------------------------------------
In verifiers.py the "strong judge" (claude_sonnet) was shown the panel's answers
and asked for `ANSWER: <letter>`. Nothing stopped it emitting a letter no panel
member had proposed -- and judge_alone.py showed it scored 0.625 on these same
40 items with NO panel at all, exactly its panel-assisted score. It was solving,
not selecting, which is why it "exceeded" the coverage ceiling C (impossible for
a true selector) and produced a meaningless v_hat of +1.33.

That is also the wrong model of a governance aggregator. A committee produces
options and the chair picks one of them; the chair does not substitute their own
answer. This script enforces exactly that:

  * the judge sees the panel's DISTINCT candidate answers, labelled by index
  * it must reply `SOLVER: <n>` -- an index into the candidate list
  * an index cannot express an answer outside the panel's span, so R <= C holds
    BY CONSTRUCTION and v_hat = (R - a_best)/(C - a_best) is interpretable again

Candidate order is randomised per question (seeded by question id) so a judge
that always picks slot 1 is detectable rather than lucky; `position_hist`
reports the picked-slot distribution.

Arms
----
  constrained   judge picks a solver index (the governance-realistic aggregator)
  unconstrained the original free-form `ANSWER: <letter>` judge, for contrast
  alone         judge answers with no panel shown, the confound control

Run for a homogeneous panel (3 samples of one cheap model) and a heterogeneous
panel (3 distinct cheap models); heterogeneity should raise C, and only the
constrained arm can honestly be said to "realize" it.

Usage
-----
  ../../.venv/bin/python verifiers_constrained.py --out ../results/verifiers_constrained.json
"""
from __future__ import annotations
import argparse, json, os, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from debate import _fmt_options  # noqa
from dataset_loader import load_json_set  # noqa
from verifiers import SOLVE, strict_parse  # noqa

# The judge may only return an INDEX into the candidate list.
SELECT = (
    "You are chairing a panel. The panel has proposed the candidate answers below. "
    "Your job is to SELECT the best candidate. You may NOT propose an answer of "
    "your own -- you must choose one of the numbered candidates.\n\n"
    "Question: {q}\nOptions:\n{opts}\n\nCandidates:\n{cands}\n\n"
    "Reply with EXACTLY one line and nothing else, in the form: SOLVER: <number>"
)
# free-form judge, reproduced from verifiers.py for a like-for-like contrast
FREEFORM = (
    "Select the best answer to this question by weighing several solvers and your "
    "own judgement.\n\nQuestion: {q}\nOptions:\n{opts}\n\nSolvers:\n{panel}\n\n"
    "Respond with EXACTLY one line and nothing else, in the form: ANSWER: <letter>"
)
ALONE = SOLVE  # no panel shown at all


def parse_index(text, n):
    """Return a 1-based candidate index, or None if the judge did not give one.

    Deliberately strict: only an explicit `SOLVER: <n>` counts. A bare-number
    fallback would match arithmetic in the judge's own working ("120 mph" -> 120)
    and silently fabricate a selection -- the same class of parsing artifact the
    original verifier-judge suffered from. Takes the LAST marker so a judge that
    reasons first and concludes with the marker parses correctly.
    """
    ms = re.findall(r"SOLVER:\s*#?(\d+)", text or "", re.I)
    if not ms:
        return None
    i = int(ms[-1])
    return i if 1 <= i <= n else None


def per_question(q, panel_models, backends, meter, judge_key, temperature):
    gold = q["answer"]
    opts = _fmt_options(q["options"])

    # ---- panel: one independent sample per slot
    slots = []
    for mk in panel_models:
        r = backends[mk].generate(SOLVE.format(q=q["q"], opts=opts),
                                  max_tokens=150, temperature=temperature)
        meter.add(mk, r)
        slots.append((strict_parse(r.text, q["options"]) if r.ok else None,
                      (r.text or "").strip()[:140]))

    answers = [a for a, _ in slots]
    # distinct candidates, randomised order (seeded => reproducible)
    seen, cands = {}, []
    for a, why in slots:
        if a and a not in seen:
            seen[a] = why
            cands.append(a)
    rng = random.Random(hash(q["id"]) & 0xFFFFFFFF)
    rng.shuffle(cands)

    out = dict(id=q["id"], gold=gold, panel=answers,
               n_candidates=len(cands),
               coverage=any(a == gold for a in answers),
               slot_correct=[a == gold for a in answers])

    jb = backends[judge_key]

    # ---- constrained: must return an index into `cands`
    if cands:
        cand_txt = "\n".join(f"{i+1}. answer {a}: {seen[a][:110]}"
                             for i, a in enumerate(cands))
        # generous budget: the judge often reasons before emitting the marker,
        # and truncating that reasoning is what produced spurious "invalid" rows
        r = jb.generate(SELECT.format(q=q["q"], opts=opts, cands=cand_txt),
                        max_tokens=300, temperature=0.0)
        meter.add(judge_key + ":constrained", r)
        idx = parse_index(r.text, len(cands)) if r.ok else None
        out["constrained"] = cands[idx - 1] if idx else None
        out["constrained_idx"] = idx
        out["constrained_invalid"] = (idx is None)
        out["constrained_raw"] = (r.text or "").strip()[-160:]
        # Did the judge try to escape the constraint by naming an option letter
        # that was not among the candidates? That is refusal-to-endorse, and is
        # different from a malformed reply.
        esc = strict_parse(r.text, q["options"]) if (idx is None and r.ok) else None
        out["constrained_escaped_to"] = esc if (esc and esc not in cands) else None
    else:
        out["constrained"] = None
        out["constrained_idx"] = None
        out["constrained_invalid"] = True

    # ---- unconstrained: free-form letter (the original design)
    panel_txt = "\n".join(f"- answer {a}: {why[:110]}" for a, why in slots if a)
    r = jb.generate(FREEFORM.format(q=q["q"], opts=opts, panel=panel_txt),
                    max_tokens=120, temperature=0.0)
    meter.add(judge_key + ":freeform", r)
    ff = strict_parse(r.text, q["options"]) if r.ok else None
    out["unconstrained"] = ff
    # did the free-form judge answer OUTSIDE the panel's span?
    out["went_outside_panel"] = bool(ff and ff not in set(a for a in answers if a))

    # ---- alone: no panel at all
    r = jb.generate(ALONE.format(q=q["q"], opts=opts), max_tokens=150,
                    temperature=0.0)
    meter.add(judge_key + ":alone", r)
    out["alone"] = strict_parse(r.text, q["options"]) if r.ok else None
    return out


def majority(ans):
    c = Counter(a for a in ans if a)
    if not c:
        return None
    top, n = c.most_common(1)[0]
    return None if list(c.values()).count(n) > 1 else top


def run_panel(name, panel_models, questions, judge_key, temperature, conc):
    meter = ModelMeter()
    backends = {mk: make_backend(mk)
                for mk in set(list(panel_models) + [judge_key])}
    rows = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(per_question, q, panel_models, backends, meter,
                          judge_key, temperature) for q in questions]
        for f in as_completed(futs):
            rows.append(f.result())

    n = len(rows)
    acc = lambda k: round(sum(r.get(k) == r["gold"] for r in rows) / n, 3)
    C = round(sum(r["coverage"] for r in rows) / n, 3)
    a_best = round(max(sum(r["slot_correct"][i] for r in rows) / n
                       for i in range(len(panel_models))), 3)
    maj = round(sum(majority(r["panel"]) == r["gold"] for r in rows) / n, 3)

    def vhat(R):
        return None if C <= a_best else round((R - a_best) / (C - a_best), 2)

    levels = {"majority_blind": maj, "constrained_judge": acc("constrained"),
              "unconstrained_judge": acc("unconstrained"),
              "judge_alone_no_panel": acc("alone"), "coverage_C": C}
    msum = meter.summary()
    cost = sum(est_cost_per_episode(k.split(":")[0], v["prompt_tokens"],
                                    v["completion_tokens"])
               for k, v in msum.items() if k.split(":")[0] in REGISTRY)
    return dict(
        name=name, panel=panel_models, judge=judge_key, n=n,
        a_best=a_best, coverage_C=C, levels=levels,
        v_hat={k: vhat(v) for k, v in levels.items() if v is not None},
        constrained_invalid=round(sum(r["constrained_invalid"] for r in rows) / n, 3),
        unconstrained_went_outside=round(
            sum(r["went_outside_panel"] for r in rows) / n, 3),
        position_hist=dict(Counter(r["constrained_idx"] for r in rows)),
        est_cost=round(cost, 3), rows=rows,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_mathsci.json")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--homo_model", default="gpt4o_mini")
    ap.add_argument("--hetero", nargs="+",
                    default=["gpt4o_mini", "or_qwen25_72b", "or_llama33_70b"])
    ap.add_argument("--judge", default="claude_sonnet")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/verifiers_constrained.json")
    args = ap.parse_args()

    for mk in set(args.hetero + [args.homo_model, args.judge]):
        ok, info = key_available(mk)
        if not ok:
            raise SystemExit(f"no access for {mk} ({info})")

    qs = load_json_set(args.dataset)[:args.limit]
    homo_panel = [args.homo_model] * len(args.hetero)
    print(f"[verifiers-constrained] {len(qs)} Qs  judge={args.judge}\n"
          f"  homo={homo_panel}\n  hetero={args.hetero}")

    out = {}
    for name, panel in [("homo", homo_panel), ("hetero", args.hetero)]:
        res = run_panel(name, panel, qs, args.judge, args.temperature, args.conc)
        out[name] = res
        print(f"\n--- {name}  a_best={res['a_best']}  C={res['coverage_C']}  "
              f"${res['est_cost']}")
        for k in ["majority_blind", "constrained_judge", "unconstrained_judge",
                  "judge_alone_no_panel", "coverage_C"]:
            v = res["levels"][k]
            print(f"   {k:22s} R={v:.3f}  v_hat={res['v_hat'].get(k)}")
        print(f"   constrained invalid-index rate : {res['constrained_invalid']}")
        print(f"   unconstrained answered OUTSIDE : {res['unconstrained_went_outside']}")
        print(f"   picked-slot histogram          : {res['position_hist']}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
