# Do Committed Minorities Tip LLM Agent Societies? Heterogeneity, Scale, and the Limits of Diversity in Multi-Agent Systems

*[Author list TBD] — [Affiliations TBD]*

---

## Abstract

A foundational result in opinion dynamics holds that a committed minority exceeding
a critical fraction **p_c ≈ 10%** can rapidly overturn the prevailing convention of a
population [Xie et al., 2011]. As multi-agent systems built from large language models
(LLMs) increasingly make collective decisions, it is natural to ask whether this
committed-minority tipping point governs *societies of LLMs*, and how it depends on
whether agents share one model (homogeneous) or mix several (heterogeneous), and on
model scale. We operationalize the binary-agreement model with LLM agents and show
that capable models reproduce the tipping point at **p_c ≈ 0.08–0.12** across five
independent model lineages, converging on the analytic value 0.0979, **once intrinsic
option bias is controlled by counterbalancing**. The transition is *capability-gated*:
models below roughly 30B parameters cannot execute the coordination primitive and the
dynamics never form. Extending beyond opinion contagion to factual problem solving,
value deliberation, and commons cooperation, we find that **heterogeneity is not
automatically beneficial**. Its value is bounded by inter-model error correlation
(measured ρ ≈ 0.53, giving only N_eff ≈ 1.7 effective independent voters among seven
lineages), it can be erased by competence dilution, and it is realized only by
aggregators able to exploit decorrelation. Heterogeneity wins cleanly only in
open-ended deliberation, where a monoculture collapses to identical stances
(groupthink) while a diverse panel preserves genuine disagreement and resists a
committed extremist. We formalize these regularities as a *competence band*: a model
helps an ensemble only above a competence floor (a > 0.5, Condorcet) and to the extent
its errors decorrelate from the pool. The committed-minority tipping point also
generalizes to cooperation: a frontier society sustains a common-pool resource but a
committed-defector minority collapses it.

---

## I. Introduction

Human collective behavior exhibits sharp tipping points: below a critical mass an
inflexible minority is absorbed, while above it the minority's position cascades to
become the majority's. Xie, Sreenivasan, Korniss, Zhang, Lim and Szymanski [1] made
this quantitative in the *binary-agreement model*, a two-opinion variant of the Naming
Game. They showed that a fraction **p** of *committed* agents — who hold opinion A,
proselytize it, and never change — flips an all-B population in a time that scales as
exp(αN) below a critical fraction **p_c ≈ 0.0979** and only as ln N above it, a phase
transition at roughly **10%**.

Multi-agent systems of LLMs now deliberate, vote, negotiate, and govern shared
resources. Their robustness is not the sum of individual safety properties; it is an
emergent, system-level property of how agents influence one another. Two design axes
dominate practice: whether all agents are instances of one model (a *monoculture*) or
a mix of different models (a *heterogeneous* society), and the *scale* of the
underlying models. This motivates three questions, which structure this paper:

1. **Homogeneity vs. heterogeneity.** Are agent societies more vulnerable to a
   committed minority when they rely on identical versus heterogeneous LLMs?
2. **Scale.** How does model capacity influence system-level robustness?
3. **Tipping points.** Is there a quantifiable threshold at which collective behavior
   abruptly changes as a function of composition or model characteristics?

**Contributions.** (i) We operationalize the binary-agreement model with LLM agents and
show capable models reproduce p_c ≈ 10% across five lineages, after controlling a
previously unreported confound — strong intrinsic option bias in LLMs. (ii) We show the
transition is capability-gated. (iii) We measure inter-model error correlation and show
LLM heterogeneity provides far less effective diversity than the number of lineages
implies. (iv) We give a *competence-band* theory unifying when adding a model helps an
ensemble, and (v) validate the picture across four domains — opinion contagion, factual
debate, value deliberation, and commons cooperation.

---

## II. The committed-minority tipping point in LLM populations

### A. The binary-agreement model and its LLM operationalization

In the binary-agreement model each agent holds opinion A, B, or AB (both). A randomly
chosen speaker voices one opinion to a neighbor; on agreement both collapse to the
shared opinion, otherwise the listener adds it (becoming AB). A committed fraction p
permanently holds and voices A. We replace the mechanical listener-update rule with an
**LLM decision**: each agent, given its current opinion and the opinion just voiced,
decides its new state in natural language, which we map back to {A, B, AB}.

