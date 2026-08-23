# AI Governance — the Spine of the Three Questions

This work is, at its core, about **governing societies of LLM agents**. As multi-agent
systems are handed authority — triaging alerts, moderating content, allocating budget,
managing a shared resource — *governing* them becomes a security problem in its own
right. An attacker need not break any single agent if a small, committed subgroup can
steer the collective; and a population that all shares one model shares every blind spot.

The professor's three questions are exactly the three governance levers a designer — or
a regulator — of such a system must reason about. The experiments and theory are
unchanged; this page makes the governance framing explicit.

---

## Threat model

We take the defender's view of an LLM agent society (deliberating, voting, or governing a
commons) against an adversary trying to control its collective behavior.

- **Assets** — the integrity of the collective output: the consensus opinion, the
  vote/decision, the legitimacy of deliberation, and the sustainability of a governed commons.
- **Adversary objectives** — **Capture** (drive the collective to an attacker-chosen outcome:
  flip opinion, force a decision, collapse cooperation) and **Compromise** (subvert agents and
  propagate the subversion).
- **Adversary capabilities (tiered, matching the experiments):**
  - **T1 — Committed minority:** controls a fraction *p* of agents that proselytize and never
    update (advocates/defectors). Cost scales with *p*. → naming game, cooperation, council.
  - **T2 — Indirect prompt injection:** controls untrusted content reaching one agent (tool
    result, retrieved doc, upstream message) that hijacks it and tells it to propagate. → the
    injection experiment.
  - *Composition is an attacker-relevant property, not a capability:* a monoculture means one
    working T2 exploit (or T1 strategy) transfers to **every** agent.
- **Trust assumptions** — the orchestrator and channel are trusted; each agent is
  *honest-but-susceptible*; the adversary can't exceed its agent-share cap, read other agents'
  weights, or compromise infrastructure.
- **Out of scope** — training/weight poisoning, model supply-chain compromise, infrastructure
  or channel compromise, confidentiality/side-channel attacks.
- **Defender levers** — composition, scale (capability gate), the aggregation rule, and the
  verifier. The whole study measures how each lever changes the adversary's cost to capture
  (T1) or compromise (T2).

---

## The three governance questions

### RQ1 — Composition (capture-resistance)
**Is a single-model *monoculture* more vulnerable to manipulation and groupthink than a
*diverse* society — and how much robustness does model diversity actually buy?**

- Diversity is a **real but bounded** safeguard. It protects most where it's most needed
  — open-ended deliberation and legitimacy, where a monoculture manufactures false
  consensus (final stance spread **0.00** vs **0.47**).
- It protects **least** where intuition expects it — factual fact-finding — because
  models share training data and fail together (error correlation **ρ ≈ 0.5**, only
  **N_eff ≈ 1.7** effective independent voters of 7). This is the *illusion of cognitive
  diversity*.
- **Governance guidance:** a diversity *mandate* ("never single-vendor") is justified for
  deliberative and value-laden decisions. For verifiable tasks the governing question is
  competence and the aggregator, not vendor count — an ill-matched panel can be *worse*
  than the best single model.

![Frontier error correlation](/fig/fig_rho.png)
![Deliberation: heterogeneity resists groupthink](/fig/fig_delib.png)

### RQ2 — Scale (fitness to govern)
**How does model scale change a society's governability — is there a capability threshold
below which agents simply cannot govern?**

- Yes: a **capability gate** around ~30B parameters. Below it, agents cannot sustain the
  coordination primitive (naming-game rule-following 33–77%) or cooperate (weak models
  collapse a commons even with **zero** defectors).
- Reasoning-tuned *small* models can be **worse** than plain instruct models here.
- **Governance guidance:** participation should be **capability-gated** — an admission
  criterion, not a tuning knob. "More reasoning" is not a safe default for a governance
  role.

### RQ3 — Capture threshold
**At what committed-minority fraction can a small group seize control of the collective —
and does that threshold transfer from human social systems to LLM societies?**

