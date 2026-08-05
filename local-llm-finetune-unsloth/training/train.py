"""Fine-tune a local LLM with Unsloth using LoRA or QLoRA.

Requires an NVIDIA GPU (Unsloth's fused Triton kernels are CUDA-only).

Usage:
    python training/train.py --mode qlora --model llama3.2
    python training/train.py --mode lora --model qwen2.5 --train-file data/processed/train.jsonl
"""

import argparse
import json
import time
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)


def build_model_and_tokenizer(model_cfg: dict, run_cfg: dict):
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_cfg["repo_id"],
        max_seq_length=model_cfg["max_seq_length"],
        dtype=None,  # auto-detect: bf16 on Ampere+, fp16 otherwise
        load_in_4bit=run_cfg["load_in_4bit"],
    )

    lora_cfg = run_cfg["lora"]
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["lora_alpha"],
        lora_dropout=lora_cfg["lora_dropout"],
        target_modules=lora_cfg["target_modules"],
        bias=lora_cfg["bias"],
        use_gradient_checkpointing=lora_cfg["use_gradient_checkpointing"],
        random_state=lora_cfg["random_state"],
    )
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["lora", "qlora"], required=True)
    parser.add_argument("--model", choices=["llama3.2", "qwen2.5"], default=None, help="overrides `active` in configs/model_config.yaml")
    parser.add_argument("--train-file", default="data/processed/train.jsonl")
    parser.add_argument("--val-file", default="data/processed/val.jsonl")
    parser.add_argument("--output-dir", default=None, help="overrides training.output_dir from the run config")
    parser.add_argument("--adapter-name", default=None, help="subdirectory under models/adapters/ to save the trained adapter")
    args = parser.parse_args()

    model_config = load_yaml(PROJECT_ROOT / "configs" / "model_config.yaml")
    run_config = load_yaml(PROJECT_ROOT / "configs" / f"{args.mode}_config.yaml")

    active_model = args.model or model_config["active"]
    model_cfg = model_config["models"][active_model]

    if args.output_dir:
        run_config["training"]["output_dir"] = args.output_dir

    print(f"Loading base model: {model_cfg['repo_id']} (mode={args.mode})")
    model, tokenizer = build_model_and_tokenizer(model_cfg, run_config)

    from training.dataset_utils import load_alpaca_dataset

    train_dataset = load_alpaca_dataset(str(PROJECT_ROOT / args.train_file), tokenizer)
    eval_dataset = load_alpaca_dataset(str(PROJECT_ROOT / args.val_file), tokenizer)
    print(f"Train examples: {len(train_dataset)} | Val examples: {len(eval_dataset)}")

    from trl import SFTConfig, SFTTrainer

    t = run_config["training"]
    sft_config = SFTConfig(
        output_dir=str(PROJECT_ROOT / t["output_dir"]),
        num_train_epochs=t["num_train_epochs"],
        per_device_train_batch_size=t["per_device_train_batch_size"],
        gradient_accumulation_steps=t["gradient_accumulation_steps"],
        learning_rate=t["learning_rate"],
        lr_scheduler_type=t["lr_scheduler_type"],
        warmup_ratio=t["warmup_ratio"],
        weight_decay=t["weight_decay"],
        optim=t["optim"],
        max_grad_norm=t["max_grad_norm"],
        logging_steps=t["logging_steps"],
        save_strategy=t["save_strategy"],
        eval_strategy=t["eval_strategy"],
        seed=t["seed"],
        packing=t["packing"],
        bf16=t["bf16"],
        fp16=not t["bf16"],
        max_seq_length=model_cfg["max_seq_length"],
        dataset_text_field="text",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=sft_config,
    )

    start = time.time()
    train_result = trainer.train()
    elapsed = time.time() - start

    adapter_name = args.adapter_name or f"{active_model}-{args.mode}"
    adapter_dir = PROJECT_ROOT / "models" / "adapters" / adapter_name
    adapter_dir.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    stats = {
        "adapter_name": adapter_name,
        "base_model": model_cfg["repo_id"],
        "mode": args.mode,
        "train_examples": len(train_dataset),
        "val_examples": len(eval_dataset),
        "epochs": t["num_train_epochs"],
        "learning_rate": t["learning_rate"],
        "lora_r": run_config["lora"]["r"],
        "lora_alpha": run_config["lora"]["lora_alpha"],
        "training_time_seconds": elapsed,
        "final_train_loss": train_result.metrics.get("train_loss"),
        "log_history": trainer.state.log_history,
    }
    with (adapter_dir / "training_stats.json").open("w") as f:
        json.dump(stats, f, indent=2)

    print(f"Adapter saved to {adapter_dir}")
    print(f"Training took {elapsed / 60:.1f} minutes, final train loss: {stats['final_train_loss']}")


if __name__ == "__main__":
    main()
