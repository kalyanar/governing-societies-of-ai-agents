"""
Experiment D-v3: independent replication of the constrained-verifier ladder on a
COMPLETELY DIFFERENT model set, plus a paired order-reversal control for
position bias.

Why this exists
---------------
verifiers_constrained.py established, on one model set, that

  * a monoculture panel has NO coverage headroom (C == a_best exactly),
  * a heterogeneous panel does (C > a_best), which blind majority voting
    destroys and a constrained selector partially realizes,
  * a free-form judge escapes the panel on 25-32% of items and so is not
    measuring aggregation at all.

Two open questions remained:

  1. Is any of that a property of those particular models? The original used
     gpt4o_mini (panel) and claude_sonnet (judge). This script shares NO model
     and NO vendor with that run, and uses a near-disjoint item set
     (questions_stem80, 2/40 overlap with questions_mathsci).

  2. Is the constrained selector choosing on content, or on position? The
     original showed 10/11 slot-1 picks among homo items that offered a real
     choice (z=2.71) -- suggestive, but n=11. Candidate order was randomised,
     which detects bias only against a uniform null and needs many items.
     A PAIRED test is far sharper: show the same candidates twice, once in
     order and once reversed. A content-driven judge returns the same ANSWER
     both times; a position-driven judge returns the same SLOT both times.
     That distinction needs no null model and no large n.

Position-bias metrics reported (over items with >=2 distinct candidates):
    answer_stable    same answer chosen under both orders  (content-driven)
    slot_stable      same slot index chosen under both orders (position-driven)
    flip_rate        1 - answer_stable
    slot1_rate_fwd   share of forward-order picks landing on slot 1

Also fixes a reproducibility defect inherited from verifiers_constrained.py:
that script seeds the candidate shuffle with Python's built-in hash(), which is
randomised per process by PYTHONHASHSEED, so its "seeded => reproducible"
comment does not hold. We use crc32 of the id bytes, which is stable.

Usage
-----
  ../../.venv/bin/python verifiers_replication.py --out ../results/verifiers_replication.json
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
from verifiers_constrained import SELECT, FREEFORM, ALONE, parse_index  # noqa


def stable_rng(qid: str) -> random.Random:
    """Deterministic across processes, unlike hash() under PYTHONHASHSEED."""
    return random.Random(zlib.crc32(str(qid).encode()) & 0xFFFFFFFF)


def parse_selection(text, cands):
    """Resolve the judge's reply to a 1-based index into `cands`.

    Primary form is `SOLVER: <n>`. Some judges instead answer `SOLVER: <letter>`
    -- expressing a genuine selection in the wrong notation. We repair that ONLY
    when the letter is actually one of the candidates; a letter outside the
    candidate span is an escape attempt, not a selection, and stays invalid so
    the R <= C guarantee is preserved. Returns (idx, mode) where mode is one of
    'index' | 'letter_repaired' | 'escape' | 'none'.
    """
    t = text or ""
    ms = re.findall(r"SOLVER:\s*#?(\d+)", t, re.I)
    if ms:
        i = int(ms[-1])
        if 1 <= i <= len(cands):
            return i, "index"
    ls = re.findall(r"(?:SOLVER|ANSWER):\s*\(?([A-J])\)?", t, re.I)
    if ls:
        L = ls[-1].upper()
        if L in cands:
            return cands.index(L) + 1, "letter_repaired"
        return None, "escape"
    return None, "none"


def _select(jb, q, opts, cands, seen, meter, judge_key, tag):
    """Ask the judge to pick an index into `cands`. Returns (answer, idx, mode, raw)."""
    cand_txt = "\n".join(f"{i+1}. answer {a}: {seen[a][:110]}"
                         for i, a in enumerate(cands))
    r = jb.generate(SELECT.format(q=q["q"], opts=opts, cands=cand_txt),
                    max_tokens=600, temperature=0.0)
    meter.add(judge_key + ":" + tag, r)
    idx, mode = parse_selection(r.text, cands) if r.ok else (None, "api_fail")
    return (cands[idx - 1] if idx else None), idx, mode, (r.text or "").strip()[-200:]


RETRY_SOLVE = (
    "Answer this multiple-choice question.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
    "Reply with EXACTLY one line and nothing else, in the form: ANSWER: <letter>"
)


def _panel_answer(backend, mk, q, opts, meter, temperature):
    """One panel sample, with a single stricter retry on an unparseable reply.

    An unparseable response is data loss, not an observation (Methods:
    Data-Quality Auditing). We retry once rather than silently dropping the
    slot, and record whether the retry was needed.
    """
    r = backend.generate(SOLVE.format(q=q["q"], opts=opts),
                         max_tokens=150, temperature=temperature)
    meter.add(mk, r)
    a = strict_parse(r.text, q["options"]) if r.ok else None
    if a is not None:
        return a, (r.text or "").strip()[:140], False
    r2 = backend.generate(RETRY_SOLVE.format(q=q["q"], opts=opts),
                          max_tokens=60, temperature=0.0)
    meter.add(mk, r2)
    a2 = strict_parse(r2.text, q["options"]) if r2.ok else None
    return a2, (r2.text or "").strip()[:140], True


def per_question(q, panel_models, backends, meter, judge_key, temperature):
    gold = q["answer"]
    opts = _fmt_options(q["options"])

    # ---- panel: one independent sample per slot (with one parse retry)
    slots, retries = [], 0
    for mk in panel_models:
        a, why, retried = _panel_answer(backends[mk], mk, q, opts, meter, temperature)
        retries += int(retried)
        slots.append((a, why))

    answers = [a for a, _ in slots]
    seen, cands = {}, []
    for a, why in slots:
        if a and a not in seen:
            seen[a] = why
            cands.append(a)
    stable_rng(q["id"]).shuffle(cands)

    out = dict(id=q["id"], gold=gold, panel=answers,
               n_candidates=len(cands),
               panel_retries=retries,
               panel_unparsed=sum(a is None for a in answers),
               coverage=any(a == gold for a in answers),
               slot_correct=[a == gold for a in answers])

    jb = backends[judge_key]

    # ---- constrained, forward order
    if cands:
        ans, idx, mode, raw = _select(jb, q, opts, cands, seen, meter,
                                      judge_key, "constrained")
        out.update(constrained=ans, constrained_idx=idx,
                   constrained_mode=mode,
                   constrained_invalid=(idx is None), constrained_raw=raw)
        out["constrained_escaped_to"] = (
            (re.findall(r"(?:SOLVER|ANSWER):\s*\(?([A-J])\)?", raw, re.I) or [None])[-1]
            if mode == "escape" else None)

        # ---- PAIRED CONTROL: identical candidates, reversed order.
        # Only meaningful when there is an actual choice to make.
        if len(cands) >= 2:
            rev = list(reversed(cands))
            ans_r, idx_r, mode_r, raw_r = _select(jb, q, opts, rev, seen, meter,
                                                  judge_key, "constrained_rev")
            out.update(rev_answer=ans_r, rev_idx=idx_r, rev_mode=mode_r,
                       rev_raw=raw_r)
            # same ANSWER under both orders => content-driven
            out["answer_stable"] = (ans is not None and ans_r is not None
                                    and ans == ans_r)
            # same SLOT under both orders => position-driven
            out["slot_stable"] = (idx is not None and idx_r is not None
                                  and idx == idx_r)
        else:
            out.update(rev_answer=None, rev_idx=None, answer_stable=None,
                       slot_stable=None)
    else:
        # No parseable candidate at all: a PANEL failure, not a judge failure.
        # Kept distinct so the two are never conflated in the summary.
        out.update(constrained=None, constrained_idx=None,
                   constrained_mode="no_candidates", constrained_invalid=True,
                   constrained_escaped_to=None, rev_answer=None, rev_idx=None,
                   answer_stable=None, slot_stable=None)

    # ---- unconstrained free-form, for the escape-rate contrast
    panel_txt = "\n".join(f"- answer {a}: {why[:110]}" for a, why in slots if a)
    r = jb.generate(FREEFORM.format(q=q["q"], opts=opts, panel=panel_txt),
                    max_tokens=120, temperature=0.0)
    meter.add(judge_key + ":freeform", r)
    ff = strict_parse(r.text, q["options"]) if r.ok else None
    out["unconstrained"] = ff
    out["went_outside_panel"] = bool(ff and ff not in set(a for a in answers if a))

    # ---- judge alone, the confound control
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
    backends = {mk: make_backend(mk) for mk in set(list(panel_models) + [judge_key])}
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

    # ---- position-bias block, over items offering a real choice
    multi = [r for r in rows if r["n_candidates"] >= 2
             and r.get("constrained_idx") and r.get("rev_idx")]
    m = len(multi)
    pos = dict(
        n_items_with_choice=m,
        answer_stable=round(sum(bool(r["answer_stable"]) for r in multi) / m, 3) if m else None,
        slot_stable=round(sum(bool(r["slot_stable"]) for r in multi) / m, 3) if m else None,
        flip_rate=round(1 - sum(bool(r["answer_stable"]) for r in multi) / m, 3) if m else None,
        slot1_rate_fwd=round(sum(r["constrained_idx"] == 1 for r in multi) / m, 3) if m else None,
        expected_slot1_if_unbiased=round(
            sum(1 / r["n_candidates"] for r in multi) / m, 3) if m else None,
        fwd_slot_hist=dict(Counter(r["constrained_idx"] for r in multi)),
        rev_slot_hist=dict(Counter(r["rev_idx"] for r in multi)),
    )

    # data-quality block: panel-side and judge-side failures kept separate
    with_cands = [r for r in rows if r["n_candidates"] > 0]
    dq = dict(
        rows=n,
        no_candidates=round(sum(r["n_candidates"] == 0 for r in rows) / n, 3),
        panel_slots_unparsed=round(
            sum(r["panel_unparsed"] for r in rows) / (n * len(panel_models)), 3),
        panel_retry_rate=round(
            sum(r["panel_retries"] for r in rows) / (n * len(panel_models)), 3),
        judge_no_index=round(sum(r["constrained_invalid"] for r in with_cands)
                             / len(with_cands), 3) if with_cands else None,
        judge_mode_hist=dict(Counter(r.get("constrained_mode") for r in rows)),
    )

    msum = meter.summary()
    cost = sum(est_cost_per_episode(k.split(":")[0], v["prompt_tokens"],
                                    v["completion_tokens"])
               for k, v in msum.items() if k.split(":")[0] in REGISTRY)

    # Cost split by role. The thesis is "cheap generators + one costly verifier
    # beats the costly model answering alone, for less money", so the two
    # comparable quantities are:
    #   deployed  = panel + the ONE constrained-selection call per item
    #   baseline  = the same frontier model solving every item by itself
    # The freeform/reversal arms are diagnostics and are excluded from both.
    def _c(tag_pred):
        return sum(est_cost_per_episode(k.split(":")[0], v["prompt_tokens"],
                                        v["completion_tokens"])
                   for k, v in msum.items()
                   if k.split(":")[0] in REGISTRY and tag_pred(k))
    panel_cost  = _c(lambda k: ":" not in k)
    select_cost = _c(lambda k: k.endswith(":constrained"))
    alone_cost  = _c(lambda k: k.endswith(":alone"))
    econ = dict(
        panel_cost=round(panel_cost, 5),
        verifier_select_cost=round(select_cost, 5),
        deployed_cost=round(panel_cost + select_cost, 5),
        baseline_judge_alone_cost=round(alone_cost, 5),
        cost_ratio_baseline_over_deployed=(
            round(alone_cost / (panel_cost + select_cost), 3)
            if (panel_cost + select_cost) > 0 else None),
        resolved_models={k: REGISTRY[k]["model"]
                         for k in set(list(panel_models) + [judge_key])},
        price_table={k: list(REGISTRY[k]["price"])
                     for k in set(list(panel_models) + [judge_key])},
    )
    return dict(
        name=name, panel=panel_models, judge=judge_key, n=n,
        a_best=a_best, coverage_C=C, levels=levels,
        v_hat={k: vhat(v) for k, v in levels.items() if v is not None},
        unconstrained_went_outside=round(
            sum(r["went_outside_panel"] for r in rows) / n, 3),
        data_quality=dq,
        position=pos,
        economics=econ,
        per_model_meter=msum,
        est_cost=round(cost, 4), rows=rows,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/questions_stem80.json")
    ap.add_argument("--limit", type=int, default=80)
    # Fresh lineup. The original used gpt4o_mini (panel) + qwen-72B + llama-70B
    # with a claude_sonnet judge; NONE of those vendors appear here. The three
    # hetero members are competence-matched on a pilot (0.40 each on 10 items)
    # so heterogeneity is not confounded with one weak member, and all three
    # emit the ANSWER: marker reliably (pilot parse rate 1.00).
    ap.add_argument("--homo_model", default="or_nova_lite")
    ap.add_argument("--hetero", nargs="+",
                    default=["or_nova_lite", "or_glm47_flash", "or_gemma3_27b"])
    # non-reasoning judge: Qwen3-235B emits long LaTeX working and then answers
    # `SOLVER: <letter>` rather than an index, which is a compliance failure
    # rather than a selection. DeepSeek-V3 is non-reasoning and shares no family
    # with any panel member.
    ap.add_argument("--judge", default="or_deepseekv3")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--out", default="../results/verifiers_replication.json")
    args = ap.parse_args()

    for mk in set([args.homo_model, args.judge] + list(args.hetero)):
        ok, env = key_available(mk)
        if not ok:
            sys.exit(f"[abort] {mk} unavailable (needs {env})")

    qs = load_json_set(args.dataset)[:args.limit]
    homo_panel = [args.homo_model] * len(args.hetero)
    print(f"[replication] {len(qs)} Qs | homo={homo_panel} "
          f"hetero={args.hetero} judge={args.judge}")

    out = {}
    for name, panel in (("homo", homo_panel), ("hetero", list(args.hetero))):
        res = run_panel(name, panel, qs, args.judge, args.temperature, args.conc)
        out[name] = res
        L, P = res["levels"], res["position"]
        print(f"\n[{name}] a_best={res['a_best']}  C={res['coverage_C']}  "
              f"headroom={round(res['coverage_C'] - res['a_best'], 3)}")
        for k, v in L.items():
            print(f"    {k:24s} {v}")
        D = res["data_quality"]
        print(f"    free-form escaped panel  : {res['unconstrained_went_outside']}")
        print(f"    -- data quality -- no_candidates {D['no_candidates']}  "
              f"panel_slots_unparsed {D['panel_slots_unparsed']}  "
              f"panel_retry {D['panel_retry_rate']}  judge_no_index {D['judge_no_index']}")
        print(f"    judge modes: {D['judge_mode_hist']}")
        print(f"    -- position control (n={P['n_items_with_choice']}) --")
        print(f"    answer_stable {P['answer_stable']}  slot_stable {P['slot_stable']}"
              f"  slot1_fwd {P['slot1_rate_fwd']} (unbiased {P['expected_slot1_if_unbiased']})")
        E = res["economics"]
        print(f"    -- economics -- panel ${E['panel_cost']:.4f} + verifier-select "
              f"${E['verifier_select_cost']:.4f} = DEPLOYED ${E['deployed_cost']:.4f}")
        print(f"       baseline (judge solves alone) ${E['baseline_judge_alone_cost']:.4f}"
              f"   ratio {E['cost_ratio_baseline_over_deployed']}x")
        print(f"    total run cost (incl. diagnostics) ${res['est_cost']}")

    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {args.out}  total=${round(sum(v['est_cost'] for v in out.values()), 4)}")


if __name__ == "__main__":
    main()
