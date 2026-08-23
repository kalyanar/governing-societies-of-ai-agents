"""
Composition layer (RQ1): build homogeneous vs heterogeneous LLM societies and
the per-agent backend map. This is what lets us measure how the tipping point
p_c shifts between a monoculture and a mixed-model population.

Composition specs
-----------------
homogeneous(model)                 : all uncommitted agents use one model.
heterogeneous(models)              : uncommitted agents round-robin across a list
                                     of DIFFERENT models (competence-matched diversity).
mixed_competence(strong, weak, f)  : fraction f of agents use a weak model, rest
                                     strong -> tests the "competence floor".

The committed minority can use its own model (committed_model) so we can scale the
ATTACKER independently of the majority (RQ2 dual-use).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import random
from model import Population
from registry import make_backend, REGISTRY


@dataclass
class Composition:
    kind: str                       # 'homogeneous' | 'heterogeneous' | 'mixed_competence'
    models: list                    # list of registry keys for uncommitted agents
    committed_model: Optional[str] = None   # registry key for committed minority
    weak_fraction: float = 0.0      # for mixed_competence
    label: str = ""

    def model_keys(self, n: int, seed: int) -> list:
        rng = random.Random(seed * 7919 + 13)
        if self.kind == "homogeneous":
            return [self.models[0]] * n
        if self.kind == "heterogeneous":
            # deterministic round-robin then shuffled so position != model
            keys = [self.models[i % len(self.models)] for i in range(n)]
            rng.shuffle(keys)
            return keys
        if self.kind == "mixed_competence":
            strong, weak = self.models[0], self.models[1]
            n_weak = int(round(self.weak_fraction * n))
            keys = [weak] * n_weak + [strong] * (n - n_weak)
            rng.shuffle(keys)
            return keys
        raise ValueError(self.kind)


def homogeneous(model, committed_model=None):
    return Composition("homogeneous", [model],
                       committed_model=committed_model or model,
                       label=f"homo:{model}")


def heterogeneous(models, committed_model=None):
    return Composition("heterogeneous", list(models),
                       committed_model=committed_model,
                       label="hetero:" + "+".join(models))


def mixed_competence(strong, weak, weak_fraction=0.5, committed_model=None):
    return Composition("mixed_competence", [strong, weak],
                       committed_model=committed_model or strong,
                       weak_fraction=weak_fraction,
                       label=f"mixed:{strong}+{weak}@{weak_fraction:g}")


def build_population(n, p_committed, seed, comp: Composition, adjacency=None,
                     committed_opinion="A"):
    """Return (Population, backend_map) for the given composition.
    committed_opinion: 'A' or 'B' — which label the minority pushes (counterbalance)."""
    mks = comp.model_keys(n, seed)
    pop = Population(n=n, p_committed=p_committed, seed=seed, adjacency=adjacency,
                     model_keys=mks, committed_model_key=comp.committed_model,
                     committed_opinion=committed_opinion)
    # build one backend per distinct model key actually used
    used = set(a.model_key for a in pop.agents if a.model_key)
    backend_map = {k: make_backend(k) for k in used}
    return pop, backend_map


def composition_report(pop):
    """Counts of model usage, split by committed/uncommitted — for logging."""
    from collections import Counter
    unc = Counter(a.model_key for a in pop.agents if not a.committed)
    com = Counter(a.model_key for a in pop.agents if a.committed)
    return dict(uncommitted=dict(unc), committed=dict(com))
