from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_LORA_KEYS = {"r", "lora_alpha", "lora_dropout", "target_modules", "bias", "use_gradient_checkpointing", "random_state"}
REQUIRED_TRAINING_KEYS = {
    "output_dir", "num_train_epochs", "per_device_train_batch_size", "gradient_accumulation_steps",
    "learning_rate", "lr_scheduler_type", "warmup_ratio", "optim", "seed",
}


def _load(name):
    with (PROJECT_ROOT / "configs" / name).open() as f:
        return yaml.safe_load(f)


def test_model_config_active_model_is_defined():
    cfg = _load("model_config.yaml")
    assert cfg["active"] in cfg["models"]


def test_model_config_entries_have_required_fields():
    cfg = _load("model_config.yaml")
    for name, model in cfg["models"].items():
        assert "repo_id" in model, f"{name} missing repo_id"
        assert "max_seq_length" in model, f"{name} missing max_seq_length"


def test_lora_config_mode_and_required_keys():
    cfg = _load("lora_config.yaml")
    assert cfg["mode"] == "lora"
    assert cfg["load_in_4bit"] is False
    assert REQUIRED_LORA_KEYS <= cfg["lora"].keys()
    assert REQUIRED_TRAINING_KEYS <= cfg["training"].keys()


def test_qlora_config_mode_and_required_keys():
    cfg = _load("qlora_config.yaml")
    assert cfg["mode"] == "qlora"
    assert cfg["load_in_4bit"] is True
    assert REQUIRED_LORA_KEYS <= cfg["lora"].keys()
    assert REQUIRED_TRAINING_KEYS <= cfg["training"].keys()
