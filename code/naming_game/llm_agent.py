"""
LLM backend for the binary-agreement model.

The LISTENER is an LLM: given its current opinion and the opinion a neighbour
just voiced, it decides its new stance. We map the reply to {A, B, AB}. The
speaker-collapse-on-success bookkeeping is handled in Population.step.

Design choices that keep this FAITHFUL to the Naming Game while letting real LLM
behaviour (stubbornness / herding / sycophancy) drive the dynamics:
  - The agent is told it currently holds opinion(s) X and a peer just asserted Y.
  - It must answer with which opinion(s) it now holds: "A", "B", or "both".
  - We do NOT hard-code the agreement rule into the prompt; the model decides.
    (A "rule-guided" prompt variant is available for ablation.)

Backend: ollama HTTP API (local). Every call is metered (prompt/eval tokens,
latency) and the totals are accessible for cost projection.
"""
from __future__ import annotations
import json, time, re
import requests
from dataclasses import dataclass, field
from model import A, B, AB

OLLAMA_URL = "http://localhost:11434/api/generate"


@dataclass
class Meter:
    calls: int = 0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    total_latency_s: float = 0.0
    parse_failures: int = 0

    def add(self, prompt_toks, eval_toks, latency):
        self.calls += 1
        self.prompt_tokens += prompt_toks
        self.eval_tokens += eval_toks
        self.total_latency_s += latency

    def summary(self):
        tot = self.prompt_tokens + self.eval_tokens
        return dict(calls=self.calls, prompt_tokens=self.prompt_tokens,
                    eval_tokens=self.eval_tokens, total_tokens=tot,
                    avg_tokens_per_call=(tot / self.calls if self.calls else 0),
                    avg_latency_s=(self.total_latency_s / self.calls
                                   if self.calls else 0),
                    parse_failures=self.parse_failures)


# NEUTRAL, randomized labels — "A"/"B" carry a huge intrinsic token bias in LLMs
# (small models collapse to "B" regardless of dynamics). A pool of roughly-neutral
# pairs, randomly assigned to the abstract opinions per episode, decorrelates any
# residual token preference from the abstract committed/resist role.
LABEL_POOL = [
    ("apple", "mango"), ("circle", "square"), ("river", "mountain"),
    ("copper", "silver"), ("maple", "cedar"), ("violet", "amber"),
    ("harbor", "meadow"), ("comet", "glacier"),
]


def make_labels(rng):
    """Pick a neutral pair and randomly map it to abstract opinions A/B."""
    pair = list(LABEL_POOL[rng.randrange(len(LABEL_POOL))])
    rng.shuffle(pair)
    return {A: pair[0], B: pair[1]}


def _tmpl(wa, wb):
    return (" Respond with ONLY one of these words and nothing else "
            f"(no explanation, no punctuation): {wa}, {wb}, or both.")

SYSTEM = (
    "A group is converging on ONE shared codeword: {wa} or {wb}. "
    "You currently use: {held}. A peer just used: \"{heard}\". "
    "Apply this rule: if you ALREADY use {heard}, drop everything else and keep "
    "ONLY {heard}; if {heard} is new to you, ADD it so you now use both.{terse}"
)

RULE_GUIDED = (
    "You are playing the Naming Game to reach consensus between {wa} and {wb}. "
    "You currently hold: {held}. A peer said: \"{heard}\". "
    "Rule of thumb: if you already hold what the peer said, agree and keep only "
    "that; otherwise add it and hold both.{terse}"
)


def _parse(text: str, labels: dict | None = None) -> str | None:
    """Map a model reply back to abstract A/B/AB. With neutral `labels`, match the
    label words; without, fall back to literal A/B/AB tokens."""
    t = text.strip().lower()
    if labels is not None:
        wa, wb = labels[A].lower(), labels[B].lower()
        ha = re.search(rf"\b{re.escape(wa)}\b", t)
        hb = re.search(rf"\b{re.escape(wb)}\b", t)
        if "both" in t or (ha and hb):
            return AB
        if ha and not hb:
            return A
        if hb and not ha:
            return B
        return None
    # legacy literal A/B/AB
    tu = text.strip().upper()
    if re.search(r"\bAB\b", tu) or "BOTH" in tu:
        return AB
    m = re.search(r"\b([AB])\b", tu)
    if m:
        return m.group(1)
    return tu[-1] if tu and tu[-1] in ("A", "B") else None


