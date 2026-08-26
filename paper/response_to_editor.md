# Response to the Associate Editor

**Manuscript ID:** COL-26-0021
**Title:** Governing Societies of AI Agents: Committed Minorities, Model Diversity, and Scale as Levers of Multi-Agent AI Governance
**Authors:** Gopal Kalyanaraman, Vijay K. Madisetti
**Journal:** *Collective Intelligence*

---

Dear Dr. Becker,

Thank you for the decision on COL-26-0021 and, in particular, for the unusual step
of returning the manuscript with a specific structural diagnosis rather than
sending it to referees in a form they could not assess. That was the right call,
and acting on it improved the paper considerably more than we anticipated — for
reasons we set out in Part B below.

We respond first to your comment point by point, then disclose a set of changes
that were not requested but that arose directly from acting on it.

---

## Part A — Response to the Associate Editor's comment

> *"your paper is missing sufficiently detailed methods description, e.g. a
> methods section… I believe both that this paper holds promise, and also that
> reviewers will be unable to assess the paper in its present form."*

We agree, and we accept the diagnosis without reservation. The original submission
described *what* each testbed measured but not *how*, which left a referee unable
to judge whether the measurements supported the claims. We have added a **Methods** section and a detailed **Appendix B**. Following your
suggestion below, the body carries a compact methods overview (~820 words) and the
full protocols, prompt templates and parameter table live in the appendix, so the
body stays readable while the paper remains conceptually replicable on its own.

> *"Please note that making your reproducibility code available to reviewers would
> not suffice for methods. The paper must stand on its own, and allow for full
> conceptual replication, without reference to any supplied reproducibility
> code."*

Understood, and the new material is written to that standard. Appendix B reproduces
**every prompt template verbatim**, together with the neutral-label pool, the
parsing rules, and a parameter table giving population size, rounds or horizon,
seed count and committed-fraction grid for all eight studies. A reader can
reconstruct each experiment from the paper alone.

> *"how you constructed the LLM interaction"*

*Methods → Agents, Models, and Providers* defines an agent as a stateless chat-completion call carrying its
current state and locally visible context, with all state held by the simulator
rather than the model. This is what makes population *composition* a free variable
and is the mechanism underlying every homogeneous-versus-heterogeneous comparison
in the paper.

> *"how you prompted the LLMs"*

Each paradigm's subsection states its prompting scheme, and Appendix B gives the
templates verbatim. We draw particular attention to *Methods → Binary Agreement*, which documents
a control absent from the original submission: the literal tokens "A" and "B" carry
a large, model-specific prior that dominates the social dynamics, so opinions are
realised as randomly drawn neutral nouns and every configuration is run in both
directions. We report the residual bias statistic (*h* ≈ 0 in all conditions).

> *"how you measured outcomes to get the reported results"*

Each subsection now states its estimator explicitly — the order parameter and
logistic fit with bootstrap intervals for the capture threshold; coverage, error
correlation and realised accuracy for the ensemble studies; survival, stock
trajectory and yield for the commons.

*Methods → Data-Quality Auditing* adds a methodological control we consider important enough to
generalise beyond this paper. Multi-agent simulations degrade *silently* under
partial API failure, because the natural fallback for a failed decision is itself
a plausible observation: in the binary-agreement model an unchanged opinion is
indistinguishable from an agent that deliberately held its ground, so a dead
endpoint renders as a population that perfectly resisted capture; in the commons
the fallback is the sustainable harvest, so a dead endpoint renders as textbook
cooperation. We now treat failed and unparseable responses as data loss rather
than observations, record the fallback rate for every run, and discard runs above
a small threshold. This was not precautionary: **three of six re-run
naming-game conditions proved silently corrupt**, and each had produced a
plausible, publishable-looking number. *Threats to Validity* quantifies the bias — a
10%-degraded run gave *p<sub>c</sub>* = 0.0795 against a clean 0.0985, a 19% error
in the direction that resembles a genuine finding. We have since applied the same
discipline to our own new experiments: every run reported in this revision records
its API-failure and parse-failure rates, and any arm above 5% loss is marked
unreliable and discarded rather than reported.

> *"You may wish to include a general methods overview in the main text of the
> paper, with more detailed methods in an Appendix."*

Adopted exactly as suggested.

> *"I also strongly encourage you to make replication code available to
> reviewers."*

All code, all result files, and the figure-generation scripts are now public at:

**https://github.com/kalyanar/governing-societies-of-ai-agents**

Every number in the manuscript is traceable to a JSON file in `code/results/`.
The repository README documents setup, the API credentials each provider requires,
and — for each of the eight experiments — the claim it was built to test. Result
files from runs that failed the data-quality audit are retained rather than
deleted, so that our exclusions are auditable.

---

## Part B — Additional experiments completed for this revision

Writing the Methods section to the standard you set required us to specify each
procedure precisely enough to re-run it. Having done so, we re-ran them, and then
extended them. This revision reports **ten new experiments**, and the paper is
materially stronger for it: the central result is measured at higher resolution, a
claim we had been prepared to withdraw turns out to hold under a fair test, the
cost result is re-established under considerably stricter conditions, and four
findings are new. Three previously reported numbers are superseded by better
measurement; we identify each explicitly at the end of this part.

