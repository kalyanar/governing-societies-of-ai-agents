"""Regenerate fig_pc and fig_govsim from the result files.

Both replace hand-entered figures: the previous fig_pc() carried its five values
as literals in the source, and fig_govsim() predates the institutional arms. Here
every number is read from results/ so the figures cannot drift from the data.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "naming_game"))
from analysis import load_condition, fit_pc  # noqa: E402

plt.rcParams.update({"font.size": 10, "axes.titlesize": 11,
                     "figure.facecolor": "white", "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
BLUE, ORANGE, GREEN, PURPLE, RED = "#2f6fe0", "#e0782f", "#1f9d57", "#7a4fd0", "#c0392b"
ANALYTIC = 0.0979


def fig_pc():
    """Five lineages at N=64 with bootstrap CIs, against the analytic value."""
    lineages = [("DeepSeek-V3", "n64_deepseekv3.json"),
                ("Qwen2.5-72B", "n64_or_qwen25_72b.json"),
                ("Claude-Haiku", "n64_claude_haiku.json"),
                ("GPT-4o-mini", "n64_or_gpt4o_mini.json"),
                ("Llama-3.3-70B", "n64_or_llama33_70b.json")]
    names, pcs, los, his = [], [], [], []
    for lbl, f in lineages:
        c = load_condition(os.path.join(RES, f))
        fit = fit_pc(c["ps"], c["nb_all"])
        names.append(lbl); pcs.append(fit["pc"])
        los.append(fit["pc"] - fit["ci"][0]); his.append(fit["ci"][1] - fit["pc"])
    w = 1.0 / np.array([(a + b) / 2 for a, b in zip(los, his)]) ** 2
    pooled = float((np.array(pcs) * w).sum() / w.sum())
    pse = float(np.sqrt(1 / w.sum()))

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    y = np.arange(len(names))
    ax.errorbar(pcs, y, xerr=[los, his], fmt="o", color=BLUE, ms=6,
                capsize=4, lw=1.6, label="lineage estimate (68% CI)")
    ax.axvline(ANALYTIC, color="k", ls="--", lw=1.3,
               label=f"analytic $p_c$ = {ANALYTIC}")
    ax.axvspan(pooled - pse, pooled + pse, color=GREEN, alpha=0.15,
               label=f"pooled {pooled:.4f} $\\pm$ {pse:.4f}")
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xlabel("committed-minority capture threshold $p_c$")
    ax.set_title("Capture threshold at $N{=}64$: lineages agree, and match theory")
    ax.set_xlim(0.085, 0.108)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_pc.png", dpi=200, bbox_inches="tight")
    print(f"fig_pc.png   pooled={pooled:.4f}+/-{pse:.4f}")


def _arm(fname, n):
    """-> {n_defectors: (all_survived, [survival_months])}"""
    d = json.load(open(os.path.join(RES, fname)))
    by = defaultdict(list)
    for r in d["rows"]:
        by[r["n_committed"]].append(r)
    return {k: (all(not r["collapsed"] for r in v),
                [r["survival_months"] for r in v]) for k, v in by.items()}


def fig_govsim():
    """(a) the institutional ladder; (b) why share is the wrong axis."""
    arms = [("Blind, self-interested", "arm_A_blind_self.json", RED, "o"),
            ("Monitored, self-interested", "arm_B_mon_self.json", ORANGE, "s"),
            ("Monitored, steward", "arm_C_mon_steward.json", BLUE, "^"),
            ("+ restitution", "arm_D_mon_steward_sanction.json", GREEN, "D")]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 3.6))

    # ---- (a) survival vs defector count, one line per institution
    for lbl, f, col, mk in arms:
        a = _arm(f, 5)
        if lbl == "+ restitution":                      # merge the high-p sweep
            a.update(_arm("arm_D_n5_high.json", 5))
        ks = sorted(a)
        med = [float(np.median(a[k][1])) for k in ks]
        ax1.plot(ks, med, color=col, lw=1.8, label=lbl, zorder=2)
        # filled = held to the horizon, hollow = collapsed (a median near 30 can
        # otherwise read as survival when the run in fact died at month 28-30)
        for k, m in zip(ks, med):
            held = a[k][0]
            ax1.plot(k, m, marker=mk, ms=7, zorder=3, color=col,
                     mfc=col if held else "white", mew=1.6)
    ax1.axhline(30, color="k", ls=":", lw=1, alpha=0.6)
    ax1.text(0.05, 31.0, "30-month horizon", fontsize=7.5, color="0.3")
    ax1.plot([], [], marker="o", ls="none", color="0.35", mfc="0.35", ms=6,
             label="filled = held")
    ax1.plot([], [], marker="o", ls="none", color="0.35", mfc="white", mew=1.6,
             ms=6, label="hollow = collapsed")
    ax1.set_xlabel("committed defectors (of $N{=}5$)")
    ax1.set_ylabel("months survived (median)")
    ax1.set_title("(a) Each institutional layer absorbs one more defector")
    ax1.set_xticks([0, 1, 2, 3, 4]); ax1.set_ylim(0, 34)
    ax1.legend(fontsize=7, loc="lower left", ncol=2)

    # ---- (b) outcome vs the restraint Eq.(7) demands
    def required(N, d, capped):
        mult = 1.2 if capped else 2.0
        fair = 100 / (2 * N)
        return fair * (N - mult * d) / (N - d) if N - d else np.nan
    pts = []
    for f, N, cap in [("arm_C_mon_steward.json", 5, False),
                      ("arm_C_n10.json", 10, False),
                      ("arm_D_mon_steward_sanction.json", 5, True),
                      ("arm_D_n5_high.json", 5, True)]:
        for d_, (surv, _) in _arm(f, N).items():
            pts.append((required(N, d_, cap), d_ / N, surv, N))
    for surv, col, mk, lbl in [(True, GREEN, "o", "commons holds"),
                               (False, RED, "X", "commons collapses")]:
        xs = [p[0] for p in pts if p[2] == surv]
        ys = [p[1] for p in pts if p[2] == surv]
        ax2.scatter(xs, ys, c=col, marker=mk, s=64, edgecolor="k",
                    linewidth=0.5, zorder=3, label=lbl)
    ax2.axvspan(3.75, 4.44, color="0.5", alpha=0.18, zorder=1)
    ax2.text(4.1, 0.62, "expressible\nfloor", ha="center", fontsize=7.5, color="0.3")
    ax2.set_xlabel("per-agent catch required to hold the stock (tons)")
    ax2.set_ylabel("committed-minority share")
    ax2.set_title("(b) Survival tracks restraint, not adversary share")
    ax2.set_yticks([0, .2, .4, .6, .8])
    ax2.set_yticklabels(["0%", "20%", "40%", "60%", "80%"])
    ax2.legend(fontsize=8, loc="upper right")

    fig.tight_layout(); fig.savefig(f"{OUT}/fig_govsim.png", dpi=200, bbox_inches="tight")
    print("fig_govsim.png")


if __name__ == "__main__":
    plt.rcParams["text.usetex"] = False
    fig_pc()
    fig_govsim()
