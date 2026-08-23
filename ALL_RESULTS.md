# All Results — Master Reference

Every empirical result in one place. Framework: Xie et al. (2011) committed-minority
tipping point (p_c ≈ 10%). Question: does it transfer to LLM societies, and how do
homogeneity and scale modulate it? Total API spend ≈ $16.

---

## R1. Mechanical baseline validates the simulator
Pure automaton binary-agreement model reproduces the analytic tipping point.
| N | measured p_c |
|---|---|
| 200 | 0.0929 |
| 500 | 0.0936 |
| 1000 | 0.0972 |
| 2000 | 0.0983 |
→ converges to analytic **p_c = 0.0979**. Order parameter collapses sharply at p_c.

## R2. LLM naming game — the tipping point transfers (~10%), bias-controlled
Capable models, neutral randomized labels + counterbalancing (intrinsic bias h ≈ 0):
| Lineage | p_c |
|---|---|
| DeepSeek | 0.084 |
| Anthropic (haiku) | 0.093 |
| Qwen-72B | 0.095 |
| Meta (Llama-70B) | 0.101 |
| OpenAI (gpt-4o-mini) | 0.118 |
→ All five lineages cluster at ~10%, matching the analytic 0.0979. Homogeneous and
heterogeneous compositions are indistinguishable (the game is a contagion model).

![Naming-game tipping point across lineages](/fig/fig_pc.png)

## R3. Capability gate — naming-game rule-following by scale
Accuracy on the 3-case agreement rule (neutral labels, sharp prompt):
| Model | Scale | Rule acc |
|---|---|---|
| llama3.2:3b / qwen2.5:3b / gemma2:2b | 2–4B | 33–77% ❌ |
| deepseek-v3 | MoE | 88% |
| llama-3.3-70b / qwen2.5-72b | 70B | 100% ✅ |
| qwen3-235b | 235B | 98% |
| gpt-4o-mini / claude-haiku / claude-sonnet / gpt-4o / gpt-5 | frontier | 100% (gpt-5-nano 33% — reasoning hurts) |
→ Below ~30B the coordination primitive fails; the "scale effect" is a threshold.

## R4. Error correlation — the illusion of cognitive diversity
**Capable models (7 lineages, 40 hard Qs):** mean ρ = 0.53, **N_eff = 1.7 of 7**.
At-least-one-right 90% vs best single 81% → headroom +9%; 10% all-wrong.
**Frontier (7 models incl. GPT-5, Claude-Opus, 100 hard Qs):** mean ρ = 0.48,
**N_eff = 1.8 of 7**. Best single = claude-opus **92%**; at-least-one-right 95% →
headroom **+2%** (a dominant model erases the diversity benefit).
→ Even across independent lineages, LLMs fail on the *same* questions.

![Frontier error-correlation matrix](/fig/fig_rho.png)

## R5. Factual debate — heterogeneity does NOT net-win vs a strong monoculture
| Setting | Accuracy |
|---|---|
| claude-haiku solo | 63% |
| **homo claude-haiku ×6 (debate)** | **75%** (self-consistency, +12) |
| hetero [haiku+gpt4o-mini+qwen72b] | 72% (dilution) |
| claude-sonnet solo | 81% |
| **homo claude-sonnet ×3** | **86%** |
| hetero matched [sonnet+qwen235b+llama70b] + judge | 80% maj / 82% judge |
→ Strong monoculture beats diverse pool; dilution > the small ρ-limited decorrelation.

## R6. Case studies (same questions, p=0): decorrelation wins vs dilution losses
On 40 hard Qs, homo:claude-haiku vs hetero 3-lineage: **5 decorrelation-wins** (homo
wrong → hetero right, e.g. TruthfulQA "drive across country": 6 identical claude-haiku
"A" answers vs gpt4o-mini+qwen72b correcting to "C") vs **9 dilution-losses** (homo
right → hetero dragged wrong). Net −4 → homo 75% > hetero 72%. (See `CASE_STUDIES.md`.)