def build_prompt(state: str, heard: str, labels: dict, rule_guided: bool = False):
    """Return (system, user) for the listener decision, using neutral `labels`."""
    wa, wb = labels[A], labels[B]
    held = f"both {wa} and {wb}" if state == AB else labels[state]
    heard_txt = labels[heard]
    tmpl = RULE_GUIDED if rule_guided else SYSTEM
    text = tmpl.format(wa=wa, wb=wb, held=held, heard=heard_txt, terse=_tmpl(wa, wb))
    return None, text


def make_society_update_fn(backend_map, meter, labels, rule_guided: bool = False,
                           temperature: float = 0.7, max_tokens: int = 8,
                           max_fail_frac: float = 0.02):
    """Per-agent dispatch update_fn: the LISTENER's own model decides its update.
    `backend_map` maps model_key -> backend; `meter` is a backends.ModelMeter;
    `labels` is the per-episode neutral A/B word mapping.

    Raises RuntimeError if more than `max_fail_frac` of calls fail, so a dead
    endpoint cannot masquerade as a population that refused to update."""
    def update_fn(listener, heard, population):
        backend = backend_map.get(listener.model_key)
        if backend is None:
            return listener.state
        system, user = build_prompt(listener.state, heard, labels, rule_guided)
        res = backend.generate(user, system=system, max_tokens=max_tokens,
                               temperature=temperature)
        meter.add(listener.model_key, res)
        if not res.ok:
            # A failed call must NOT silently look like "the agent held its
            # ground": that renders an API outage as perfect resistance
            # (n_resist=1.0 at every p), which is indistinguishable from a real
            # scientific result. Abort loudly once failures dominate.
            # Use the shared meter for BOTH numerator and denominator: it is
            # global across episodes, whereas a per-episode counter would be
            # compared against a global call count and under-report the rate.
            st = meter.summary().get(listener.model_key, {})
            n_fail, n_tot = st.get("failures", 0), max(st.get("calls", 1), 1)
            if n_tot >= 50 and n_fail / n_tot > max_fail_frac:
                raise RuntimeError(
                    f"aborting: {n_fail}/{n_tot} calls failed "
                    f"({n_fail/n_tot:.0%} > {max_fail_frac:.0%}) for "
                    f"{listener.model_key}. last error: {res.error}")
            return listener.state
        parsed = _parse(res.text, labels)
        return parsed if parsed is not None else listener.state
    return update_fn


def make_llm_update(model: str, meter: Meter, rule_guided: bool = False,
                    temperature: float = 0.7, num_predict: int = 6,
                    timeout: float = 60.0):
    """Return an update_fn(listener_agent, heard, population) for Population.step."""
    tmpl = RULE_GUIDED if rule_guided else SYSTEM

    is_reasoner = any(tag in model.lower() for tag in ("qwen3", "r1", "deepseek-r1",
                                                        "thinking"))

    def update_fn(listener, heard, population):
        held = "both A and B" if listener.state == AB else listener.state
        heard_txt = "option A" if heard == A else "option B"
        prompt = tmpl.format(held=held, heard=heard_txt)
        if is_reasoner:
            prompt = "/no_think\n" + prompt
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": temperature,
                        # reasoners need more room even with thinking off
                        "num_predict": 32 if is_reasoner else num_predict},
        }
        t0 = time.time()
        try:
            resp = requests.post(OLLAMA_URL, json=body, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            meter.parse_failures += 1
            return listener.state  # network failure -> no change
        latency = time.time() - t0
        meter.add(data.get("prompt_eval_count", 0),
                  data.get("eval_count", 0), latency)
        parsed = _parse(data.get("response", ""))
        if parsed is None:
            meter.parse_failures += 1
            return listener.state  # unparseable -> no change (conservative)
        return parsed

    return update_fn


def ping(model: str) -> bool:
    try:
        r = requests.post(OLLAMA_URL,
                          json={"model": model, "prompt": "Reply with: A",
                                "stream": False,
                                "options": {"num_predict": 3}}, timeout=30)
        return r.ok
    except Exception:
        return False
