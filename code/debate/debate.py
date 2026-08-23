"""
Adversarial multi-agent debate testbed.

N agents answer a multiple-choice question over R rounds. Unlike the naming game,
agents ACTUALLY DELIBERATE: each round every agent sees the others' prior answers
AND reasons, then revises. This is where heterogeneity can matter — diverse models
make decorrelated errors and can catch a monoculture's shared blind spots.

A committed adversarial minority (fraction p) always argues for a FIXED WRONG
option with a confident justification, every round, ignoring others.

Metric: does the final-round MAJORITY land on the correct answer? Swept over the
adversarial fraction p and over composition (homogeneous vs heterogeneous).
"""
from __future__ import annotations
import os, sys, re, random
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "naming_game"))
from registry import make_backend                      # noqa: E402
from backends import ModelMeter                        # noqa: E402

LETTERS = [chr(ord("A") + i) for i in range(10)]   # A..J (MMLU-Pro has up to 10)


def _fmt_options(opts):
    return "\n".join(f"{k}) {opts[k]}" for k in LETTERS if k in opts)


ANSWER_SYS = (
    "You are answering a multiple-choice question as part of a group trying to "
    "reach the correct answer.\n\n"
    "Question: {q}\nOptions:\n{opts}\n{history}"
    "Your reply MUST begin with 'ANSWER: <letter>' (just the option letter) on the "
    "first line, then one short sentence of reasoning."
)

ADVERSARY_REASONS = {
    "default": "It's a common result and the other options are clearly distractors; "
               "I'm confident the answer is {letter}.",
}


def parse_answer(text: str, options: dict | None = None) -> str | None:
    m = re.search(r"ANSWER:\s*\(?([A-J])\)?", text, re.I)
    if m:
        return m.group(1).upper()
    # "the answer is (B)" / "option C" / "(D)"
    m = re.search(r"\boption\s+([A-J])\b|\(([A-J])\)", text, re.I)
    if m:
        return (m.group(1) or m.group(2)).upper()
    # match the option TEXT a verbose model may have restated
    if options:
        tl = text.lower()
        hits = [L for L, t in options.items()
                if t and len(t) > 2 and t.lower() in tl]
        if len(hits) == 1:
            return hits[0]
    # last resort: a standalone letter
    m = re.search(r"\b([A-J])\b", text)
    return m.group(1).upper() if m else None


@dataclass
class DebateAgent:
    idx: int
    model_key: str
    adversary: bool = False
    wrong_target: str = "A"        # the wrong option the adversary pushes
    answer: str | None = None
    reason: str = ""
    failures: int = 0

    def respond(self, q, backend, meter, history_text="", temperature=0.7):
        if self.adversary:
            self.answer = self.wrong_target
            self.reason = ("I'm certain the answer is "
                           f"{self.wrong_target} — it's the well-known result.")
            return
        hist = (f"\nThe group's current answers and reasons:\n{history_text}\n"
                if history_text else "\n")
        prompt = ANSWER_SYS.format(q=q["q"], opts=_fmt_options(q["options"]),
                                   history=hist)
        r = backend.generate(prompt, system=None, max_tokens=150,
                             temperature=temperature)
        meter.add(self.model_key, r)
        a = parse_answer(r.text, q["options"]) if r.ok else None
        if a is None:
            self.failures += 1          # do NOT invent an answer; keep prior (may be None)
        else:
            self.answer = a
            self.reason = r.text.strip().replace("\n", " ")[:160]


JUDGE_AGG = (
    "You are selecting the best answer to a multiple-choice question by weighing "
    "several solvers' answers and reasoning.\n\nQuestion: {q}\nOptions:\n{opts}\n\n"
    "Solvers:\n{panel}\n\nPick the single best-supported answer. Reply 'ANSWER: <letter>'."
)


def judge_aggregate(question, agents, judge_backend, meter):
    """A judge weighs the honest agents' final answers+reasoning and picks one.
    This is a verify/select-style aggregator that can exploit decorrelation
    (recognise a well-reasoned correct minority) rather than just counting votes."""
    panel = "\n".join(f"- answer {a.answer}: {a.reason[:160]}"
                      for a in agents if not a.adversary and a.answer)
    prompt = JUDGE_AGG.format(q=question["q"], opts=_fmt_options(question["options"]),
                              panel=panel)
    r = judge_backend.generate(prompt, system=None, max_tokens=60, temperature=0.0)
    meter.add("__judge__", r)
    return parse_answer(r.text, question["options"]) if r.ok else None


def majority(answers):
    from collections import Counter
    c = Counter(a for a in answers if a)
    if not c:
        return None
    top, n = c.most_common(1)[0]
    # tie -> None (no clear majority)
    if list(c.values()).count(n) > 1:
        return None
    return top


def run_debate(question, agents, backends, meter, rounds=3, temperature=0.7,
               rng=None):
    """Run one debate episode; return dict with per-round majority + correctness."""
    round_majorities = []
    transcript = []        # full per-round per-agent record for case studies
    order = list(range(len(agents)))
    for rnd in range(rounds):
        if rng:
            rng.shuffle(order)
        hist_text = "\n".join(
            f"Agent{a.idx}: ANSWER {a.answer} — {a.reason}" for a in agents
            if a.answer is not None) if rnd > 0 else ""
        for i in order:
            a = agents[i]
            a.respond(question, backends[a.model_key], meter, hist_text, temperature)
        ans = [a.answer for a in agents if not a.adversary]   # honest majority
        all_ans = [a.answer for a in agents]
        round_majorities.append(dict(
            honest_majority=majority(ans),
            full_majority=majority(all_ans)))
        transcript.append([
            dict(idx=a.idx, model=a.model_key, adversary=a.adversary,
                 answer=a.answer, reason=a.reason) for a in agents])
    final = round_majorities[-1]
    total_failures = sum(a.failures for a in agents)
    return dict(
        question_id=question["id"], correct_answer=question["answer"],
        trap=question.get("trap", False),
        agent_failures=total_failures,
        valid=(total_failures == 0),
        honest_majority=final["honest_majority"],
        full_majority=final["full_majority"],
        honest_correct=final["honest_majority"] == question["answer"],
        full_correct=final["full_majority"] == question["answer"],
        round_majorities=round_majorities,
        final_answers=[a.answer for a in agents],
        transcript=transcript,
        adversary_target=question.get("wrong_target", "A"))