## R7. Competence band — weak models and the aggregator
Three sub-floor weak models (gemma2 33%, llama3b 34%, qwen2.5 38%; ρ = 0.29):
| measure | one weak | one weak ×3 (homo) | three different weak (hetero) |
|---|---|---|---|
| majority-vote accuracy | 33% | 36% | **36%** (no gain) |
| coverage (≥1 right) | 38% | ~38% | **60%** (+22%) |
→ Below the 0.5 floor, two weak = one weak by voting, but two diverse weak ≫ one by
coverage. "Two weak beat one" holds for verify/select use cases, fails for voting.

## R8. Value deliberation — heterogeneity WINS (no ground truth)
Moral dilemmas/fables, homo:claude-sonnet vs hetero:5-architectures:
| Metric | homogeneous | heterogeneous |
|---|---|---|
| distinct considerations | 5.9 | **6.9** |
| final stance spread (0 = false consensus) | **0.00** | **0.47** |
| sway toward committed extremist (lower = resists) | 0.20 | **0.13** |
→ Homo collapses to *identical* stances with verbatim reasoning (groupthink); hetero
preserves disagreement, raises more considerations, resists the extremist.
(See `DELIBERATION_DYNAMICS.md`.)

![Deliberation: heterogeneity resists groupthink](/fig/fig_delib.png)

## R9. GovSim cooperation — capability gate + tipping generalizes to ~25%
| Model | p=0 (no defectors) | tipping |
|---|---|---|
| gpt-4o-mini | collapses (~4 mo) | — (below cooperation floor) |
| **claude-sonnet** | **sustains 10/10 mo, yield 500 (sustainable max)** | sustains ≤20% defectors, **collapses at 30%** |
→ Committed-minority tipping **generalizes to cooperation at ~25%** (Centola-like),
distinct from the ~10% opinion threshold. Weak models can't cooperate at all.

![GovSim commons collapse vs defector fraction](/fig/fig_govsim.png)

## R10. Cost vs quality — when cheap heterogeneous beats one expensive model
**General (mixed, 100 Qs):** cheap panel majority 78% (= best cheap single) vs opus 92%
— blind voting can't reach opus. Coverage (verify) 91% ≈ opus.
**Verifiable STEM (MMLU-Pro math/sci, 40 Qs):**
| Approach | Accuracy | cost/1000Q |
|---|---|---|
| **claude-opus alone** | **81%** | ~$11 |
| gpt-4o / deepseek-v3 / qwen235b (each alone) | 48% / 56% / 68% | |
| **cheap panel [3 models] + judge** | **81%** ✅ | ~$5 |
→ On verifiable tasks a cheap diverse panel + checker **matches Opus at ~2× lower cost**.
On non-verifiable tasks, use the best single affordable model.

![Cheap panel matches Opus on verifiable STEM](/fig/fig_costquality.png)

Decision tool (`decision_tool.py`): C = 1−(1−ā)^N_eff; R = a_best + v·(C−a_best);
recommend cheap panel iff R ≥ a_expensive and cheaper. (See `COST_QUALITY.md`.)

## R11. Prompt-injection propagation — monoculture is a shared attack surface
Relay chain (N=6, 8 seeds); benign detectable marker payload, "infection" = emitting it.
Susceptibility is model-dependent (Claude resists even undefended; DeepSeek/Gemma/Qwen-3B
comply even when hardened).
| Chain | infected | depth | reached end |
|---|---|---|---|
| homo, susceptible (gpt4o-mini/qwen72b/llama70b/deepseekv3/gpt4o) | **100%** | 5/5 | 100% |
| homo, resistant (claude sonnet/haiku) | 0% | 0/5 | 0% |
| **hetero (mid, incl. immune haiku)** | **38%** | 1.9/5 | 12% |
| **hetero (frontier, incl. immune sonnet)** | **18%** | 0.9/5 | 0% |
| homo gpt4o-mini *defended* | 0% | — | — |
| homo deepseekv3 *defended* | **62%** | 3.1/5 | — |
| hetero *defended* | 2% | — | — |
→ One injection compromises a whole monoculture; a diverse chain breaks at its first
immune link. Hardening works for strong models, FAILS for robustly-susceptible ones.

