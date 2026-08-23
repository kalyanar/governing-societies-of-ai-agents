# Tipping the Machine: How Model Homogeneity and Scale Set the Committed-Minority Threshold in LLM Agent Societies

**Working design / pre-registration — v0.1 (2026-06-22)**

---

## 1. Framework under test

Xie, Sreenivasan, Korniss, Zhang, Lim & Szymanski (2011), *"Social consensus through the influence of committed minorities"*, Phys. Rev. E **84**, 011130 (arXiv:1102.3931).

- **Binary agreement model** (a 2-opinion Naming-Game variant): each agent holds opinion **A**, **B**, or **AB** (both). Random speaker→listener interactions update states by the model's transition rules (Table I of the paper).
- A fraction **p** of agents are **committed**: they permanently hold and proselytize **A** and are immune to influence.
- **Result:** a sharp phase transition at **p_c ≈ 0.0979 (~10%)**. Below p_c the time to convert the population scales as **T_c ~ exp(αN)** (effectively never; α(p) ~ |p−p_c|^ν, ν≈1.65). Above p_c, **T_c ~ ln N** (fast, inevitable). Holds on complete, Erdős–Rényi, and scale-free graphs.

**Security reading:** a committed minority that flips consensus *is* an adversarial takeover. **A lower p_c means a more vulnerable system.**

## 2. Research questions (the professor's three, in framework terms)

- **RQ1 — Homogeneity vs heterogeneity:** does p_c shift when committed + uncommitted agents share one LLM (monoculture) vs. a mix of LLMs?
- **RQ2 — Scale:** does LLM size move p_c? Are larger models more *stubborn* (higher p_c) or more *persuadable* (lower p_c)? Does the *committed* minority's scale matter separately from the majority's?
- **RQ3 — Tipping point:** measure p_c for LLM populations and compare to the analytic 9.79%.

## 3. Hypotheses (with the genuine scientific tension stated)

The deep-research literature gives **competing predictions**, which is what makes the measurement worth doing:

| # | Hypothesis | Direction | Mechanism / source |
|---|---|---|---|
| **H1** Monoculture vulnerability | Homogeneous pools have **lower p_c** than competence-matched heterogeneous pools | monoculture more vulnerable | One persuasion strategy that works on model X flips *all* X-agents (correlated vulnerability); diverse pools resist a single rhetoric → higher p_c |
| **H1′** Counter-effect | Heterogeneous pools may *fail to self-organize* (different intrinsic biases) → a fragmented majority is easier to capture → could **lower** het p_c | open | OASIS herd/fragmentation; competing with H1 — **empirical question** |
| **H2** Majority stubbornness | Larger uncommitted models → **higher p_c** (resist takeover) | scale = robustness | Intrinsic-bias dominance (Ising-style: field h ≫ neighbor coupling J); stronger priors resist weak arguments |
| **H2′** Sycophancy/herding | LLMs herd *more* than humans / are sycophantic → could push p_c **below** 9.79% | scale ambiguous | OASIS, Perez sycophancy (inverse scaling) |
| **H3** Dual-use committed scale | Larger *committed* (adversary) models → **lower p_c** (more persuasive) | scale = offense | Capable attacker; persuasion capability rises (with diminishing returns, Hackenburg PNAS 2025) |
| **H4** Comparison to theory | Measured LLM p_c ≠ 9.79%; the *sign* of the deviation is the headline finding | — | net of H2 vs H2′ |

The paper's contribution is resolving these tensions with measured p_c values across composition and scale — **the first such measurement**, and exactly the two axes the closest prior work (Ashery, Aiello & Baronchelli, *Science Advances* 2025) did **not** systematically vary.

## 4. Primary testbed — LLM binary-agreement / Naming Game

