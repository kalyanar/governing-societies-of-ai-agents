"""Plot the mechanical-baseline validation: n_B(p) order-parameter drop for
several N, and p_c(N) converging to the analytic 0.0979."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = sys.argv[1] if len(sys.argv) > 1 else "../results/finite_size.json"
out = sys.argv[2] if len(sys.argv) > 2 else "../figures/validation.png"
d = json.load(open(src))["by_N"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

# --- left: n_B plateau (active-state order parameter) vs p, per N ---
for n in sorted(d, key=int):
    r = d[n]
    ax1.plot(r["p"], r["plateau"], marker="o", ms=4, label=f"N={n}")
ax1.axvline(0.0979, ls="--", c="k", lw=1, label="analytic $p_c$=0.0979")
ax1.set_xlabel("committed fraction $p$")
ax1.set_ylabel("active-state $n_B$ (order parameter)")
ax1.set_title("Order parameter collapses at the tipping point")
ax1.legend(fontsize=8)
ax1.grid(alpha=0.3)

# --- right: p_c(N) convergence ---
ns = sorted(d, key=int)
pcs = [d[n]["pc_midpoint"] for n in ns]
ax2.plot([int(n) for n in ns], pcs, "o-", color="#2f6fe0", label="measured $p_c(N)$")
ax2.axhline(0.0979, ls="--", c="k", lw=1, label="analytic 0.0979")
ax2.set_xscale("log")
ax2.set_xlabel("system size $N$ (log)")
ax2.set_ylabel("measured $p_c$")
ax2.set_title("Finite-size convergence to analytic $p_c$")
ax2.legend(fontsize=9)
ax2.grid(alpha=0.3)

fig.suptitle("Mechanical binary-agreement baseline reproduces Xie et al. (2011)",
             fontsize=12, y=1.02)
fig.tight_layout()
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)
