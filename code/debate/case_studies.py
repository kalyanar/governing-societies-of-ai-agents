"""
Extract qualitative case studies: questions where the HOMOGENEOUS pool failed
(honest majority wrong) but the HETEROGENEOUS pool succeeded — and dump the
side-by-side transcripts showing the mechanism (monoculture's correlated blind
spot vs the corrective signal a different lineage provides).

Usage: python case_studies.py homo.json hetero.json [out.md]
"""
import json, sys
from collections import defaultdict


def index_by_q(path):
    """Map (question_id, seed) -> row, and keep question metadata."""
    d = json.load(open(path))
    by = {}
    for r in d["rows"]:
        by[(r["question_id"], r["seed"])] = r
    return d, by


def agent_line(a):
    tag = "ADV" if a["adversary"] else a["model"]
    return f"      [{tag}] answered {a['answer']}: {a['reason'][:140]}"


def render_case(q_id, seed, homo_row, het_row, fout):
    correct = homo_row["correct_answer"]
    fout.write(f"\n### {q_id} (seed {seed}) — correct = {correct}, "
               f"source={homo_row.get('source','?')}\n\n")
    fout.write(f"- **Homogeneous** honest majority: **{homo_row['honest_majority']}** "
               f"({'✓' if homo_row['honest_correct'] else '✗ WRONG'})\n")
    fout.write(f"- **Heterogeneous** honest majority: **{het_row['honest_majority']}** "
               f"({'✓' if het_row['honest_correct'] else '✗'})\n\n")
    # final-round transcripts
    fout.write("  **Homogeneous — final round (a monoculture echoing one blind spot):**\n")
    for a in homo_row["transcript"][-1]:
        if not a["adversary"]:
            fout.write(agent_line(a) + "\n")
    fout.write("\n  **Heterogeneous — final round (diverse lineages, corrective signal):**\n")
    for a in het_row["transcript"][-1]:
        if not a["adversary"]:
            fout.write(agent_line(a) + "\n")
    fout.write("\n")


def main():
    homo_path, het_path = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "../../CASE_STUDIES.md"
    dh, homo = index_by_q(homo_path)
    de, het = index_by_q(het_path)

    decorr, dilution = [], []          # homo-fail/het-win  AND  het-fail/homo-win
    for key in homo:
        if key in het:
            h, e = homo[key], het[key]
            if (not h["honest_correct"]) and e["honest_correct"]:
                decorr.append((key, h, e))
            elif h["honest_correct"] and (not e["honest_correct"]):
                dilution.append((key, h, e))

    def acc(rows):
        v = list(rows.values())
        return sum(x["honest_correct"] for x in v) / max(len(v), 1)

    def src_counts(cases):
        c = defaultdict(int)
        for (qid, s), h, e in cases:
            c[h.get("source", "?")] += 1
        return dict(c)

    with open(out, "w") as f:
        f.write("# Case Studies: the heterogeneity trade-off (decorrelation vs dilution)\n\n")
        f.write(f"At p=0 (no adversary): homogeneous honest accuracy **{acc(homo):.0%}** "
                f"vs heterogeneous **{acc(het):.0%}**.\n\n")
        f.write(f"- **Decorrelation wins** (homo WRONG → hetero CORRECT): "
                f"**{len(decorr)}** cases, by source {src_counts(decorr)}\n")
        f.write(f"- **Dilution losses** (homo CORRECT → hetero WRONG): "
                f"**{len(dilution)}** cases, by source {src_counts(dilution)}\n\n")
        f.write("Net effect = decorrelation wins − dilution losses. Heterogeneity "
                "net-helps only when the wins outweigh the dilution (competence-matched).\n")
        f.write("\n## A. Decorrelation wins — monoculture's shared blind spot, "
                "corrected by a different lineage\n")
        for key, h, e in decorr:
            render_case(key[0], key[1], h, e, f)
        f.write("\n## B. Dilution losses — a correct monoculture dragged wrong by "
                "weaker/divergent peers\n")
        for key, h, e in dilution:
            render_case(key[0], key[1], h, e, f)
    print(f"wrote {out}  | decorrelation-wins={len(decorr)} dilution-losses={len(dilution)}")
    print(f"homo acc={acc(homo):.0%}  hetero acc={acc(het):.0%}")


if __name__ == "__main__":
    main()
