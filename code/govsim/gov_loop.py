"""
GovSim episode loop + committed-defector composition builder.

Each month: (optional discussion phase) -> simultaneous harvest -> regeneration.
Run up to `max_months` or until collapse. A fraction p of agents are committed
defectors (the "minority"); composition controls which LLM backs each cooperator.
"""
from __future__ import annotations
import os, sys, random
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import make_backend                      # noqa: E402
from backends import ModelMeter                        # noqa: E402

from resource import Fishery, episode_metrics
from gov_agents import GovAgent, MONITOR_BLOCK

NAMES = ["Ada", "Ben", "Cora", "Dan", "Eve", "Finn", "Gita", "Hugo", "Ivy", "Jon"]


@dataclass
class GovComposition:
    kind: str                 # 'homogeneous' | 'heterogeneous' | 'mixed_competence'
    models: list              # registry keys for cooperators
    adversary: str = "greedy" # 'greedy' | 'persuasive' | 'injected'
    label: str = ""

    def cooperator_models(self, n, seed):
        rng = random.Random(seed * 104729 + 7)
        if self.kind == "homogeneous":
            return [self.models[0]] * n
        if self.kind == "heterogeneous":
            keys = [self.models[i % len(self.models)] for i in range(n)]
            rng.shuffle(keys)
            return keys
        if self.kind == "mixed_competence":
            strong, weak = self.models[0], self.models[1]
            n_weak = n // 2
            keys = [weak] * n_weak + [strong] * (n - n_weak)
            rng.shuffle(keys)
            return keys
        raise ValueError(self.kind)


def homogeneous(model, adversary="greedy"):
    return GovComposition("homogeneous", [model], adversary, f"homo:{model}")

def heterogeneous(models, adversary="greedy"):
    return GovComposition("heterogeneous", list(models), adversary,
                          "hetero:" + "+".join(models))


def build_agents(n, p_committed, seed, comp: GovComposition):
    rng = random.Random(seed)
    n_committed = int(round(p_committed * n))
    committed_ids = set(rng.sample(range(n), n_committed))
    coop_models = comp.cooperator_models(n, seed)
    agents = []
    for i in range(n):
        if i in committed_ids:
            agents.append(GovAgent(i, NAMES[i % len(NAMES)],
                                   model_key=coop_models[i], committed=True,
                                   adversary=comp.adversary))
        else:
            agents.append(GovAgent(i, NAMES[i % len(NAMES)],
                                   model_key=coop_models[i], committed=False))
    backends = {k: make_backend(k) for k in set(coop_models)}
    return agents, backends, n_committed


def run_episode(n, p_committed, seed, comp, meter, max_months=12,
                capacity=100.0, discussion=True, temperature=0.7,
                monitoring=False, sanction=False, sanction_tol=1.2,
                steward=False):
    """`monitoring` reveals last month's per-agent catches (Ostrom principle 4);
    `sanction` reclaims an over-harvester's excess before regeneration
    (principle 5 / restitution). Both default off, reproducing the blind society."""
    agents, backends, n_committed = build_agents(n, p_committed, seed, comp)
    fishery = Fishery(capacity=capacity, stock=capacity, n_agents=n)
    monthly = []
    # both failures and unparseable replies silently fall back to the perfectly
    # sustainable harvest, which would fake the "commons survives" result.
    n_failed = n_unparsed = n_decisions = 0
    last_actual = None          # previous month's per-agent catches (monitoring)
    prev_fair = None            # and the sustainable share they should have met
    total_reclaimed = 0.0
    for month in range(1, max_months + 1):
        # discussion phase (needed for persuasive/injected adversaries)
        disc_summary = ""
        if discussion:
            utterances = [a.discuss(fishery, backends[a.model_key], meter,
                                    temperature) for a in agents]
            disc_summary = "\n".join(utterances)
        if monitoring and last_actual is not None:
            fair_prev = prev_fair if prev_fair is not None else fishery.per_capita_sustainable()
            catches = ", ".join(f"{a.name} {c:.1f}t"
                                for a, c in zip(agents, last_actual))
            disc_summary += MONITOR_BLOCK.format(catches=catches, fair=fair_prev)
        # simultaneous harvest decisions
        prev_fair = fishery.per_capita_sustainable()
        requests = []
        for a in agents:
            tons, _, okflag = a.decide_harvest(fishery, backends[a.model_key],
                                               meter,
                                               history_summary=disc_summary,
                                               temperature=temperature,
                                               steward=steward)
            if okflag is False:
                n_failed += 1
            elif okflag is None:
                n_unparsed += 1
            n_decisions += 1
            requests.append(tons)
        reclaim_fn = None
        if sanction:
            share = fishery.per_capita_sustainable()
            def reclaim_fn(actual, _stock, _share=share, _tol=sanction_tol):
                # majority-rule restitution: any catch beyond `tol` x the
                # sustainable share is returned to the resource
                return sum(max(0.0, c - _tol * _share) for c in actual)
        rec = fishery.apply_harvests(requests, reclaim_fn=reclaim_fn)
        last_actual = rec["actual"]
        total_reclaimed += rec.get("reclaimed", 0.0)
        monthly.append(dict(month=month, stock=round(fishery.stock, 1),
                            caught=round(rec["caught"], 1)))
        if fishery.collapsed():
            break
    m = episode_metrics(fishery, max_months)
    bad = n_failed + n_unparsed
    # Abort only on SYSTEMATIC loss (a dead endpoint, exhausted credit), which
    # shows up as a high rate on a meaningful count. Requiring an absolute floor
    # as well stops two isolated unparseable replies from killing a whole sweep;
    # isolated cases are still recorded below and must be checked in analysis.
    if n_decisions and bad >= 4 and bad / n_decisions > 0.05:
        raise RuntimeError(
            f"aborting: {bad}/{n_decisions} harvest decisions were not real "
            f"observations ({n_failed} failed, {n_unparsed} unparseable). These "
            f"default to the sustainable harvest and would fake cooperation.")
    m.update(n_committed=n_committed, monthly=monthly, n_failed=n_failed,
             n_unparsed=n_unparsed, n_decisions=n_decisions,
             monitoring=monitoring, sanction=sanction, steward=steward,
             total_reclaimed=round(total_reclaimed, 1))
    return m
