"""Minimal .env loader (no dependency). Reads KEY=VALUE lines from a .env file
in this directory into os.environ if not already set. Imported by registry.py so
API keys are available before any backend is built."""
import os

def load_env(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

load_env()
# the project root .env also holds keys (OpenRouter lives there as `openrouterkey`)
load_env(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# normalise the root file's lowercase names to the env vars the registry expects
if "openrouterkey" in os.environ and "OPENROUTER_API_KEY" not in os.environ:
    os.environ["OPENROUTER_API_KEY"] = os.environ["openrouterkey"]
if "groqkey" in os.environ and "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = os.environ["groqkey"]

# Cerebras key lives in a sibling project's .env on this machine. Optional --
# absent on any other checkout, in which case Cerebras models are simply
# reported unavailable by key_available().
load_env(os.path.expanduser("~/pet/edgerouter/.env"))
for _alias in ("CEREBRAS_API_KEY", "CEREBROS_API_KEY_VIJAY", "CEREBROS_API_KEY"):
    if _alias in os.environ and "CEREBRAS_API_KEY" not in os.environ:
        os.environ["CEREBRAS_API_KEY"] = os.environ[_alias]
        break
