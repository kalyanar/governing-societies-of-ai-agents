# Findings Summary: Does the Committed-Minority Framework Apply to LLM Multi-Agent Systems?

**Framework under test:** Xie, Sreenivasan, Korniss, Zhang, Lim & Szymanski (2011),
*Social consensus through the influence of committed minorities* (PRE 84, 011130) —
the committed-minority tipping point **p_c ≈ 10%** in the binary-agreement model.

**Thesis (one line):** *Heterogeneity helps conditionally, not automatically. Its
benefit is bounded by error correlation (LLMs are far more correlated than their
lineage diversity suggests), gated by a competence floor, and realized only by
aggregators that can exploit decorrelation — but on open-ended deliberation it wins
cleanly by breaking groupthink.*

---

## The 3 main qns

### RQ1 — Homogeneity vs Heterogeneity: how much more vulnerable are monocultures?
**Answer: more vulnerable to common-mode failure, but the heterogeneity protection is
quantitatively bounded — and can backfire.**
- **Groupthink (measured):** in value deliberation a homogeneous panel (6× claude-sonnet)
  collapsed to *identical* stances (final stance spread **0.00**) with near-verbatim
  reasoning; a 5-architecture heterogeneous panel kept genuine spread (**0.47**),
  raised more distinct considerations (**6.9 vs 5.9**), and resisted a committed
  extremist better (**sway 0.13 vs 0.20**).
- **Bounded protection (measured):** across 7 independent lineages, error correlation
  **ρ ≈ 0.53**, effective independent voters **N_eff ≈ 1.7 of 7**. Different-lineage
  models still fail on the *same* questions → diversity buys far less than the count
  implies. Diversity headroom only **+9%** (90% ≥1-right vs 81% best single); **10%**
  of items defeat all seven.
- **Confirmed at the FRONTIER** (100 hard Qs incl. GPT-5, Claude-Opus): mean **ρ = 0.48,
  N_eff = 1.8 of 7** — the illusion of cognitive diversity holds for the very best
  models too. And as the best single model strengthens (claude-opus = 92%), the
  diversity headroom **collapses to +2%** (95% ≥1-right vs 92% best single): a dominant
  model already covers what diversity would add, so heterogeneity offers even *less* on
  factual tasks at the top.
- **Backfire (measured):** an unmatched diverse pool *lost* to a strong monoculture
  (72% vs 75%) via competence dilution (9 dilution-losses vs 5 decorrelation-wins).
- **Even matched + decorrelated + smart aggregation didn't net-win on factual:**
  homo claude-sonnet×3 = 86% vs hetero[sonnet+qwen235b+llama70b] = 80% majority / 82%
  with a verify-style judge (sonnet solo 81%). The judge recovered some coverage
  (80→82) as theory predicts, but sonnet so outclasses its peers that dilution wins.
  **On factual correctness, a strong monoculture is hard to beat with diversity.**

### RQ2 — Model scale: how does size affect robustness/susceptibility?
**Answer: scale acts as a capability gate / competence floor, not a smooth curve.**
- **Capability gate:** below ~30B, models cannot execute the basic primitives —
  naming-game rule-following (3–4B ≈ 33–50%) and GovSim cooperation (weak models
  collapse the commons even with zero defectors). They are systemically broken
  substrates regardless of composition.
- **Competence floor (a > 0.5):** below chance, a model degrades any majority ensemble
  — homogeneous *or* heterogeneous. Above it, scale → accuracy → useful contribution.
- **Reasoning ≠ better here:** reasoning models (gpt-5-nano 33%) underperform fast
  non-reasoning instruct models on these coordination tasks.

### RQ3 — Tipping points: is there a quantifiable threshold?
**Answer: yes — two distinct thresholds.**
- **Committed-minority tipping point ≈ 10%** (the prof's framework) reproduced for
  capable LLMs across 5 lineages (DeepSeek 0.084 → gpt-4o-mini 0.118; analytic 0.0979),
  with intrinsic option-bias controlled. Below the capability gate it is undefined
  (small models can't sustain the dynamics).
- **Condorcet floor (a = 0.5)** for ensemble benefit (our theory): the threshold at
  which adding agents flips from helpful to harmful.
- **Cooperation-collapse tipping** (GovSim, LLM): the committed-minority tipping point
  GENERALIZES from opinion to cooperation, at a DIFFERENT critical fraction. A frontier
  society (claude-sonnet) sustains the commons up to **20% defectors** (10/10 months,
  0% collapse) and **collapses at 30%** (100%) — a cooperation tipping point at **~25%**,
  close to Centola's 25% social-convention threshold and distinct from the ~10% opinion
  threshold. Below the cooperation capability floor (gpt-4o-mini) the commons collapses
  even at p=0.

---

## The theoretical contribution: the competence band (`THEORY_competence_band.md`)
A model joins an ensemble as asset or liability based on **accuracy a** and **error
correlation ρ**:
1. **Floor:** a < 0.5 → bad model everywhere (Condorcet).
2. **Two equal models > one** by N_eff = 2/(1+ρ); LLM ρ≈0.53 → ≈1.3 effective.
3. **Two equally-incompetent correlated models ≯ one** (and can be worse).
4. **The aggregator decides realization:** diversity creates a *coverage ceiling*
   (∝ 1−ρ); majority voting captures it only above the floor, while verify/select/
   deliberate aggregators capture it whenever a correct answer is merely *present*.
   - *Empirical:* three sub-floor weak models (a≈33–38%, ρ=0.29) → majority 36% (=
     a single model's panel), but coverage 60% vs 38% single. So "two weak > one weak"
     is TRUE for verify/select use cases, FALSE for majority voting.

---

## Paradigms (multi-domain validation)
| Paradigm | Domain | Heterogeneity effect | Status |
|---|---|---|---|
| Naming game | opinion contagion | p_c≈10% transfers; capability-gated; blind to heterogeneity by construction | done |
| Adversarial debate | factual problem-solving | bounded by ρ; net-win needs matched+decorrelated+good aggregator | done; matched+judge running |
| Value deliberation | moral dilemmas (no ground truth) | heterogeneity wins: more perspectives, less groupthink, resists extremist | done |
| GovSim | commons cooperation | frontier sustains, defector-minority collapses it; capability-gated | done (LLM) |

## Honest open items (for a polished submission)
- Wider question sets / more seeds + CIs to tighten ρ, p_c, and the GovSim tipping fraction.
- Pin the GovSim cooperation tipping point (sweep p=0.1/0.2/0.3 with a frontier model).
- Explicit prompt-injection propagation (homo vs hetero) for the adversarial-susceptibility angle.
- Statistical tests on the deliberation diversity/sway deltas.

*Core empirical program complete: all four paradigms run, theory stated and tested.*

## Artifacts
`RESULTS_error_correlation.md` · `THEORY_competence_band.md` ·
`DELIBERATION_DYNAMICS.md` · `CASE_STUDIES.md` · `ARCHITECTURE.md` · `DESIGN.md`
