# Governing Societies of AI Agents

Code, data and figures for *Governing Societies of AI Agents: Committed Minorities,
Model Diversity, and Scale as Levers of Multi-Agent AI Governance*
(Kalyanaraman & Madisetti).

The paper asks three questions about societies of LLM agents:

| | Question |
|---|---|
| **RQ1** | Is a single-model *monoculture* more capturable than a *heterogeneous* society? |
| **RQ2** | Does model scale determine fitness to govern? |
| **RQ3** | What fraction of committed agents can capture a collective decision? |

Every number in the paper is produced by a script here and traceable to a JSON
file in `code/results/`. Figures are regenerated from those same files by
`code/make_figures_refresh.py` into `code/figures/`.

The manuscript source is not included here while the paper is under review; this
repository is the code, the per-run result files, and the figures.

---

## Reproducing the revision experiments

Each writes a JSON to `code/results/` and records its own API-failure and
parse-failure rates; any arm above 5% loss is marked unreliable rather than
reported.

```bash
cd code/debate

# cheap panel + a constrained arbiter, versus the same model reasoning alone.
# Both arms use one judge model and an identical token budget.
../../.venv/bin/python head_to_head.py --limit 80 \
  --panel cb_gptoss120b cb_gemma4_31b gq_qwen36_27b \
  --judge an_opus5 --out ../results/head_to_head.json

# eleven verifiers, 2B to frontier, against a fixed panel:
# select-vs-solve plus a paired order-reversal control
../../.venv/bin/python verifier_price_ladder.py --limit 80 \
  --out ../results/verifier_size_ladderA.json

# does the arbiter need the source, or only the candidates?
../../.venv/bin/python blind_selector.py --limit 80 \
  --out ../results/blind_selector.json

cd ../naming_game
# does the tipping point depend on WHAT is agreed? identical mechanism,
# three content conditions, counterbalanced
for C in neutral coop_sym coop_asym; do
  ../../.venv/bin/python run_society.py --comp homo --models or_gpt4o_mini \
    --n 48 --ps 0.0625 0.0833 0.1042 0.125 0.1667 0.2083 0.25 \
    --seeds 5 --t_max_units 25 --push both --content $C \
    --out ../results/norm_content_$C.json
done
../../.venv/bin/python analyze_content.py     # p_c per condition, bootstrap CIs
```

Then, with no API calls:

```bash
cd code
../.venv/bin/python make_figures_refresh.py   # figures -> code/figures/
../.venv/bin/python audit_paper.py --tex /path/to/paper_dtrap.tex
```

`audit_paper.py` checks every load-bearing number in a manuscript against the
result file that produced it, and flags figures older than their data, dangling
cross-references, and superseded claim text.

### Cost

Every run records its own metered spend, so the total is recomputable rather than
asserted:

```bash
../.venv/bin/python total_cost.py            # total, plus the ten priciest runs
../.venv/bin/python total_cost.py --by-file  # every file
```

**$82.32** across 113 result files (83 with recorded cost), split roughly
$33 for the original study, $46 for the higher-resolution revision sweeps, and
$3 for the final round. The two largest single runs are the `N=64` capture-threshold
sweeps for Claude-Haiku ($11.82) and Llama-70B ($10.71). Runs on local Ollama,
Cerebras and Groq are priced at zero and contribute nothing.

Two caveats a reader reconciling this against the paper will hit. Provider list
prices change, so these are the prices recorded at run time rather than today's.
And superseded runs are retained rather than deleted, so the total includes work
that no longer backs a claim -- the free-form-judge verifier run replaced by the
constrained instrument, and runs discarded by the data-quality audit. Keeping them
is deliberate: it makes the exclusions auditable.

