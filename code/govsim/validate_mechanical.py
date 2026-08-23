"""
Fast no-LLM validation of the fishery dynamics + collapse tipping point.
Replaces LLM cooperators with a fixed sustainable policy (catch the per-capita
sustainable amount) and committed defectors with the greedy policy, then sweeps
the committed fraction p to confirm a collapse tipping point emerges. No tokens.
"""
from __future__ import annotations
from resource import Fishery, episode_metrics
from gov_agents import GREEDY_MULT


def run_mechanical(n, p_committed, max_months=12, capacity=100.0, seed=0,
                   greedy_mult=GREEDY_MULT):
    import random
    rng = random.Random(seed)
    n_committed = int(round(p_committed * n))
    committed = set(rng.sample(range(n), n_committed))
    fishery = Fishery(capacity=capacity, stock=capacity, n_agents=n)
    for _ in range(max_months):
        reqs = []
        for i in range(n):
            if i in committed:
                reqs.append(greedy_mult * fishery.per_capita_sustainable())  # defector
            else:
                reqs.append(fishery.per_capita_sustainable())                # cooperator
        fishery.apply_harvests(reqs)
        if fishery.collapsed():
            break
    return episode_metrics(fishery, max_months)


def main():
    n = 10
    ps = [round(0.05 * i, 2) for i in range(0, 13)]   # 0.0 .. 0.6
    for gm in [2.0, 3.0, 4.0]:
        print(f"\n=== Mechanical fishery (N={n}, greedy_mult={gm}) ===")
        print(f"{'p':>5} {'n_comm':>7} {'survival':>9} {'collapse_rate':>14}")
        for p in ps:
            surv, coll = [], []
            for s in range(20):
                m = run_mechanical(n, p, seed=s, greedy_mult=gm)
                surv.append(m["survival_months"]); coll.append(m["collapsed"])
            nc = int(round(p * n))
            bar = "#" * int(round(sum(coll) / len(coll) * 20))
            print(f"{p:5.2f} {nc:7d} {sum(surv)/len(surv):8.1f}mo "
                  f"{sum(coll)/len(coll):13.0%} {bar}")
    print("\nPick the greedy_mult that gives a GRADED collapse curve (tipping point "
          "in the middle of the p range), so collapse depends on the defector FRACTION.")


if __name__ == "__main__":
    main()
