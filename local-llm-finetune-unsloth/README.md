# 🦥 Local LLM Fine-Tuning Studio

Fine-tune **Llama 3.2** or **Qwen 2.5** locally with **LoRA/QLoRA** using **Unsloth**, then compare the fine-tuned model against the base model in a live Streamlit app — latency, quality, and training diagnostics included.

Built as an end-to-end demonstration of parameter-efficient fine-tuning (PEFT): dataset preparation, quantized training, adapter management, evaluation, and a usable inference UI — the full lifecycle, not just a training script.

> **GPU requirement:** Unsloth's fused Triton kernels are CUDA-only. Training and full inference need an NVIDIA GPU (a single 8–16GB consumer card is enough for 3B–7B models with QLoRA). The Streamlit app still runs without a GPU in a clearly labeled **Demo Mode** so the UI/UX can be reviewed anywhere. No local GPU? Run the full pipeline on a free Colab T4 with [`notebooks/colab_finetune.ipynb`](notebooks/colab_finetune.ipynb).

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Project structure](#project-structure)
- [Dataset](#dataset)
- [Fine-tuning process](#fine-tuning-process)
- [Evaluation](#evaluation)
- [Interface](#interface)
- [Installation](#installation)
- [Testing](#testing)
- [Usage](#usage)
- [Results](#results)
- [Screenshots](#screenshots)

---

## Overview

This project fine-tunes a small local LLM (Llama 3.2 3B or Qwen 2.5 7B, both loaded as 4-bit Unsloth checkpoints) on instruction-following data, using **LoRA** or **QLoRA** adapters trained via **Unsloth**, **Hugging Face TRL/PEFT**, and **bitsandbytes** quantization. The trained adapter is saved separately from the base model, reloaded for inference, and benchmarked against the untouched base model on both perplexity and qualitative output.

Everything is config-driven (`configs/*.yaml`) — swapping the base model, switching LoRA↔QLoRA, or changing hyperparameters requires no code edits.

## Architecture

```
                 ┌─────────────────────┐
                 │   Public / Custom    │
                 │      Dataset         │
                 └──────────┬───────────┘
                             │  scripts/convert_to_alpaca.py
                             ▼
                 ┌─────────────────────┐
                 │  Alpaca-format JSONL │  {instruction, input, output}
                 └──────────┬───────────┘
                 scripts/clean_dataset.py
                 scripts/split_dataset.py
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
        data/processed/train.jsonl   val.jsonl
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │   training/train.py (Unsloth + TRL)      │
        │   base model (4-bit) + LoRA/QLoRA config │
        └──────────────────┬───────────────────────┘
                             │  model.save_pretrained()
                             ▼
        models/adapters/<name>/  (adapter weights + training_stats.json)
                             │
             ┌───────────────┴───────────────┐
             ▼                                 ▼
   inference/generate.py (CLI)     evaluation/evaluate.py
             │                        (perplexity + base-vs-ft compare)
             └───────────────┬───────────────┘
                             ▼
                 app/streamlit_app.py
           (chat · compare · upload · training stats)
```

## Technologies

| Layer | Tool |
|---|---|
| Fine-tuning engine | [Unsloth](https://github.com/unslothai/unsloth) — fused Triton kernels, ~2x faster training, ~60% less VRAM |
| PEFT method | LoRA / QLoRA via Hugging Face [PEFT](https://github.com/huggingface/peft) |
| Quantization | [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) — 4-bit NF4 base weights for QLoRA |
| Training loop | Hugging Face [TRL](https://github.com/huggingface/trl) (`SFTTrainer`) + [Transformers](https://github.com/huggingface/transformers) |
| Data | Hugging Face [Datasets](https://github.com/huggingface/datasets) |
| Base models | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`, `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` |
| Interface | [Streamlit](https://streamlit.io/) + Plotly |
| Config | YAML (`configs/`) |

## Project structure

```
local-llm-finetune-unsloth/
├── app/
│   └── streamlit_app.py       # Chat, base-vs-ft comparison, dataset upload, training stats
├── configs/
│   ├── model_config.yaml      # Base model selection (llama3.2 / qwen2.5)
│   ├── lora_config.yaml       # Full-precision LoRA hyperparameters
│   └── qlora_config.yaml      # 4-bit QLoRA hyperparameters
├── data/
│   ├── raw/                   # Unprocessed / converted datasets (gitignored, .gitkeep only)
│   └── processed/             # train.jsonl / val.jsonl (Alpaca format, ready to train)
├── docs/
│   ├── DATASET_GUIDE.md       # Public dataset comparison + Alpaca conversion guide
│   └── CUSTOM_DATASET_GUIDE.md # Building & cleaning your own dataset
├── evaluation/
│   ├── eval_prompts.json      # Held-out qualitative comparison prompts
│   ├── evaluate.py            # Perplexity + base-vs-ft qualitative comparison
│   └── results/               # Generated comparison_<adapter>.json reports
├── inference/
│   ├── model_loader.py        # Shared base/adapter loading logic
│   └── generate.py            # CLI single-prompt inference
├── models/
│   ├── base/                  # (optional) locally cached base weights
│   └── adapters/              # Trained LoRA/QLoRA adapters + training_stats.json
├── scripts/
│   ├── convert_to_alpaca.py   # Dolly / ShareGPT / OASST1 → Alpaca format
│   ├── clean_dataset.py       # Dedup, length-filter, sanitize
│   └── split_dataset.py       # Train/validation split
├── training/
│   ├── dataset_utils.py       # Alpaca prompt template + dataset loading
│   └── train.py                # Unsloth + TRL training entrypoint
├── tests/                      # Unit tests for GPU-independent pipeline code
└── requirements.txt
```

## Dataset

Training data is **Alpaca-format** JSONL — one JSON object per line:

```json
{"instruction": "Summarize the following text in one sentence.",
 "input": "The Amazon rainforest, spanning over 5.5 million square kilometers...",
 "output": "The Amazon rainforest is a vast, biodiverse ecosystem that plays a key role in regulating the Earth's climate."}
```

- `instruction` (required) — the task.
- `input` (optional, `""` if unused) — context the instruction operates on.
- `output` (required) — the target response.

A seed dataset (43 hand-written examples, `data/processed/train.jsonl` + `val.jsonl`) ships with the repo so the pipeline runs end-to-end out of the box. For a real fine-tune, swap in a larger dataset — see **[docs/DATASET_GUIDE.md](docs/DATASET_GUIDE.md)** for a full comparison of Alpaca, Dolly 15K, OpenHermes-2.5, UltraChat 200k, OASST1, and ShareGPT-style sources (sizes, licenses, pros/cons, and conversion code for each), and **[docs/CUSTOM_DATASET_GUIDE.md](docs/CUSTOM_DATASET_GUIDE.md)** for building and cleaning your own task-specific dataset (sourcing, sample-count guidance, cleaning checklist, train/val split strategy).

Convert any public dataset to Alpaca format, then clean and split:

```bash
python scripts/convert_to_alpaca.py --source dolly --output data/raw/dolly_alpaca.jsonl
python scripts/clean_dataset.py --input data/raw/dolly_alpaca.jsonl --output data/raw/dolly_clean.jsonl
python scripts/split_dataset.py --input data/raw/dolly_clean.jsonl \
  --train-output data/processed/train.jsonl --val-output data/processed/val.jsonl --val-ratio 0.1
```

## Fine-tuning process

`training/train.py` loads the base model via Unsloth's `FastLanguageModel`, wraps it with a LoRA adapter, and trains with TRL's `SFTTrainer`. Mode (`lora` vs `qlora`) and all hyperparameters come from `configs/lora_config.yaml` / `configs/qlora_config.yaml`.

**LoRA vs QLoRA:**

| | LoRA | QLoRA |
|---|---|---|
| Base weights | bf16/fp16 (full precision) | 4-bit NF4 quantized |
| VRAM (3B model) | ~10-12GB | ~6-8GB |
| Speed | Slightly faster | Slightly slower (dequant overhead) |
| Quality | Marginally better | ~1-2% quality trade-off from quantization noise |
| When to use | You have the VRAM headroom | Consumer GPU, larger base model |

**Key hyperparameters** (from `configs/qlora_config.yaml`):

| Parameter | Default | What it controls |
|---|---|---|
| `r` (LoRA rank) | 16 | Adapter capacity — 8-16 for simple tasks, 32-64 for complex domain adaptation. Higher = more trainable params, more overfitting risk on small data. |
| `lora_alpha` | 16 | Scaling factor for adapter output; `alpha/r` ratio of 1-2x is standard. |
| `lora_dropout` | 0.0 | Regularization on adapter layers; raise to 0.05 if you see overfitting. |
| `target_modules` | all attention + MLP projections | Which layers get adapters — covering both attention (`q/k/v/o_proj`) and MLP (`gate/up/down_proj`) gives the best quality/size trade-off. |
| `learning_rate` | 2e-4 | Standard LoRA LR — much higher than full fine-tuning (~2e-5) since only a small adapter is trained. |
| `num_train_epochs` | 3 | 2-3 epochs is typical for instruction tuning; more risks overfitting on small datasets. |
| `per_device_train_batch_size` / `gradient_accumulation_steps` | 4 / 4 (QLoRA) | Effective batch size = product of the two; tune batch size down and accumulation up if you hit OOM. |
| `lr_scheduler_type` | cosine | Smooth decay works better than linear for short instruction-tuning runs. |
| `warmup_ratio` | 0.03 | Brief LR warmup stabilizes early training. |
| `optim` | `paged_adamw_8bit` (QLoRA) / `adamw_8bit` (LoRA) | 8-bit optimizer states cut memory further; paged variant avoids VRAM spikes with 4-bit base weights. |
| `bnb_4bit_quant_type` | `nf4` | NormalFloat4 — fits normally-distributed weights better than plain int4. |
| `bnb_4bit_use_double_quant` | `true` | Quantizes the quantization constants themselves, saving ~0.4 bits/param more. |
| `use_gradient_checkpointing` | `unsloth` | Unsloth's custom checkpointing saves ~30% more VRAM than standard HF checkpointing. |

Run training:

```bash
python training/train.py --mode qlora --model llama3.2
python training/train.py --mode lora  --model qwen2.5 --adapter-name qwen-lora-v1
```

This saves the adapter (not merged weights) plus a `training_stats.json` (loss curve, timing, hyperparameters) to `models/adapters/<name>/`, which the Streamlit app reads directly.

## Evaluation

`evaluation/evaluate.py` compares a trained adapter against the base model on two axes:

1. **Perplexity** on the held-out validation set (lower = better fit to target distribution).
2. **Qualitative side-by-side generations** on `evaluation/eval_prompts.json` — a fixed set of prompts never seen during training — plus per-prompt latency for both models.

```bash
python evaluation/evaluate.py --adapter llama3.2-qlora
```

Produces `evaluation/results/comparison_<adapter>.json`, which the Streamlit app's **Training Stats** tab renders automatically (perplexity delta, per-prompt base-vs-fine-tuned text, latency).

## Interface

`app/streamlit_app.py` — four tabs:

- **💬 Chat** — single-prompt generation against the base model or any trained adapter, with adjustable max tokens / temperature / top-p and latency display.
- **⚖️ Compare Base vs Fine-Tuned** — same prompt run through both models side by side.
- **📤 Upload Dataset** — drop in an Alpaca-format `.jsonl`/`.json`, validates required fields, previews rows, saves to `data/raw/`, and prints the exact clean → split → train commands to run next.
- **📊 Training Stats** — reads `training_stats.json` and evaluation reports directly from disk; plots the train/eval loss curve and shows the perplexity comparison.

On a non-CUDA machine (e.g. a MacBook), the app detects the missing GPU and switches to a labeled **Demo Mode**: generation returns a placeholder response instead of failing, while training stats and evaluation reports (if present) still render from real saved data.

## Installation

```bash
git clone <your-repo-url>
cd local-llm-finetune-unsloth
python -m venv .venv && source .venv/bin/activate   # CUDA machine
pip install -r requirements.txt
```

> `unsloth` and `bitsandbytes` require an NVIDIA GPU + CUDA. On a CPU-only/macOS machine, `pip install -r requirements.txt` will still succeed for everything except `unsloth`/`xformers`; the Streamlit app runs in Demo Mode without them.

If using the gated Llama 3.2 checkpoint, accept Meta's license on Hugging Face and set `HF_TOKEN`:

```bash
huggingface-cli login
```

## Testing

Unit tests cover the parts of the pipeline that don't require a GPU: dataset cleaning/splitting/conversion, the Alpaca prompt template, and config file validation.

```bash
pip install pytest   # already in requirements.txt
pytest
```

## Usage

```bash
# 1. Prepare data (or use the seed data/processed/*.jsonl already included)
python scripts/convert_to_alpaca.py --source dolly --output data/raw/dolly_alpaca.jsonl
python scripts/clean_dataset.py --input data/raw/dolly_alpaca.jsonl --output data/raw/dolly_clean.jsonl
python scripts/split_dataset.py --input data/raw/dolly_clean.jsonl \
  --train-output data/processed/train.jsonl --val-output data/processed/val.jsonl

# 2. Fine-tune
python training/train.py --mode qlora --model llama3.2

# 3. Run inference
python inference/generate.py --adapter llama3.2-qlora --instruction "Explain LoRA in one paragraph."

# 4. Evaluate against the base model
python evaluation/evaluate.py --adapter llama3.2-qlora

# 5. Launch the interface
streamlit run app/streamlit_app.py
```

## Results

_Populate this section after your first training run — `evaluation/evaluate.py` and the Streamlit "Training Stats" tab generate everything needed:_

| Metric | Base model | Fine-tuned |
|---|---|---|
| Validation perplexity | _run evaluate.py_ | _run evaluate.py_ |
| Avg. generation latency | _run evaluate.py_ | _run evaluate.py_ |
| Training time | — | _from training_stats.json_ |
| Final train loss | — | _from training_stats.json_ |

Example qualitative comparison (fill in from `evaluation/results/comparison_<adapter>.json`):

> **Prompt:** "Explain what LoRA is in one paragraph."
> **Base:** _..._
> **Fine-tuned:** _..._

## Screenshots

Captured from `streamlit run app/streamlit_app.py` running in **Demo Mode** (no CUDA GPU in the capture environment — see the banner in each shot). On a CUDA machine the same views render real model output instead of the placeholder text.

| Chat | Compare Base vs Fine-Tuned | Training Stats |
|---|---|---|
| ![Chat tab](docs/screenshots/chat.jpg) | ![Compare tab](docs/screenshots/compare.jpg) | ![Training stats tab](docs/screenshots/stats.jpg) |

---

## License

MIT (or your preferred license — add a `LICENSE` file).
