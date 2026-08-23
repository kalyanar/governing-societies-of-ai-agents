"""
Load real hard MC benchmarks and normalize to the debate format:
  dict(id, q, options{A..}, answer<letter>, wrong_target<letter>, trap, source)

Datasets
- TruthfulQA (MC1): questions engineered to elicit COMMON MISCONCEPTIONS — models
  give the same systematic wrong answer, so a monoculture fails together. The
  adversary's wrong_target is the misconception (most-tempting distractor).
- MMLU-Pro: 10-option professional-domain questions; much harder than MMLU.
- GPQA-Diamond (optional, gated on HF): PhD-level science, hardest tier.

Builds a fixed, cached question set (data/questions_<tag>.json) for reproducibility.
"""
from __future__ import annotations
import os, json, random

# make HF_TOKEN available for dataset downloads
_envp = os.path.join(os.path.dirname(__file__), "..", "naming_game", ".env")
if os.path.exists(_envp) and "HF_TOKEN" not in os.environ:
    for line in open(_envp):
        if line.startswith("HF_TOKEN="):
            os.environ["HF_TOKEN"] = line.split("=", 1)[1].strip()

LETTERS = [chr(ord("A") + i) for i in range(10)]


def load_truthfulqa_mc1(n=60, seed=0, max_opts=5):
    from datasets import load_dataset
    d = load_dataset("truthfulqa/truthful_qa", "multiple_choice", split="validation")
    rng = random.Random(seed)
    idxs = rng.sample(range(len(d)), min(n, len(d)))
    out = []
    for i in idxs:
        ex = d[i]
        choices = ex["mc1_targets"]["choices"]
        labels = ex["mc1_targets"]["labels"]
        correct = [c for c, l in zip(choices, labels) if l == 1]
        wrong = [c for c, l in zip(choices, labels) if l == 0]
        if not correct or not wrong:
            continue
        rng.shuffle(wrong)
        # misconception distractor = the first listed wrong answer in mc1 (most plausible)
        misconception = wrong[0]
        opt_texts = [correct[0]] + wrong[:max_opts - 1]
        rng.shuffle(opt_texts)
        options = {LETTERS[k]: t for k, t in enumerate(opt_texts)}
        ans = next(L for L, t in options.items() if t == correct[0])
        wt = next((L for L, t in options.items() if t == misconception), None)
        if wt is None or wt == ans:
            wt = next(L for L in options if L != ans)
        out.append(dict(id=f"tqa_{i}", q=ex["question"], options=options,
                        answer=ans, wrong_target=wt, trap=True, source="truthfulqa"))
    return out


def load_mmlu_pro(n=60, seed=0, categories=None):
    from datasets import load_dataset
    d = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
    if categories:
        d = d.filter(lambda x: x["category"] in categories)
    rng = random.Random(seed + 1)
    idxs = rng.sample(range(len(d)), min(n, len(d)))
    out = []
    for i in idxs:
        ex = d[i]
        opts = ex["options"]
        options = {LETTERS[k]: t for k, t in enumerate(opts)}
        ans = ex["answer"]
        wrong = [L for L in options if L != ans]
        out.append(dict(id=f"mmlupro_{ex['question_id']}", q=ex["question"],
                        options=options, answer=ans,
                        wrong_target=rng.choice(wrong), trap=False,
                        source="mmlupro", category=ex["category"]))
    return out


def build_set(tag, n_tqa=50, n_mmlu=50, seed=0, mmlu_categories=None):
    qs = []
    if n_tqa:
        qs += load_truthfulqa_mc1(n_tqa, seed)
    if n_mmlu:
        qs += load_mmlu_pro(n_mmlu, seed, mmlu_categories)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"questions_{tag}.json")
    with open(path, "w") as f:
        json.dump(qs, f, indent=2)
    print(f"wrote {path}  ({len(qs)} questions: "
          f"{sum(1 for q in qs if q['source']=='truthfulqa')} TruthfulQA + "
          f"{sum(1 for q in qs if q['source']=='mmlupro')} MMLU-Pro)")
    return path


def load_json_set(path):
    return json.load(open(path))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="hard")
    ap.add_argument("--n_tqa", type=int, default=50)
    ap.add_argument("--n_mmlu", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mmlu_categories", nargs="*", default=None)
    a = ap.parse_args()
    build_set(a.tag, a.n_tqa, a.n_mmlu, a.seed, a.mmlu_categories)
