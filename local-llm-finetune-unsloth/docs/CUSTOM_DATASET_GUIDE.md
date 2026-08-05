# Building a Custom Dataset

Public datasets are for prototyping the pipeline. The part of a fine-tune that actually differentiates your model — and demonstrates judgment on your CV — is a **custom dataset built for a specific task or domain**. This guide covers how to build one from scratch.

## When a custom dataset is worth it

Build your own when you need the model to:
- follow a specific output format consistently (JSON schema, a report template, a specific tone/persona)
- perform a narrow task better than a general instruct model does out of the box (support ticket triage, domain Q&A, code review comments in your team's style)
- reflect domain knowledge or vocabulary that's underrepresented in public instruction data (legal, medical, a specific industry, a low-resource language)

If you just need general knowledge, fine-tuning is the wrong tool — reach for RAG instead (retrieval over a document store beats trying to bake facts into weights).

## Sourcing examples

1. **Mine real interactions.** Support logs, chat transcripts, past Q&A, code review comments — anywhere a human already produced the instruction→output pattern you want. This is the highest-quality source because it reflects real usage.
2. **Write them by hand.** For a portfolio project, 100-300 hand-written examples covering the core task variations is enough to prove the concept and is far more convincing than a scraped/unverified set.
3. **Bootstrap with a stronger LLM, then edit.** Ask Claude/GPT-4 to draft instruction/output pairs for your task, then **manually review and correct every one** — synthetic data you didn't check is a liability, not an asset (it silently teaches the model whatever mistakes the generator made).
4. **Augment public data with your own.** Take a filtered slice of Dolly/OpenHermes as a stability base (60-80% of the set) and mix in your hand-curated task-specific examples (20-40%) so the model doesn't overfit narrowly to your small custom slice.

## How many samples do you need?

There's no fixed number — it depends on task narrowness and base model size — but as a rule of thumb with LoRA/QLoRA on a 3B-8B model:

| Goal | Approx. sample count | Notes |
|---|---|---|
| Prove the pipeline works / smoke test | 50-200 | Overfits fast, fine for a demo, not for real quality claims |
| Narrow, well-defined task (fixed format, small vocabulary) | 300-1,000 | Sweet spot for most portfolio projects — enough signal, still hand-auditable |
| Broader task or style transfer | 1,000-5,000 | Diminishing returns beyond this without diversity, not just volume |
| General-purpose instruction-following | 10,000+ | This is what Alpaca/Dolly-scale sets are for — not usually worth hand-building |

Quality and diversity beat raw count almost every time: 300 varied, clean examples covering edge cases outperform 3,000 near-duplicates of the same phrasing. LoRA/QLoRA's low parameter count also means it's much easier to overfit a tiny, repetitive dataset than full fine-tuning is — watch validation loss (see `evaluation/evaluate.py`), not just training loss.

## Best practices

- **One clear task per example.** Don't blend "summarize this" and "translate this" into one instruction unless multi-task behavior is the explicit goal.
- **Match instruction phrasing diversity to real usage.** If users will ask the same thing five different ways, include five phrasings — not five copies of the same output.
- **Keep outputs in the exact style/format you want at inference time.** The model mimics format precisely (including verbosity, markdown usage, sign-offs) — sloppy example outputs become the model's default behavior.
- **Include some negative/edge cases**, e.g. instructions with insufficient input, ambiguous requests, or "I don't know" cases if you want the model to hedge rather than hallucinate.
- **Avoid contradictions across examples.** If two examples give different outputs for near-identical instructions, the model averages toward a confused middle behavior.
- **Don't include eval prompts in training data.** Hold out a validation slice untouched by any editing pass you did on the training set.

## Data cleaning checklist (`scripts/clean_dataset.py`)

Run every dataset — public or custom — through these passes before training:

1. **Deduplicate.** Exact-match dedup on `(instruction, input)` pairs, then near-duplicate dedup (e.g. via a simple normalized-text hash or embedding cosine similarity above ~0.95) to catch paraphrased repeats.
2. **Length filtering.** Drop examples where `output` is empty, a single word, or truncated mid-sentence; drop egregiously long outliers that will dominate token budget (`scripts/clean_dataset.py --max-output-tokens 512` as a starting cap).
3. **Language/encoding filtering.** Strip control characters, fix mojibake/encoding artifacts, filter to your target language(s) if the source is multilingual and you don't want that.
4. **PII scrubbing.** If mining real logs, redact names, emails, phone numbers, IDs — a regex pass at minimum, an NER-based scrubber if the volume justifies it.
5. **Format validation.** Every row must have non-empty `instruction` and `output` keys and valid JSON — malformed rows should hard-fail the loader, not get silently skipped.
6. **Manual spot-check.** Read a random 5-10% sample end-to-end before training. This catches systemic issues (a bad conversion script, a mislabeled field) that automated filters won't.

## Train / validation split

- Use `scripts/split_dataset.py --val-ratio 0.1` (90/10) for datasets under ~2,000 examples; drop to 0.05 (95/5) for larger sets so you keep enough training signal.
- **Split before any augmentation or oversampling**, never after — otherwise near-duplicate examples leak between train and validation and your eval loss lies to you.
- Stratify by task type/source if your set blends multiple sources (e.g. hand-written + public-data slice), so validation isn't accidentally 100% one source.
- Keep a small **held-out qualitative eval set** (10-30 prompts, see `evaluation/eval_prompts.json`) that's never touched by training or the automated split — this is what you use for side-by-side base-vs-fine-tuned comparison in the Streamlit app, and it should look like real usage, not like the training distribution.

```bash
python scripts/clean_dataset.py --input data/raw/custom_raw.jsonl --output data/raw/custom_clean.jsonl
python scripts/split_dataset.py --input data/raw/custom_clean.jsonl \
  --train-output data/processed/train.jsonl \
  --val-output data/processed/val.jsonl \
  --val-ratio 0.1 --seed 3407
```
