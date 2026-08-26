"""
Unified multi-provider LLM backend for the naming-game harness.

Every backend exposes the same `.generate(prompt, system, max_tokens, temperature)`
and returns a normalized GenResult with token usage + latency, so the simulation
loop is provider-agnostic and the cost meter works across all of them.

Providers:
  - ollama            : local models (llama3.2:3b, qwen3:4b, qwen3:32b, ...)
  - openai-compatible : OpenAI, HuggingFace Inference Providers router, and any
                        vLLM/Atlas server (all speak /v1/chat/completions)
  - anthropic         : native Claude /v1/messages

Model IDs are "provider:model" and resolved via registry.py. API keys are read
from the environment; nothing is called unless a key is present.
"""
from __future__ import annotations
import os, time, json, random
from dataclasses import dataclass
from typing import Optional
import requests


def _post_with_retry(url, payload, headers, timeout, max_retries=5):
    """POST with exponential backoff on rate limits (429) / 5xx / transient network
    errors. Honors Retry-After when present. Returns parsed JSON or raises."""
    delay = 1.0
    last_exc = None
    for attempt in range(max_retries):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 529):
                ra = r.headers.get("Retry-After")
                wait = float(ra) if ra and ra.replace(".", "").isdigit() else delay
                time.sleep(wait + random.uniform(0, 0.5))
                delay = min(delay * 2, 30)
                last_exc = requests.HTTPError(f"{r.status_code}")
                continue
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 30)
    raise last_exc if last_exc else RuntimeError("retry failed")


@dataclass
class GenResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    ok: bool = True
    error: Optional[str] = None
    # OpenRouter reports which upstream host served the request. Quantization
    # varies by host, so a scale claim must record it.
    served_by: Optional[str] = None


# ----------------------------------------------------------------------------
class OllamaBackend:
    def __init__(self, model: str, host: str = "http://localhost:11434",
                 timeout: float = 120.0):
        self.model = model
        self.url = host.rstrip("/") + "/api/generate"
        self.timeout = timeout
        self.is_reasoner = any(t in model.lower()
                               for t in ("qwen3", "r1", "deepseek-r1", "thinking"))

    def generate(self, prompt, system=None, max_tokens=8, temperature=0.7):
        full = prompt if system is None else f"{system}\n\n{prompt}"
        if self.is_reasoner:
            full = "/no_think\n" + full
        body = {"model": self.model, "prompt": full, "stream": False,
                "think": False,
                "options": {"temperature": temperature,
                            "num_predict": 32 if self.is_reasoner else max_tokens,
                            "num_ctx": 512}}        # tiny ctx: prompts ~100 tok
        t0 = time.time()
        try:
            r = requests.post(self.url, json=body, timeout=self.timeout)
            r.raise_for_status()
            d = r.json()
        except Exception as e:
            return GenResult("", 0, 0, time.time() - t0, False, str(e))
        return GenResult(d.get("response", ""),
                         d.get("prompt_eval_count", 0), d.get("eval_count", 0),
                         time.time() - t0, True)


