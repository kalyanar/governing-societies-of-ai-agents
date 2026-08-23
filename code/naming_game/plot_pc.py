"""Plot the homo-vs-hetero p_c comparison:
  left  : n_B(p) order-parameter curves + logistic fits + p_c markers
  right : p_c per condition with bootstrap CI, vs the mechanical 0.0979 line
"""
import sys, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analysis import analyze_dir, logistic

result_glob = sys.argv[1] if len(sys.argv) > 1 else "../results/rq1_*.json"
out = sys.argv[2] if len(sys.argv) > 2 else "../figures/rq1_pc_comparison.png"

conds = analyze_dir(result_glob)
if not conds:
    print("no result files match", result_glob); sys.exit(0)

colors = plt.cm.tab10(np.linspace(0, 1, max(len(conds), 3)))
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))

for c, col in zip(conds, colors):
    ps = np.array(c["ps"])
    nb = np.array(c["nb_mean"])
    # scatter all seeds faintly
    for p in ps:
        ys = c["nb_all"][p]
        ax1.scatter([p] * len(ys), ys, color=col, alpha=0.15, s=12)
    ax1.plot(ps, nb, "o", color=col, label=c["label"], ms=5)
    if c.get("popt") is not None:
        xs = np.linspace(ps.min(), ps.max(), 200)
        ax1.plot(xs, logistic(xs, *c["popt"]), "-", color=col, lw=1.5)
    if c["pc"] is not None:
        ax1.axvline(c["pc"], color=col, ls=":", lw=1, alpha=0.7)

ax1.axvline(0.0979, color="k", ls="--", lw=1.2, label="mechanical $p_c$=0.0979")
ax1.set_xlabel("committed fraction $p$")
ax1.set_ylabel("order parameter $n_B$ (B-density at horizon)")
ax1.set_title("LLM tipping: order parameter vs committed fraction")
ax1.legend(fontsize=8)
ax1.grid(alpha=0.3)

# right: p_c bars with CI
labels = [c["label"].replace("homo:", "H:").replace("hetero:", "MIX:") for c in conds]
pcs = [c["pc"] for c in conds]
los = [c["pc"] - c["ci"][0] if c["ci"][0] == c["ci"][0] else 0 for c in conds]
his = [c["ci"][1] - c["pc"] if c["ci"][1] == c["ci"][1] else 0 for c in conds]
y = np.arange(len(conds))
ax2.barh(y, pcs, xerr=[los, his], color=colors[:len(conds)], alpha=0.8,
         capsize=4, error_kw=dict(lw=1.2))
ax2.axvline(0.0979, color="k", ls="--", lw=1.2, label="mechanical 0.0979")
ax2.set_yticks(y); ax2.set_yticklabels(labels, fontsize=8)
ax2.set_xlabel("estimated tipping point $p_c$")
ax2.set_title("Where does each composition tip?")
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3, axis="x")

fig.suptitle("RQ1: does mixing model families shift the committed-minority tipping point?",
             fontsize=12, y=1.02)
fig.tight_layout()
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)
for c in conds:
    print(f"  {c['label']:40} p_c={c['pc']:.3f}  CI={c['ci']}")
