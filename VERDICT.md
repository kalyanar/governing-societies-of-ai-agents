# Verdict: Is Heterogeneity Better?

**Short answer: not automatically — but not "no" either.** "Is a mix of different models
better than one model?" turns out to be the wrong question. The right one is **"better at
*what*, and aggregated *how*?"** Across every experiment, the answer separates cleanly by
task regime.

## The organizing principle

> Heterogeneity creates **potential** — a higher coverage ceiling, more perspectives, a
> decorrelated attack surface. But that potential is **realized only by the right
> aggregator, and only above the competence floor.** Blind majority voting throws it away
> (and can dilute below your best model).

**Diversity is a second-order effect. The competence floor and the aggregator are
first-order.**

## When heterogeneity beats a monoculture — and when it doesn't

| Setting | Verdict | Why / what to do |
|---|---|---|
| **Open-ended / value decisions** (no right answer) | ✅ **Hetero wins** | Monoculture collapses to groupthink (stance spread 0.00 vs 0.47). Mandate diversity. |
| **Adversarial robustness** (prompt injection, compromise) | ✅ **Hetero wins (strongly)** | Monoculture is one shared attack surface (100% vs 18–38% infected). Diversity is a firewall. |
| **Verifiable task *with* a calibrated verifier** | ✅ **Hetero wins** | Higher coverage ceiling (C = 0.60 vs 0.375), realized by the verifier (0.625). |
| **Verifiable / factual task with *blind* voting** | ❌ **Hetero loses** | Correlated errors (ρ≈0.5) + dilution: majority 0.45 < best single 0.525. |
| **Factual task with a dominant strong model** | ➖ **≈ Neutral / loses** | Diversity headroom collapses to +2% at the frontier. Use the strong model. |
| **Below the capability gate** (<~30B) | ⚠️ **Neither works** | Agents can't execute the primitive. Gate participation first. |
| **Pure opinion contagion** (token passing) | ➖ **No difference** | Blind to composition by construction; ~10% tipping point either way. |

## The one nuance worth remembering

The strongest *unconditional* case for diversity is **security**. Most of the accuracy
results are aggregator-dependent (diversity helps only if you harvest it correctly). But a
monoculture's **shared attack surface** makes it dangerous *regardless* of how you combine
outputs — one working injection compromises the whole pipeline. So for safety-critical
pipelines, mix vendors as defense-in-depth even when you wouldn't bother for accuracy.

## Bumper sticker

**Mix models for safety, deliberation, and verifiable-and-verified tasks — not as a reflex,
and never behind a blind majority vote.**

See [Adversarial & Institutional](adversarial), [AI Governance](governance), and
[All Results](all-results) for the experiments behind each row.
