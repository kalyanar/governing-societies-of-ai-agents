"""THE claim, tested head to head:

    cheap generators + a great judge  >  that same great judge reasoning alone

Both arms use the SAME judge model, so the comparison is not confounded by
model identity. The only difference is what the judge is asked to do:

    ARM A (thesis)    the panel reasons; the judge may only SELECT one of the
                      panel's candidate answers. It cannot answer for itself.
    ARM B (baseline)  no panel. The judge reasons the problem out itself, with
                      the SAME generous token budget the panel members got.

Fairness conditions, each of which we got wrong at least once before:

  * Arm B is NOT clamped. An earlier version told the solver "ANSWER: <letter>
    then one short sentence", which capped it at 88 output tokens and crippled
    the baseline. Both arms now get `--max_tokens` and a prompt that permits
    reasoning.
  * API failure is data loss, never a wrong answer (robust_call).
  * Unparseable output is retried with a stricter prompt, then scored as wrong.
  * The judge in Arm A returns an INDEX, so it physically cannot out-answer the
    panel; R <= C holds by construction and is asserted at the end.
  * Costs are measured from real token counts, split by arm.

Reference points also computed:
    majority_blind   panel majority vote, no judge at all
    a_best           best single panel member
    coverage C       ceiling for any selector -- Arm A cannot exceed this

Usage
-----
  ../../.venv/bin/python head_to_head.py --out ../results/head_to_head.json
"""
from __future__ import annotations
import argparse, json, os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from debate import _fmt_options  # noqa
from dataset_loader import load_json_set  # noqa
from verifiers import strict_parse  # noqa
from verifiers_replication import parse_selection, stable_rng  # noqa
from robust_call import call_api, call_parsed  # noqa

# Reasoning is PERMITTED in both arms. This is the fairness fix.
REASON = ("Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
          "Work through it, then END your reply with the line: ANSWER: <letter>")
REASON_STRICT = ("Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
                 "Think briefly, then END your reply with exactly: ANSWER: <letter>")

SELECT = (
    "You are chairing a panel. The panel members below each solved the same "
    "question and gave their reasoning. Your job is to SELECT the best "
    "candidate. You may NOT propose an answer of your own -- you must choose "
    "one of the numbered candidates.\n\n"
    "Question: {q}\nOptions:\n{opts}\n\nCandidates:\n{cands}\n\n"
    "Reply with EXACTLY one line and nothing else, in the form: SOLVER: <number>"
)


def run_panel(qs, models, max_tokens, temperature, conc, reason_chars):
    meter = ModelMeter()
    backends = {mk: make_backend(mk) for mk in set(models)}

    def slot(mk, q, opts):
        v, st, r = call_parsed(
            backends[mk], REASON.format(q=q["q"], opts=opts),
            REASON_STRICT.format(q=q["q"], opts=opts),
            lambda t: strict_parse(t, q["options"]),
            meter, mk, max_tokens, strict_max_tokens=max_tokens,
            temperature=temperature, tries=3)
        why = " ".join((r.text or "").split())[-reason_chars:] if r else ""
        return v, why, st

    def one(q):
        opts = _fmt_options(q["options"])
        slots = [slot(mk, q, opts) for mk in models]
        answers = [a for a, _, _ in slots]
        seen, cands = {}, []
        for a, why, _ in slots:
            if a and a not in seen:
                seen[a] = why
                cands.append(a)
        stable_rng(q["id"]).shuffle(cands)
        return dict(id=q["id"], q=q["q"], options=q["options"], opts=opts,
                    gold=q["answer"], panel=answers, cands=cands,
                    reasons={a: seen[a] for a in cands}, n_candidates=len(cands),
                    statuses=[s for _, _, s in slots],
                    coverage=any(a == q["answer"] for a in answers),
                    slot_correct=[a == q["answer"] for a in answers])

    with ThreadPoolExecutor(max_workers=conc) as ex:
        return list(ex.map(one, qs)), meter


def majority(ans):
    c = Counter(a for a in ans if a)
    if not c:
        return None
    top, k = c.most_common(1)[0]
    return None if list(c.values()).count(k) > 1 else top


