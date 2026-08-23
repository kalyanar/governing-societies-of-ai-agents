"""Figures for the four governance experiments (A injection, B institutions, D verifiers)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 11, "axes.titlesize": 12,
                     "figure.facecolor": "white", "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "figures")
RES = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, GREEN, PURPLE, RED = "#2f6fe0", "#e0782f", "#1f9d57", "#7a4fd0", "#b0392f"


def _final(name):
    return json.load(open(os.path.join(RES, f"inj_{name}.json")))["meta"]["mean_final"] * 100


def fig_inject():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.7))
    # undefended: homo monocultures vs heterogeneous
    labels = ["Homo\nsusceptible", "Homo\nresistant", "Hetero\n(mid)", "Hetero\n(frontier)"]
    vals = [np.mean([_final("homo_gpt4omini"), _final("homo_qwen72b"),
                     _final("homo_llama70b"), _final("homo_deepseekv3"), _final("homo_gpt4o")]),
            np.mean([_final("homo_haiku"), _final("homo_sonnet")]),
            _final("hetero"), _final("hetero_frontier")]
    colors = [RED, GREEN, ORANGE, BLUE]
    ax1.bar(labels, vals, color=colors, alpha=0.88)
    for i, v in enumerate(vals):
        ax1.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
    ax1.set_ylabel("pipeline infected (%)")
    ax1.set_title("Injection spread (relay chain, undefended)")
    ax1.set_ylim(0, 108)
    # defended: hardening is composition-dependent
    dl = ["Homo\ngpt4o-mini", "Homo\nDeepSeek-V3", "Hetero\n(mixed)"]
    dv = [_final("homo_gpt4omini_def"), _final("homo_deepseekv3_def"), _final("hetero_def")]
    ax2.bar(dl, dv, color=[GREEN, RED, BLUE], alpha=0.88)
    for i, v in enumerate(dv):
        ax2.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
    ax2.set_ylabel("pipeline infected (%)")
    ax2.set_title("With hardening: works for strong, fails for weak")
    ax2.set_ylim(0, 108)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_inject.png", dpi=150, bbox_inches="tight")
    print("fig_inject.png")


def fig_institutions():
    d = json.load(open(os.path.join(RES, "institutions_mech.json")))
    rules = [("majority", "Majority\n(>1/2)"), ("supermajority23", "Super-\nmajority (2/3)")]
    pcs = [d[k]["p_c"] for k, _ in rules]
    names = [n for _, n in rules]
    # add delegation and veto
    pcs.append(d["delegation"]["p_c"]); names.append("Delegation\n(liquid dem.)")
    pcs.append(d["veto_block"]["blocking_threshold"]); names.append("Veto / block\n(obstruction)")
    colors = [BLUE, GREEN, ORANGE, RED]
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    bars = ax.bar(names, [p * 100 for p in pcs], color=colors, alpha=0.88)
    for b, p in zip(bars, pcs):
        ax.text(b.get_x() + b.get_width() / 2, p * 100 + 1, f"{p*100:.1f}%",
                ha="center", fontsize=9)
    ax.axhline(10, color="k", ls=":", lw=1, alpha=0.5)
    ax.text(3.3, 11, "opinion\n~10%", fontsize=7, color="k", alpha=0.6)
    ax.set_ylabel("committed-minority capture threshold (%)")
    ax.set_title("Institutional rule sets the capture threshold")
    ax.set_ylim(0, 45)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_institutions.png", dpi=150, bbox_inches="tight")
    print("fig_institutions.png")


def fig_verifiers():
    d = json.load(open(os.path.join(RES, "verifiers.json")))
    order = ["v0_majority", "v1_selfverify", "v2_weakjudge", "v3_strongjudge"]
    xlbl = ["majority", "self-\nverify", "weak\njudge", "strong\njudge"]
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    for name, color, mk in [("homo", PURPLE, "o"), ("hetero", GREEN, "s")]:
        r = d[name]
        ys = [r["levels"][k] * 100 for k in order]
        ax.plot(x, ys, mk + "-", color=color, lw=2, label=f"{name} panel")
        ax.axhline(r["levels"]["oracle_C"] * 100, color=color, ls="--", lw=1, alpha=0.6)
        ax.axhline(r["a_best"] * 100, color=color, ls=":", lw=1, alpha=0.5)
    ax.text(0.05, d["hetero"]["levels"]["oracle_C"] * 100 + 1,
            "hetero coverage ceiling C", fontsize=7, color=GREEN)
    ax.text(0.05, d["homo"]["levels"]["oracle_C"] * 100 - 4,
            "homo C = best single (no headroom)", fontsize=7, color=PURPLE)
    ax.set_xticks(x); ax.set_xticklabels(xlbl)
    ax.set_ylabel("realized accuracy R (%)")
    ax.set_title("Verifier quality realizes the coverage ceiling")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_verifiers.png", dpi=150, bbox_inches="tight")
    print("fig_verifiers.png")


if __name__ == "__main__":
    fig_inject(); fig_institutions(); fig_verifiers()
    print("done ->", OUT)