- **Agents:** N LLM-backed agents on a graph. Each holds A / B / AB. Memory = recent interaction history (bounded).
- **Committed agents:** fraction p, system-prompted to always hold/advocate A and never change.
- **Interaction step:** pick random speaker + neighbor listener. Speaker (LLM) voices an opinion; listener (LLM) decides its updated state given the voiced opinion + memory. We let the LLM make the speak/adopt decisions (so LLM behavior — stubbornness, persuadability, scale — actually drives the dynamics) while the *bookkeeping* follows the binary-agreement state machine.
- **Order parameter:** n_B (density of uncommitted B) — compare steady state to the theory's 0.6504 active state and the jump to 0 at p_c.
- **Topologies:** complete graph (primary, matches theory) → ER and scale-free (robustness).
- **Opinion representation:** abstract A/B tokens (clean, theory-comparable) **+ a small topical-robustness run** (real contested stances; committed = zealots) to show p_c isn't an artifact of abstract tokens.

## 5. Secondary testbed — GovSim (cooperation domain)

Show the committed-minority tipping point **generalizes from opinion to cooperation**: inject a committed-defector minority (fraction p) into GovSim; measure the fraction at which sustainable cooperation collapses. Adversary tiers: greedy defector → persuasive saboteur → prompt-injected. Same composition × scale axes, fewer cells.

## 6. Factorial design

- **A. Composition** ×3: homogeneous · heterogeneous-balanced (competence-matched) · heterogeneous-mixed-competence (strong+weak).
- **B. Scale** ×~6: Qwen2.5 {0.5, 1.5, 3, 7, 14, 32}B + Llama-3.x {3, 8, 70}B (**local, free**) + frontier {GPT-4o, Claude, Gemini} **API only in H2/H3/H5 cells**. Applied to majority and (separately) to the committed minority.
- **C. Committed fraction p** (the tipping curve): fine grid, dense near the transition — e.g. {0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30}.
- **D. System size N** for finite-size scaling: {20, 50, 100, (200)} — to test T_c ~ exp(N) below vs ln N above p_c.
- **E. Topology** ×3 (complete / ER / scale-free).
- **Seeds:** 20–50 per cell (social sims are high-variance).

## 7. Metrics

- **p_c** (tipping point) via finite-size scaling / Bayesian change-point on P(consensus→A) vs p, with CIs, per composition & scale.
- **T_c** (consensus time) and its N-scaling (exp vs ln) — the model's signature.
- **n_B** steady state vs the analytic 0.6504.
- **ρ** pairwise inter-agent decision correlation; **N_eff = N/(1+(N−1)ρ)** — the monoculture mechanism metric.
- **Ising decomposition** (per model): intrinsic-bias field **h** vs conformity coupling **J** — quantifies "does the LLM follow peers or its prior?"
- Committed-fraction **competence covariate** (capability probe) to separate scale from competence.

## 8. Analysis plan

Segmented logistic regression / Bayesian change-point to locate p_c with uncertainty; finite-size scaling collapse to extract the critical exponent and compare to ν≈1.65; mixed-effects models with the competence covariate; pre-registered to avoid p-hacking the tipping point.

## 9. Cost & compute

- Naming-Game interactions are **short, small-context** (≈ hundreds of tokens) — far cheaper than GovSim's long reasoning episodes. The full scale sweep up to 70B runs **free** on the GB10.
- Frontier API confined to the cells where a claim is *about* frontier capability (H2/H3). **Hard cap ~$500**, metered on the first ~10 runs before any big spend. Subscriptions cannot drive the harness (API tokens only).

## 10. Venue & deliverables

Target: NeurIPS / ICLR / ICML or ACL/EMNLP. Deliverables: open testbed code, measured p_c tables/curves across composition & scale, finite-size-scaling figures, and a clear answer to the professor's three RQs grounded in his own 2011 framework.

## 11. Build order (next steps)

1. Implement the binary-agreement state machine + LLM agent wrapper (ollama backend) + token meter.
2. Reproduce the **abstract, homogeneous, complete-graph** case at small N; confirm a tipping point exists and read its location.
3. Add composition + scale axes; pilot 10 runs; report measured cost.
4. Lock budget → run full factorial → analysis → GovSim secondary → write-up.

---

### Caveats carried forward
- Deep-research files `view1.md`/`view2.md` contain hallucinated/future-dated citations — use only as hypothesis sources; verify every cite.
- Differentiate explicitly from Ashery/Aiello/Baronchelli 2025 (LLM Naming Game + committed minority already shown) — our novelty is the homogeneity & scale axes on p_c.
