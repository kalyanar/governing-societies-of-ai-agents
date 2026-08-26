"""
Experiment D-v4: does the verifier have to be expensive?

Motivation
----------
verifiers_replication / cheap_panel_frontier_verifier established that a
constrained selector's value depends on the SELECTOR, not just the panel:
Claude Opus 5 realized v_hat=+0.91 of the available headroom while DeepSeek-V3
realized v_hat=-0.25. But Opus 5 is the most expensive option on the menu, and
the deployed system then costs as much as that model answering alone -- which
kills the economic case.

The open question is whether verifier COMPETENCE saturates well below frontier
price. If a $0.03/1M model selects as well as a $5/1M model, the architecture is
cheap after all; if selection quality tracks price all the way up, it is not.

Design
------
The panel is run ONCE and its candidates+reasons are cached, so every verifier
sees byte-identical inputs -- the only variable is the verifier. For each
verifier we measure:

  select_fwd   constrained selection, candidates in canonical order
  select_rev   same candidates, order reversed  (paired position-bias control)
  solve_alone  the same model answering from scratch, no panel  (its own baseline)

and report accuracy, v_hat, order-stability, and real measured cost for each.

The three quantities that decide the architecture:
  deployed_cost = panel + select_fwd     (what you would actually pay)
  baseline_cost = that verifier solving alone
  ceiling       = panel coverage C -- no selector can exceed it

Usage
-----
  ../../.venv/bin/python verifier_price_ladder.py --out ../results/verifier_price_ladder.json
"""
from __future__ import annotations
import argparse, json, os, random, re, sys, zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import REGISTRY, key_available, make_backend, est_cost_per_episode  # noqa
from backends import ModelMeter  # noqa
from debate import _fmt_options  # noqa
from dataset_loader import load_json_set  # noqa
from verifiers import SOLVE, strict_parse  # noqa
from verifiers_constrained import SELECT, ALONE  # noqa
from verifiers_replication import parse_selection, stable_rng, _panel_answer, RETRY_SOLVE  # noqa
from robust_call import call_api, call_parsed  # noqa
from head_to_head import run_panel as h2h_run_panel  # noqa


def build_panel(questions, panel_models, temperature, conc):
    """Run the panel once; return per-question candidate sets + reasons."""
    meter = ModelMeter()
    backends = {mk: make_backend(mk) for mk in set(panel_models)}

    def one(q):
        opts = _fmt_options(q["options"])
        slots, retries = [], 0
        for mk in panel_models:
            a, why, r = _panel_answer(backends[mk], mk, q, opts, meter, temperature)
            retries += int(r)
            slots.append((a, why))
        answers = [a for a, _ in slots]
        seen, cands = {}, []
        for a, why in slots:
            if a and a not in seen:
                seen[a] = why
                cands.append(a)
        stable_rng(q["id"]).shuffle(cands)
        return dict(id=q["id"], q=q["q"], options=q["options"], opts=opts,
                    gold=q["answer"], panel=answers, cands=cands,
                    reasons={a: seen[a] for a in cands},
                    n_candidates=len(cands), panel_retries=retries,
                    coverage=any(a == q["answer"] for a in answers),
                    slot_correct=[a == q["answer"] for a in answers])

    with ThreadPoolExecutor(max_workers=conc) as ex:
        items = list(ex.map(one, questions))
    return items, meter


def _cand_text(cands, reasons):
    return "\n".join(f"{i+1}. answer {a}: {reasons[a][:110]}"
                     for i, a in enumerate(cands))


