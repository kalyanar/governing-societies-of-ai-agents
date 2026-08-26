"""Regenerate the figures whose underlying results changed, reading every value
from the result JSON rather than hard-coding it.

Why this exists
---------------
Two figures shipped with the submission were stale in a way that contradicted the
revised text:

  fig_costquality.png  hard-coded [48,56,68,81,81] and a title claiming
                       "~2x lower cost". Not read from any result file, so it
                       could not track the corrected measurement.
  fig_verifiers.png    read verifiers.json -- the ORIGINAL free-form judge run --
                       and plotted the strong judge at 0.625 ABOVE the 0.600
                       coverage ceiling. That is precisely the artifact the paper
                       now disproves (a constrained selector was correct on 0 of
                       112 items no panel member solved). The figure asserted the
                       opposite of the section it illustrated.

Everything below reads its numbers from disk, so a re-run of any experiment
propagates to the figure without hand editing.

  fig_costquality.png  head-to-head: free panel + constrained arbiter vs the same
                       model reasoning alone, with measured cost per arm
  fig_verifiers.png    the CONSTRAINED ladder: majority vote, constrained
                       selector, best member and coverage ceiling, per panel
  fig_content.png      p_c is unchanged across neutral / cooperative-symmetric /
                       cooperative-asymmetric conventions

Usage
-----
  ../.venv/bin/python make_figures_refresh.py
"""
from __future__ import annotations
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "..", "paper")

PURPLE, GREEN, ORANGE, GREY = "#6C5CE7", "#00B894", "#E17055", "#95A5A6"


def load(n):
    p = os.path.join(RES, n)
    if not os.path.exists(p):
        print(f"  [skip] {n} not found")
        return None
    return json.load(open(p))