**1. The capture threshold generalises across content (new).**
Our original claim that the threshold carries from opinion formation to cooperative
behaviour required a fair test, which the commons study turned out not to provide
(item~2). We therefore held the coordination mechanism fixed—identical update
rule, population, grid, estimator and counterbalancing, through the same code
path—and varied only what is being agreed: neutral codewords; two conservation
rules of equal merit; and a restrained versus a greedy harvest norm. At N=48 with
five seeds and both push directions (70 episodes per condition, 0% parse loss),
**the tipping point does not move**: *p_c* =0.128, 0.136, 0.131, spread
0.0087, every bootstrap interval overlapping. The asymmetric condition shows
residual directional bias h=0.000, so the identical threshold is not an artifact
of the two options being interchangeable in substance. The threshold is a property
of how agreement propagates, not of its subject matter, and it therefore transfers
to cooperation organised as a convention with rival stable states—the structure of
most norms, standards and protocols an agent society would negotiate.

**2. Why a commons behaves differently, and a law that recovers our
**25% (new).
The fishery updates as S  (2(S-h),K): harvesting at or below S/2 pins the
stock at capacity and anything above sends it down geometrically, with no
intermediate rest point. The system has one attractor and an absorbing death state.
A tipping point requires **bistability**—two states each stable under
perturbation, separated by a barrier—so a depletion process cannot exhibit one at
any adversary share; it exhibits a *rate*. Inverting the collapse-time law
gives the tolerance an observer reports after watching for H months,

> p_c(H) \;=\; 1-(S_c/S_0)^1/H,

which returns **25.9% at H=10**—reproducing our published figure to within
a percentage point. Our 25% was therefore correct for the horizon at which
it was measured; what was missing was the horizon itself. We now report the law
rather than the point estimate, together with the general observation that any
capture threshold quoted without its observation window overstates robustness by a
computable amount. We note that the human result usually cited alongside ours
(Centola et al.\ 2018, 25%) concerns social *conventions*, which are
bistable, and is thus structurally a naming game rather than a commons.

**3. The cost--quality result, re-established under stricter conditions
(new design).**
Our original comparison relied on a price table and an unconstrained judge. We have
replaced it with a head-to-head in which **both arms use the same judge model,
the same token budget and the same items**, so the comparison cannot be confounded by
model identity or by handicapping either side. A panel of three zero-cost models
reasons; the judge may then only return an index into their candidates. Result:
**0.938 at 0.454 against 0.912 at 1.148 for that same model reasoning
alone—2.53 cheaper**; a panel of 24--31B models gives 1.88. We
report this as **parity at a 2.5 discount rather than as an
improvement**, since the accuracy margin is not significant (McNemar exact,
p=0.625), and we say so in the text. The saving is a token accounting rather than
a sampling estimate, and because both arms use one model the ratio is invariant to
that model's price—which removes the dependence on a price table that a referee
would otherwise have to date-check.

**4. Two preconditions that make the architecture deployable (new).**
The substitution in item~3 is not universally available, and we can now say exactly
when it is. The panel's coverage must exceed the arbiter's solo accuracy: across
four panels spanning a factor of fifteen in member capability, this rule decides
every case, including the two where the architecture loses. And the panel must be
**competence-matched**—with members at 0.912/0.650/0.637 the selector simply
tracks the leader and realises  v = 0.00, so diversity of lineage without
comparable competence buys nothing. Relatedly, blind majority voting fell
*below* the panel's own best member in three of the four panels: aggregation by
counting is not a weak form of arbitration but an actively harmful one wherever
competence is uneven. Both conditions are measurable before any system is deployed.

**5. A decisive control for constrained arbitration (new).**
On items where **no** panel member is correct, a genuine selector must be wrong
every time; any correct answer there proves the mechanism is generating rather than
selecting. Pooling four independent arms gives 112 such items. **A constrained
selector was correct on 0 of 112; a free-form judge was correct on 26.** Under the
constrained instrument the competence-band prediction holds end to end, with a
competent selector realising  v = 0.33--0.91 of the available headroom across
four panels. This control also explains an artifact in our earlier verifier
numbers, discussed below.

**6. Verification is easier than generation, and the gap closes with
capability (new).**
Every verifier we tested selects better than it solves—eleven models from 2B to
frontier, ratios from 1.95 down to 1.03, declining monotonically with
capability. This is the mechanism that makes an arbitration architecture possible at
all, and it carries a caution we now state explicitly: because *every* model
selects better than it solves, a candidate verifier beating its own solo score is no
evidence of fitness. The relevant comparison is against the panel's best member, on
which every sub-frontier verifier we tried failed.

