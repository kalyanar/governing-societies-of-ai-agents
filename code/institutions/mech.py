"""
Experiment B (mechanical core): institutional rules shift the committed-minority
CAPTURE threshold.

A committed minority (fraction p) permanently advocates the proposal A (a change to the
status quo B). Free agents follow a Granovetter-style threshold rule: a free agent adopts
A once the assembly-wide support for A reaches its personal threshold theta_i. We iterate
to a fixed point and get the final A-support f_A. The INSTITUTIONAL RULE then maps f_A to
an outcome:
  - majority           : adopt iff f_A > 1/2
  - supermajority 2/3  : adopt iff f_A >= 2/3
  - supermajority 3/4  : adopt iff f_A >= 3/4
  - delegation         : a fraction of free agents delegate to the most-confident
                         advocate bloc (liquid democracy), accelerating the cascade,
                         then majority is applied -> LOWERS the capture threshold.
Sweeping p per rule yields the capture threshold p_c(rule) = smallest p with
P(adopt) >= 1/2. We also report the dual VETO/blocking threshold: the committed fraction
needed to BLOCK adoption under a consensus(no-veto) rule -- capture by obstruction.

Pure mechanism (no LLM); many seeds -> tight thresholds. Free and instant.
"""
from __future__ import annotations
import json, os, argparse
import numpy as np


def cascade_fixed_point(p, thetas, delegation=0.0, rng=None):
    """Return final A-support fraction. N = len(thetas)+committed. thetas are the free
    agents' thresholds. Committed are fraction p of the WHOLE assembly."""
    n_free = len(thetas)
    N = int(round(n_free / (1 - p))) if p < 1 else n_free
    n_cmt = N - n_free
    # delegation: a fraction of free agents copy the advocate bloc outright
    n_deleg = int(round(delegation * n_free))
    state = np.zeros(n_free, dtype=bool)          # free agents holding A
    if n_deleg:
        state[:n_deleg] = True                    # delegators adopt A (liquid democracy)
    for _ in range(200):
        support = (n_cmt + state.sum()) / N
        new = support >= thetas                   # adopt A iff support meets threshold
        new[:n_deleg] = True                      # delegators stay with their guru
        if np.array_equal(new, state):
            break
        state = new
    return (n_cmt + state.sum()) / N


RULES = {
    "majority":        lambda f: f > 0.5,
    "supermajority23": lambda f: f >= 2/3,
    "supermajority34": lambda f: f >= 0.75,
    "delegation":      lambda f: f > 0.5,   # same test, but cascade runs with delegation
}


def p_adopt(p, rule, n_free=60, seeds=400, theta_mu=0.65, theta_sd=0.30, seed0=0):
    deleg = 0.25 if rule == "delegation" else 0.0
    test = RULES[rule]
    hits = 0
    for s in range(seeds):
        rng = np.random.default_rng(seed0 * 100000 + s)
        thetas = np.clip(rng.normal(theta_mu, theta_sd, n_free), 0.01, 0.99)
        f = cascade_fixed_point(p, thetas, delegation=deleg, rng=rng)
        hits += test(f)
    return hits / seeds


def capture_threshold(rule, ps, **kw):
    curve = [(p, p_adopt(p, rule, **kw)) for p in ps]
    pc = next((p for p, q in curve if q >= 0.5), None)
    return pc, curve


def blocking_threshold(n_free=60, seeds=400, theta_mu=0.5, theta_sd=0.15):
    """Veto/consensus rule: a committed bloc DEFENDING the status quo (holding B and
    refusing A) blocks adoption of an otherwise-popular reform. Returns the smallest
    status-quo-defender fraction that blocks adoption in >=50% of runs. With a strict
    no-veto (consensus) rule, even one defender blocks -> ~1/N."""
    # popular reform: free agents would reach high A-support; defenders hold B and veto.
    for q in np.arange(0, 0.5, 1.0 / n_free):
        blocked = 0
        for s in range(seeds):
            rng = np.random.default_rng(7777 * s + 3)
            thetas = np.clip(rng.normal(theta_mu, theta_sd, int(round(n_free*(1-q)))), 0.01, 0.99)
            # reform drive modeled as committed-A fraction 0.3 (a strong but sub-majority push)
            f = cascade_fixed_point(0.3, thetas, rng=rng)
            # consensus rule: adoption requires ~unanimity; any defender bloc q blocks it
            adopted = (f >= 0.99) and (q == 0)
            blocked += (not adopted)
        if blocked / seeds >= 0.5:
            return float(q)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../results/institutions_mech.json")
    args = ap.parse_args()
    ps = [round(x, 3) for x in np.arange(0, 0.55, 0.025)]
    results = {}
    print(f"{'rule':16} {'p_c (capture)':>14}")
    for rule in RULES:
        pc, curve = capture_threshold(rule, ps)
        results[rule] = dict(p_c=pc, curve=curve)
        print(f"{rule:16} {str(pc):>14}")
    veto = blocking_threshold()
    results["veto_block"] = dict(blocking_threshold=veto)
    print(f"{'veto/consensus':16} blocking threshold (capture-by-obstruction) = {veto}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(results, open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
