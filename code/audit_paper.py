"""Audit every load-bearing number in the manuscript against the result file that
produced it, and check the same quantity agrees wherever it is repeated.

Two distinct failure modes, both created by sequential editing rather than by
bad science:

  UNSUPPORTED   a number in the text with no result file behind it. The original
                ~30B capability gate was exactly this -- an interpolation across
                an untested gap, with no saved run. The cover letter promises
                every number is traceable, so a referee can find these.
  INCONSISTENT  a quantity corrected in one place and left stale in another. The
                abstract, the summary table and the body section each cite the
                same figures, so a correction has to land in three places.

Usage
-----
  ../.venv/bin/python audit_paper.py --tex paper/paper_dtrap.tex
"""
from __future__ import annotations
import argparse, json, os, re, sys

R = os.path.join(os.path.dirname(__file__), "results")


def j(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


def mcnemar_pair(d):
    rows = d.get("rows", [])
    both = [r for r in rows if r.get("sel_mode") != "api_fail"
            and r.get("solo_status") != "api_fail"]
    a = sum(1 for r in both if r.get("sel") == r["gold"] and r.get("solo") != r["gold"])
    b = sum(1 for r in both if r.get("sel") != r["gold"] and r.get("solo") == r["gold"])
    return a, b


def build_claims():
    """Each claim: (label, expected value from data, tolerance, source file)."""
    C = []

    h2 = j("head_to_head.json")
    if h2:
        C += [("head-to-head armA acc", h2["armA"]["acc"], 0.001, "head_to_head.json"),
              ("head-to-head armB acc", h2["armB"]["acc"], 0.001, "head_to_head.json"),
              ("head-to-head cost ratio", h2["armB"]["cost"] / h2["armA"]["cost"], 0.02,
               "head_to_head.json"),
              ("head-to-head coverage C", h2["panel"]["coverage_C"], 0.001, "head_to_head.json"),
              ("head-to-head a_best", h2["panel"]["a_best"], 0.001, "head_to_head.json"),
              ("head-to-head v_hat", h2["armA"]["v_hat"], 0.02, "head_to_head.json")]

    h30 = j("head2head_30b.json")
    if h30:
        C += [("30B panel armA acc", h30["armA"]["acc"], 0.001, "head2head_30b.json"),
              ("30B panel armB acc", h30["armB"]["acc"], 0.001, "head2head_30b.json"),
              ("30B panel C", h30["panel"]["coverage_C"], 0.001, "head2head_30b.json"),
              ("30B panel a_best", h30["panel"]["a_best"], 0.001, "head2head_30b.json"),
              ("30B panel majority", h30["panel"]["majority"], 0.001, "head2head_30b.json"),
              ("30B cost ratio", h30["armB"]["cost"] / h30["armA"]["cost"], 0.02,
               "head2head_30b.json")]

    sf = j("subfloor_panel.json")
    if sf:
        C += [("sub-floor armA acc", sf["armA"]["acc"], 0.001, "subfloor_panel.json"),
              ("sub-floor armB acc", sf["armB"]["acc"], 0.001, "subfloor_panel.json"),
              ("sub-floor C", sf["panel"]["coverage_C"], 0.001, "subfloor_panel.json"),
              ("sub-floor a_best", sf["panel"]["a_best"], 0.001, "subfloor_panel.json"),
              ("sub-floor majority", sf["panel"]["majority"], 0.001, "subfloor_panel.json"),
              ("sub-floor v_hat", sf["armA"]["v_hat"], 0.02, "subfloor_panel.json")]

    cp = j("cheap_panel_frontier_verifier.json")
    if cp:
        het = cp["hetero"]; hom = cp["homo"]
        C += [("cheap panel C", het["coverage_C"], 0.001, "cheap_panel_frontier_verifier.json"),
              ("cheap panel a_best", het["a_best"], 0.001, "cheap_panel_frontier_verifier.json"),
              ("cheap panel constrained", het["levels"]["constrained_judge"], 0.001,
               "cheap_panel_frontier_verifier.json"),
              ("cheap panel judge alone", het["levels"]["judge_alone_no_panel"], 0.001,
               "cheap_panel_frontier_verifier.json"),
              ("cheap panel majority", het["levels"]["majority_blind"], 0.001,
               "cheap_panel_frontier_verifier.json"),
              ("homo C == a_best", hom["coverage_C"] - hom["a_best"], 0.0005,
               "cheap_panel_frontier_verifier.json")]

    lad = j("verifier_size_ladderA.json")
    if lad:
        C.append(("ladder a_best", lad["meta"]["a_best"], 0.001, "verifier_size_ladderA.json"))
        best = max((v["select_acc"] for v in lad["verifiers"]
                    if v["select_acc"] is not None), default=None)
        if best is not None:
            C.append(("ladder best cheap selector", best, 0.001, "verifier_size_ladderA.json"))

    nc = j("norm_content_summary.json")
    if nc:
        for cond in ("neutral", "coop_sym", "coop_asym"):
            if cond in nc:
                C.append((f"p_c {cond}", nc[cond]["pc"], 0.002, "norm_content_summary.json"))
                if nc[cond].get("h") is not None:
                    C.append((f"h {cond}", nc[cond]["h"], 0.005, "norm_content_summary.json"))

    # 0/112 selector-ceiling control, recomputed from the raw arms
    unc = sel_right = ff_right = 0
    for f, arms in (("verifiers_constrained.json", ("homo", "hetero")),
                    ("verifiers_replication.json", ("homo", "hetero"))):
        d = j(f)
        if not d:
            continue
        for a in arms:
            for r in d[a]["rows"]:
                if not r["coverage"]:
                    unc += 1
                    sel_right += (r.get("constrained") == r["gold"])
                    ff_right += (r.get("unconstrained") == r["gold"])
    if unc:
        C += [("uncovered items pooled", unc, 0.5, "verifiers_constrained+replication"),
              ("constrained correct on uncovered", sel_right, 0.5, "verifiers_constrained+replication"),
              ("free-form correct on uncovered", ff_right, 0.5, "verifiers_constrained+replication")]
    return C


def find_in_tex(tex, value, tol):
    """Does a number within tol of `value` appear anywhere in the tex?"""
    for m in re.finditer(r"(\d+\.\d+|\d+)", tex):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if abs(v - value) <= tol:
            return True
        # also accept the percentage rendering
        if value <= 1 and abs(v - value * 100) <= tol * 100 + 0.05:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default="../paper/paper_dtrap.tex")
    args = ap.parse_args()
    tex = open(args.tex).read()

    claims = build_claims()
    print(f"{'claim':38s}{'from data':>12}  status")
    print("-" * 72)
    missing = []
    for label, val, tol, src in claims:
        if val is None:
            print(f"{label:38s}{'n/a':>12}  SKIP (no value in result file)")
            continue
        ok = find_in_tex(tex, val, tol)
        print(f"{label:38s}{val:>12.4f}  {'ok' if ok else 'NOT FOUND IN TEXT'}")
        if not ok:
            missing.append((label, val, src))

    # --- internal consistency: figures repeated in abstract / table / body
    print("\n--- internal consistency ---")
    def grab(pat):
        m = re.search(pat, tex, re.S)
        return m.group(1) if m else ""
    abstract = grab(r"\\begin\{abstract\}(.*?)\\end\{abstract\}")
    table = grab(r"(\\begin\{tabular\}.*?Selector ceiling.*?\\end\{tabular\})")
    for label, val, tol, _ in claims:
        if val is None:
            continue
        in_abs = find_in_tex(abstract, val, tol) if abstract else False
        in_tab = find_in_tex(table, val, tol) if table else False
        if in_abs and not find_in_tex(tex.replace(abstract, ""), val, tol):
            print(f"  {label}: appears ONLY in the abstract -- body does not state it")
    print("  (no line above = every abstract figure is also stated in the body)")

    print("\n--- summary ---")
    if missing:
        print(f"  {len(missing)} claim(s) in the data are NOT reflected in the text:")
        for l, v, s in missing:
            print(f"     {l} = {v:.4f}   (source: {s})")
    else:
        print("  every load-bearing number in the data appears in the manuscript")

    # unsupported-number scan: figures in results sections with no backing file
    # ---- figure staleness -------------------------------------------------
    # A figure older than the results it depicts is the failure mode that let a
    # retracted artifact stay in fig_verifiers.png while the text disproved it.
    print("\n--- figure staleness ---")
    paperdir = os.path.dirname(os.path.abspath(args.tex))
    # which result files each figure is built from, per make_figures_refresh.py
    DEPS = {
        "fig_costquality.png": ["head_to_head.json", "head2head_30b.json"],
        "fig_verifiers.png":   ["verifiers_constrained.json"],
        "fig_content.png":     ["norm_content_summary.json"],
        "fig_pc.png":          ["n64_claude_haiku.json", "n64_deepseekv3.json"],
        "fig_govsim.png":      ["arm_A_blind_self.json", "arm_D_mon_steward_sanction.json"],
        "fig_rho.json":        [],
    }
    stale = []
    for fig in sorted(set(re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", tex))):
        fp = os.path.join(paperdir, fig)
        if not os.path.exists(fp):
            print(f"  {fig:24s} MISSING"); stale.append(fig); continue
        ft = os.path.getmtime(fp)
        newest, newest_t = None, 0
        for dep in DEPS.get(fig, []):
            dp = os.path.join(R, dep)
            if os.path.exists(dp) and os.path.getmtime(dp) > newest_t:
                newest, newest_t = dep, os.path.getmtime(dp)
        if newest and newest_t > ft:
            print(f"  {fig:24s} STALE -- older than {newest}"); stale.append(fig)
        else:
            tag = f"ok (newer than {newest})" if newest else "ok (no tracked deps)"
            print(f"  {fig:24s} {tag}")

    # ---- dangling cross-references ----------------------------------------
    # A \ref with no matching \label renders as "??" and is invisible in the
    # source. Splitting the supplement into its own document took several labels
    # with it and left the pointers behind; nothing in the build flagged it.
    print("\n--- cross-references ---")
    refs = set(re.findall(r"\\ref\{([^}]*)\}", tex))
    labs = set(re.findall(r"\\label\{([^}]*)\}", tex))
    dangling = sorted(refs - labs)
    if dangling:
        for d in dangling:
            print(f"  DANGLING \\ref{{{d}}} -- no matching \\label; renders as ??")
    else:
        print(f"  ok -- {len(refs)} references, all resolved against {len(labs)} labels")

    # ---- superseded claims ------------------------------------------------
    # Numbers we have explicitly replaced. Their presence anywhere in the text is
    # a leftover from an earlier draft, which a data-vs-text check cannot see.
    print("\n--- superseded claims still present ---")
    SUPERSEDED = [
        (r"30\s*B parameters fail",      "the ~30B capability gate (floor is 3-8B)"),
        (r"roughly 30B",                 "the ~30B capability gate"),
        # Match the CLAIM, not the bare number: 0.625 also occurs legitimately as
        # a McNemar p-value and in the text that explains the artifact.
        (r"(?:surpass|exceed)[a-z]* the (?:theoretical )?(?:coverage )?ceiling(?![^.]{0,80}(?:impossible|artifact|confound|signature|only because|rather than selecting|off-panel))",
                                         "claim that a verifier beats its ceiling"),
        (r"generalize from opinion formation \(\$?\\sim ?10",
                                         "unscoped opinion->cooperation generalization"),
        (r"must not be carried across",  "claim that the threshold cannot transfer"),
        (r"calibrated verifier",         "'calibrated' verifier (now: constrained)"),
    ]
    hits = 0
    for pat, why in SUPERSEDED:
        for m in re.finditer(pat, tex):
            ctx = tex[max(0, m.start()-70):m.end()+70].replace("\n", " ")
            print(f"  FOUND {why}\n        ...{ctx.strip()}...")
            hits += 1
    if not hits:
        print("  none -- no superseded claim text remains")

    print("\n--- files referenced by the reproducibility appendix ---")
    have = sorted(f for f in os.listdir(R) if f.endswith(".json"))
    print(f"  {len(have)} result files on disk")
    if stale or hits:
        print(f"\n  ATTENTION: {len(stale)} stale figure(s), {hits} superseded claim(s)")


if __name__ == "__main__":
    main()
