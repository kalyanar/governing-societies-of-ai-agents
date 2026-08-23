# Cost vs. quality: when can cheap heterogeneous models replace one expensive model?

A practical question with a clean answer from the competence-band theory: given the
accuracies of cheaper models on a class of questions, can a panel of them replace a
single costly frontier model? **It depends on whether the answer is verifiable.**

## The data (100 hard questions: TruthfulQA + MMLU-Pro)

**Individual accuracy:**
| Model | Accuracy | Relative cost ($/1M out) |
|---|---|---|
| **claude-opus** (expensive) | **92%** | ~75 |
| claude-sonnet | 78% | ~15 |
| qwen235b | 75% | ~3 |
| gpt-5 (min-reasoning) | 69% | ~10 |
| gpt-4o | 66% | ~10 |
| deepseek-v3 | 65% | ~1 |
| llama70b | 58% | ~1 |

**Cheap panel vs. expensive single:**
| Approach | Majority vote | Coverage (verify ceiling) |
|---|---|---|
| **Opus alone** | **92%** | — |
| cheap panel (gpt4o+deepseek+qwen235b) | 69% | 84% |
| 5 cheap models | 68% | 87% |
| **all 6 non-opus** | **78%** | **91%** |

## The reasoning

**Why majority vote of cheap models does NOT reach Opus.** Majority voting can only
amplify what the models already agree on. Because LLM errors are correlated
(ρ ≈ 0.5), the cheap models tend to be wrong *together*, so the vote lands at roughly
the **best single cheap model** (78% = claude-sonnet) and no higher. Adding more cheap
models does not help — they bring correlated mistakes and dilute the strongest member.
**Blind voting cannot turn cheap models into an expensive one.**

**Why coverage (verify) almost DOES reach Opus.** The cheap models *fail on different
questions* enough that *at least one* of them is right **91%** of the time — within a
point of Opus's 92%. That coverage is a real, latent resource. The catch: to cash it in
you must be able to **identify the correct answer when it is present** — i.e. *verify*.

**The decision rule.**
- **Verifiable task** (code with tests, math with a checker, or a reliable judge):
  a panel of cheap models + a verifier reaches ≈ the coverage (~91%), **matching Opus at
  a fraction of the cost** (a handful of cheap calls < one Opus call). **Use the cheap
  panel.**
- **Non-verifiable task** (must trust the answer, majority vote): the panel lands at the
  best single cheap model (78%), well below Opus. **Use the single best model you can
  afford** — a panel buys nothing.

This is the practical face of the competence-band theory: diversity creates a *coverage
ceiling* (set by error correlation), and **the aggregator — i.e. whether you can verify —
decides how much of that ceiling you capture.**

## Empirical confirmation (verifiable STEM subset) ✅

MMLU-Pro math/physics/chemistry/engineering (40 questions; objectively checkable):

| Approach | Accuracy | Rel. cost / 1000 Q |
|---|---|---|
| **claude-opus alone** (expensive) | **81%** | ~$11 |
| gpt-4o alone | 48% | |
| deepseek-v3 alone | 56% | |
| qwen235b alone | 68% | |
| **cheap panel [gpt4o+deepseek+qwen235b] + judge (debate, 2 rounds)** | **81%** | **~$5** |

Three cheap models — each individually far below Opus — **matched Opus (81% = 81%) at
~2× lower cost**. On STEM the cheap models are well-decorrelated (ρ=0.30, N_eff=1.89 of
3), giving 80% static coverage; debate + judge reached 81%, slightly exceeding static
coverage because two rounds of deliberation also *improve* answers, not just select among
them. **This is the verifiable case made concrete: cheap diverse panel + checker = an
expensive single model, cheaper.**

## A decision tool (the theory, made usable)
`code/debate/decision_tool.py` turns sample accuracies into a recommendation:

```
coverage ceiling   C    = 1 − (1 − ā)^N_eff      with N_eff = N/(1+(N−1)ρ)
projected panel    R    = a_best + v·(C − a_best)   (v: verifier quality, 0=blind, 1=oracle)
recommend cheap panel iff R ≥ a_expensive − tol  AND  cost_panel < cost_expensive
```

Worked from our 6 cheap models (accuracies 58–78%, ρ=0.48) vs Opus 92%:
| scenario | verifier v | projected panel | recommend |
|---|---|---|---|
| non-verifiable (blind majority) | 0.0 | 78% (= best single cheap) | **expensive single** |
| verifiable (strong checker) | 0.9 | 86% (analytical) / ~91% (empirical) | depends on Δ to Opus |

**Caveat on the formula.** The exchangeable estimate C = 1−(1−ā)^N_eff is a *conservative
lower bound* (it assumes worst-case homogeneity within the effective voters); the
*measured* coverage of the same 6 models was 91% vs the formula's 87%. Use the formula
for planning and the empirical coverage when available.

**The headline for practitioners:** estimate your cheap models' accuracy and correlation
on a sample of the target questions; if the task is **verifiable**, a cheap diverse panel
+ checker typically matches a costly single model at a fraction of the price; if it is
**not verifiable**, pay for the best single model — a cheap panel will only reach the
best cheap member.
