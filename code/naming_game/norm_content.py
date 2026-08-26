"""Content conditions for the binary-agreement sweep (Experiment A).

Question
--------
Does the committed-minority tipping point depend on WHAT is being agreed, or only
on HOW agreement propagates?

Why it is open
--------------
We reported that the threshold does not generalize from opinion formation to
cooperation. But the two testbeds are not structurally comparable. The naming
game is BISTABLE -- two absorbing conventions -- so a committed minority can flip
it and a sharp p_c exists. The fishery has ONE attractor plus an absorbing death
state: harvesting at or below stock/2 pins the stock at capacity, anything above
decays geometrically to zero, and there is no degraded-but-stable equilibrium in
between. A system without bistability cannot have a tipping point at all, only a
rate -- which is precisely why its apparent threshold proved horizon-dependent.

So the failed generalization may say nothing about cooperation; it may only say
that a depletion process is the wrong instrument for detecting a tipping point.
Note also that the human ~25% result usually cited here (Centola et al. 2018) is
itself about social CONVENTIONS, structurally a naming game rather than a commons.

Design
------
Hold the mechanism exactly fixed -- same update rule, population, grid, estimator
and code path as the published p_c sweep -- and vary only the content of the two
conventions:

  neutral    arbitrary codewords (reproduces the published condition)
  coop_sym   two cooperative norms of equal merit: cooperative framing, but
             neither option is greedier, isolating framing from payoff
  coop_asym  a restrained norm versus a greedy one: cooperative framing WITH the
             payoff asymmetry that a commons has

Reading the result
------------------
p_c unchanged across all three  -> the tipping point is a property of the
    coordination mechanism and is content-independent. The original
    generalization claim was right in substance and the commons was simply an
    unfair test of it.
p_c shifts only in coop_asym    -> payoff asymmetry is the operative variable,
    a sharper claim than either the original or the retraction.

The asymmetric pair is non-neutral by construction, which is the same confound
the p_c study had to fix for the literal tokens "A"/"B". Run every condition with
--push both so the committed minority pushes each side in turn, and report the
residual bias h; otherwise an intrinsic preference for the greedy option would
masquerade as a shifted threshold.
"""
from __future__ import annotations

# Each condition: an ordered label pool plus the one-line framing sentence.
# For coop_asym the first element is the RESTRAINED norm and the second the
# GREEDY one, so that --push A/B is a clean counterbalance over that axis.
CONDITIONS = {
    "neutral": dict(
        pool=[("apple", "mango"), ("circle", "square"), ("river", "mountain"),
              ("copper", "silver"), ("maple", "cedar"), ("violet", "amber"),
              ("harbor", "meadow"), ("comet", "glacier")],
        frame="A group is converging on ONE shared codeword: {wa} or {wb}.",
        asymmetric=False),

    "coop_sym": dict(
        pool=[("east-basin", "west-basin"), ("odd-weeks", "even-weeks"),
              ("dawn-shift", "dusk-shift"), ("north-run", "south-run"),
              ("blue-quota", "green-quota"), ("inner-bay", "outer-bay"),
              ("spring-close", "autumn-close"), ("net-one", "net-two")],
        frame=("A fishing cooperative is converging on ONE shared conservation "
               "rule so the stock survives: {wa} or {wb}. Both protect the stock "
               "equally well; what matters is that everyone follows the same one."),
        asymmetric=False),

    "coop_asym": dict(
        pool=[("take-ten", "take-twenty"), ("half-net", "full-net"),
              ("one-trip", "three-trips"), ("small-mesh", "wide-mesh"),
              ("quota-low", "quota-high"), ("rest-days", "no-rest"),
              ("share-catch", "keep-catch"), ("light-haul", "heavy-haul")],
        frame=("A fishing cooperative is converging on ONE shared harvest rule: "
               "{wa} or {wb}. Everyone must end up following the same rule."),
        asymmetric=True),
}

RULE_TAIL = (
    " You currently use: {held}. A peer just used: \"{heard}\". "
    "Apply this rule: if you ALREADY use {heard}, drop everything else and keep "
    "ONLY {heard}; if {heard} is new to you, ADD it so you now use both.{terse}"
)


def install(cond: str):
    """Swap llm_agent's label pool and framing in place.

    Only the words and the framing sentence change; the update rule, the parser,
    the population and the estimator are untouched, so any difference in p_c is
    attributable to content alone.
    """
    if cond not in CONDITIONS:
        raise KeyError(f"unknown content condition {cond!r}; "
                       f"known: {sorted(CONDITIONS)}")
    import random as _random
    import llm_agent
    from model import A, B

    c = CONDITIONS[cond]
    pool = list(c["pool"])

    def make_labels(rng: _random.Random):
        pair = list(pool[rng.randrange(len(pool))])
        # Deliberately NOT shuffled: the pool order carries the restrained/greedy
        # axis for coop_asym, and --push A/B is what counterbalances it. For the
        # symmetric pools the order is arbitrary anyway.
        return {A: pair[0], B: pair[1]}

    llm_agent.make_labels = make_labels
    llm_agent.SYSTEM = c["frame"] + RULE_TAIL
    llm_agent.RULE_GUIDED = c["frame"] + RULE_TAIL
    return c