Two design choices proved essential. First, the literal labels "A"/"B" carry a strong
**intrinsic token bias** in LLMs — small models converge to "B" (or, for some models,
"A") regardless of the dynamics — which swamps the social signal. We therefore use
**neutral, randomized labels** (e.g. *apple*/*mango*) and **counterbalance** which label
the minority commits to, reporting a bias-controlled order parameter (the density still
holding the *resistance* opinion). Second, the update is run by the agent's own model,
so heterogeneous societies dispatch each agent's decision to its own backend.

### B. Mechanical validation

With the deterministic rule the simulator reproduces the analytic result: the measured
tipping point converges upward to **p_c → 0.0979** with system size (0.093 at N=200 to
0.098 at N=2000), and the order parameter shows the expected sharp collapse.

### C. LLM tipping points and the capability gate

For sufficiently capable models the committed-minority transition is recovered with
intrinsic bias controlled (h ≈ 0). Across five independent lineages the measured p_c
clusters near 10%:

| Lineage | p_c |
|---|---|
| DeepSeek | 0.084 |
| Anthropic (haiku) | 0.093 |
| Qwen-72B | 0.095 |
| Meta (Llama-70B) | 0.101 |
| OpenAI (gpt-4o-mini) | 0.118 |

The transition is **capability-gated**: models of ≈2–4B parameters cannot reliably
execute the agreement rule (rule-following accuracy 33–50% vs 100% for 70B+/frontier
non-reasoning models), so the dynamics never form. The "scale effect" for this task is
therefore a *threshold* — a competence floor below which the system is not merely worse
but non-functional — rather than a smooth dependence on parameter count. Notably,
reasoning-tuned models underperform fast instruct models on this coordination primitive.

---

## III. Homogeneity, heterogeneity, and the limits of diversity

The naming game is a *contagion* model: agents exchange opinion tokens, not arguments,
so a society's composition barely matters once each agent can follow the rule — and
indeed all capable lineages tip near 10%. To probe whether heterogeneity helps when
agents must *reason*, we turn to tasks with ground truth.

### A. Error correlation and effective diversity

Seven models from independent lineages each answered 40 hard multiple-choice questions
(TruthfulQA misconception items and MMLU-Pro). The mean pairwise **error correlation is
ρ ≈ 0.53**: different-lineage models fail on the *same* questions. The effective number
of independent voters is therefore **N_eff = N/(1+(N−1)ρ) ≈ 1.7 of 7**. At least one
model is correct on 90% of items versus 81% for the best single model — a diversity
*ceiling* of only +9% — and on 10% of items all seven fail together. LLM heterogeneity
is thus, to a large degree, an *illusion of cognitive diversity*: lineage diversity
overstates statistical independence. The picture holds at the frontier: on a larger
100-item set including GPT-5 and Claude-Opus, ρ = 0.48 and N_eff = 1.8. Moreover, as the
best single model strengthens (Claude-Opus at 92%) the diversity ceiling collapses to
+2% — a dominant model already covers nearly everything a diverse panel could add, so on
factual tasks heterogeneity offers *less* at the top, not more.

### B. Multi-agent debate: bounded gains and dilution

In adversarial debate, a committed minority argues for a fixed wrong answer. A
homogeneous panel of the strong claude-sonnet improves over a single instance (81% →
86%) through self-consistency. A heterogeneous panel of competence-*mismatched* models
*loses* (72% vs 75%) because dilution by weaker members outweighs decorrelation (9
dilution losses vs 5 decorrelation wins). Even a competence-matched, low-ρ panel with a
verify-style judge aggregator did not beat the strong monoculture (82% vs 86%); the
judge recovered some coverage (80% → 82%) but not enough. On factual correctness a
strong monoculture is hard to beat with diversity.

### C. The competence band

These regularities follow from classical ensemble theory with correlation. A model
joins an ensemble as an asset or a liability according to its accuracy a and its error
correlation ρ with the pool:

1. **Floor (Condorcet).** Below a = 0.5 a model degrades any majority ensemble —
   homogeneous or heterogeneous. One cannot fix incompetence by adding correlated
   incompetence.
2. **Two equal models beat one** by N_eff = 2/(1+ρ); for LLM ρ ≈ 0.53 this is ≈ 1.3
   effective voters — real but modest.
3. **The aggregator decides realization.** Diversity creates a coverage ceiling
   (∝ 1−ρ). Majority voting captures it only above the floor; verify/select/deliberate
   aggregators capture it whenever a correct answer is *present*. Empirically, three
   sub-floor weak models (a ≈ 33–38%, ρ = 0.29) give majority accuracy 36% (no gain over
   a single panel) yet coverage 60% vs 38% — so "two weak beat one" holds for
   verify/select use cases and fails for plain voting.

---

## IV. Beyond opinion: deliberation and cooperation

### A. Value deliberation — where heterogeneity wins

On moral dilemmas and fables with no ground truth, six copies of claude-sonnet
collapsed to *identical* stances (final stance spread 0.00) with near-verbatim
reasoning — textbook groupthink. A five-architecture heterogeneous panel preserved
genuine disagreement (spread 0.47), raised more distinct considerations (6.9 vs 5.9),
and was less swayed by a committed extremist (0.13 vs 0.20 on a 1–7 scale). Absent a
shared factual error to dilute, heterogeneity's benefit — perspective diversity and
resistance to groupthink — is realized cleanly.

### B. Commons cooperation (GovSim) — generalization and the capability gate

In a common-pool fishery, a frontier society (claude-sonnet) sustains the resource
indefinitely (10/10 months, 0% collapse, harvesting at exactly the sustainable
maximum), whereas a committed-defector minority collapses it: the commons survives up to 20%
defectors but collapses at 30% (100%), placing the cooperation tipping point at **~25%**
— close to Centola's 25% social-convention threshold [2] and distinct from the ~10%
opinion threshold. The committed-minority tipping point thus **generalizes from opinion
to cooperation, at a domain-specific critical fraction**.
Below the cooperation capability floor (gpt-4o-mini) the commons collapses even with no
defectors, mirroring the capability gate of Section II.

---

## V. Summary and discussion

We set out to test whether the committed-minority framework of Xie et al. [1] applies
to societies of LLM agents, and how composition and scale modulate it. It does: capable
LLM populations reproduce the ~10% tipping point across five lineages, and the same
committed-minority phenomenon collapses cooperation in a commons game. The dominant
scale effect is a **capability gate / competence floor**, not a smooth curve — below it
agents cannot sustain the collective dynamics at all.

On heterogeneity our results are deliberately two-sided. A monoculture is genuinely
more vulnerable to common-mode failure and groupthink — most starkly in open-ended
deliberation, where identical models reach a false consensus that diverse models avoid.
But for tasks with a correct answer, heterogeneity is **not automatically better**: its
benefit is bounded by inter-model error correlation (LLMs are far more correlated than
their lineage diversity suggests), can be erased by competence dilution, and is realized
only by aggregators that exploit decorrelation. We summarize this as a competence band:
add a model only above the floor and to the extent its errors decorrelate, and choose an
aggregator matched to whether the task can verify a present-but-minority correct answer.

For practitioners the prescription is concrete: prefer deliberate, decorrelated,
competence-matched heterogeneity over either a monoculture or an indiscriminate mix;
keep the strongest model as a verifier; and recognize that below the competence floor,
more agents — diverse or not — do not help.

**Limitations and future work.** Estimates use modest question sets and seed counts;
tightening confidence intervals on ρ, p_c, and the cooperation tipping fraction
(sweeping p = 0.1–0.3 with a frontier model) is ongoing. Direct prompt-injection
propagation across homogeneous vs heterogeneous topologies would sharpen the
adversarial-susceptibility angle.

---

## Acknowledgments
*[TBD]*

## References
[1] J. Xie, S. Sreenivasan, G. Korniss, W. Zhang, C. Lim, B. K. Szymanski, "Social
consensus through the influence of committed minorities," Phys. Rev. E **84**, 011130 (2011).
[2] D. Centola, J. Becker, D. Brackbill, A. Baronchelli, "Experimental evidence for
tipping points in social convention," Science **360**, 1116 (2018).
[3] G. Piatti et al., "Cooperate or Collapse: Emergence of Sustainable Cooperation in a
Society of LLM Agents," NeurIPS 2024.
[4] A. Ashery, L. M. Aiello, A. Baronchelli, "Emergent social conventions and collective
bias in LLM populations," Science Advances (2025).
[5] Marquis de Condorcet, *Essai sur l'application de l'analyse à la probabilité des
décisions rendues à la pluralité des voix* (1785).
[6] S. Lin, J. Hilton, O. Evans, "TruthfulQA: Measuring How Models Mimic Human
Falsehoods," ACL 2022.
[7] Y. Wang et al., "MMLU-Pro: A More Robust and Challenging Multi-Task Language
Understanding Benchmark," NeurIPS 2024 Datasets & Benchmarks.
