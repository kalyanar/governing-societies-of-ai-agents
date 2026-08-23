# What we learned: GovSim, morality, and why the original test was the wrong instrument

## 1. What GovSim (cooperation) taught us

GovSim places 5 agents on a shared fishery (100 tons, doubles each month up to
capacity; sustainable total harvest = half the stock). We injected a committed-defector
minority and swept its fraction p.

**Result — capability gate for cooperation:**
| Model | p=0 (no defectors) |
|---|---|
| gpt-4o-mini | collapses in ~4 months (100% collapse) |
| claude-sonnet (frontier) | **sustains 10/10 months, 0% collapse, yield = 500 (the exact sustainable maximum)** |

**Result — the tipping point generalizes to cooperation:**
| claude-sonnet | survival | collapse |
|---|---|---|
| p = 0.0 | 10 mo | 0% |
| p = 0.4 | 6.5 mo | 100% |

**Result — graded degradation** (homo gpt-4o-mini): survival 4.5 → 3.0 → 2.5 months as
the defector fraction rises 0 → 0.2 → 0.4.

**Learnings:**
1. **Cooperation is capability-gated**, exactly like opinion consensus. Weak/mid models
   over-harvest and collapse the commons *even with zero defectors*. Only frontier
   models sustain — reproducing GovSim's published "only the most powerful models reach
   sustainable equilibrium."
2. **The committed-minority tipping point is not specific to opinion.** The same
   phenomenon — a small immune minority overturning the collective state — collapses a
   cooperating society. The framework crosses domains: opinion → cooperation.
3. So "robustness to a committed minority" is **two thresholds stacked**: first the
   society must be capable enough to cooperate at all (capability floor), then it must
   survive the defector fraction (tipping point). Below the floor there is nothing to
   tip — it is already collapsed.

## 2. What the morality / deliberation experiment taught us

We had 6 agents deliberate moral dilemmas (trolley, Heinz, euthanasia, wealth seizure,
…) on a 1–7 stance scale over several rounds, with an optional committed extremist.
Homogeneous = 6× claude-sonnet; heterogeneous = 5 different architectures (Anthropic,
OpenAI, Qwen-MoE, Meta, DeepSeek-MoE), with claude-sonnet present in *both* so we could
watch the same model behave differently.

**Result — heterogeneity wins cleanly (every metric):**
| Metric | homogeneous | heterogeneous |
|---|---|---|
| distinct considerations raised | 5.9 | **6.9** |
| final stance spread (0 = false consensus) | **0.00** | **0.47** |
| sway toward committed extremist (lower = resists) | 0.20 | **0.13** |

**Result — the mechanism, made visible (`wealth_seizure`):** all six claude-sonnet copies
returned the *identical* stance (4/7) with **near-verbatim identical reasoning**; the
five-architecture panel produced different stances and genuinely different framings
(moral imperative vs. correcting systemic injustice vs. fairness/method critique),
11 distinct considerations vs 6.

**Result — stance trajectories:** homogeneous panels were **frozen flat** (e.g.
4.0 → 4.0 → 4.0 → 4.0) — instant unanimity, no deliberation; heterogeneous panels
**evolved** across rounds as agents argued.

**Learnings:**
1. **A monoculture suffers literal groupthink.** Identical models reach a *false
   consensus* — not because they reasoned to agreement, but because they are the same
   mind echoed six times (representational collapse, made concrete).
2. **This is exactly where heterogeneity pays off**, and it pays off *more* here than on
   factual tasks. Why? On a question with no ground truth there is no shared *factual*
   error to dilute and no single "right answer" for a strong model to dominate — so
   diverse value-priors translate directly into richer deliberation and resistance to a
   one-sided push.
3. **The benefit is qualitatively different from the factual case.** On factual tasks
   heterogeneity buys (bounded) *error decorrelation*; on value deliberation it buys
   *perspective coverage and anti-groupthink*. The professor's "vulnerability"
   intuition is most clearly vindicated here.

## 3. Why the original test (the Naming Game) was the wrong instrument — LLMs are too capable for it

The Naming Game / binary-agreement model is the *faithful* operationalization of the
professor's framework, and it did its job for one question: **capable LLMs reproduce the
~10% committed-minority tipping point across five lineages** (p_c = 0.084–0.118 vs
analytic 0.0979). That validates the framework (RQ3).

But as an instrument for the *heterogeneity* question (RQ1) it is structurally
inadequate — and the reason is precisely that **LLMs are far more capable than the
automaton agents the model was designed for.**

**Evidence 1 — it is blind to heterogeneity by construction.** In the Naming Game agents
exchange opinion *tokens* (A/B/AB) under a fixed update rule; they do **not reason or
argue**. So once a model can follow the rule, a monoculture and a diverse society follow
the *same* contagion dynamics. Empirically, **all five capable lineages tipped at ~10%**
— homogeneous and heterogeneous compositions were indistinguishable. There is no
"reasoning" to decorrelate, no argument to weigh; heterogeneity has nowhere to act.

**Evidence 2 — LLMs are "opinionated" in ways automatons are not.** The abstract labels
"A"/"B" carried a massive intrinsic token bias: small models converged to "B" (others
to "A") *regardless of the dynamics*, with the push-against-bias direction completely
degenerate. We had to switch to neutral, randomized labels and counterbalance just to
recover the underlying dynamics. An automaton has no such priors; an LLM brings a whole
pretrained worldview to a task meant to be value-free.

**Evidence 3 — the capability gate.** Small models (2–4B) could not execute the basic
agreement rule at all (33–50% vs 100% for 70B+/frontier), defaulting to "both" and never
converging. The token-passing game both *under-uses* capable models and *excludes* weak
ones — leaving only a narrow band of models for which, per Evidence 1, composition does
not matter.

**The lesson.** The Naming Game is a *contagion* model: it answers "does an opinion
spread?" LLMs' distinctive value lives in *deliberation* — reasoning, argument, catching
each other's mistakes — which a token-passing game does not exercise. To test whether
heterogeneity helps, we had to move to tasks that actually use LLM reasoning (factual
debate, moral deliberation, cooperation). There, composition matters — sometimes for
diversity, sometimes against it (dilution), and most clearly for anti-groupthink. So the
original test was the right tool to *validate the framework* but the wrong tool to
*answer the professor's heterogeneity question* — and the mismatch is itself a finding:
**you cannot study LLM cognitive diversity with a model that throws away their
cognition.**
