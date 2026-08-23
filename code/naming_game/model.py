"""
Binary-agreement (2-word Naming Game) model — faithful to
Xie, Sreenivasan, Korniss, Zhang, Lim & Szymanski (2011),
"Social consensus through the influence of committed minorities", PRE 84, 011130.

Opinion states per agent: 'A', 'B', or 'AB' (holds both).
A fraction p of agents are COMMITTED to A: they always hold 'A', always voice 'A',
and never update (immune to influence).

Interaction rule (the agreement / Naming-Game dynamics), Table I of the paper:
  - pick a random speaker and one of its neighbours as listener.
  - speaker VOICES one opinion:
        speaker 'A'  -> says 'A'
        speaker 'B'  -> says 'B'
        speaker 'AB' -> says 'A' or 'B' with prob 1/2 each
  - listener UPDATES:
        if listener already holds the voiced opinion -> listener collapses to ONLY
            that opinion (drops the other). [agreement]
        else -> listener ADDS the voiced opinion (becomes 'AB').
  - speaker state is unchanged (single-speaker convention used in the paper).

This module is the PURE MECHANICAL baseline. The listener-update decision is
abstracted behind an `Agent` interface so the same driver can later be backed by
an LLM (llm_agent.py) instead of the deterministic rule.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional

A, B, AB = "A", "B", "AB"
OPINIONS = (A, B, AB)


def voice(state: str, rng: random.Random) -> str:
    """What opinion a speaker in `state` voices."""
    if state == AB:
        return A if rng.random() < 0.5 else B
    return state  # 'A' -> 'A', 'B' -> 'B'


def mechanical_update(listener_state: str, heard: str) -> str:
    """Deterministic Naming-Game listener update (Table I)."""
    if listener_state == heard:               # already holds it -> agree, collapse
        return heard
    if listener_state == AB:                  # holds both, hears one -> collapse to it
        return heard
    # listener holds the single *other* opinion -> add heard -> AB
    return AB


@dataclass
class Agent:
    """A single agent. `committed` agents are immune zealots permanently on A.
    `model_key` names which LLM backs this agent (for heterogeneous societies)."""
    idx: int
    state: str = B
    committed: bool = False
    model_key: Optional[str] = None

    def speak(self, rng: random.Random) -> str:
        if self.committed:
            return self.state    # committed agents always voice their fixed opinion
        return voice(self.state, rng)

    def listen(self, heard: str) -> None:
        if self.committed:
            return  # immune
        self.state = mechanical_update(self.state, heard)


@dataclass
class Population:
    n: int
    p_committed: float
    seed: int = 0
    # adjacency: list of neighbour-index lists. None => complete graph (any pair).
    adjacency: Optional[list] = None
    # model_keys: optional per-agent LLM assignment (len n). committed_model_key:
    # optional override for the committed minority (scale-of-attacker experiments).
    model_keys: Optional[list] = None
    committed_model_key: Optional[str] = None
    # committed_opinion: which opinion the minority pushes (A or B). Uncommitted
    # agents start on the OPPOSITE (the "resistance" opinion). Counterbalancing
    # A vs B controls for a model's intrinsic option bias.
    committed_opinion: str = A
    agents: list = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self.resist_opinion = B if self.committed_opinion == A else A
        n_committed = int(round(self.p_committed * self.n))
        committed_ids = set(self.rng.sample(range(self.n), n_committed))
        self.agents = []
        for i in range(self.n):
            mk = self.model_keys[i] if self.model_keys else None
            if i in committed_ids:
                self.agents.append(Agent(i, state=self.committed_opinion,
                                         committed=True,
                                         model_key=self.committed_model_key or mk))
            else:
                # uncommitted start on the resistance opinion (to be overturned)
                self.agents.append(Agent(i, state=self.resist_opinion,
                                         committed=False, model_key=mk))
        self.n_committed = n_committed

    # --- opinion bookkeeping ---
    def counts(self) -> dict:
        c = {A: 0, B: 0, AB: 0}
        for a in self.agents:
            c[a.state] += 1
        return c

    def frac_A_only(self) -> float:
        return sum(1 for a in self.agents if a.state == A) / self.n

    def n_B(self) -> float:
        """Order parameter from the paper: density of uncommitted nodes in state B."""
        unc = [a for a in self.agents if not a.committed]
        if not unc:
            return 0.0
        return sum(1 for a in unc if a.state == B) / len(unc)

    def n_B_total(self) -> float:
        """Density of ALL nodes in state B (the paper's n_B order parameter,
        active-state value ~0.6504)."""
        return sum(1 for a in self.agents if a.state == B) / self.n

    def n_resist(self) -> float:
        """Unified order parameter: fraction of ALL nodes still holding ONLY the
        resistance opinion (the one the committed minority is trying to overturn).
        Goes 1 -> 0 as the minority wins, regardless of which label (A/B) is
        committed -> directly comparable across counterbalanced runs."""
        return sum(1 for a in self.agents if a.state == self.resist_opinion) / self.n

    def frac_committed_opinion(self) -> float:
        """Fraction of ALL nodes holding ONLY the committed opinion."""
        return sum(1 for a in self.agents if a.state == self.committed_opinion) / self.n

    def consensus_A(self) -> bool:
        """All agents hold exactly A (committed already do)."""
        return all(a.state == A for a in self.agents)

    def consensus(self) -> Optional[str]:
        """Return 'A' or 'B' if the population has reached single-opinion
        consensus, else None. (B-consensus = the committed A-minority failed to
        tip the system = it resisted takeover.)"""
        first = self.agents[0].state
        if first == AB:
            return None
        for a in self.agents:
            if a.state != first:
                return None
        return first  # 'A' or 'B'

    # --- one interaction ---
    def _random_pair(self):
        if self.adjacency is None:
            s, l = self.rng.sample(range(self.n), 2)
            return s, l
        # graph case: pick speaker with >=1 neighbour, then a random neighbour
        while True:
            s = self.rng.randrange(self.n)
            nbrs = self.adjacency[s]
            if nbrs:
                l = nbrs[self.rng.randrange(len(nbrs))]
                return s, l

    def step(self, update_fn=None) -> None:
        """One speaker->listener interaction (standard 2-word Naming Game, Table I).

        Speaker voices an opinion. If the listener already holds it (SUCCESS),
        BOTH speaker and listener collapse to that single opinion. Otherwise
        (FAILURE) the listener ADDS it (becomes AB); speaker is unchanged.
        Committed agents never change state.

        update_fn(listener_agent, heard, population) -> 'A'|'B'|'AB' optionally
        overrides the LISTENER's decision (used by the LLM backend); the
        speaker-collapse-on-success bookkeeping still follows the model.
        """
        s_idx, l_idx = self._random_pair()
        speaker = self.agents[s_idx]
        listener = self.agents[l_idx]
        heard = speaker.speak(self.rng)

        if update_fn is None:
            success = (heard in _inventory(listener.state))
            if success:
                if not listener.committed:
                    listener.state = heard
                if not speaker.committed:
                    speaker.state = heard
            else:
                if not listener.committed:
                    listener.state = AB
        else:
            # LLM decides the listener's new state; speaker collapse on success
            # is inferred from whether the listener ends up holding `heard` alone.
            if not listener.committed:
                new = update_fn(listener, heard, self)
                listener.state = new
            success = (heard in _inventory(listener.state)) and listener.state != AB
            if success and not speaker.committed:
                speaker.state = heard


def _inventory(state: str):
    """The set of opinions an agent in `state` holds."""
    if state == AB:
        return (A, B)
    return (state,)