---

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then add your key(s) -- see below
```

Reproduce the two headline figures from the committed result files, with no API
calls and no keys:

```bash
.venv/bin/python code/make_figures_v2.py
```

---

## API keys

Copy `.env.example` to `.env` (git-ignored) and fill in whichever providers you
plan to use. **One OpenRouter key is enough to run everything in the paper** — it
reaches OpenAI, Anthropic, Mistral, Google, Qwen and Meta models through a single
endpoint.

| Variable | Provider | Needed for |
|---|---|---|
| `openrouterkey` | OpenRouter | all `or_*` model keys — the simplest route |
| `OPENAI_API_KEY` | OpenAI | `gpt4o`, `gpt4o_mini`, `gpt5*` |
| `ANTHROPIC_API_KEY` | Anthropic | `claude_haiku`, `claude_sonnet`, `claude_opus` |
| `HF_TOKEN` | HuggingFace router | `llama70b`, `qwen72b`, `deepseekv3`, … |
| *(none)* | Ollama on `:11434` | `llama3b`, `qwen25_3b`, `gemma2_2b`, … |

`code/naming_game/config.py` loads `.env` from both the repo root and
`code/naming_game/`, and maps the lowercase `openrouterkey` to
`OPENROUTER_API_KEY`. To see what is reachable right now:

```bash
cd code/naming_game && ../../.venv/bin/python registry.py
```

**Cost.** The full set of experiments in the paper costs roughly **$70** in API
spend. The expensive item is the naming-game sweep (~$20; ~120k calls per model
lineage); everything else is single-digit dollars, and the capability probe is
under $0.02.

---

## The experiments

Each subsection states *why the experiment exists* — what claim it was built to
test, and what a negative result would have meant.

### 1. Binary agreement / naming game — `code/naming_game/`

**Purpose (RQ3).** Xie et al. (2011) proved that in a two-opinion Naming Game, a
committed minority above `p_c ≈ 0.0979` flips the population's convention. The
question is whether that carries over when the update rule is executed by an LLM
rather than by an automaton. If it does, "committed minority" becomes a
*quantifiable attack surface* for agent societies.

**Design.** `N` agents hold `A`, `B` or `AB`. A fraction `p` is permanently
committed. Each interaction picks a speaker and a listener; the listener's update
is decided by *its own model*. Opinions are presented as randomly drawn neutral
nouns (maple/cedar) rather than the literal tokens "A"/"B", which carry a large
model-specific prior, and each configuration is run in both directions so that
residual bias cancels.

```bash
cd code/naming_game
# mechanical baseline -- no LLM, no key, validates the harness
../../.venv/bin/python simulate.py --n 1000 --seeds 20
# finite-size scaling of the mechanical model
../../.venv/bin/python finite_size.py
# the LLM sweep (this is the expensive one)
./run_n64.sh anthropic          # or: openai | hf | all
# fit p_c with bootstrap CIs
../../.venv/bin/python analysis.py '../results/n64_*.json'
```

**Result files.** `results/n64_*.json`, `results/finite_size.json`.
**Finding.** Five lineages pool to `p_c = 0.0959 ± 0.0019`, against the analytic
`0.0979`.

> **Note on grid resolution.** Earlier runs used `N=16` on a grid whose only
> interior point was `p=0.1`, so the whole transition fell between two points and
> the fitted `p_c` was a re-encoding of a single measurement. `run_n64.sh` places
> grid points on exact multiples of `1/N` so each corresponds to an unambiguous
> committed count. Those superseded files are kept (`n64_qwen72b.json`,
> `n64_llama70b.json`, `n64_gpt4o_mini.json`) because they failed the data-quality
> audit below and are cited as such in the paper.

### 2. Capability probe — `code/naming_game/rule_probe.py`

**Purpose (RQ2).** The paper claims a *capability gate*: below some scale, agents
cannot execute the coordination primitive at all, so composition is moot. The
probe measures that directly instead of inferring it from dynamics.

**Design.** The agreement rule has three cases — hear what you hold (collapse),
hear something new (adopt both), hold both and hear one (collapse to it). Each is
scored separately against the mechanical rule, using the *identical* prompt the
live simulation sends. Scoring the cases separately matters: the characteristic
small-model failure is answering "both" regardless of input, which is correct for
exactly one of the three and therefore invisible in a pooled accuracy figure.

```bash
cd code/naming_game
../../.venv/bin/python rule_probe.py --models llama3b qwen25_3b gemma2_2b --trials 30 \
    --out ../results/rule_probe_local_baseline.json