![Injection propagation](/fig/fig_inject.png)

## R12. Institutional rules set the capture threshold
Granovetter cascade (400 seeds): committed fraction needed to CAPTURE the decision.
| Rule | capture threshold p_c |
|---|---|
| majority (>1/2) | 30% |
| supermajority (2/3) | 37.5% |
| **delegation (liquid democracy)** | **7.5%** |
| **veto / consensus (obstruction)** | **1.7%** |
→ The decision RULE is a capture lever: supermajority raises resistance; delegation and
veto collapse it far below the ~10% opinion threshold. LLM-council confirmation (N=7):
capable councils don't get persuaded — homo≈hetero — so capture is purely mechanical and
supermajority blocks it.

![Institutional capture thresholds](/fig/fig_institutions.png)

## R13. Calibrated verifiers realize the coverage ceiling (validates the band)
40 verifiable STEM Qs; homo (3× one cheap model) vs hetero (3 different cheap models).
| | a_best | coverage C | majority | strong judge |
|---|---|---|---|---|
| **homo** | 0.375 | **0.375** (no headroom) | 0.375 | 0.525 |
| **hetero** | 0.525 | **0.60** (+7.5pts headroom) | 0.45 (dilution!) | **0.625** |
→ Monoculture has zero coverage headroom (identical errors). Hetero has real headroom, but
BLIND voting dilutes below best-single (v̂≈−1); only a strong calibrated verifier realizes
it (v̂≈+1.3). Mirror image of R8 (no verifier possible there → diversity realized via
deliberation): the two ends of the competence-band aggregator axis.

![Verifier quality realizes coverage](/fig/fig_verifiers.png)

## R14. Frontier replication (arm of R11)
The monoculture-vulnerability result holds at the frontier: homo gpt4o = 100%, homo claude
sonnet = 0%, hetero frontier (incl. sonnet) = 18% — diversity contains injection even among
top models.

---

## Synthesis (the 3 main qns)
- **RQ1 (homo/hetero):** monocultures more vulnerable to groupthink/common-mode (R8,
  R6), but heterogeneity's protection is bounded by ρ (R4), can backfire via dilution
  (R5), and is realized only by the right aggregator (R7, R10).
- **RQ2 (scale):** a capability gate / competence floor, not a smooth curve (R3, R9).
- **RQ3 (tipping points):** ~10% committed-minority threshold in opinion (R2) and ~25%
  in cooperation (R9), plus the Condorcet floor (R7).

**Thesis:** heterogeneity helps *conditionally* — gated by a competence floor, bounded
by error correlation (LLMs are more correlated than they look), and realized only by
aggregators that exploit decorrelation — but it wins cleanly on open-ended deliberation.

## Document index
| File | Contents |
|---|---|
| `PAPER.md` / `PAPER.pdf` | Formal write-up (Xie-paper structure) |
| `FINDINGS_SUMMARY.md` | Prof-facing map to the three RQs |
| `ALL_RESULTS.md` | This master results reference |
| `THEORY_competence_band.md` | Floor × decorrelation × aggregator theory |
| `COST_QUALITY.md` | Cheap-panel-vs-expensive decision + STEM confirmation |
| `LEARNINGS.md` | GovSim, morality, why the naming game was the wrong instrument |
| `RESULTS_error_correlation.md` | The ρ / N_eff centerpiece |
| `DELIBERATION_DYNAMICS.md` | Deliberation homo-vs-hetero + case study |
| `CASE_STUDIES.md` | Debate transcripts: decorrelation wins vs dilution losses |
| `ARCHITECTURE.md` | Testbed system design + capability-gate detail |
| `DESIGN.md` | Original experimental design / pre-registration |
| `code/{naming_game,debate,deliberate,govsim}` | Reproducible code |
