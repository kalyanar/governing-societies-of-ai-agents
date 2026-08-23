# Testbed Architecture & the Capability-Gate Finding

Companion to `DESIGN.md`. Two things are documented here:
1. **System architecture** of the LLM Naming-Game testbed (how the code is laid out).
2. **The architectural *difference* between models** that we discovered empirically —
   the **capability gate** that decides whether a model can even play the game.

---

## 1. System architecture

```
code/
├── naming_game/                  PRIMARY testbed (opinion consensus)
│   ├── model.py                  abstract binary-agreement state machine (A/B/AB),
│   │                             committed agents, n_resist order parameter
│   ├── backends.py               multi-provider LLM clients (ollama / OpenAI-compat /
│   │                             Anthropic) + thread-safe token meter
│   ├── registry.py               the model ladder: id -> provider, scale, family,
│   │                             tier, price  (.env auto-loaded via config.py)
│   ├── society.py                composition layer: homogeneous / heterogeneous /
│   │                             mixed-competence per-agent model assignment
│   ├── llm_agent.py              neutral randomized labels + the listener prompt +
│   │                             reply parsing + per-agent dispatch update_fn
│   ├── run_society.py            episode loop + p-sweep + COUNTERBALANCING (push A/B)
│   │                             + episode-level CONCURRENCY (ThreadPoolExecutor)
│   ├── analysis.py / plot_pc.py  logistic p_c fit + bootstrap CI + bias h + figures
│   ├── simulate.py/validate.py/finite_size.py   MECHANICAL baseline (no LLM):
│   │                             reproduces the analytic p_c = 0.0979
│   └── .env                      API keys (gitignored)
└── govsim/                       SECONDARY testbed (cooperation collapse)
    ├── resource.py               fishery dynamics + metrics
    ├── gov_agents.py             LLM harvest + 3 committed-defector adversary tiers
    ├── simulate.py / run_govsim.py
    └── validate_mechanical.py    collapse tipping ~0.25-0.30 (Centola-like)
```

**Key design choices**
- **Provider-agnostic backends.** Every model is `provider:id` resolved via the
  registry; one OpenAI-compatible client covers OpenAI, the HF Inference-Providers
  router, and any vLLM server. Anthropic has its own client. So a model is just an id.
- **Composition as a first-class axis.** `society.py` assigns each agent its own
  model, so homogeneous and heterogeneous societies share one code path.
- **Counterbalancing is built in.** Each condition runs the committed minority
  pushing *both* opinions; the unified `n_resist` order parameter and the bias `h`
  are computed from the pair. This neutralises intrinsic option bias.
- **Concurrency.** Episodes are independent, so they run on a thread pool
  (API/HF calls are I/O-bound). ~10x wall-clock reduction; meter is lock-guarded.

---

## 2. The capability gate — the architectural difference that matters

The central empirical finding about model architecture is **not** a smooth
"bigger = higher p_c" curve. It is a **threshold on whether a model can execute the
coordination primitive at all.**

### The primitive
The binary-agreement (Naming-Game) update is a 3-case rule:

| You hold | You hear | Correct new state |
|---|---|---|
| X | X | **X**  (agree → keep the shared one) |
| X | Y (new) | **both** (add it) |
| both | X | **X**  (collapse onto the heard one) |

### Measured rule-following accuracy (neutral labels, sharp prompt, ≥8 trials/case)

| Model | Scale | NG-rule accuracy |
|---|---|---|
| llama3.2:3b | 3B | 37% ❌ |
| qwen2.5:3b | 3B | 70% ⚠️ |
| gemma2:2b | 2B | 77% ⚠️ |
| deepseek-v3 | 671B (MoE) | 88% ✅ |
| llama-3.3-70b | 70B | 100% ✅ |
| qwen2.5-72b | 72B | 100% ✅ |
| qwen3-235b | 235B | 98% ✅ |
| gpt-4o-mini | frontier | 100% ✅ |
| claude-haiku | frontier | 100% ✅ |
| claude-sonnet | frontier | 100% ✅ |
| gpt-4o / gpt-5 | frontier | 100% ✅ |
| **gpt-5-nano / gpt-5-mini** | frontier *reasoning* | **33% / 67% ❌** |

### Three architectural lessons

1. **There is a competence floor (~30–70B).** Below it (2–4B) agents default to
   "both" and the population never converges — the committed-minority dynamics
   cannot run. Above it, models play cleanly. The "scale effect" the project set out
   to measure is, for this task, *this gate* — not a continuous p_c(size) law.

2. **Reasoning models are *worse*, not better.** gpt-5-nano (33%) and gpt-5-mini
   (67%) underperform non-reasoning peers: minimal-effort reasoning mis-handles a
   task that needs none, and full reasoning wastes the token budget on a one-token
   answer. **Use fast non-reasoning instruct models** (gpt-4o-mini, claude-haiku,
   llama-70b, qwen-72b) as the workhorses.

3. **Prompt sensitivity is itself capability-graded.** A freeform prompt
   ("decide which you now hold") collapsed mid-tier models to "both" (claude-haiku
   78%); an explicit *rule* prompt lifted the same models to 100%. Strong models are
   prompt-robust; weaker ones need the rule spelled out. The small models stay low
   regardless — a genuine capability limit, not a prompt artifact.

### Why this matters for the homo-vs-hetero (RQ1) architecture
Heterogeneity is only meaningful **above the gate** — a "diverse" society that
includes a sub-floor model isn't diverse, it's broken (the weak agents inject noise
that never resolves). So:
- Heterogeneous conditions mix **rule-capable** lineages
  (OpenAI, Anthropic, Meta, Qwen, DeepSeek).
- Sub-floor models (gemma2, llama3b) are used only as deliberate
  **low-competence probes** for the competence-floor question (H2), never as
  silent members of a "capable" mix.

---

## 3. Validated result so far (homogeneous, capable lineages)

With bias controlled (h ≈ 0 for all) and p_c properly pinned, **five independent
lineages all reproduce the committed-minority tipping point at ~10%:**

| Lineage | p_c | vs analytic 0.0979 |
|---|---|---|
| DeepSeek | 0.084 | 0.9× |
| Anthropic (haiku) | 0.093 | 1.0× |
| Qwen-72B | 0.095 | 1.0× |
| Meta (llama-70b) | 0.101 | 1.0× |
| OpenAI (gpt-4o-mini) | 0.118 | 1.2× |

→ The Xie–Szymanski (2011) framework **transfers to capable LLM societies,
provider-independently**, with only modest per-lineage variation. The
heterogeneous-mix runs (RQ1) test whether composition shifts this ~10% law.