- It transfers. A committed **~10%** flips an LLM opinion-formation process (matching the
  analytic 0.0979, across five lineages), **independent of vendor mix**.
- The threshold is **domain-dependent**: a committed-defector **~25%** collapses a
  governed commons (close to Centola's human 25% result).
- **Governance guidance:** treat the committed-minority threshold as an **attack
  surface**. Cap any single principal's effective share of agents, detect committed
  (never-updating) participants, and monitor the order parameter for the metastable
  plateau that precedes a cascade.

![Capture threshold ~10% (opinion)](/fig/fig_pc.png)
![Commons collapse ~25% (cooperation)](/fig/fig_govsim.png)

---

## Implications for AI governance (summary)

| Lever | Governance rule |
|---|---|
| **Composition (RQ1)** | Mandate diversity for deliberative/value-laden decisions; for verifiable tasks, optimize competence + aggregator, not vendor count. |
| **Scale (RQ2)** | Capability-gate participation; sub-~30B agents are unfit to govern regardless of composition. |
| **Capture (RQ3)** | Cap any principal's share of agents below the threshold (~10% opinion, ~25% cooperation); detect committed agents; watch the pre-cascade plateau. |
| **Cost-aware** | On *verifiable* tasks a cheap diverse panel + verifier matches an expensive model at ~2× lower cost; on non-verifiable tasks, spend on the single best model. |

![Cheap panel matches Opus on verifiable tasks](/fig/fig_costquality.png)

---

## Mapping to policy & standards

The findings operationalize specific requirements in emerging AI-governance frameworks —
turning abstract obligations into measurable controls on an agent society.

| Finding | Framework | Provision |
|---|---|---|
| Injection propagation; monoculture attack surface | OWASP; EU AI Act | **LLM01 Prompt Injection**; **Art. 15** (robustness & cybersecurity) |
| Capture threshold as a quantifiable attack surface | NIST AI RMF; EU AI Act | MEASURE/MANAGE (secure & resilient); **Art. 9** (risk mgmt) |
| Vendor diversity; non-uniform patching | NIST GenAI Profile; EU AI Act | Value-chain & component integration; provider due-diligence |
| Capability gate / fitness to govern | EU AI Act | **Art. 15** (accuracy); **Art. 9** |
| Capture monitoring; pre-cascade plateau | EU AI Act; NIST AI RMF | **Art. 14** (human oversight); MANAGE |
| Auditing the aggregation rule | NIST AI RMF | GOVERN (accountability) |
| Verifier as an engineered control | NIST AI RMF | MEASURE (**TEVV**) |

Two mappings are especially direct: **EU AI Act Article 15** requires high-risk systems to be
resilient to exploited vulnerabilities and to faults from interacting with other systems — the
injection result shows a *monoculture fails exactly this bar* while a diverse fleet can meet
it; and **NIST's TEVV** (test, evaluation, validation, verification) is precisely the
calibrated verifier the cost-quality result identifies as the binding control.

> References: NIST AI RMF 1.0 (AI 100-1, 2023) & GenAI Profile (AI 600-1, 2024); EU AI Act
> (Reg. (EU) 2024/1689); OWASP Top 10 for LLM Applications (2025).

---

## Did the governance framing change the experiments?

**No.** AI governance is the *stakes* of the three questions, not a different experiment.
Every governance claim above traces to an experiment we already ran — GovSim is *literally*
a commons-governance simulation, deliberation tests the legitimacy of collective
reasoning, and the committed-minority sweeps measure capture directly. The theory
(competence band) and all results are unchanged; the paper was previously *under-claiming*
its own relevance by framing as an ML-ensembles study.

**Update:** the two governance-specific experiments originally listed as future work —
explicit institutional mechanisms (voting rules, veto, delegation) and direct
prompt-injection *propagation* across homo vs hetero topologies — have **now been run** (see
[Adversarial & Institutional](adversarial)). Remaining future work: multi-payload/topology
injection, weaker-model councils, and calibrated verifiers trained for the cost-quality regime.
