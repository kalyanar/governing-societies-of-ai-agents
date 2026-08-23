# When does adding a model help? The competence band for heterogeneous ensembles

A model can join a multi-agent panel as either an asset or a liability. The
boundary is governed by two quantities: the model's individual accuracy **a** and
its error correlation **ρ** with the rest of the pool. This note states the
thresholds the project's experiments are built to test.

## Setup
N agents answer a question; the group answer is the majority (or a debate that
resolves toward it). Agent k has accuracy a_k; pairwise error correlation is ρ.
Effective independent voters: **N_eff = N / (1 + (N−1)·ρ)**.

## 1. The universal floor: a > 0.5 (Condorcet)
For majority aggregation, an agent **degrades** the ensemble if a < 0.5 — it drags
the vote toward the wrong answer. So:
- **a < 0.5 → a "bad" model everywhere** (homogeneous OR heterogeneous): adding
  more copies, or adding it to a diverse pool, *lowers* majority accuracy.
- **a = 0.5 → neutral.**
- **a > 0.5 → can help**, by an amount set by ρ.

This is why you **cannot fix incompetence by adding more (correlated) incompetence**:
two sub-floor models reinforce the same mistakes.

## 2. The diversity ceiling (what's *possible*): ρ < 1
With an oracle aggregator that picks a correct answer whenever ≥1 agent has it, two
agents beat one whenever
  a·(1−a)·(1−ρ) > 0  ⟺  0 < a < 1 and ρ < 1.
So **potential** diversity value exists for *any* a∈(0,1) as long as errors aren't
perfectly correlated. Measured form: "at-least-one-right" (90%) − "best single"
(81%) = **+9% headroom** on our hard set. The headroom shrinks to 0 as ρ→1.

## 3. The realized gain (what you *get*): floor + decorrelation + aggregator
The gap between the ceiling (#2) and reality (#1) is the **aggregation problem** —
plain majority vote only captures the headroom when a > 0.5; a debate / confidence-
weighting / verifier that can surface a correct minority captures more. Net:

  **realized gain ≈ (decorrelation benefit) − (competence dilution)**
  decorrelation benefit grows with (1 − ρ);
  dilution cost grows with (a_best − a_new), the gap below the pool's strongest member.

## 4. The competence band for a model to *improve* a heterogeneous pool
A model with accuracy a_new joining a pool whose best member is a_best and whose
mean error-correlation with the pool is ρ helps the majority outcome when:
- **a_new > 0.5** (clears the floor), AND
- **a_new not far below a_best** (else dilution dominates), AND
- **ρ < 1** (adds genuinely new, decorrelated signal).

Loosely: useful diverse members live in a band roughly **[max(0.5, a_best − Δ(ρ)), …]**,
where the allowed gap Δ widens as the candidate is *more decorrelated* (lower ρ) —
a very different-but-slightly-weaker model can still pay for itself, while a
similar-and-weaker one only dilutes.

## 5. Corollaries (the project's claims)
- **Below 0.5 accuracy → bad model, homo or hetero.** (floor)
- **Two equally-competent frontier models > one**, but only by N_eff = 2/(1+ρ);
  with measured LLM ρ≈0.53 that's ≈1.3 effective voters — real but modest.
- **Two equally-*incompetent* correlated models ≯ one** (and can be worse).
- **Diversity pays only when decorrelated *and* competence-matched** — and for LLMs
  these two are partly in tension (matched-accuracy pairs are often high-ρ).
- **Tasks without ground truth (deliberation)** escape the dilution term: there the
  benefit is perspective diversity / groupthink resistance, and heterogeneity wins
  cleanly (homo collapses to identical stances; hetero retains real spread).

## 6. The aggregator decides whether diversity's potential is realized
Diversity creates a **ceiling** (coverage = P(≥1 agent right), governed by ρ —
*lower ρ → higher ceiling*). How much of that ceiling you capture depends on the
aggregator and therefore the **use case**:
- **Majority / consensus voting** captures the ceiling only above the 0.5 floor.
  Below it, diversity is *uncashable*.
- **Verify / select / union** (generate-and-verify, tool-checked tasks, retrieval,
  human-in-the-loop, brainstorming, deliberation) captures the ceiling as long as a
  correct answer is *present* — no floor needed.

**Empirical confirmation (40 hard Qs, three sub-floor weak models, a≈33–38%, ρ=0.29):**
| measure | one weak | one weak ×3 (homo) | three different weak (hetero) |
|---|---|---|---|
| majority-vote accuracy | 33% | 36% | **36%** (no gain) |
| coverage (≥1 right) | 38% | ~38% | **60%** (+22%) |

→ Below the floor, **two weak = one weak by voting**, but **two diverse weak ≫ one
weak by coverage**. So "two weak beats one" is TRUE for verify/select/deliberate
use cases and FALSE for majority-vote use cases. The decorrelation is real; only
the aggregator differs.

*Empirical tests: error-correlation pass (ρ, N_eff, headroom) and the weak-model
panel (two sub-floor models vs one) — see RESULTS_error_correlation.md, wpanel_* runs.*
