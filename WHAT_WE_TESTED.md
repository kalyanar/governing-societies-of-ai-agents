# What We Tested — in Plain English

We ran four very different "games" for AI agents. Each one asks the same underlying
question — *does it matter whether the agents are the same model or different models?*
— but in a different setting. Here is each one in plain language: what it is, what we
expected, and what we actually got.

---

## 1. The Naming Game — *do opinions spread the same way they do in people?*

**What it is.** Imagine a room of people who each prefer one of two names for something
(say *apple* vs *mango*). They mingle, and whenever two meet, one tries to get the other
to switch. Eventually the whole room usually agrees on one name. Now drop in a few
**stubborn** people who will *never* change and always push *apple*. How many stubborn
people does it take to flip the entire room to *apple*?

**What we expected.** A famous 2011 result says the magic number is about **10%**: below
that, the stubborn minority gets ignored; above it, they flip everyone. We wanted to see
if AI agents behave like the people in that theory.

**What we got.** They do — almost exactly. Capable AI models flip at **~10%**, across
five different AI companies' models. But two caveats: small/weak models can't even play
(they just say "both" and never commit), and because this game is pure opinion-passing
with *no real reasoning*, it doesn't matter at all whether the agents are identical or
diverse. It confirmed the theory but, by design, says nothing about diversity.

![Naming game tipping point](/fig/fig_pc.png)

---

## 2. Adversarial Debate — *can a group reason its way to the right answer despite saboteurs?*

**What it is.** A group of AI agents gets a hard quiz question that has a real correct
answer, and they debate it over a few rounds. We secretly plant **saboteurs** who
confidently argue for a *wrong* answer. Does the group still land on the truth?

**What we expected.** That a **diverse** group (different AI models) would resist the
saboteurs and catch each other's mistakes better than a group of identical clones —
because different models should have different blind spots.

**What we got.** A surprise. Different AI models make the **same** mistakes far more
often than expected — they all trained on similar internet text. So a diverse group
barely did better, and when we mixed a strong model with weaker ones, the weak ones
**dragged the group down**. A group of clones of the *best* single model often won
outright. Diversity helped much less than the hype suggests — this is the
"illusion of cognitive diversity."

![Error correlation among models](/fig/fig_rho.png)

---

## 3. Value Deliberation — *does diversity make for a better discussion when there's no right answer?*

**What it is.** A group discusses a **moral dilemma** (the trolley problem, "should a
starving parent steal food?"). Each agent rates its agreement 1–7 over several rounds,
seeing everyone's reasoning. There's no "correct" answer — what matters is the *quality*
of the deliberation. We also add a stubborn extremist pushing one side.

**What we expected.** That a diverse group would have a richer, more balanced discussion
than identical clones, and would resist the extremist better.

**What we got.** This is where diversity clearly **won**. Six copies of the same model
gave nearly *word-for-word identical* opinions and instantly "agreed" — textbook
groupthink. A diverse group genuinely disagreed, raised more distinct considerations,
and was harder for the extremist to push around. When there's no single right answer,
**diversity of perspective genuinely matters.**

![Deliberation: heterogeneity resists groupthink](/fig/fig_delib.png)

---

## 4. GovSim (Sharing a Resource) — *can agents cooperate, and what breaks it?*

**What it is.** Five AI agents share a **fishing lake**. Each month they choose how much
to catch. Overfish and the lake empties forever; restrain themselves and it refills so
everyone keeps fishing. We add **cheaters** who always overfish. How many cheaters before
the whole lake collapses?

**What we expected.** A cooperation tipping point (like the ~10% for opinions), and that
stronger vs weaker models would cooperate differently.

**What we got.** Only the strongest models could cooperate at all — weaker models
overfished and crashed the lake even with **zero** cheaters. For the strong model, the
lake survived up to **20%** cheaters but collapsed at **30%** — a tipping point around
**25%** (close to a known human result). So the same "a committed minority flips the
system" idea appears in cooperation too, just at a higher threshold than opinions.

![GovSim cooperation collapse](/fig/fig_govsim.png)

---

## The one-paragraph takeaway

Mixing different AI models is **not** automatically better. On tasks with a right answer,
the models are surprisingly alike (they fail together), so diversity barely helps and can
even hurt by diluting your best model — *unless you can verify the answer*, in which case
a cheap diverse panel can match an expensive model at lower cost. Where diversity truly
shines is **open-ended discussion**, where identical models fall into groupthink and
diverse ones keep a real range of views. And across every setting, a small committed
minority can tip the whole system — at ~10% for opinions and ~25% for cooperation.

![Cheap panel matches Opus on verifiable tasks](/fig/fig_costquality.png)
