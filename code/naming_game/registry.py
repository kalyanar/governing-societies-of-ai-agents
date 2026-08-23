"""
Model registry: the experimental ladder in one place.

Each entry: friendly key -> dict(provider, model, scale_b, family, tier, price).
- scale_b : approx parameter count in billions (for the RQ2 scale axis; MoE uses
            total params, with active params noted separately).
- family  : lineage (for the RQ1 heterogeneity axis — diversity = different family)
- tier    : 'local-free' | 'hf-open' | 'frontier' (for budgeting / which-cell)
- price   : (usd_per_1M_input, usd_per_1M_output); (0,0) for local. APPROXIMATE —
            verify against provider pricing pages before any large spend.

IDs/prices are editable: model names and prices drift, so treat this as config.
"""
from __future__ import annotations
import os
import config  # noqa: F401  -- loads .env into os.environ on import
from backends import OllamaBackend, OpenAICompatBackend, AnthropicBackend

OPENAI_BASE = "https://api.openai.com/v1"
HF_BASE = "https://router.huggingface.co/v1"   # HF Inference Providers (OpenAI-compat)
ATLAS_VLLM_BASE = "http://localhost:8000/v1"   # vLLM inside Atlas (when running)
DEEPSEEK_BASE = "https://api.deepseek.com/v1"  # OpenAI-compatible
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"  # OpenAI-compat
OPENROUTER_BASE = "https://openrouter.ai/api/v1"  # OpenAI-compatible multi-vendor router