**7. The capability floor is a property of the role (new).**
Sweeping eleven verifiers from 2B to frontier against a fixed panel, every model up
to and including a current cheap frontier model *selected worse than the
panel's own best member*. A model that clears the coordination floor at 8B is
nowhere near the arbitration floor. A capability gate is therefore a (role, floor)
pair, and a governance regime that admits agents on a single threshold will
misallocate them across roles even when that threshold is measured rather than
assumed.

**8. The central result at higher resolution (strengthened).**
Our original sweep used N=16 on a grid whose only interior point was p=0.1, so
the entire transition fell between two grid points. Re-running all five lineages at
N=64, with grid points on exact multiples of 1/N and seven resolving points
inside the transition, **strengthens the paper's central claim**: the lineages
pool to *p_c* =0.0959  0.0019, with the analytic 0.0979 inside every
individual interval and a cross-lineage spread seven times tighter.

**Measurements updated by the above.**
Three figures from the original submission are replaced by the work described here.
*(i)* The five per-lineage thresholds were estimated on an N=16 grid whose
only interior point, p=0.1, is not realisable on a population of sixteen; the data
could not support the reported precision, and the data-quality audit described in
Part~A found that three of the six re-run conditions were additionally corrupted by
silent API failure. We re-ran all five lineages clean at N=64 with seven resolving
points inside the transition, which is the basis for item~8; the apparent spread of
0.084--0.118 was resolution, and at N=64 the lineages agree. *(ii)* Our
capability probe covered 2--4B and 70B-plus, and the 30B figure interpolated
across the range between them. We have now measured that range: across fourteen
models from 2B to 123B the floor sits between 3B and 8B, a 4B-active
mixture-of-experts model passes where dense 3B models fail, and a 123B model scores
below an 8B one. The structural claim—that fitness to govern is a threshold rather
than a smooth scale curve—is unchanged and now rests on fourteen models rather than
on an interpolation; what changes is its operational form, since an admission rule
stated as a parameter count errs in both directions. *(iii)* Our verifier was
free to emit any answer, including one no panel member had proposed, which makes
verifier quality unidentifiable: the same judge scored equivalently with no panel at
all. Item~5 supplies the constrained instrument and the control that separates
selection from generation, and the verifier figures are reported under it.

In each case the theory the paper advances is unchanged; the measurements behind it
are better.

## Part C — Presentation

Following your suggestion, the body carries a compact methods overview and the
detailed protocols sit in Appendix B. To keep the body readable at 20 pages we have
also moved to a supplementary appendix the material that supports but is not central
to the argument: the mechanical study of institutional decision rules, the full
institutional-ladder arms, the granularity account of commons survival, the
sustainability–equity trade-off, the token-budget caution, and five single-result
figures whose values are stated in the text. Each has a pointer from the body, and
no result has been removed.

We have also corrected a figure that had become inconsistent with the revised text:
the verifier figure was generated from the original free-form-judge run and depicted
the very artifact the section now disproves. All figures are now generated from the
released result files by a script in the repository, and a companion script checks
every number in the manuscript against those files and flags any figure older than
the data it depicts. The reported total API expenditure has been updated from ~\$16
to ~\$82, summed from the per-run cost fields in the released results.

---

## Summary of changes

| Change | Section | Nature |
|---|---|---|
| Methods section added; detailed protocols in appendix | *Methods*; *Appendix B* | As requested |
| Prompt templates, parameter table | *Appendix B* | As requested |
| Data-quality auditing described and applied to new runs | *Methods*; *Threats to Validity* | New control |
| Capture threshold re-run at *N* = 64 | *Capture Threshold Transfers* | Result strengthened |
| Capability gate re-measured; floor shown to be role-specific | *Capability Gate is a Floor* | Result corrected, then extended |
| Verifier constrained to selection; 0/112 control added | *Only a Constrained Verifier* | Confound removed; prediction confirmed |
| Commons horizon extended; *p<sub>c</sub>(H)* law derived | *Cooperation* | ~25% recovered as *p<sub>c</sub>*(H=10) |
| Bistability analysis; content-independence experiment | *Cooperation*; *Threshold Does Generalize* | Original claim scoped, not withdrawn |
| Cost-quality replaced by same-model head-to-head | *Cost vs. Quality* | Re-established at 2.53×, stated as parity |
| Coverage precondition and competence matching | *Coverage Precondition* | New result |
| Verification-easier-than-generation ladder | *Only a Constrained Verifier* | New result |
| Institutional ladder | *Cooperation* | New result |
| Ostrom (1990) added | Refs | New citation |
| Figures regenerated from result files; two were stale | — | Consistency fix |
| Peripheral material moved to supplement | *Appendix C* | Presentation |

A version with all changes in coloured text accompanies this submission, as
requested in the decision letter.

We recognise this is more change than a Methods request would normally produce. Two
of the three corrections we reported earlier turned out, on closer testing, to be
underspecification rather than error — the ~25% needed its horizon and the capability
gate needed its role — and we judged it better to establish that properly than to
leave either as a bare retraction. We are grateful for a review process that
improved the work rather than merely judging it, and we hope the revised manuscript
is now in a form your referees can assess.

Sincerely,

Gopal Kalyanaraman and Vijay K. Madisetti