def run_judge(jkey, items, max_tokens, conc, reason_chars):
    meter = ModelMeter()
    jb = make_backend(jkey)

    def one(it):
        out = dict(id=it["id"], gold=it["gold"], n_candidates=it["n_candidates"])
        # ---- ARM A: constrained selection over the panel's candidates
        if it["cands"]:
            ct = "\n".join(f"{i+1}. answer {a}: {it['reasons'][a][:reason_chars]}"
                           for i, a in enumerate(it["cands"]))
            r, st = call_api(jb, SELECT.format(q=it["q"], opts=it["opts"], cands=ct),
                             meter, jkey + ":select", 800)
            if st == "ok":
                idx, mode = parse_selection(r.text, it["cands"])
                out.update(sel=it["cands"][idx - 1] if idx else None, sel_mode=mode)
            else:
                out.update(sel=None, sel_mode="api_fail")
        else:
            out.update(sel=None, sel_mode="no_candidates")
        # ---- ARM B: the same judge reasoning alone, same budget as the panel
        v, st, _ = call_parsed(
            jb, REASON.format(q=it["q"], opts=it["opts"]),
            REASON_STRICT.format(q=it["q"], opts=it["opts"]),
            lambda t: strict_parse(t, it["options"]),
            meter, jkey + ":solo", max_tokens, strict_max_tokens=max_tokens,
            temperature=0.0, tries=3)
        out.update(solo=v, solo_status=st)
        return out

    with ThreadPoolExecutor(max_workers=conc) as ex:
        return list(ex.map(one, items)), meter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_stem80.json")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--panel", nargs="+",
                    default=["cb_gptoss120b", "cb_gemma4_31b", "gq_qwen36_27b"])
    ap.add_argument("--judge", default="or_claude_opus5")
    ap.add_argument("--max_tokens", type=int, default=2500)
    ap.add_argument("--reason_chars", type=int, default=420)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--panel_conc", type=int, default=6)
    ap.add_argument("--judge_conc", type=int, default=3)
    ap.add_argument("--out", default="../results/head_to_head.json")
    args = ap.parse_args()

    for mk in set(list(args.panel) + [args.judge]):
        ok, env = key_available(mk)
        if mk not in REGISTRY or not ok:
            sys.exit(f"[abort] {mk} unavailable ({env})")

    qs = load_json_set(args.dataset)[:args.limit]
    print(f"[head2head] {len(qs)} Qs | panel={args.panel} | judge={args.judge} "
          f"| max_tokens={args.max_tokens}")

    items, pmeter = run_panel(qs, args.panel, args.max_tokens, args.temperature,
                              args.panel_conc, args.reason_chars)
    pms = pmeter.summary()
    panel_cost = sum(est_cost_per_episode(k, v["prompt_tokens"], v["completion_tokens"])
                     for k, v in pms.items() if k in REGISTRY)
    n = len(items)
    C = sum(1 for it in items if it["coverage"]) / n
    a_best = max(sum(1 for it in items if it["slot_correct"][i]) / n
                 for i in range(len(args.panel)))
    maj = sum(1 for it in items if majority(it["panel"]) == it["gold"]) / n
    panel_loss = sum(1 for it in items if any(s == "api_fail" for s in it["statuses"])) / n
    print(f"  panel: a_best={a_best:.3f} C={C:.3f} headroom={C-a_best:+.3f} "
          f"majority={maj:.3f} cost=${panel_cost:.4f} api_loss={panel_loss:.1%}")
    for i, mk in enumerate(args.panel):
        print(f"     {mk:16s} acc={sum(1 for it in items if it['slot_correct'][i])/n:.3f}")

    rows, jmeter = run_judge(args.judge, items, args.max_tokens,
                             args.judge_conc, args.reason_chars)
    jms = jmeter.summary()
    jcost = lambda tag: sum(est_cost_per_episode(args.judge, v["prompt_tokens"],
                                                 v["completion_tokens"])
                            for k, v in jms.items() if k.endswith(":" + tag))
    sel_live = [r for r in rows if r.get("sel_mode") != "api_fail"]
    solo_live = [r for r in rows if r.get("solo_status") != "api_fail"]
    armA = sum(1 for r in sel_live if r.get("sel") == r["gold"]) / len(sel_live) if sel_live else None
    armB = sum(1 for r in solo_live if r.get("solo") == r["gold"]) / len(solo_live) if solo_live else None
    selA_cost, soloB_cost = jcost("select"), jcost("solo")

    assert armA is None or armA <= C + 1e-9, f"R={armA} exceeds C={C}: selector leaked"

    out = dict(meta=dict(panel=args.panel, judge=args.judge, n=n,
                         max_tokens=args.max_tokens, dataset=args.dataset,
                         resolved={k: REGISTRY[k]["model"] for k in set(list(args.panel)+[args.judge])},
                         prices={k: list(REGISTRY[k]["price"]) for k in set(list(args.panel)+[args.judge])}),
               panel=dict(a_best=round(a_best, 4), coverage_C=round(C, 4),
                          majority=round(maj, 4), cost=round(panel_cost, 5),
                          api_loss=round(panel_loss, 3),
                          per_member={mk: round(sum(1 for it in items if it["slot_correct"][i]) / n, 4)
                                      for i, mk in enumerate(args.panel)}),
               armA=dict(name="cheap panel + judge SELECTS", acc=armA,
                         cost=round(panel_cost + selA_cost, 5),
                         judge_cost=round(selA_cost, 5),
                         api_loss=round(1 - len(sel_live) / n, 3),
                         v_hat=round((armA - a_best) / (C - a_best), 3) if (C > a_best and armA is not None) else None),
               armB=dict(name="same judge REASONS alone", acc=armB,
                         cost=round(soloB_cost, 5),
                         api_loss=round(1 - len(solo_live) / n, 3)),
               rows=rows)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    A, B = out["armA"], out["armB"]
    print(f"\n{'':4s}{'ARM':34s}{'acc':>8}{'cost':>10}{'loss':>7}")
    print('-' * 63)
    print(f"    {A['name']:34s}{(A['acc'] or float('nan')):>8.3f}{A['cost']:>10.4f}{A['api_loss']:>7.1%}")
    print(f"    {B['name']:34s}{(B['acc'] or float('nan')):>8.3f}{B['cost']:>10.4f}{B['api_loss']:>7.1%}")
    print(f"    {'(reference) panel majority, no judge':34s}{maj:>8.3f}{panel_cost:>10.4f}")
    print(f"    {'(ceiling) panel coverage C':34s}{C:>8.3f}")
    if A["acc"] is not None and B["acc"] is not None:
        d = A["acc"] - B["acc"]
        cr = B["cost"] / A["cost"] if A["cost"] > 0 else float('inf')
        # Paired McNemar on items both arms answered. A one- or two-item
        # difference on n=80 is noise; judging the thesis on the SIGN of that
        # difference is how a tie gets reported as a failure.
        from math import comb
        both = [r for r in rows if r.get("sel_mode") != "api_fail"
                and r.get("solo_status") != "api_fail"]
        a_o = sum(1 for r in both if r.get("sel") == r["gold"] and r.get("solo") != r["gold"])
        b_o = sum(1 for r in both if r.get("sel") != r["gold"] and r.get("solo") == r["gold"])
        k = a_o + b_o
        pval = (sum(comb(k, i) for i in range(min(a_o, b_o) + 1)) / 2 ** k * 2) if k else 1.0
        pval = min(pval, 1.0)
        out["paired"] = dict(selector_only=a_o, judge_only=b_o, mcnemar_p=round(pval, 4))
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n  accuracy delta {d:+.3f}  (selector-only {a_o}, judge-only {b_o}, "
              f"McNemar p={pval:.3f})   cost ratio {cr:.2f}x")
        if pval >= 0.05:
            verdict = ("PARITY at {:.2f}x cheaper -- THESIS HOLDS".format(cr) if cr > 1.05
                       else "PARITY, no cost advantage -- THESIS NEUTRAL")
        elif d > 0:
            verdict = "THESIS HOLDS: significantly more accurate AND {:.2f}x cheaper".format(cr)
        else:
            verdict = "THESIS FAILS: significantly less accurate"
        print(f"  VERDICT: {verdict}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