# key = friendly id used on the CLI / in result files
REGISTRY = {
    # ---- local, free (ollama) -- NON-reasoning instruct models (terse, clean) ----
    "llama3b":   dict(provider="ollama", model="llama3.2:3b",  scale_b=3,  family="llama",  tier="local-free", price=(0, 0)),
    "qwen25_3b": dict(provider="ollama", model="qwen2.5:3b",   scale_b=3,  family="qwen",   tier="local-free", price=(0, 0)),
    "gemma2_2b": dict(provider="ollama", model="gemma2:2b",    scale_b=2,  family="gemma",  tier="local-free", price=(0, 0)),
    # ---- local reasoning models (need special handling; NOT in default sweeps) ----
    "qwen4b":    dict(provider="ollama", model="qwen3:4b",     scale_b=4,  family="qwen",   tier="local-reasoner", price=(0, 0)),
    "qwen32b":   dict(provider="ollama", model="qwen3:32b",    scale_b=32, family="qwen",   tier="local-reasoner", price=(0, 0)),
    # local dense 70B exists on disk but OOMs by default — keep, do not auto-use
    "llama70b_local": dict(provider="ollama", model="llama3.3:70b", scale_b=70, family="llama", tier="local-free", price=(0, 0)),

    # ---- local, free (Atlas vLLM; MoE 35B / ~3B active) ----
    "qwen36_35b_moe": dict(provider="vllm", model="Qwen/Qwen3.6-35B-A3B-FP8", scale_b=35, family="qwen", tier="local-free", price=(0, 0), active_b=3),

    # ---- HuggingFace Inference Providers (big open models, pay-per-token) ----
    "llama70b":  dict(provider="hf", model="meta-llama/Llama-3.3-70B-Instruct",   scale_b=70,  family="llama",   tier="hf-open", price=(0.60, 0.90)),
    "qwen72b":   dict(provider="hf", model="Qwen/Qwen2.5-72B-Instruct",           scale_b=72,  family="qwen",    tier="hf-open", price=(0.60, 0.90)),
    # ---- frontier-class open models (different lineages -> genuine heterogeneity) ----
    # (Llama-405B is NOT served on the HF router; gpt-oss-120b is the OpenAI-lineage open frontier)
    "gptoss120b":dict(provider="hf", model="openai/gpt-oss-120b",                 scale_b=120, family="openai-oss", tier="frontier", price=(0.10, 0.50)),
    "qwen235b":  dict(provider="hf", model="Qwen/Qwen3-235B-A22B",                scale_b=235, family="qwen",    tier="frontier", price=(0.70, 2.80), active_b=22),
    "deepseekv3":dict(provider="hf", model="deepseek-ai/DeepSeek-V3",             scale_b=671, family="deepseek", tier="frontier", price=(0.27, 1.10), active_b=37),
    "deepseekr1":dict(provider="hf", model="deepseek-ai/DeepSeek-R1",             scale_b=671, family="deepseek", tier="frontier", price=(0.55, 2.19), active_b=37),  # reasoning frontier
    # optional cheaper/diverse direct routes (need their own keys; OpenAI-compatible)
    "deepseek_direct": dict(provider="deepseek", model="deepseek-chat",           scale_b=671, family="deepseek", tier="frontier", price=(0.27, 1.10), active_b=37),
    "gemini_pro":      dict(provider="gemini",   model="gemini-2.5-pro",          scale_b=None, family="google",  tier="frontier", price=(1.25, 10.0)),
    "gemini_flash":    dict(provider="gemini",   model="gemini-2.5-flash",        scale_b=None, family="google",  tier="frontier", price=(0.30, 2.50)),

    # ---- OpenAI: full within-family ladder nano -> mini -> flagship ----  prices ~current, verify
    "gpt5":      dict(provider="openai", model="gpt-5",        scale_b=None, family="openai", tier="frontier", price=(1.25, 10.00)),  # current flagship
    "gpt4o_mini":dict(provider="openai", model="gpt-4o-mini",  scale_b=None, family="openai", tier="frontier", price=(0.15, 0.60)),  # cheap NON-reasoning
    "gpt5_mini": dict(provider="openai", model="gpt-5-mini",   scale_b=None, family="openai", tier="frontier", price=(0.25, 2.00)),
    "gpt5_nano": dict(provider="openai", model="gpt-5-nano",   scale_b=None, family="openai", tier="frontier", price=(0.05, 0.40)),
    "gpt4o":     dict(provider="openai", model="gpt-4o",       scale_b=None, family="openai", tier="frontier", price=(2.50, 10.00)),  # prev-gen, for cross-generation comparison

    # ---- Anthropic (frontier + haiku) ----  prices ~current, verify
    "claude_opus":   dict(provider="anthropic", model="claude-opus-4-8",   scale_b=None, family="anthropic", tier="frontier", price=(15.0, 75.0)),
    "claude_sonnet": dict(provider="anthropic", model="claude-sonnet-4-6", scale_b=None, family="anthropic", tier="frontier", price=(3.0, 15.0)),

    # ---- OpenRouter: dense NON-REASONING ladder for the RQ2 capability gate ----
    # Same vendor, same instruct recipe, four dense sizes straddling the claimed
    # ~30B gate. `reasoning=False` marks models with no thinking mode to suppress.
    "or_ministral8b":   dict(provider="openrouter", model="mistralai/ministral-8b-2512",              scale_b=8,   family="mistral", tier="or-open", price=(0.15, 0.15), reasoning=False),
    "or_ministral14b":  dict(provider="openrouter", model="mistralai/ministral-14b-2512",             scale_b=14,  family="mistral", tier="or-open", price=(0.20, 0.20), reasoning=False),
    "or_mistralsmall24b": dict(provider="openrouter", model="mistralai/mistral-small-3.2-24b-instruct", scale_b=24, family="mistral", tier="or-open", price=(0.075, 0.20), reasoning=False),
    "or_mistrallarge":  dict(provider="openrouter", model="mistralai/mistral-large-2512",             scale_b=123, family="mistral", tier="or-open", price=(0.50, 1.50), reasoning=False),
    # cross-family non-reasoning checks (same-generation pairs)
    "or_gemma3_12b":    dict(provider="openrouter", model="google/gemma-3-12b-it",                    scale_b=12,  family="gemma",   tier="or-open", price=(0.05, 0.15), reasoning=False),
    "or_gemma3_27b":    dict(provider="openrouter", model="google/gemma-3-27b-it",                    scale_b=27,  family="gemma",   tier="or-open", price=(0.08, 0.45), reasoning=False),
    "or_granite8b":     dict(provider="openrouter", model="ibm-granite/granite-4.1-8b",               scale_b=8,   family="granite", tier="or-open", price=(0.05, 0.10), reasoning=False),
    "or_llama33_70b":   dict(provider="openrouter", model="meta-llama/llama-3.3-70b-instruct",        scale_b=70,  family="llama",   tier="or-open", price=(0.10, 0.32), reasoning=False),
    "or_qwen25_72b":    dict(provider="openrouter", model="qwen/qwen-2.5-72b-instruct",               scale_b=72,  family="qwen",    tier="or-open", price=(0.36, 0.40), reasoning=False),
    "or_gpt4o_mini":    dict(provider="openrouter", model="openai/gpt-4o-mini",                     scale_b=None, family="openai",  tier="or-open", price=(0.15, 0.60), reasoning=False),
    # ---- OpenRouter replacements for the HF-routed models (HF credits exhausted).
    # Same weights, different host: `served_by` is recorded per call so any
    # quantization difference vs the published HF runs stays auditable.
    "or_deepseekv3":    dict(provider="openrouter", model="deepseek/deepseek-chat-v3-0324",           scale_b=671, family="deepseek",   tier="or-frontier", price=(0.25, 1.00), reasoning=False, active_b=37),
    "or_qwen235b":      dict(provider="openrouter", model="qwen/qwen3-235b-a22b-2507",                scale_b=235, family="qwen",       tier="or-frontier", price=(0.09, 0.55), reasoning=False, active_b=22),
    "or_gptoss120b":    dict(provider="openrouter", model="openai/gpt-oss-120b",                      scale_b=120, family="openai-oss", tier="or-frontier", price=(0.03, 0.17), reasoning=True, no_disable_reasoning=True),
    "or_deepseekr1":    dict(provider="openrouter", model="deepseek/deepseek-r1",                     scale_b=671, family="deepseek",   tier="or-frontier", price=(0.70, 2.50), reasoning=True, active_b=37),
    # identical weights to the direct-API `claude_sonnet` entry (claude-sonnet-4-6);
    # routed via OpenRouter after the direct Anthropic credit balance was exhausted.
    "or_claude_sonnet": dict(provider="openrouter", model="anthropic/claude-sonnet-4.6",              scale_b=None, family="anthropic", tier="or-frontier", price=(3.0, 15.0), reasoning=False),
    # Gemma-4: generation / reasoning / MoE-vs-dense probe (NOT scale-ladder rungs)
    "or_gemma4_31b":    dict(provider="openrouter", model="google/gemma-4-31b-it",                    scale_b=31,  family="gemma",   tier="or-open", price=(0.10, 0.34), reasoning=True),
    "or_gemma4_26b_moe":dict(provider="openrouter", model="google/gemma-4-26b-a4b-it",                scale_b=26,  family="gemma",   tier="or-open", price=(0.07, 0.34), reasoning=True, active_b=4),

    "claude_haiku":  dict(provider="anthropic", model="claude-haiku-4-5",  scale_b=None, family="anthropic", tier="frontier", price=(0.80, 4.0)),
}