# ----------------------------------------------------------------------------
class OpenAICompatBackend:
    """OpenAI, HF Inference Providers router, and vLLM/Atlas — all /v1/chat."""
    def __init__(self, model: str, base_url: str, api_key_env: str,
                 timeout: float = 120.0, extra_headers: Optional[dict] = None,
                 extra_body: Optional[dict] = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}

    @property
    def available(self) -> bool:
        # vLLM/Atlas/local servers often need no key
        return bool(self.api_key) or "localhost" in self.base_url or "127.0.0.1" in self.base_url

    def generate(self, prompt, system=None, max_tokens=8, temperature=0.7):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        ml = self.model.lower()
        is_openai = "api.openai.com" in self.base_url
        # reasoning models: GPT-5 / o-series (OpenAI), gpt-oss, deepseek-r1
        is_reasoner = any(t in ml for t in ("gpt-5", "o1", "o3", "o4-mini",
                                            "gpt-oss", "-r1", "reasoner", "thinking"))
        body = {"model": self.model, "messages": msgs}
        if is_openai and (is_reasoner or ml.startswith("o")):
            # GPT-5/o-series: max_completion_tokens, no custom temperature,
            # minimal reasoning so a 1-token answer stays cheap/fast
            body["max_completion_tokens"] = max(48, max_tokens)
            body["reasoning_effort"] = "minimal"
        else:
            body["max_tokens"] = max(64, max_tokens) if is_reasoner else max_tokens
            body["temperature"] = temperature

        body.update(self.extra_body)
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        t0 = time.time()
        try:
            d = _post_with_retry(self.base_url + "/chat/completions",
                                 body, headers, self.timeout)
        except Exception as e:
            return GenResult("", 0, 0, time.time() - t0, False, str(e))
        try:
            msg = d["choices"][0]["message"]
        except (KeyError, IndexError):
            return GenResult("", 0, 0, time.time() - t0, False,
                             f"no choices: {str(d)[:120]}")
        # robust to null content / reasoning-only replies
        # reasoning-native endpoints may return content=null with the answer in
        # `reasoning` / `reasoning_content` instead
        text = (msg.get("content") or msg.get("reasoning_content")
                or msg.get("reasoning") or "")
        u = d.get("usage", {}) or {}
        return GenResult(text, u.get("prompt_tokens", 0),
                         u.get("completion_tokens", 0), time.time() - t0, True,
                         served_by=d.get("provider"))


# ----------------------------------------------------------------------------
class AnthropicBackend:
    def __init__(self, model: str, api_key_env: str = "ANTHROPIC_API_KEY",
                 base_url: str = "https://api.anthropic.com/v1",
                 version: str = "2023-06-01", timeout: float = 120.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.api_key_env = api_key_env
        self.version = version
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt, system=None, max_tokens=8, temperature=0.7):
        body = {"model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        # Sampling params are REMOVED (hard 400: "`temperature` is deprecated for
        # this model") on the current reasoning tier -- Opus 4.7/4.8/5, Sonnet 5,
        # Fable 5, Mythos 5. Opus/Sonnet 4.6 and older still accept them.
        # Verified against the live API 2026-08-24.
        ml = self.model.lower()
        _no_temp = ("claude-opus-4-7", "claude-opus-4-8", "claude-opus-5",
                    "claude-sonnet-5", "claude-fable-5", "claude-mythos-5")
        if not ml.startswith(_no_temp):
            body["temperature"] = temperature
        if system:
            body["system"] = system
        headers = {"Content-Type": "application/json",
                   "x-api-key": self.api_key,
                   "anthropic-version": self.version}
        t0 = time.time()
        try:
            d = _post_with_retry(self.base_url + "/messages",
                                 body, headers, self.timeout)
        except Exception as e:
            return GenResult("", 0, 0, time.time() - t0, False, str(e))
        text = "".join(b.get("text", "") for b in d.get("content", []))
        u = d.get("usage", {}) or {}
        return GenResult(text, u.get("input_tokens", 0),
                         u.get("output_tokens", 0), time.time() - t0, True)


# ----------------------------------------------------------------------------
class ModelMeter:
    """Per-model token/latency accounting for cost projection. Thread-safe so
    episodes can run concurrently."""
    def __init__(self):
        self.by_model = {}
        import threading
        self._lock = threading.Lock()

    def add(self, model_id: str, r: GenResult):
        with self._lock:
            m = self.by_model.setdefault(model_id, dict(
                calls=0, prompt_tokens=0, completion_tokens=0,
                latency_s=0.0, failures=0, served_by={}))
            m["calls"] += 1
            m["prompt_tokens"] += r.prompt_tokens
            m["completion_tokens"] += r.completion_tokens
            m["latency_s"] += r.latency_s
            if getattr(r, "served_by", None):
                m.setdefault("served_by", {})
                m["served_by"][r.served_by] = m["served_by"].get(r.served_by, 0) + 1
            if not r.ok:
                m["failures"] += 1

    def summary(self):
        return self.by_model