```

**Finding.** The floor is between 3B and 8B, not ~30B. Above 8B the curve is flat;
a 123B model scores *below* an 8B one, and a mixture-of-experts model with 4B
*active* parameters passes. Parameter count is not the operative variable.

### 3. Adversarial debate & error correlation — `code/debate/`

**Purpose (RQ1).** Heterogeneity is assumed to decorrelate errors. If different
lineages fail on the *same* items, a diverse panel is diverse in name only, and
the wisdom-of-crowds argument for it collapses.

```bash
cd code/debate
../../.venv/bin/python run_debate.py --comp hetero --models claude_haiku gpt4o_mini qwen72b \
    --n 6 --rounds 3 --out ../results/debate_hard_hetero.json
../../.venv/bin/python error_correlation.py ../results/fsolo_*.json
```

**Finding.** Pairwise error correlation `ρ ≈ 0.5`, so seven lineages behave like
~1.7 independent voters — the *illusion of diversity*.

### 4. Verifier ladder — `code/debate/verifiers_constrained.py`

**Purpose (RQ1).** The competence band predicts that diversity raises a *coverage
ceiling* which only a good aggregator realizes. Testing that requires a verifier
that **selects** among the panel's answers.

**Why the original design failed.** An unconstrained judge stronger than the panel
can simply answer the question itself, and then its accuracy says nothing about
the panel. `judge_alone.py` demonstrates this: the judge scored 0.625 with **no
panel at all**, identical to its panel-assisted score, and it answered *outside*
the panel's span on 25–33% of items. The fix is to require a *solver index*, which
makes an off-panel answer inexpressible.

```bash
cd code/debate
../../.venv/bin/python judge_alone.py            # the control that exposed it
../../.venv/bin/python verifiers_constrained.py  # constrained ladder + controls
```

**Finding.** With the constraint enforced the theory holds end to end: a
monoculture's ceiling equals its best member exactly (0.350 = 0.350, no headroom),
a diverse panel has headroom that blind voting destroys (0.450, `v̂ ≈ −1`) and a
constrained selector partly realizes (0.550, `v̂ ≈ +0.33`).

### 5. Value deliberation — `code/deliberate/`

**Purpose (RQ1).** The clearest case *for* heterogeneity should be where no ground
truth exists and no verifier can be built. If a monoculture converges to identical
positions, diversity is protecting against manufactured consensus.

```bash
cd code/deliberate
../../.venv/bin/python run_deliberate.py --comp homo --models claude_sonnet --n 6 --rounds 4 \
    --out ../results/dyn_homo_sonnet.json
../../.venv/bin/python dynamics.py ../results/dyn_homo_sonnet.json ../results/dyn_hetero5.json
```

**Finding.** Six copies of one model converge to identical stances (dispersion
0.00) with near-verbatim reasoning; five distinct models preserve disagreement
(0.47) and resist a committed extremist.

### 6. Commons cooperation — `code/govsim/`

**Purpose (RQ2, RQ3).** Whether the capture threshold generalizes from opinion
formation to a setting with a real resource at stake.

**Design.** A fishery of 100 tons; whatever remains after harvest **doubles**,
capped at capacity, so sustainable total harvest is `stock/2`. Committed defectors
take twice the per-capita sustainable share. Three institutional options, added
one at a time, instantiate Ostrom's design principles:

| flag | what it adds | Ostrom |
|---|---|---|
| *(none)* | agents see the stock and stated intentions only | — |
| `--monitoring` | reveals last month's **per-agent catches** | principle 4 |
| `--steward` | objective becomes resource persistence + fair sharing | — |
| `--sanction` | an over-harvester's excess is returned to the lake | principle 5 |

```bash
cd code/govsim
# the four arms reported in the paper
../../.venv/bin/python run_govsim.py --comp homo --models or_claude_sonnet \
    --ps 0.0 0.20 0.40 --n 5 --seeds 3 --max_months 30 \
    --monitoring --steward --sanction --out ../results/arm_D_mon_steward_sanction.json