def run_verifier(vkey, items, conc):
    """Score one verifier on the cached panel. Returns a result dict."""
    meter = ModelMeter()
    jb = make_backend(vkey)

    def _pick(cs, tag, it):
        prompt = SELECT.format(q=it["q"], opts=it["opts"], cands=_cand_text(cs, it["reasons"]))
        r, st = call_api(jb, prompt, meter, vkey + ":" + tag, 600)
        if st != "ok":
            return None, None, "api_fail"
        idx, mode = parse_selection(r.text, cs)
        return (cs[idx - 1] if idx else None), idx, mode

    def one(it):
        out = dict(id=it["id"], gold=it["gold"], n_candidates=it["n_candidates"])
        cands = it["cands"]
        if cands:
            a, i, m = _pick(cands, "select_fwd", it)
            out.update(sel=a, sel_idx=i, sel_mode=m)
            if len(cands) >= 2:
                rev = list(reversed(cands))
                a2, i2, m2 = _pick(rev, "select_rev", it)
                out.update(rev=a2, rev_idx=i2, rev_mode=m2)
        # The verifier's own solo baseline. It gets the SAME parse-retry the
        # panel gets -- without it, a verbose model that buries the marker is
        # scored as wrong and its baseline is understated.
        v, st, _ = call_parsed(
            jb, ALONE.format(q=it["q"], opts=it["opts"]),
            RETRY_SOLVE.format(q=it["q"], opts=it["opts"]),
            lambda t: strict_parse(t, it["options"]),
            meter, vkey + ":solve_alone", 2000)
        out["alone"] = v
        out["alone_status"] = st
        return out

    with ThreadPoolExecutor(max_workers=conc) as ex:
        rows = list(ex.map(one, items))

    n = len(rows)
    msum = meter.summary()
    cost = lambda tag: sum(est_cost_per_episode(vkey, v["prompt_tokens"], v["completion_tokens"])
                           for k, v in msum.items() if k.endswith(":" + tag))

    # An API failure is DATA LOSS, not a wrong answer. Scoring it as incorrect
    # is exactly the silent-degradation bug this project's Methods section warns
    # about: a rate-limited verifier then looks like an incompetent one. Accuracy
    # is computed over calls that actually returned, and the loss rate is
    # reported so any run with meaningful loss can be discarded.
    def _acc(key, failmode):
        got = [r for r in rows if not (r.get(failmode) == "api_fail")]
        return (round(sum(1 for r in got if r.get(key) == r["gold"]) / len(got), 4)
                if got else None), round(1 - len(got) / n, 3)
    sel_acc, sel_loss = _acc("sel", "sel_mode")
    # api_fail is data loss (excluded); 'unparsed' is a real failure to answer
    # and is scored as incorrect, since the model did reply.
    alone_ok = [r for r in rows if r.get("alone_status") != "api_fail"]
    alone_acc = (round(sum(1 for r in alone_ok if r.get("alone") == r["gold"]) / len(alone_ok), 4)
                 if alone_ok else None)
    alone_loss = round(1 - len(alone_ok) / n, 3)
    alone_unparsed = round(sum(1 for r in rows if r.get("alone_status") == "unparsed") / n, 3)
    acc = lambda k: sum(1 for r in rows if r.get(k) == r["gold"]) / n
    multi = [r for r in rows if r["n_candidates"] >= 2 and r.get("sel_idx") and r.get("rev_idx")]
    m = len(multi)
    tok = lambda tag: (sum(v["prompt_tokens"] for k, v in msum.items() if k.endswith(":" + tag)) / n,
                       sum(v["completion_tokens"] for k, v in msum.items() if k.endswith(":" + tag)) / n)
    return dict(
        verifier=vkey, model=REGISTRY[vkey]["model"], price=list(REGISTRY[vkey]["price"]),
        n=n,
        select_acc=sel_acc, alone_acc=alone_acc,
        select_loss=sel_loss, alone_loss=alone_loss,
        alone_unparsed=alone_unparsed,
        unreliable=bool((sel_loss or 0) > 0.05 or (alone_loss or 0) > 0.05),
        select_cost=round(cost("select_fwd"), 5),
        alone_cost=round(cost("solve_alone"), 5),
        select_tok_in_out=[round(x, 1) for x in tok("select_fwd")],
        alone_tok_in_out=[round(x, 1) for x in tok("solve_alone")],
        invalid_rate=round(sum(1 for r in rows if r["n_candidates"] and not r.get("sel_idx")) / n, 3),
        mode_hist=dict(Counter(r.get("sel_mode") for r in rows)),
        n_choice=m,
        answer_stable=round(sum(1 for r in multi if r["sel"] and r["sel"] == r["rev"]) / m, 3) if m else None,
        slot_stable=round(sum(1 for r in multi if r["sel_idx"] == r["rev_idx"]) / m, 3) if m else None,
        slot1_rate=round(sum(1 for r in multi if r["sel_idx"] == 1) / m, 3) if m else None,
        slot1_chance=round(sum(1 / r["n_candidates"] for r in multi) / m, 3) if m else None,
        rows=rows,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_stem80.json")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--panel", nargs="+",
                    default=["or_gemma3_27b", "cheap_solar_pro4", "or_nova_lite"])
    ap.add_argument("--verifiers", nargs="+", default=[
        "v_qwen37_flash", "v_dsv4_flash", "v_gpt56_luna",
        "v_haiku45", "v_sonnet5", "or_claude_opus5"])   # gpt5_nano: hard 400 on this account
    ap.add_argument("--panel_max_tokens", type=int, default=2500)
    ap.add_argument("--reason_chars", type=int, default=420)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/verifier_price_ladder.json")
    args = ap.parse_args()

    for mk in set(list(args.panel) + list(args.verifiers)):
        if mk not in REGISTRY:
            sys.exit(f"[abort] '{mk}' not in registry")
        ok, env = key_available(mk)
        if not ok:
            sys.exit(f"[abort] {mk} unavailable (needs {env})")

    qs = load_json_set(args.dataset)[:args.limit]
    print(f"[ladder] {len(qs)} Qs | panel={args.panel}")
    items, pmeter = h2h_run_panel(qs, args.panel, args.panel_max_tokens,
                                  args.temperature, args.conc, args.reason_chars)
    pmsum = pmeter.summary()
    panel_cost = sum(est_cost_per_episode(k, v["prompt_tokens"], v["completion_tokens"])
                     for k, v in pmsum.items() if k in REGISTRY)
    n = len(items)
    C = sum(1 for it in items if it["coverage"]) / n
    a_best = max(sum(1 for it in items if it["slot_correct"][i]) / n
                 for i in range(len(args.panel)))
    unparsed = sum(1 for it in items if it["n_candidates"] == 0)
    print(f"  panel done: a_best={a_best:.3f}  C={C:.3f}  headroom={C-a_best:+.3f}  "
          f"cost=${panel_cost:.4f}  no-candidate items={unparsed}\n")

    out = dict(meta=dict(panel=args.panel, n=n, coverage_C=round(C, 4),
                         a_best=round(a_best, 4), panel_cost=round(panel_cost, 5),
                         panel_models={k: REGISTRY[k]["model"] for k in args.panel},
                         dataset=args.dataset), verifiers=[])
    hdr = (f"{'verifier':22s}{'$/1M in':>8}{'select':>8}{'alone':>7}{'v_hat':>7}"
           f"{'ansStab':>8}{'depl$':>8}{'base$':>8}{'ratio':>7}{'loss':>7}")
    print(hdr); print('-' * len(hdr))
    for vk in args.verifiers:
        r = run_verifier(vk, items, args.conc)
        vh = ((r["select_acc"] - a_best) / (C - a_best)) if (C > a_best and r["select_acc"] is not None) else None
        r["v_hat"] = round(vh, 3) if vh is not None else None
        r["deployed_cost"] = round(panel_cost + r["select_cost"], 5)
        r["cost_ratio_baseline_over_deployed"] = (
            round(r["alone_cost"] / r["deployed_cost"], 3) if r["deployed_cost"] > 0 else None)
        out["verifiers"].append(r)
        flag = "  <-- UNRELIABLE, DISCARD" if r["unreliable"] else ""
        print(f"{vk:22s}{r['price'][0]:>8.3f}"
              f"{(r['select_acc'] if r['select_acc'] is not None else float('nan')):>8.3f}"
              f"{(r['alone_acc'] if r['alone_acc'] is not None else float('nan')):>7.3f}"
              f"{(r['v_hat'] if r['v_hat'] is not None else float('nan')):>7.2f}"
              f"{(r['answer_stable'] or 0):>8.3f}{r['deployed_cost']:>8.4f}"
              f"{r['alone_cost']:>8.4f}{(r['cost_ratio_baseline_over_deployed'] or 0):>7.2f}"
              f"{max(r['select_loss'],r['alone_loss']):>7.1%}{flag}")
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
    print(f"\nwrote {args.out}")
    tot = panel_cost + sum(v["select_cost"] + v["alone_cost"] for v in out["verifiers"])
    print(f"approx run cost (excl. reversal arm) ${tot:.4f}")


if __name__ == "__main__":
    main()
