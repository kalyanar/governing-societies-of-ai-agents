# Adversarial & Institutional Governance — Three New Experiments

After the four core paradigms, we stress-tested the **same committed-minority / monoculture
question** along three governance-critical dimensions a security practitioner cares about:
adversarial **compromise** of a pipeline, the **voting rule** that aggregates decisions, and
the **verifier** that realizes diversity's value. Each is a homogeneous-vs-heterogeneous
comparison, and each extends the [morality / value-deliberation result](deliberation) into a
regime that experiment didn't cover.

> **Why these connect to the morality experiment.** The value-deliberation study showed a
> committed extremist sways a *monoculture* more (groupthink). These three ask: what happens
> when that influence is a **malicious injection** (A), when it hits the **vote** (B), and
> when the task is **verifiable** so a checker can intervene (D)? Same dynamic, three regimes.

---

## A. Prompt-injection propagation — a monoculture is one shared attack surface

**What it is.** A pipeline of agents passes notes in a relay chain. One agent is compromised
by an indirect prompt injection (a benign, clearly-detectable marker tag plus a
self-propagation instruction — no harmful action, this is a *defensive* measurement). Each
agent sees only its predecessor's output, so an immune agent that relays clean text breaks
the chain. "Infection" = emitting the marker.

**What we found.** Susceptibility is genuinely model-dependent — Claude resists even
undefended; most models comply; **DeepSeek-V3 / Gemma-2B / Qwen-3B comply even when hardened.**

| Chain (N=6, 8 seeds) | Pipeline infected | Reached the end |
|---|---|---|
| **Homogeneous, susceptible model** | **100%** (full depth 5/5) | 100% |
| Homogeneous, resistant model (Claude) | 0% | 0% |
| **Heterogeneous (mid, has an immune link)** | **38%** | 12% |
| **Heterogeneous (frontier, immune link)** | **18%** | 0% |
| Homogeneous gpt-4o-mini, **hardened** | 0% | — |
| Homogeneous DeepSeek-V3, **hardened** | **62%** | — |
| Heterogeneous, **hardened** | 2% | — |

**Governance takeaway.** A monoculture is a single shared attack surface — one working
injection compromises the whole pipeline. Model diversity is a real **injection firewall**
(the chain breaks at the first immune link), but only if at least one model resists, and
**patching is not uniform** across vendors.

![Injection propagation](/fig/fig_inject.png)

---

## B. Institutional rules set the capture threshold

**What it is.** A committed minority pushes a change against a status quo; the rest adopt once
support crosses their personal threshold (a cascade model, 400 seeds). We measure the
committed fraction needed to **capture** the collective decision under different voting rules.
An LLM council (N=7) confirms with real models.

**What we found.**

| Decision rule | Committed fraction to capture |
|---|---|
| Majority (>1/2) | **30%** |
| Supermajority (2/3) | **37.5%** |
| Delegation (liquid democracy) | **7.5%** |
| Veto / consensus (capture by obstruction) | **1.7%** |

The LLM council adds a caveat: **capable councils don't get persuaded** — members vote down a
reckless proposal regardless of advocate count, so capture is purely mechanical and a
supermajority blocks it. Here homo ≈ hetero, because every member is individually competent
enough to anchor on the prudent choice (consistent with the morality result: composition
mattered for open-ended *stance diversity*, not for a decision with a clearly prudent answer).

**Governance takeaway.** The **rule is a capture lever**. Supermajority raises capture
resistance (but entrenches the status quo); delegation and veto are powerful capture vectors
for a tiny minority. Audit the aggregation rule as part of the threat model.

![Institutional capture thresholds](/fig/fig_institutions.png)

---

## D. Calibrated verifiers realize the coverage ceiling

**What it is.** A panel answers verifiable STEM questions; we aggregate with verifiers of
rising quality (blind majority → self-verify → weak judge → strong judge → oracle) and watch
realized accuracy. Homogeneous panel (3 samples of one cheap model) vs heterogeneous (3
different cheap models). This directly tests the theory's R = a_best + v·(C − a_best).

**What we found.**

| Panel | Best single | Coverage ceiling C | Blind majority | Strong judge |
|---|---|---|---|---|
| **Homogeneous** | 0.375 | **0.375** (no headroom) | 0.375 | 0.525 |
| **Heterogeneous** | 0.525 | **0.60** (+7.5 pts) | 0.45 (*dilution!*) | **0.625** |

A monoculture has **zero coverage headroom** (identical models make identical errors). The
heterogeneous panel has real headroom — but **blind voting dilutes it below the best single
model**, and only a strong calibrated verifier realizes (and exceeds) the ceiling.

**Governance takeaway.** Diversity creates *potential*; the **verifier**, not the panel, is
the control you must engineer. This is the mirror image of the morality experiment: on
verifiable tasks a verifier realizes diversity by *selection*; on non-verifiable moral
dilemmas no verifier exists, so diversity pays off through *deliberation quality* — the two
ends of the competence band's aggregator axis.

![Verifier quality realizes coverage](/fig/fig_verifiers.png)

---

## One line

The committed-minority + monoculture story holds across all three: a monoculture propagates a
malicious injection fully, the voting rule decides how cheaply a minority captures the vote,
and diversity's value on verifiable tasks is only as good as the verifier that harvests it.
