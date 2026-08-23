# Headline Result: LLM Heterogeneity is Largely an Illusion of Cognitive Diversity

**Setup:** 7 models from independent lineages each answered 40 hard MC questions
(TruthfulQA misconceptions + MMLU-Pro) *solo* (no deliberation), 3 seeds.
Per-question correctness → pairwise **error correlation ρ** and effective
independent voters **N_eff = N / (1 + (N−1)·mean_ρ)**.

## Individual accuracy (the competence to match on)
| Model | Lineage | Acc |
|---|---|---|
| claude-sonnet | Anthropic | 81% |
| qwen235b | Qwen | 73% |
| qwen72b | Qwen | 72% |
| llama70b | Meta | 69% |
| claude-haiku | Anthropic | 63% |
| gpt4o-mini | OpenAI | 60% |
| deepseek-v3 | DeepSeek | 58% |

## Error correlation
- **Mean pairwise ρ = +0.53** — strong positive correlation: different-lineage
  models fail on the *same* questions.
- Range **0.34** (claude-haiku vs deepseek-v3) → **0.84** (claude-sonnet vs qwen72b).
- **N_eff = 1.68 of 7** — seven lineages ≈ fewer than two independent voters.

## Diversity headroom
- At-least-one-model-right: **90%**  ·  best single model: **81%**  → ceiling **+9%**.
- **All-seven-wrong (shared blind spots): 10%** — unrecoverable by any diversity.

## Interpretation (paper spine)
LLM heterogeneity provides **far less effective diversity than the model count
implies**, because models share training data and failure modes → correlated
errors. This is the quantitative form of "representational collapse / illusion of
cognitive diversity." It explains the project's other findings:
- Hetero did not net-win the debate (small decorrelation gain, eaten by competence
  dilution).
- All 5 lineages tipped at ~10% in the naming game (not that independent).
- Same ρ→N_eff lens as the naming game, now on real reasoning errors.

**Actionable:** ρ ranges 0.34–0.84, so *which* models you mix matters more than *how
many*. Strikingly, competence-matched pairs are often the MOST correlated
(sonnet/qwen72b ρ=0.84) — "competence-matched" and "decorrelated" diversity are
partly in tension.

(Estimates from 40 questions × 3 seeds; widen the question set to tighten ρ.)
