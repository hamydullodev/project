"""Streamlit interface for the Local LLM Fine-Tuning project.

Run with: streamlit run app/streamlit_app.py

Falls back to a clearly-labeled Demo Mode when no CUDA GPU is available, so the
UI stays fully explorable on a laptop even though Unsloth itself requires CUDA.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Local LLM Fine-Tuning Studio", page_icon="🦥", layout="wide")

PALETTE = {
    "series_1": "#2a78d6",   # base model
    "series_2": "#eb6834",   # fine-tuned model
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "muted": "#898781",
    "text": "#0b0b0b",
}

st.markdown(
    """
    <style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .metric-card {
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 10px;
        padding: 1rem 1.25rem;
        background: rgba(42,120,214,0.04);
    }
    .demo-banner {
        background: #fff7e6;
        border: 1px solid #eda100;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


@st.cache_resource
def get_base_model(model_key: str, load_in_4bit: bool):
    from inference.model_loader import load_base_model
    return load_base_model(model_key, load_in_4bit=load_in_4bit)


@st.cache_resource
def get_finetuned_model(adapter_name: str, load_in_4bit: bool):
    from inference.model_loader import load_finetuned_model
    return load_finetuned_model(adapter_name, load_in_4bit=load_in_4bit)


def list_adapters() -> list[str]:
    from inference.model_loader import list_available_adapters
    return list_available_adapters()


def demo_generate(instruction: str, input_: str) -> tuple[str, float]:
    seed_text = (
        f"[DEMO OUTPUT — no CUDA GPU detected in this environment]\n\n"
        f"This is a placeholder response standing in for real model generation. "
        f"On a CUDA-equipped machine, this panel would show the actual output for:\n"
        f"\"{instruction}\"" + (f" (with input: \"{input_}\")" if input_ else "")
    )
    time.sleep(0.4)
    return seed_text, 0.4


def run_generation(instruction: str, input_: str, use_adapter: str | None, model_key: str,
                    load_in_4bit: bool, max_new_tokens: int, temperature: float, top_p: float) -> tuple[str, float]:
    if not cuda_available():
        return demo_generate(instruction, input_)

    from inference.generate import generate

    if use_adapter:
        model, tokenizer = get_finetuned_model(use_adapter, load_in_4bit)
    else:
        model, tokenizer = get_base_model(model_key, load_in_4bit)

    return generate(model, tokenizer, instruction, input_,
                     max_new_tokens=max_new_tokens, temperature=temperature, top_p=top_p)


st.title("🦥 Local LLM Fine-Tuning Studio")
st.caption("LoRA / QLoRA fine-tuning with Unsloth, PEFT, and bitsandbytes — base vs. fine-tuned comparison, live inference, and training diagnostics.")

if not cuda_available():
    st.markdown(
        '<div class="demo-banner">⚠️ <b>Demo Mode</b> — no CUDA GPU detected in this environment. '
        "Unsloth requires an NVIDIA GPU, so live generation is disabled here and placeholder outputs are shown instead. "
        "Training stats and evaluation reports (if present under <code>models/adapters/</code> and "
        "<code>evaluation/results/</code>) still render from real saved data. Deploy on a CUDA machine "
        "(local GPU, Colab, RunPod, Lambda) for live inference.</div>",
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.header("Configuration")

    model_key = st.selectbox("Base model", options=["llama3.2", "qwen2.5"], index=0)
    load_in_4bit = st.toggle("Load in 4-bit (QLoRA-style)", value=True)

    adapters = list_adapters()
    adapter_choice = st.selectbox(
        "Fine-tuned adapter",
        options=["(none — base model only)"] + adapters,
        index=1 if adapters else 0,
    )
    selected_adapter = None if adapter_choice.startswith("(none") else adapter_choice

    st.subheader("Generation parameters")
    max_new_tokens = st.slider("Max new tokens", min_value=32, max_value=1024, value=256, step=32)
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.05)
    top_p = st.slider("Top-p", min_value=0.1, max_value=1.0, value=0.9, step=0.05)

tab_chat, tab_compare, tab_upload, tab_stats = st.tabs(
    ["💬 Chat", "⚖️ Compare Base vs Fine-Tuned", "📤 Upload Dataset", "📊 Training Stats"]
)

with tab_chat:
    st.subheader("Ask the model")
    instruction = st.text_area("Instruction", placeholder="Explain what LoRA is in one paragraph.", height=100, key="chat_instruction")
    input_context = st.text_area("Input (optional context)", placeholder="", height=80, key="chat_input")

    active_label = f"adapter: {selected_adapter}" if selected_adapter else f"base model: {model_key}"
    st.caption(f"Currently using **{active_label}**")

    if st.button("Generate", type="primary", key="chat_generate"):
        if not instruction.strip():
            st.warning("Enter an instruction first.")
        else:
            with st.spinner("Generating..."):
                response, latency = run_generation(
                    instruction, input_context, selected_adapter, model_key, load_in_4bit,
                    max_new_tokens, temperature, top_p,
                )
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown("**Response**")
                st.write(response)
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Latency", f"{latency:.2f}s")
                st.markdown("</div>", unsafe_allow_html=True)

with tab_compare:
    st.subheader("Base model vs. fine-tuned model, same prompt")
    if not adapters:
        st.info("No trained adapters found under models/adapters/. Train one first with `training/train.py`, or point this at an existing adapter directory.")
    compare_instruction = st.text_area("Instruction", placeholder="Write a limerick about a programmer who loves coffee.", height=100, key="compare_instruction")
    compare_input = st.text_area("Input (optional context)", placeholder="", height=80, key="compare_input")
    compare_adapter = st.selectbox("Adapter to compare against base", options=adapters, key="compare_adapter") if adapters else None

    if st.button("Compare", type="primary", key="compare_generate", disabled=not adapters):
        with st.spinner("Generating from both models..."):
            base_response, base_latency = run_generation(
                compare_instruction, compare_input, None, model_key, load_in_4bit,
                max_new_tokens, temperature, top_p,
            )
            ft_response, ft_latency = run_generation(
                compare_instruction, compare_input, compare_adapter, model_key, load_in_4bit,
                max_new_tokens, temperature, top_p,
            )

        col_base, col_ft = st.columns(2)
        with col_base:
            st.markdown(f"**Base model** ({model_key})")
            st.write(base_response)
            st.caption(f"Latency: {base_latency:.2f}s")
        with col_ft:
            st.markdown(f"**Fine-tuned** ({compare_adapter})")
            st.write(ft_response)
            st.caption(f"Latency: {ft_latency:.2f}s")

with tab_upload:
    st.subheader("Upload an Alpaca-format dataset")
    st.caption('Each row must be JSON with keys: "instruction", "input", "output". Accepts .jsonl or .json (list of objects).')

    uploaded = st.file_uploader("Choose a file", type=["jsonl", "json"])
    if uploaded is not None:
        raw_text = uploaded.read().decode("utf-8")
        try:
            if uploaded.name.endswith(".json"):
                rows = json.loads(raw_text)
            else:
                rows = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        except json.JSONDecodeError as e:
            st.error(f"Could not parse file as JSON/JSONL: {e}")
            rows = []

        valid_rows = [r for r in rows if isinstance(r, dict) and "instruction" in r and "output" in r]
        invalid_count = len(rows) - len(valid_rows)

        if rows:
            st.success(f"Parsed {len(rows)} rows — {len(valid_rows)} valid, {invalid_count} missing required fields.")
            st.dataframe(pd.DataFrame(valid_rows[:20]), use_container_width=True)

            if st.button("Save to data/raw/"):
                out_name = f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                out_path = PROJECT_ROOT / "data" / "raw" / out_name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with out_path.open("w", encoding="utf-8") as f:
                    for row in valid_rows:
                        f.write(json.dumps({
                            "instruction": row["instruction"],
                            "input": row.get("input", ""),
                            "output": row["output"],
                        }, ensure_ascii=False) + "\n")
                st.success(f"Saved to {out_path.relative_to(PROJECT_ROOT)}")
                st.code(
                    f"python scripts/clean_dataset.py --input data/raw/{out_name} --output data/raw/{out_name.replace('.jsonl', '_clean.jsonl')}\n"
                    f"python scripts/split_dataset.py --input data/raw/{out_name.replace('.jsonl', '_clean.jsonl')} "
                    f"--train-output data/processed/train.jsonl --val-output data/processed/val.jsonl\n"
                    f"python training/train.py --mode qlora --model {model_key}",
                    language="bash",
                )

with tab_stats:
    st.subheader("Training statistics")

    adapters_dir = PROJECT_ROOT / "models" / "adapters"
    stats_files = sorted(adapters_dir.glob("*/training_stats.json")) if adapters_dir.exists() else []

    if not stats_files:
        st.info("No training_stats.json found yet. Run `training/train.py` to produce one — it's written automatically to models/adapters/<name>/training_stats.json.")
    else:
        chosen = st.selectbox("Select a trained adapter", options=[f.parent.name for f in stats_files])
        stats_path = adapters_dir / chosen / "training_stats.json"
        with stats_path.open() as f:
            stats = json.load(f)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Base model", stats["base_model"].split("/")[-1])
        c2.metric("Mode", stats["mode"].upper())
        c3.metric("Epochs", stats["epochs"])
        c4.metric("Final train loss", f"{stats.get('final_train_loss', 0):.4f}")

        c5, c6, c7 = st.columns(3)
        c5.metric("Train examples", stats["train_examples"])
        c6.metric("Training time", f"{stats['training_time_seconds'] / 60:.1f} min")
        c7.metric("LoRA rank / alpha", f"r={stats['lora_r']} / α={stats['lora_alpha']}")

        log_history = stats.get("log_history", [])
        loss_points = [(e["step"], e["loss"]) for e in log_history if "loss" in e]
        eval_points = [(e["step"], e["eval_loss"]) for e in log_history if "eval_loss" in e]

        if loss_points:
            fig = go.Figure()
            steps, losses = zip(*loss_points)
            fig.add_trace(go.Scatter(
                x=list(steps), y=list(losses), mode="lines", name="Train loss",
                line=dict(color=PALETTE["series_1"], width=2),
            ))
            if eval_points:
                e_steps, e_losses = zip(*eval_points)
                fig.add_trace(go.Scatter(
                    x=list(e_steps), y=list(e_losses), mode="lines+markers", name="Eval loss",
                    line=dict(color=PALETTE["series_2"], width=2),
                    marker=dict(size=8),
                ))
            fig.update_layout(
                height=380,
                margin=dict(l=40, r=20, t=20, b=40),
                plot_bgcolor="#fcfcfb",
                paper_bgcolor="#fcfcfb",
                font=dict(color=PALETTE["text"]),
                xaxis=dict(title="Step", gridcolor=PALETTE["grid"], linecolor=PALETTE["axis"]),
                yaxis=dict(title="Loss", gridcolor=PALETTE["grid"], linecolor=PALETTE["axis"]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        eval_report_path = PROJECT_ROOT / "evaluation" / "results" / f"comparison_{chosen}.json"
        if eval_report_path.exists():
            st.subheader("Base vs. fine-tuned evaluation")
            with eval_report_path.open() as f:
                report = json.load(f)

            r1, r2 = st.columns(2)
            r1.metric("Base perplexity", f"{report['base_perplexity']:.2f}")
            r2.metric("Fine-tuned perplexity", f"{report['finetuned_perplexity']:.2f}",
                       delta=f"{report['finetuned_perplexity'] - report['base_perplexity']:.2f}", delta_color="inverse")

            with st.expander("Qualitative comparisons"):
                for comp in report["comparisons"]:
                    st.markdown(f"**{comp['instruction']}**")
                    cb, cf = st.columns(2)
                    cb.caption(f"Base ({comp['base_latency_seconds']:.2f}s)")
                    cb.write(comp["base_response"])
                    cf.caption(f"Fine-tuned ({comp['finetuned_latency_seconds']:.2f}s)")
                    cf.write(comp["finetuned_response"])
                    st.divider()
        else:
            st.caption(f"No evaluation report found for '{chosen}'. Run `python evaluation/evaluate.py --adapter {chosen}` to generate one.")