def make_backend(key: str):
    """Build a backend object for a registry key."""
    if key not in REGISTRY:
        raise KeyError(f"unknown model '{key}'. known: {sorted(REGISTRY)}")
    e = REGISTRY[key]
    p = e["provider"]
    if p == "ollama":
        return OllamaBackend(e["model"])
    if p == "vllm":
        return OpenAICompatBackend(e["model"], ATLAS_VLLM_BASE, api_key_env="ATLAS_API_KEY")
    if p == "hf":
        return OpenAICompatBackend(e["model"], HF_BASE, api_key_env="HF_TOKEN")
    if p == "openai":
        return OpenAICompatBackend(e["model"], OPENAI_BASE, api_key_env="OPENAI_API_KEY")
    if p == "deepseek":
        return OpenAICompatBackend(e["model"], DEEPSEEK_BASE, api_key_env="DEEPSEEK_API_KEY")
    if p == "gemini":
        return OpenAICompatBackend(e["model"], GEMINI_BASE, api_key_env="GEMINI_API_KEY")
    if p == "openrouter":
        # Ask the router to disable thinking for hybrid-reasoning models so the
        # coordination-primitive probe measures instruction following, not CoT.
        extra = {"HTTP-Referer": "https://github.com/", "X-Title": "agent-governance"}
        body = {"provider": {"require_parameters": False}}
        # some endpoints (gpt-oss-120b) reject the disable flag outright:
        # "Reasoning is mandatory for this endpoint and cannot be disabled."
        if not e.get("no_disable_reasoning"):
            body["reasoning"] = {"enabled": False}
        return OpenAICompatBackend(e["model"], OPENROUTER_BASE,
                                   api_key_env="OPENROUTER_API_KEY",
                                   extra_headers=extra, extra_body=body)
    if p == "anthropic":
        return AnthropicBackend(e["model"])
    raise ValueError(f"bad provider {p}")


def key_available(key: str) -> tuple[bool, str]:
    """Is the model usable right now (key present / local up)?"""
    e = REGISTRY[key]
    p = e["provider"]
    if p == "ollama":
        return True, "local"
    if p == "vllm":
        return True, "needs Atlas vLLM running on :8000"
    env = {"hf": "HF_TOKEN", "openai": "OPENAI_API_KEY",
           "anthropic": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
           "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}[p]
    return bool(os.environ.get(env)), env


def est_cost_per_episode(key: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = REGISTRY[key]["price"]
    return tokens_in / 1e6 * pin + tokens_out / 1e6 * pout


if __name__ == "__main__":
    # `python registry.py` -> show the ladder + key availability
    print(f"{'key':14} {'provider':10} {'tier':11} {'scale':>6} {'family':10} "
          f"{'price(in/out)':>16}  available")
    for k, e in REGISTRY.items():
        ok, info = key_available(k)
        sb = e["scale_b"]
        scale = f"{sb}B" if sb else "-"
        if e.get("active_b"):
            scale += f"/{e['active_b']}A"
        price = f"{e['price'][0]}/{e['price'][1]}"
        flag = "yes" if ok else f"NO ({info})"
        print(f"{k:14} {e['provider']:10} {e['tier']:11} {scale:>6} "
              f"{e['family']:10} {price:>16}  {flag}")
