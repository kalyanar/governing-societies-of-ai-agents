"""
Experiment D-v5: does the verifier need to read the source, or only the answers?

Motivation
----------
Cost algebra (input-token-equivalents, p_out/p_in ~ 5):

    solve        = Q + 5*O_solve
    select_full  = Q + K + 5*O_select      <- verifier re-reads the whole input
    select_blind =     K + 5*O_select      <- verifier sees only candidates+rationale

With select_full the task input Q appears on BOTH sides, so it cancels and the
ratio tends to 1.0 no matter how big the input gets -- which is what the earlier
run measured (0.98x on a 271-token question). With select_blind, Q appears only
on the solve side, so the saving grows without bound in Q: 1.6x at Q=271, 12x at
Q=5000, 45x at Q=20000.

That is the whole economic case for the architecture. It is only available if a
verifier can pick the right candidate WITHOUT the source -- judging the
rationales against each other rather than against the question. This script
measures the accuracy cost of that blindness.

Design
------
The panel is run once with a JUSTIFY prompt (answer + 2-3 sentences of
reasoning), so a blind verifier has something substantive to arbitrate. Then
each verifier is scored three ways on byte-identical candidates:

    sighted   question + options + candidates(answer+rationale)
    blind     candidates(answer+rationale) only -- no question, no options
    alone     the verifier solving from scratch (its own baseline)

Reported per verifier: accuracy for each mode, measured cost, and the
extrapolated cost ratio at larger task inputs.

Usage
-----
  ../../.venv/bin/python blind_selector.py --out ../results/blind_selector.json
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
from verifiers_constrained import ALONE  # noqa
from verifiers_replication import parse_selection, stable_rng  # noqa
from robust_call import call_api, call_parsed  # noqa

# Panel prompt: a real justification, so blind arbitration is possible at all.
JUSTIFY = (
    "Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
    "Reply with 'ANSWER: <letter>' on the first line, then 2-3 sentences "
    "justifying that choice. Make the justification self-contained: state the "
    "reasoning, not just the conclusion."
)
JUSTIFY_RETRY = (
    "Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
    "First line must be exactly 'ANSWER: <letter>'. Then one sentence of reasoning."
)

SIGHTED = (
    "You are chairing a panel. The panel has proposed the candidate answers below. "
    "Your job is to SELECT the best candidate. You may NOT propose an answer of "
    "your own -- you must choose one of the numbered candidates.\n\n"
    "Question: {q}\nOptions:\n{opts}\n\nCandidates:\n{cands}\n\n"
    "Reply with EXACTLY one line and nothing else, in the form: SOLVER: <number>"
)
# Identical task, minus the source. The verifier must arbitrate the reasoning.
BLIND = (
    "You are chairing a panel. Several solvers answered the same question and "
    "each gave their reasoning below. You do NOT have the question itself -- "
    "judge which reasoning is soundest and most likely correct on its own terms. "
    "You may NOT propose an answer of your own; choose one of the numbered "
    "candidates.\n\nCandidates:\n{cands}\n\n"
    "Reply with EXACTLY one line and nothing else, in the form: SOLVER: <number>"
)


def build_panel(questions, panel_models, temperature, conc, reason_chars):
    meter = ModelMeter()
    backends = {mk: make_backend(mk) for mk in set(panel_models)}

    def one_slot(mk, q, opts):
        b = backends[mk]
        r = b.generate(JUSTIFY.format(q=q["q"], opts=opts), max_tokens=300,
                       temperature=temperature)
        meter.add(mk, r)
        a = strict_parse(r.text, q["options"]) if r.ok else None
        if a is None:
            r = b.generate(JUSTIFY_RETRY.format(q=q["q"], opts=opts), max_tokens=120,
                           temperature=0.0)
            meter.add(mk, r)
            a = strict_parse(r.text, q["options"]) if r.ok else None
        why = " ".join((r.text or "").split())[:reason_chars]
        return a, why

    def one(q):
        opts = _fmt_options(q["options"])
        slots = [one_slot(mk, q, opts) for mk in panel_models]
        answers = [a for a, _ in slots]
        seen, cands = {}, []
        for a, why in slots:
            if a and a not in seen:
                seen[a] = why
                cands.append(a)
        stable_rng(q["id"]).shuffle(cands)
        return dict(id=q["id"], q=q["q"], options=q["options"], opts=opts,
                    gold=q["answer"], panel=answers, cands=cands,
                    reasons={a: seen[a] for a in cands}, n_candidates=len(cands),
                    coverage=any(a == q["answer"] for a in answers),
                    slot_correct=[a == q["answer"] for a in answers])

    with ThreadPoolExecutor(max_workers=conc) as ex:
        items = list(ex.map(one, questions))
    return items, meter


def _cands(it, reason_chars):
    return "\n".join(f"{i+1}. answer {a}: {it['reasons'][a][:reason_chars]}"
                     for i, a in enumerate(it["cands"]))


def run_verifier(vkey, items, conc, reason_chars):
    meter = ModelMeter()
    jb = make_backend(vkey)

    def _sel(prompt, tag, it):
        r, st = call_api(jb, prompt, meter, vkey + ":" + tag, 600)
        if st != "ok":
            return None, "api_fail"
        i, m = parse_selection(r.text, it["cands"])
        return (it["cands"][i - 1] if i else None), m

    def one(it):
        out = dict(id=it["id"], gold=it["gold"], n_candidates=it["n_candidates"])
        if it["cands"]:
            ct = _cands(it, reason_chars)
            a1, m1 = _sel(SIGHTED.format(q=it["q"], opts=it["opts"], cands=ct),
                          "sighted", it)
            out.update(sighted=a1, sighted_mode=m1)
            a2, m2 = _sel(BLIND.format(cands=ct), "blind", it)
            out.update(blind=a2, blind_mode=m2)
        v, st, _ = call_parsed(
            jb, ALONE.format(q=it["q"], opts=it["opts"]),
            JUSTIFY_RETRY.format(q=it["q"], opts=it["opts"]),
            lambda t: strict_parse(t, it["options"]),
            meter, vkey + ":alone", 400)
        out["alone"] = v
        out["alone_status"] = st
        return out

    with ThreadPoolExecutor(max_workers=conc) as ex:
        rows = list(ex.map(one, items))

    n = len(rows)
    ms = meter.summary()
    # API failure = data loss, not a wrong answer (see verifier_price_ladder).
    def _live(k):
        # exclude only true API failures; a returned-but-wrong answer still counts
        if k == "alone":
            return [r for r in rows if r.get("alone_status") != "api_fail"]
        return [r for r in rows if r.get(k + "_mode") != "api_fail"]
    def acc(k):
        got = _live(k)
        return round(sum(1 for r in got if r.get(k) == r["gold"]) / len(got), 4) if got else None
    def loss(k):
        return round(1 - len(_live(k)) / n, 3)
    cost = lambda t: round(sum(est_cost_per_episode(vkey, v["prompt_tokens"],
                                                    v["completion_tokens"])
                               for k, v in ms.items() if k.endswith(":" + t)), 5)
    tok = lambda t: [round(sum(v["prompt_tokens"] for k, v in ms.items()
                               if k.endswith(":" + t)) / n, 1),
                     round(sum(v["completion_tokens"] for k, v in ms.items()
                               if k.endswith(":" + t)) / n, 1)]
    return dict(verifier=vkey, model=REGISTRY[vkey]["model"],
                price=list(REGISTRY[vkey]["price"]), n=n,
                sighted_acc=acc("sighted"), blind_acc=acc("blind"), alone_acc=acc("alone"),
                sighted_loss=loss("sighted"), blind_loss=loss("blind"), alone_loss=loss("alone"),
                unreliable=bool(max(loss("sighted"), loss("blind"), loss("alone")) > 0.05),
                sighted_cost=cost("sighted"), blind_cost=cost("blind"), alone_cost=cost("alone"),
                sighted_tok=tok("sighted"), blind_tok=tok("blind"), alone_tok=tok("alone"),
                invalid_sighted=round(sum(1 for r in rows if r["n_candidates"] and not r.get("sighted")) / n, 3),
                invalid_blind=round(sum(1 for r in rows if r["n_candidates"] and not r.get("blind")) / n, 3),
                mode_hist_blind=dict(Counter(r.get("blind_mode") for r in rows)),
                rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_stem80.json")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--panel", nargs="+",
                    default=["or_gemma3_27b", "cheap_solar_pro4", "or_nova_lite"])
    ap.add_argument("--verifiers", nargs="+",
                    default=["or_claude_opus5", "v_sonnet5", "v_dsv4_flash"])
    ap.add_argument("--reason_chars", type=int, default=420)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/blind_selector.json")
    args = ap.parse_args()

    for mk in set(list(args.panel) + list(args.verifiers)):
        ok, env = key_available(mk)
        if mk not in REGISTRY or not ok:
            sys.exit(f"[abort] {mk} unavailable")

    qs = load_json_set(args.dataset)[:args.limit]
    print(f"[blind] {len(qs)} Qs | panel={args.panel} | reason_chars={args.reason_chars}")
    items, pm = build_panel(qs, args.panel, args.temperature, args.conc, args.reason_chars)
    pms = pm.summary()
    panel_cost = sum(est_cost_per_episode(k, v["prompt_tokens"], v["completion_tokens"])
                     for k, v in pms.items() if k in REGISTRY)
    n = len(items)
    C = sum(1 for it in items if it["coverage"]) / n
    a_best = max(sum(1 for it in items if it["slot_correct"][i]) / n
                 for i in range(len(args.panel)))
    avg_reason = sum(len(it["reasons"][a]) for it in items for a in it["cands"]) / \
                 max(sum(it["n_candidates"] for it in items), 1)
    print(f"  panel: a_best={a_best:.3f} C={C:.3f} headroom={C-a_best:+.3f} "
          f"cost=${panel_cost:.4f} avg_rationale={avg_reason:.0f} chars "
          f"no-cand={sum(1 for it in items if it['n_candidates']==0)}\n")

    out = dict(meta=dict(panel=args.panel, n=n, coverage_C=round(C, 4),
                         a_best=round(a_best, 4), panel_cost=round(panel_cost, 5),
                         avg_rationale_chars=round(avg_reason, 1),
                         panel_models={k: REGISTRY[k]["model"] for k in args.panel}),
               verifiers=[])
    hdr = (f"{'verifier':20s}{'sighted':>9}{'blind':>8}{'alone':>8}"
           f"{'sight$':>9}{'blind$':>9}{'alone$':>9}{'blind in/out':>15}{'loss':>7}")
    print(hdr); print('-' * len(hdr))
    for vk in args.verifiers:
        r = run_verifier(vk, items, args.conc, args.reason_chars)
        vh = lambda a: round((a - a_best) / (C - a_best), 3) if (C > a_best and a is not None) else None
        r["v_hat_sighted"] = vh(r["sighted_acc"]); r["v_hat_blind"] = vh(r["blind_acc"])
        r["deployed_sighted"] = round(panel_cost + r["sighted_cost"], 5)
        r["deployed_blind"] = round(panel_cost + r["blind_cost"], 5)
        out["verifiers"].append(r)
        nan=float('nan')
        flag = "  <-- UNRELIABLE" if r["unreliable"] else ""
        print(f"{vk:20s}{(r['sighted_acc'] if r['sighted_acc'] is not None else nan):>9.3f}"
              f"{(r['blind_acc'] if r['blind_acc'] is not None else nan):>8.3f}"
              f"{(r['alone_acc'] if r['alone_acc'] is not None else nan):>8.3f}"
              f"{r['sighted_cost']:>9.4f}{r['blind_cost']:>9.4f}{r['alone_cost']:>9.4f}"
              f"{str(r['blind_tok']):>15}"
              f"{max(r['sighted_loss'],r['blind_loss'],r['alone_loss']):>7.1%}{flag}")
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
