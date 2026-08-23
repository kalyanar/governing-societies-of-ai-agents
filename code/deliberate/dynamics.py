"""
Did heterogeneity help the DELIBERATION? Compares homo vs hetero runs on:
  - perspective diversity  : distinct considerations raised (LLM-judged) — does a
                             monoculture echo itself while diversity surfaces more?
  - groupthink / false consensus : stance variance round-1 vs final — does the
                             monoculture collapse to agreement faster?
  - sway resistance        : at p>0, how far the committed extremist drags the group.
Plus side-by-side stance trajectories + reasoning for case studies.

Usage: python dynamics.py homo.json hetero.json [out.md]
"""
import json, sys, statistics
from collections import defaultdict


def load(path):
    return json.load(open(path))


def by_key(d):
    return {(r["stim_id"], r["p"], r["seed"], r["extreme"]): r for r in d["rows"]}


def agg(d):
    """Aggregate metrics at p=0 (diversity/groupthink) and p>0 (sway)."""
    p0 = [r for r in d["rows"] if r["p"] == 0.0]
    pos = [r for r in d["rows"] if r["p"] > 0.0]
    def mean(xs):
        xs = [x for x in xs if x is not None]
        return statistics.mean(xs) if xs else float("nan")
    # diversity + final variance at p=0
    distinct = mean([r["n_distinct"] for r in p0])
    final_var = mean([r["honest_stdev_final"] for r in p0])
    # round-1 vs final stdev (groupthink collapse) at p=0
    r1_var = mean([r["trajectory"][0]["honest_stdev"] for r in p0 if r["trajectory"]])
    # sway at p>0 vs p=0 baseline (per stim/seed/extreme)
    base = {(r["stim_id"], r["seed"], r["extreme"]): r["honest_mean_final"] for r in p0}
    sways = []
    for r in pos:
        b = base.get((r["stim_id"], r["seed"], r["extreme"]))
        if b is not None and r["honest_mean_final"] is not None:
            sign = 1 if r["extreme"] >= 4 else -1
            sways.append(sign * (r["honest_mean_final"] - b))
    return dict(distinct=distinct, r1_var=r1_var, final_var=final_var,
                mean_sway=mean(sways))


def traj_str(r):
    return " -> ".join(f"{t['honest_mean']:.1f}" for t in r["trajectory"]
                       if t["honest_mean"] is not None)


def main():
    homo, het = load(sys.argv[1]), load(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else "../../DELIBERATION_DYNAMICS.md"
    ah, ae = agg(homo), agg(het)

    with open(out, "w") as f:
        f.write("# Did heterogeneity help the deliberation?\n\n")
        f.write(f"Homo = `{'+'.join(homo['meta']['models'])}`  |  "
                f"Hetero = `{'+'.join(het['meta']['models'])}`\n\n")
        f.write("| metric | homogeneous | heterogeneous | favors |\n|---|---|---|---|\n")
        def row(lbl, hv, ev, higher_better):
            better = "HETERO" if ((ev > hv) == higher_better) else "homo"
            f.write(f"| {lbl} | {hv:.2f} | {ev:.2f} | **{better}** |\n")
        row("perspective diversity (distinct args, p=0)", ah["distinct"], ae["distinct"], True)
        row("round-1 stance spread", ah["r1_var"], ae["r1_var"], True)
        row("final stance spread (high = avoids false consensus)", ah["final_var"], ae["final_var"], True)
        row("sway toward extremist (LOW = resists)", ah["mean_sway"], ae["mean_sway"], False)
        f.write("\n*Higher perspective-diversity and final-spread = less groupthink. "
                "Lower sway = better resistance to the committed extremist.*\n")

        # side-by-side trajectories per dilemma (p=0)
        hk, ek = by_key(homo), by_key(het)
        f.write("\n## Stance trajectories (p=0, mean honest stance per round)\n\n")
        f.write("| dilemma | homo trajectory | hetero trajectory | homo distinct | hetero distinct |\n")
        f.write("|---|---|---|---|---|\n")
        for key in sorted(hk):
            if key[1] != 0.0:
                continue
            if key in ek:
                h, e = hk[key], ek[key]
                f.write(f"| {key[0]} | {traj_str(h)} | {traj_str(e)} | "
                        f"{h['n_distinct']} | {e['n_distinct']} |\n")

        # one rich case study: a dilemma where hetero raised more considerations
        cands = [(ek[k]["n_distinct"] - hk[k]["n_distinct"], k)
                 for k in hk if k in ek and k[1] == 0.0
                 and ek[k]["n_distinct"] and hk[k]["n_distinct"]]
        if cands:
            cands.sort(reverse=True)
            _, key = cands[0]
            h, e = hk[key], ek[key]
            f.write(f"\n## Case study: {key[0]} — final-round reasoning\n\n")
            for tag, r in [("HOMOGENEOUS (one model, echoing)", h),
                           ("HETEROGENEOUS (diverse architectures)", e)]:
                f.write(f"\n**{tag}** — distinct considerations: {r['n_distinct']}\n")
                for a in r["full_transcript"][-1]:
                    if not a["committed"]:
                        f.write(f"  - [{a['model']}] stance {a['stance']}/7: "
                                f"{a['reason'][:170]}\n")
    print(f"wrote {out}")
    print(f"  perspective diversity: homo {ah['distinct']:.1f} vs hetero {ae['distinct']:.1f}")
    print(f"  final stance spread:   homo {ah['final_var']:.2f} vs hetero {ae['final_var']:.2f}")
    print(f"  sway to extremist:     homo {ah['mean_sway']:+.2f} vs hetero {ae['mean_sway']:+.2f}")


if __name__ == "__main__":
    main()
