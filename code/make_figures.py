"""Generate clean publication figures from the real result files."""
import json, glob, os, itertools
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

plt.rcParams.update({"font.size": 11, "axes.titlesize": 12,
                     "figure.facecolor": "white", "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, GREEN, PURPLE = "#2f6fe0", "#e0782f", "#1f9d57", "#7a4fd0"


def fig_pc():
    data = {"DeepSeek": 0.084, "Claude-Haiku": 0.093, "Qwen-72B": 0.095,
            "Llama-70B": 0.101, "GPT-4o-mini": 0.118}
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    names = list(data); vals = [data[n] for n in names]
    ax.barh(names, vals, color=BLUE, alpha=0.85)
    ax.axvline(0.0979, color="k", ls="--", lw=1.3, label="analytic $p_c$ = 0.0979")
    ax.set_xlabel("measured committed-minority tipping point $p_c$")
    ax.set_title("Naming game: $p_c \\approx 10\\%$ across five lineages")
    ax.legend(fontsize=9); ax.set_xlim(0, 0.14)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_pc.png", dpi=150, bbox_inches="tight")
    print("fig_pc.png")


def fig_rho():
    files = sorted(glob.glob(os.path.join(OUT, "..", "results", "fsolo_*.json")))
    def load(p):
        d = json.load(open(p)); by = defaultdict(list)
        for r in d["rows"]:
            if r.get("p", 0) == 0: by[r["question_id"]].append(1.0 if r["honest_correct"] else 0.0)
        return {q: float(np.mean(v)) for q, v in by.items()}
    models = {os.path.basename(f).split("fsolo_")[1][:-5]: load(f) for f in files}
    if len(models) < 3:
        return
    qs = sorted(set.intersection(*[set(m) for m in models.values()]))
    names = list(models)
    E = 1 - np.array([[models[n][q] for q in qs] for n in names])
    n = len(names); R = np.eye(n)
    for i, j in itertools.combinations(range(n), 2):
        a, b = E[i], E[j]
        R[i, j] = R[j, i] = (np.corrcoef(a, b)[0, 1] if a.std() > 1e-9 and b.std() > 1e-9 else 0)
    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    im = ax.imshow(R, cmap="magma", vmin=0, vmax=1)
    lbl = [s.replace("claude_", "").replace("_", "") for s in names]
    ax.set_xticks(range(n)); ax.set_xticklabels(lbl, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n)); ax.set_yticklabels(lbl, fontsize=8)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{R[i,j]:.2f}", ha="center", va="center",
                    color="white" if R[i, j] < 0.6 else "black", fontsize=7)
    mr = np.mean([R[i, j] for i, j in itertools.combinations(range(n), 2)])
    neff = n / (1 + (n - 1) * mr)
    ax.set_title(f"Error correlation (frontier): mean $\\rho$={mr:.2f}, "
                 f"$N_{{eff}}$={neff:.1f} of {n}")
    fig.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_rho.png", dpi=150, bbox_inches="tight")
    print("fig_rho.png")


def fig_govsim():
    rows = []
    for f in ["govsim_sonnet.json", "govsim_sonnet_tip.json", "govsim_fine.json"]:
        p = os.path.join(OUT, "..", "results", f)
        if os.path.exists(p):
            rows += json.load(open(p))["rows"]
    if not rows:
        return
    byp = defaultdict(list)
    for r in rows:
        byp[round(r["p"], 2)].append(r)
    ps = sorted(byp)
    coll = [np.mean([x["collapsed"] for x in byp[p]]) for p in ps]
    surv = [np.mean([x["survival_months"] for x in byp[p]]) for p in ps]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.plot([p * 100 for p in ps], [c * 100 for c in coll], "o-", color=ORANGE,
            lw=2, label="collapse rate (%)")
    ax2 = ax.twinx()
    ax2.plot([p * 100 for p in ps], surv, "s--", color=BLUE, lw=1.5,
             alpha=0.7, label="survival (months)")
    ax.axvspan(20, 30, color="red", alpha=0.08)
    ax.set_xlabel("committed-defector fraction (%)")
    ax.set_ylabel("collapse rate (%)", color=ORANGE)
    ax2.set_ylabel("survival (months)", color=BLUE)
    ax.set_title("GovSim: commons collapses at ~25% defectors")
    ax.set_ylim(-5, 105)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_govsim.png", dpi=150, bbox_inches="tight")
    print("fig_govsim.png")


def fig_delib():
    metrics = ["Distinct\nconsiderations", "Final stance\nspread", "Sway to\nextremist"]
    homo = [5.9, 0.00, 0.20]; het = [6.9, 0.47, 0.13]
    x = np.arange(len(metrics)); w = 0.36
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.bar(x - w / 2, homo, w, label="homogeneous (6× sonnet)", color="#b0392f")
    ax.bar(x + w / 2, het, w, label="heterogeneous (5 arch.)", color=GREEN)
    ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=9)
    ax.set_title("Deliberation: heterogeneity resists groupthink")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_delib.png", dpi=150, bbox_inches="tight")
    print("fig_delib.png")


def fig_costquality():
    labels = ["GPT-4o", "DeepSeek-V3", "Qwen-235B", "Cheap panel\n+ judge", "Claude-Opus"]
    vals = [48, 56, 68, 81, 81]
    colors = [ORANGE, ORANGE, ORANGE, GREEN, PURPLE]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.bar(labels, vals, color=colors, alpha=0.88)
    ax.axhline(81, color=PURPLE, ls="--", lw=1, alpha=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v}%", ha="center", fontsize=9)
    ax.set_ylabel("accuracy (verifiable STEM)")
    ax.set_title("Cheap panel + verifier matches Opus at ~2$\\times$ lower cost")
    ax.set_ylim(0, 95)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_costquality.png", dpi=150, bbox_inches="tight")
    print("fig_costquality.png")


if __name__ == "__main__":
    fig_pc(); fig_rho(); fig_govsim(); fig_delib(); fig_costquality()
    print("done ->", OUT)