# ---------------------------------------------------------------------------
def fig_costquality():
    """Accuracy with cost annotation, both arms on the same judge model."""
    h = load("head_to_head.json")
    h30 = load("head2head_30b.json")
    if not h:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8), sharey=True)

    for ax, d, title in ((axes[0], h, "free panel, 27--120B"),
                         (axes[1], h30, "pure 24--31B panel")):
        if d is None:
            continue
        p, A, B = d["panel"], d["armA"], d["armB"]
        members = list(p["per_member"].values())
        labels = ([f"member {i+1}" for i in range(len(members))]
                  + ["majority\nvote", "panel +\nselector", "judge\nalone"])
        vals = members + [p["majority"], A["acc"], B["acc"]]
        colors = [GREY] * len(members) + [ORANGE, GREEN, PURPLE]
        bars = ax.bar(labels, [v * 100 for v in vals], color=colors, alpha=0.9)
        ax.axhline(p["coverage_C"] * 100, color=GREEN, ls="--", lw=1.2, alpha=0.75)
        ax.text(0.02, p["coverage_C"] * 100 + 1.2,
                f"coverage ceiling $C$={p['coverage_C']:.3f}",
                fontsize=7.5, color=GREEN, transform=ax.get_yaxis_transform())
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1.2, f"{v*100:.1f}",
                    ha="center", fontsize=8)
        ratio = B["cost"] / A["cost"]
        ax.annotate(f"\\${A['cost']:.2f}", (len(members) + 1, A["acc"] * 100 - 8),
                    ha="center", fontsize=8, color="white", weight="bold")
        ax.annotate(f"\\${B['cost']:.2f}", (len(members) + 2, B["acc"] * 100 - 8),
                    ha="center", fontsize=8, color="white", weight="bold")
        ax.set_title(f"{title}\n{ratio:.2f}$\\times$ cheaper at equal accuracy", fontsize=9.5)
        ax.tick_params(axis="x", labelsize=7.5)
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("accuracy, verifiable STEM (%)")
    fig.suptitle("A constrained selector over a free panel matches the same model reasoning alone",
                 fontsize=10.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_costquality.png", dpi=150, bbox_inches="tight")
    print("  fig_costquality.png  (from head_to_head.json + head2head_30b.json)")


# ---------------------------------------------------------------------------
def fig_verifiers():
    """The constrained ladder: what each aggregator realizes of the headroom."""
    d = load("verifiers_constrained.json")
    if not d:
        return
    order = ["majority_blind", "constrained_judge"]
    xlbl = ["blind majority\nvote", "constrained\nselector"]
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    for name, color, mk in (("homo", PURPLE, "o"), ("hetero", GREEN, "s")):
        r = d[name]
        ys = [r["levels"][k] * 100 for k in order]
        ax.plot(x, ys, mk + "-", color=color, lw=2, ms=7, label=f"{name} panel")
        ax.axhline(r["coverage_C"] * 100, color=color, ls="--", lw=1.1, alpha=0.7)
        ax.axhline(r["a_best"] * 100, color=color, ls=":", lw=1.1, alpha=0.6)
    hom, het = d["homo"], d["hetero"]
    ax.text(1.02, het["coverage_C"] * 100, f"  hetero $C$={het['coverage_C']:.3f}",
            fontsize=7.5, color=GREEN, va="center")
    ax.text(1.02, hom["coverage_C"] * 100 - 2.0,
            f"  homo $C$ = best member = {hom['a_best']:.3f}\n  (no headroom)",
            fontsize=7.5, color=PURPLE, va="center")
    ax.text(1.02, het["a_best"] * 100, f"  hetero best member {het['a_best']:.3f}",
            fontsize=7.5, color=GREEN, alpha=0.8, va="center")
    ax.set_xticks(x); ax.set_xticklabels(xlbl)
    ax.set_xlim(-0.25, 2.05)
    ax.set_ylabel("realized accuracy $R$ (%)")
    ax.set_title("Only a constrained selector realizes the coverage ceiling\n"
                 "(a free-form judge exceeds $C$ only by answering off-panel)",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_verifiers.png", dpi=150, bbox_inches="tight")
    print("  fig_verifiers.png  (from verifiers_constrained.json -- NOT the free-form run)")


# ---------------------------------------------------------------------------
def fig_content():
    """p_c is unchanged when only the CONTENT of the convention varies."""
    s = load("norm_content_summary.json")
    if not s:
        return
    nice = {"neutral": "neutral\ncodewords",
            "coop_sym": "cooperative,\nsymmetric",
            "coop_asym": "cooperative,\nrestrained vs greedy"}
    conds = [c for c in ("neutral", "coop_sym", "coop_asym") if c in s]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.7))

    ax = axes[0]
    for c, col in zip(conds, (GREY, GREEN, ORANGE)):
        pp = s[c]["per_p"]
        xs = sorted(float(k) for k in pp)
        ys = [pp[f"{x:.4f}"] for x in xs]
        ax.plot([x * 100 for x in xs], ys, "o-", color=col, lw=1.8, ms=5,
                label=nice.get(c, c).replace("\n", " "))
    ax.axhline(0.5, color="k", ls=":", lw=0.8, alpha=0.5)
    ax.set_xlabel("committed fraction $p$ (%)")
    ax.set_ylabel("fraction of runs that flip")
    ax.set_title("Flip curves are superimposed", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")

    ax = axes[1]
    ys = np.arange(len(conds))
    for i, c in enumerate(conds):
        v = s[c]
        ax.errorbar(v["pc"] * 100, i,
                    xerr=[[(v["pc"] - v["lo"]) * 100], [(v["hi"] - v["pc"]) * 100]],
                    fmt="o", color=(GREY, GREEN, ORANGE)[i], capsize=4, ms=7)
        ax.text(v["pc"] * 100, i + 0.18, f"{v['pc']:.3f}", ha="center", fontsize=8)
    ax.set_yticks(ys); ax.set_yticklabels([nice.get(c, c) for c in conds], fontsize=8)
    ax.set_xlabel("$p_c$ (%)")
    ax.set_title("Tipping point does not move with content", fontsize=10)
    ax.set_ylim(-0.6, len(conds) - 0.2)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_content.png", dpi=150, bbox_inches="tight")
    print("  fig_content.png  (from norm_content_summary.json)")


if __name__ == "__main__":
    print("regenerating figures from current results:")
    fig_costquality()
    fig_verifiers()
    fig_content()
    print("done ->", os.path.normpath(OUT))
