"""Run inference with the base model or a fine-tuned adapter from the command line.

Usage:
    python inference/generate.py --instruction "Write a haiku about autumn."
    python inference/generate.py --adapter llama3.2-qlora --instruction "Explain LoRA." --input ""
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.dataset_utils import ALPACA_PROMPT, ALPACA_PROMPT_NO_INPUT


def build_prompt(instruction: str, input_: str) -> str:
    if input_.strip():
        return ALPACA_PROMPT.format(instruction, input_, "")
    return ALPACA_PROMPT_NO_INPUT.format(instruction, "")


def generate(model, tokenizer, instruction: str, input_: str = "", max_new_tokens: int = 256,
             temperature: float = 0.7, top_p: float = 0.9) -> tuple[str, float]:
    prompt = build_prompt(instruction, input_)
    inputs = tokenizer([prompt], return_tensors="pt").to(model.device)

    start = time.time()
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        do_sample=temperature > 0,
        use_cache=True,
        pad_token_id=tokenizer.eos_token_id,
    )
    latency = time.time() - start

    generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return generated.strip(), latency


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--input", default="")
    parser.add_argument("--adapter", default=None, help="adapter name under models/adapters/; omit to use the base model")
    parser.add_argument("--model", default=None, help="model key from configs/model_config.yaml, only used without --adapter")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--load-in-4bit", action="store_true", default=True)
    args = parser.parse_args()

    from inference.model_loader import load_base_model, load_finetuned_model

    if args.adapter:
        model, tokenizer = load_finetuned_model(args.adapter, load_in_4bit=args.load_in_4bit)
    else:
        model, tokenizer = load_base_model(args.model, load_in_4bit=args.load_in_4bit)

    response, latency = generate(
        model, tokenizer, args.instruction, args.input,
        max_new_tokens=args.max_new_tokens, temperature=args.temperature, top_p=args.top_p,
    )

    print(f"\n--- Response ({latency:.2f}s) ---\n{response}\n")


if __name__ == "__main__":
    main()
