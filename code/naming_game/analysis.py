"""
Estimate the LLM tipping point p_c from a run_society.py result file and compare
conditions. The order parameter is final n_B (density still holding B): it falls
from ~1 (committed A-minority fails to tip) toward 0 (A takes over) as p rises.
We fit a 4-parameter logistic n_B(p) and read p_c as its midpoint, with a
bootstrap CI over seeds.
"""
from __future__ import annotations
import json, glob, os
from collections import defaultdict
import numpy as np
from scipy.optimize import curve_fit


def logistic(p, base, top, k, pc):
    """Decreasing logistic in p: top at low p, base at high p, midpoint pc."""
    return base + (top - base) / (1.0 + np.exp(k * (p - pc)))


def load_condition(path):
    """Load a (possibly counterbalanced) run. Order parameter = n_resist (fraction
    still holding the resistance opinion). Combines push-A and push-B per p for the
    bias-controlled p_c, and computes intrinsic bias h from the p=0 drift."""
    d = json.load(open(path))
    meta = d["meta"]
    # order parameter, by p, combined over push directions (counterbalanced)
    by_p = defaultdict(list)
    # per-push p=0 drift for the intrinsic-bias estimate
    p0_resist = defaultdict(list)   # push -> list of n_resist at p=0
    legacy = False
    for r in d["rows"]:
        nr = r.get("final_n_resist")
        if nr is None:                       # legacy files used final_n_B
            nr = r.get("final_n_B"); legacy = True
        by_p[r["p"]].append(nr)
        if r["p"] == 0.0:
            p0_resist[r.get("committed_opinion", "A")].append(nr)
    ps = sorted(by_p)
    # intrinsic bias h = drift_toward_A - drift_toward_B at p=0 (0 = unbiased)
    driftA = 1 - np.mean(p0_resist["A"]) if p0_resist.get("A") else float("nan")
    driftB = 1 - np.mean(p0_resist["B"]) if p0_resist.get("B") else float("nan")
    h = (driftA - driftB) if (driftA == driftA and driftB == driftB) else float("nan")
    # Data-quality: a failed call leaves the agent's state unchanged, which is
    # indistinguishable from an agent that held its ground -- so a dead endpoint
    # renders as a population that perfectly resisted capture. Surface the rate
    # here so a corrupt run cannot be quietly fitted alongside clean ones.
    pm = meta.get("per_model_meter", {}) or {}
    calls = sum(v.get("calls", 0) for v in pm.values())
    fails = sum(v.get("failures", 0) for v in pm.values())
    fail_frac = (fails / calls) if calls else float("nan")
    return dict(label=meta.get("composition", os.path.basename(path)),
                kind=meta.get("kind"), meta=meta, legacy=legacy,
                calls=calls, failures=fails, fail_frac=fail_frac,
                ps=ps,
                nb_mean=[float(np.mean(by_p[p])) for p in ps],
                nb_all={p: by_p[p] for p in ps},
                h=float(h), driftA=float(driftA), driftB=float(driftB))


def fit_pc(ps, nb_per_p_samples, n_boot=400, seed=0):
    """Fit logistic to (p, mean n_B); bootstrap over seeds for a CI on p_c.
    nb_per_p_samples: dict p -> list of n_B values (one per seed)."""
    ps = np.array(sorted(ps), float)
    means = np.array([np.mean(nb_per_p_samples[p]) for p in ps])

    def _fit(y):
        top0, base0 = max(y.max(), 0.5), min(y.min(), 0.5)
        p0 = [base0, top0, 20.0, float(np.median(ps))]
        bounds = ([0.0, 0.0, 0.1, ps.min() - 0.05],
                  [1.0, 1.0, 500.0, ps.max() + 0.05])
        try:
            popt, _ = curve_fit(logistic, ps, y, p0=p0, bounds=bounds, maxfev=20000)
            return popt
        except Exception:
            return None

    popt = _fit(means)
    pc = float(popt[3]) if popt is not None else _crossing(ps, means)

    # bootstrap over seeds
    rng = np.random.default_rng(seed)
    n_seed = len(next(iter(nb_per_p_samples.values())))
    boot_pc = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_seed, n_seed)
        y = np.array([np.mean(np.array(nb_per_p_samples[p])[idx]) for p in ps])
        po = _fit(y)
        val = po[3] if po is not None else _crossing(ps, y)
        if val is not None and ps.min() - 0.05 <= val <= ps.max() + 0.05:
            boot_pc.append(val)
    if boot_pc:
        lo, hi = np.percentile(boot_pc, [16, 84])
    else:
        lo = hi = float("nan")
    return dict(pc=pc, ci=(float(lo), float(hi)), popt=popt,
                n_boot=len(boot_pc))


def _crossing(ps, y, thresh=0.5):
    """Fallback: linear-interpolated p where n_B crosses `thresh`."""
    for (p0, y0), (p1, y1) in zip(zip(ps, y), zip(ps[1:], y[1:])):
        if (y0 - thresh) * (y1 - thresh) <= 0 and y1 != y0:
            return float(p0 + (thresh - y0) * (p1 - p0) / (y1 - y0))
    return None


def analyze_dir(result_glob):
    conds = []
    for path in sorted(glob.glob(result_glob)):
        c = load_condition(path)
        f = fit_pc(c["ps"], c["nb_all"])
        c.update(f)
        conds.append(c)
    return conds


if __name__ == "__main__":
    import sys
    g = sys.argv[1] if len(sys.argv) > 1 else "../results/rq1_*.json"
    conds = analyze_dir(g)
    print(f"{'condition':32} {'p_c':>7} {'68% CI':>15} {'xMech':>6} {'bias h':>7} {'fail%':>7}  data")
    bad = 0
    for c in conds:
        lo, hi = c["ci"]
        ci = f"[{lo:.3f},{hi:.3f}]" if lo == lo else "   --   "
        ratio = c['pc'] / 0.0979 if c['pc'] else float('nan')
        hstr = f"{c['h']:+.2f}" if c['h'] == c['h'] else " n/a"
        ff = c.get("fail_frac", float("nan"))
        # >2% of calls falling back is not a noisy estimate, it is a corrupt run
        ok = ff == ff and ff <= 0.02
        if not ok: bad += 1
        qual = "ok" if ok else "*** DISCARD ***"
        fstr = f"{ff:6.1%}" if ff == ff else "   n/a"
        flag = "" if c.get("legacy") is False else " (legacy)"
        print(f"{c['label']:32} {c['pc']:7.3f} {ci:>15} {ratio:5.1f}x {hstr:>7} {fstr:>7}  {qual}{flag}")
    if bad:
        print(f"\n!! {bad} run(s) exceeded the 2% fallback threshold and must NOT be")
        print("   pooled with the clean runs: a failed call leaves an agent's state")
        print("   unchanged, which inflates apparent resistance to capture.")