```

**Findings.** Without adversaries the society holds the lake at *exact* capacity
for 30/30 months — a counterexample to the Hardin baseline. With adversaries,
tolerance is a property of the institution: none at all when blind and
self-interested, one defector under stewardship, three in five with restitution.
Survival is predicted not by the adversary's *share* but by whether the required
per-agent restraint exceeds the granularity at which agents can express a
decision.

> **Horizon matters.** A 10-month window records the single-defector runs as
> survivals while their stock is already down to a fifth of capacity and still
> falling. Any threshold quoted without its observation horizon overstates
> robustness. Use `--max_months 30`.

### 7. Prompt-injection propagation — `code/injection/`

**Purpose (RQ1, security).** The unconditional argument for diversity: a
monoculture is one shared attack surface. Infection is operationalized strictly as
emitting an inert marker; no harmful capability is requested or exercised.

```bash
cd code/injection && ./run_all.sh
```

**Finding.** A susceptible monoculture is 100% compromised; a heterogeneous chain
is contained by its first resistant link (18–38%). Note that containment depends
on *where* that link falls, so the per-seed distribution matters, not just the
mean.

### 8. Institutional decision rules — `code/institutions/`

**Purpose (RQ3).** Whether the capture threshold is a property of the population
or of the voting rule. Purely mechanical, so it is free and fast.

```bash
cd code/institutions
../../.venv/bin/python mech.py                  # cascade model, no API calls
./run_council_all.sh                            # LLM council counterpart
```

**Finding.** Simple majority ≈ 30%, two-thirds supermajority ≈ 37.5%, delegation
≈ 7.5%, veto ≈ 1.7%. The aggregation rule moves the threshold by a factor of ~20.

---

## Data-quality auditing

Multi-agent simulations degrade *silently* under partial API failure, because the
natural fallback for a failed decision is itself a plausible observation:

- In the naming game, leaving an agent's state unchanged is indistinguishable from
  an agent that deliberately held its ground — so a dead endpoint renders as a
  population that **perfectly resisted capture**.
- In the commons, the fallback is the sustainable harvest — so a dead endpoint
  renders as **textbook cooperation**, which is the headline result.

Both harnesses therefore treat failed and unparseable responses as *data loss, not
observations*. Every run records how many decisions fell back to a default, and
aborts when that count is both material and above a small fraction of the total.

This is not hypothetical. **Three of six naming-game runs were silently corrupt**
(one at 100% failure from exhausted credit, two at 10–13% from rate limiting), and
each produced a plausible, publishable-looking number. The 10%-degraded Llama run
gave `p_c = 0.0795` against a clean `0.0985` — a 19% error in the direction that
looks like a real finding. Always check the reported fallback count before
trusting a result file.

Related pitfall: **parse strictly.** Free-text numeric answers must be read from an
explicit marker (`CATCH: <n>`, `ANSWER: <letter>`, `SOLVER: <n>`), never by
scanning for the first number — a truncated reply then yields the *stock size*
from the model's own reasoning and manufactures a catastrophic over-harvest.

## Provider notes

- **OpenRouter** may route one nominal model to many upstream hosts at differing
  quantization. `backends.py` records the serving host per call
  (`served_by` in each result file's meter); one Qwen host returns empty content.
  Pin providers before publishing scale-sensitive numbers.
- **Reasoning models** are disabled where the provider allows it, so the
  coordination tasks measure instruction-following rather than chain-of-thought.
  `gpt-oss-120b` mandates reasoning and is flagged accordingly — it needs ~49
  output tokens to say one word, so it is poor value for high-call-count sweeps.
- **Anthropic reports an exhausted balance as HTTP 400**, not 402/429, which reads
  like a malformed request. Check the response body.

## Layout

```
code/
  naming_game/   binary-agreement model, capability probe, model registry, backends
  debate/        adversarial debate, error correlation, verifier ladder + controls
  deliberate/    value deliberation on moral dilemmas
  govsim/        commons cooperation with monitoring / steward / restitution
  injection/     prompt-injection propagation through an agent chain
  institutions/  Granovetter cascade + LLM council
  results/       every result file cited in the paper
  figures/       generated figures
  make_figures_v2.py
paper/           manuscript sources, figures, bibliography
```

## Citation

```bibtex
@article{kalyanaraman2026governing,
  title  = {Governing Societies of AI Agents: Committed Minorities, Model
            Diversity, and Scale as Levers of Multi-Agent AI Governance},
  author = {Kalyanaraman, Gopal and Madisetti, Vijay K.},
  year   = {2026}
}
```
