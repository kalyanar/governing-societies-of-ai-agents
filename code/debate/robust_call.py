"""Experiment-level retry, above the HTTP-level backoff in backends.py.

Two distinct failure modes kept separate, because conflating them is how a
rate-limited model gets recorded as an incompetent one:

  api_fail   the request never returned (429 exhausted, 5xx, timeout). This is
             DATA LOSS. It must never be scored as a wrong answer.
  unparsed   the request returned, but no answer marker could be extracted.
             Usually a verbose model truncated before emitting the marker.
             Retried with a stricter prompt, then recorded as unparsed.

backends._post_with_retry already handles per-request 429/5xx backoff, but a
sustained upstream throttle can exhaust it. These wrappers retry the whole call
with longer, jittered waits so a transient capacity window degrades latency
rather than silently corrupting a run.
"""
from __future__ import annotations
import random
import time


def call_api(backend, prompt, meter, tag, max_tokens, temperature=0.0, tries=4):
    """Return (GenResult, status) where status is 'ok' or 'api_fail'."""
    r = None
    for attempt in range(tries):
        r = backend.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        meter.add(tag, r)
        if r.ok:
            return r, "ok"
        if attempt < tries - 1:
            time.sleep(min(2 ** attempt * 3, 30) + random.uniform(0, 1.5))
    return r, "api_fail"


def call_parsed(backend, prompt, strict_prompt, parse, meter, tag,
                max_tokens, strict_max_tokens=120, temperature=0.0, tries=4):
    """Call, parse, and retry on BOTH api failure and unparseable output.

    `parse` takes the reply text and returns a value or None. After the first
    unparseable reply we switch to `strict_prompt`, which should demand the
    marker and nothing else. Returns (value, status, last_result) with status
    in {'ok', 'api_fail', 'unparsed'}.
    """
    r = None
    saw_api_fail = False
    for attempt in range(tries):
        p = prompt if attempt == 0 else strict_prompt
        mt = max_tokens if attempt == 0 else strict_max_tokens
        r = backend.generate(p, max_tokens=mt, temperature=temperature)
        meter.add(tag, r)
        if not r.ok:
            saw_api_fail = True
            if attempt < tries - 1:
                time.sleep(min(2 ** attempt * 3, 30) + random.uniform(0, 1.5))
            continue
        v = parse(r.text)
        if v is not None:
            return v, "ok", r
    return None, ("api_fail" if (r is None or not r.ok) and saw_api_fail else "unparsed"), r
