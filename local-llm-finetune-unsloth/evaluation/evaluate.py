"""Compare a fine-tuned adapter against its base model: perplexity on the validation set,
plus qualitative side-by-side generations and latency on a fixed prompt set.

Usage:
    python evaluation/evaluate.py --adapter llama3.2-qlora
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from inference.generate import generate
from inference.model_loader import load_base_model, load_finetuned_model
from training.dataset_utils import ALPACA_PROMPT, ALPACA_PROMPT_NO_INPUT


@torch.no_grad()
def compute_perplexity(model, tokenizer, examples: list[dict]) -> float:
    total_loss, total_tokens = 0.0, 0
    for ex in examples:
        instruction, input_, output = ex["instruction"], ex.get("input", ""), ex["output"]
        template = ALPACA_PROMPT if input_.strip() else ALPACA_PROMPT_NO_INPUT
        args = (instruction, input_, output) if input_.strip() else (instruction, output)
        text = template.format(*args) + tokenizer.eos_token

        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        outputs = model(**inputs, labels=inputs["input_ids"])
        n_tokens = inputs["input_ids"].shape[1]
        total_loss += outputs.loss.item() * n_tokens
        total_tokens += n_tokens

    avg_loss = total_loss / total_tokens
    return float(torch.exp(torch.tensor(avg_loss)))


def run_qualitative_comparison(base_model, base_tok, ft_model, ft_tok, prompts: list[dict]) -> list[dict]:
    results = []
    for p in prompts:
        base_response, base_latency = generate(base_model, base_tok, p["instruction"], p.get("input", ""))
        ft_response, ft_latency = generate(ft_model, ft_tok, p["instruction"], p.get("input", ""))
        results.append({
            "instruction": p["instruction"],
            "input": p.get("input", ""),
            "base_response": base_response,
            "base_latency_seconds": base_latency,
            "finetuned_response": ft_response,
            "finetuned_latency_seconds": ft_latency,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--val-file", default="data/processed/val.jsonl")
    parser.add_argument("--eval-prompts", default="evaluation/eval_prompts.json")
    parser.add_argument("--load-in-4bit", action="store_true", default=True)
    args = parser.parse_args()

    with (PROJECT_ROOT / args.val_file).open("r") as f:
        val_examples = [json.loads(line) for line in f if line.strip()]
    with (PROJECT_ROOT / args.eval_prompts).open("r") as f:
        eval_prompts = json.load(f)

    print("Loading base model...")
    base_model, base_tok = load_base_model(load_in_4bit=args.load_in_4bit)

    print(f"Loading fine-tuned model (adapter={args.adapter})...")
    ft_model, ft_tok = load_finetuned_model(args.adapter, load_in_4bit=args.load_in_4bit)

    print("Computing perplexity on validation set...")
    base_ppl = compute_perplexity(base_model, base_tok, val_examples)
    ft_ppl = compute_perplexity(ft_model, ft_tok, val_examples)

    print("Running qualitative comparison...")
    comparisons = run_qualitative_comparison(base_model, base_tok, ft_model, ft_tok, eval_prompts)

    avg_base_latency = sum(c["base_latency_seconds"] for c in comparisons) / len(comparisons)
    avg_ft_latency = sum(c["finetuned_latency_seconds"] for c in comparisons) / len(comparisons)

    report = {
        "adapter": args.adapter,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "val_examples": len(val_examples),
        "base_perplexity": base_ppl,
        "finetuned_perplexity": ft_ppl,
        "avg_base_latency_seconds": avg_base_latency,
        "avg_finetuned_latency_seconds": avg_ft_latency,
        "comparisons": comparisons,
    }

    results_dir = PROJECT_ROOT / "evaluation" / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"comparison_{args.adapter}.json"
    with out_path.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== Results: base vs {args.adapter} ===")
    print(f"Perplexity (lower is better): base={base_ppl:.2f}  finetuned={ft_ppl:.2f}")
    print(f"Avg latency: base={avg_base_latency:.2f}s  finetuned={avg_ft_latency:.2f}s")
    print(f"Full report saved to {out_path}")


if __name__ == "__main__":
    main()
