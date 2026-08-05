"""Shared model-loading helpers for base and fine-tuned (base + LoRA adapter) inference.

Used by inference/generate.py, evaluation/evaluate.py, and app/streamlit_app.py so all three
share identical loading/generation behavior.
"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_model_config() -> dict:
    with (PROJECT_ROOT / "configs" / "model_config.yaml").open("r") as f:
        return yaml.safe_load(f)


def load_base_model(model_key: str | None = None, load_in_4bit: bool = True):
    """Load the base model (no adapter) for inference and comparison."""
    from unsloth import FastLanguageModel

    model_config = load_model_config()
    model_key = model_key or model_config["active"]
    model_cfg = model_config["models"][model_key]

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_cfg["repo_id"],
        max_seq_length=model_cfg["max_seq_length"],
        dtype=None,
        load_in_4bit=load_in_4bit,
    )
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def load_finetuned_model(adapter_name: str, load_in_4bit: bool = True):
    """Load the base model with a trained LoRA/QLoRA adapter applied on top."""
    from unsloth import FastLanguageModel

    adapter_dir = PROJECT_ROOT / "models" / "adapters" / adapter_name

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(adapter_dir),
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=load_in_4bit,
    )
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def list_available_adapters() -> list[str]:
    adapters_dir = PROJECT_ROOT / "models" / "adapters"
    if not adapters_dir.exists():
        return []
    return sorted(p.name for p in adapters_dir.iterdir() if p.is_dir() and (p / "adapter_config.json").exists())
