"""Streamlit interface for the Local LLM Fine-Tuning project.

Run with: streamlit run app/streamlit_app.py

Falls back to a clearly-labeled Demo Mode when no CUDA GPU is available, so the
UI stays fully explorable on a laptop even though Unsloth itself requires CUDA.
"""

import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Fine-Tuning Studio", page_icon="🦥", layout="wide")

PALETTE = {
    "series_1": "#2563EB",   # base model
    "series_2": "#0EA5E9",   # fine-tuned model
    "grid": "rgba(15,23,42,0.08)",
    "axis": "rgba(15,23,42,0.18)",
    "muted": "#64748b",
    "text": "#0f172a",
}

NAV_PAGES = ["💬 Chat", "⚖️ Solishtirish", "📤 Dataset", "📊 Statistika"]

SUGGESTIONS = [
    "LoRA nima va u qanday ishlaydi?",
    "QLoRA bilan LoRA o'rtasidagi farq nima?",
    "Fine-tuning uchun nechta namuna kerak?",
    "Bu loyihada qaysi baza modellar qo'llab-quvvatlanadi?",
]

THINKING_STAGES = ["🧩 Kontekst tayyorlanmoqda...", "🧠 Javob generatsiya qilinmoqda..."]

# Canned, genuinely-informative answers for Demo Mode — a real answer body
# instead of a meta "no GPU" placeholder, so the demo actually reads like the
# assistant working. The GPU disclaimer is shown once, separately, as a badge
# above the chat rather than inline in every bubble.
DEMO_ANSWERS = {
    "lora": (
        "**LoRA (Low-Rank Adaptation)** — katta tilni modeli (LLM) og'irliklarini "
        "to'liq qayta o'qitish o'rniga, har bir qatlamga kichik, arzon o'qitiladigan "
        "\"adapter\" matritsalarini qo'shadigan fine-tuning usuli.\n\n"
        "Asl model og'irliklari **muzlatiladi** (o'zgarmaydi) — faqat past-rangli "
        "(low-rank) `A` va `B` matritsalari o'qitiladi, ular asl og'irlik "
        "matritsasiga qo'shiladi: `W' = W + BA`. Bu o'qitiladigan "
        "parametrlar sonini **99%+ ga kamaytiradi**, shu bilan birga sifat deyarli "
        "to'liq fine-tuning darajasida qoladi."
    ),
    "qlora": (
        "**QLoRA** — LoRA'ning xotira-tejamkor versiyasi: baza model og'irliklari "
        "**4-bit NF4** formatida kvantlanadi (siqiladi), shu bilan birga LoRA "
        "adapterlari yuqori aniqlikda (bf16) o'qitiladi.\n\n"
        "Natijada 3B model ~6–8GB VRAM'da o'qitiladi (LoRA'da ~10–12GB kerak "
        "bo'lardi) — kichik consumer GPU'larda ham katta modellarni fine-tune "
        "qilish imkonini beradi, sifatda atigi 1–2% yo'qotish evaziga."
    ),
    "namuna": (
        "Vazifaning murakkabligiga bog'liq: oddiy uslub/format moslashuvi uchun "
        "**50–200 namuna** yetarli, domenga xos bilim (masalan huquqiy yoki "
        "tibbiy) uchun **500–2000+** namuna tavsiya etiladi.\n\n"
        "Sifat miqdordan ustun — 200 ta yaxshi tozalangan, xilma-xil namuna "
        "1000 ta shovqinli namunadan ko'ra yaxshiroq natija beradi."
    ),
    "model": (
        "Hozircha ikkita baza model qo'llab-quvvatlanadi (`configs/model_config.yaml` "
        "orqali almashtiriladi):\n\n"
        "- **Llama 3.2 3B Instruct** (4-bit Unsloth checkpoint)\n"
        "- **Qwen 2.5 7B Instruct** (4-bit Unsloth checkpoint)\n\n"
        "Ikkalasi ham LoRA va QLoRA rejimlarini qo'llab-quvvatlaydi."
    ),
}
DEMO_FALLBACK = (
    "Bu **Demo Mode** javobi — haqiqiy modelga ulanish o'rniga oldindan "
    "tayyorlangan namuna ko'rsatilmoqda. CUDA GPU'li muhitda shu joyda "
    "sizning promptingizga real modeldan kelgan javob chiqadi, xuddi shu "
    "chat interfeysi orqali."
)


def greeting() -> str:
    hour = datetime.now().hour
    if hour < 6:
        return "Xayrli tun"
    if hour < 12:
        return "Xayrli tong"
    if hour < 18:
        return "Xayrli kun"
    return "Xayrli kech"


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #ffffff; }

    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid rgba(15,23,42,0.06);
    }

    .metric-card {
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        background: #f4f6fb;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    }
    .info-card {
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        background: #ffffff;
        box-shadow: 0 2px 10px rgba(15,23,42,0.05);
        margin-bottom: 0.75rem;
    }
    .info-card h5 { margin: 0 0 0.4rem 0; font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    .demo-banner {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 0.6rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #1e40af;
    }
    .greeting-title {
        font-size: 2.4rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .greeting-sub { color: #64748b; font-size: 1rem; margin-bottom: 1.5rem; }

    div[data-testid="stChatMessage"] {
        border-radius: 16px;
        border: 1px solid rgba(15,23,42,0.06);
        box-shadow: 0 1px 3px rgba(15,23,42,0.04);
        padding: 0.25rem 0.5rem;
    }

    button[kind="secondary"] {
        border-radius: 999px !important;
        border: 1px solid rgba(15,23,42,0.12) !important;
    }

    .history-item {
        font-size: 0.85rem;
        padding: 0.4rem 0.6rem;
        border-radius: 8px;
        color: #334155;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .history-item:hover { background: #eef2ff; }
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


def list_uploaded_datasets() -> list[str]:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    if not raw_dir.exists():
        return []
    return sorted(p.name for p in raw_dir.glob("*.jsonl"))


def demo_generate(instruction: str, input_: str) -> tuple[str, float]:
    lowered = instruction.lower()
    answer = DEMO_FALLBACK
    # Longest key first so "qlora" matches before the "lora" substring it contains.
    for key in sorted(DEMO_ANSWERS, key=len, reverse=True):
        if key in lowered:
            answer = DEMO_ANSWERS[key]
            break
    time.sleep(0.2)
    return answer, 0.4


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


def new_session() -> dict:
    return {"id": str(uuid.uuid4()), "title": "Yangi suhbat", "messages": []}


def stream_words(text: str):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.012)


# ---------------------------------------------------------------- State ----
if "sessions" not in st.session_state:
    st.session_state.sessions = [new_session()]
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = st.session_state.sessions[0]["id"]
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "nav" not in st.session_state:
    st.session_state.nav = NAV_PAGES[0]
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []
if "show_info_panel" not in st.session_state:
    st.session_state.show_info_panel = True


def active_session() -> dict:
    for s in st.session_state.sessions:
        if s["id"] == st.session_state.active_session_id:
            return s
    return st.session_state.sessions[0]


with st.sidebar:
    st.markdown("### 🦥 Fine-Tuning Studio")
    st.caption("Unsloth · LoRA / QLoRA · Streamlit")

    st.session_state.nav = st.radio("Navigatsiya", NAV_PAGES, label_visibility="collapsed")

    if st.session_state.nav == "💬 Chat":
        if st.button("🆕 Yangi suhbat", use_container_width=True):
            session = new_session()
            st.session_state.sessions.insert(0, session)
            st.session_state.active_session_id = session["id"]
            st.rerun()

        with st.expander("🕘 Suhbatlar tarixi", expanded=False):
            search_query = st.text_input("🔍 Qidirish", key="chat_search", placeholder="Suhbat nomi bo'yicha...", label_visibility="collapsed")
            visible_sessions = [
                s for s in st.session_state.sessions
                if not search_query or search_query.lower() in s["title"].lower()
            ]
            if not visible_sessions:
                st.caption("Hech narsa topilmadi.")
            for s in visible_sessions:
                label = "🟢 " + s["title"] if s["id"] == st.session_state.active_session_id else s["title"]
                if st.button(label, key=f"hist_{s['id']}", use_container_width=True):
                    st.session_state.active_session_id = s["id"]
                    st.rerun()

        with st.expander("⭐ Saqlangan javoblar", expanded=False):
            if not st.session_state.bookmarks:
                st.caption("Hali hech narsa saqlanmagan.")
            for i, b in enumerate(st.session_state.bookmarks):
                st.caption(f"**{b['prompt'][:40]}**")
                st.markdown(b["content"][:120] + ("…" if len(b["content"]) > 120 else ""))
                st.divider()

        with st.expander("📤 Yuklangan datasetlar", expanded=False):
            uploaded_names = list_uploaded_datasets()
            if not uploaded_names:
                st.caption("data/raw/ ostida hali fayl yo'q.")
            for name in uploaded_names:
                st.caption(f"📄 {name}")

        with st.expander("🗂️ Adapterlar (Knowledge Base)", expanded=False):
            known_adapters = list_adapters()
            if not known_adapters:
                st.caption("Hali o'qitilgan adapter yo'q.")
            for name in known_adapters:
                st.caption(f"🧠 {name}")

    st.divider()

    with st.expander("⚙️ Sozlamalar", expanded=False):
        model_key = st.selectbox("Base model", options=["llama3.2", "qwen2.5"], index=0)
        load_in_4bit = st.toggle("Load in 4-bit (QLoRA-style)", value=True)

        adapters = list_adapters()
        adapter_choice = st.selectbox(
            "Fine-tuned adapter",
            options=["(none — base model only)"] + adapters,
            index=1 if adapters else 0,
        )
        selected_adapter = None if adapter_choice.startswith("(none") else adapter_choice

        st.markdown("**Generation parameters**")
        max_new_tokens = st.slider("Max new tokens", min_value=32, max_value=1024, value=256, step=32)
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.05)
        top_p = st.slider("Top-p", min_value=0.1, max_value=1.0, value=0.9, step=0.05)

if not adapters:
    adapters = []

if not cuda_available():
    st.markdown(
        '<div class="demo-banner">⚠️ <b>Demo Mode</b> — bu muhitda CUDA GPU topilmadi. '
        "Javoblar oldindan tayyorlangan namunalar, lekin interfeys va training statistikasi "
        "to'liq real ma'lumotlar bilan ishlaydi. CUDA GPU'li muhitda (lokal, Colab, RunPod) "
        "jonli generatsiya ishga tushadi.</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- Chat ----
if st.session_state.nav == "💬 Chat":
    active_label = f"adapter: {selected_adapter}" if selected_adapter else f"base model: {model_key}"
    session = active_session()

    st.session_state.show_info_panel = st.toggle(
        "ℹ️ Ma'lumot panelini ko'rsatish", value=st.session_state.show_info_panel,
    )

    if st.session_state.show_info_panel:
        col_main, col_info = st.columns([3, 1])
    else:
        col_main = st.container()
        col_info = None

    with col_main:
        if not session["messages"]:
            st.markdown(f'<div class="greeting-title">{greeting()} 👋</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="greeting-sub">Fine-tuning, LoRA/QLoRA yoki bu loyiha haqida '
                "istalgan narsani so'rang.</div>",
                unsafe_allow_html=True,
            )
            cols = st.columns(2)
            for i, suggestion in enumerate(SUGGESTIONS):
                if cols[i % 2].button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    st.session_state.pending_prompt = suggestion
                    st.rerun()

        for i, msg in enumerate(session["messages"]):
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🦥"):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "latency" in msg:
                    st.caption(f"⏱ {msg['latency']:.2f}s · {active_label}")
                    b1, b2, b3, b4, b5, _ = st.columns([1, 1, 1, 1, 1, 5])
                    if b1.button("📋", key=f"copy_{session['id']}_{i}", help="Nusxalash"):
                        st.session_state[f"show_code_{session['id']}_{i}"] = True
                    if b2.button("⭐", key=f"bookmark_{session['id']}_{i}", help="Saqlash"):
                        prev_prompt = session["messages"][i - 1]["content"] if i > 0 else ""
                        st.session_state.bookmarks.append({"prompt": prev_prompt, "content": msg["content"]})
                        st.toast("Javob saqlandi")
                    if b3.button("🔄", key=f"regen_{session['id']}_{i}", help="Qayta generatsiya"):
                        prev_prompt = session["messages"][i - 1]["content"] if i > 0 else ""
                        with st.spinner("Qayta generatsiya qilinmoqda..."):
                            new_response, new_latency = run_generation(
                                prev_prompt, "", selected_adapter, model_key, load_in_4bit,
                                max_new_tokens, temperature, top_p,
                            )
                        session["messages"][i] = {"role": "assistant", "content": new_response, "latency": new_latency}
                        st.rerun()
                    feedback = msg.get("feedback")
                    like_label = "👍" if feedback != "like" else "✅"
                    dislike_label = "👎" if feedback != "dislike" else "❌"
                    if b4.button(like_label, key=f"like_{session['id']}_{i}", help="Yoqdi"):
                        msg["feedback"] = None if feedback == "like" else "like"
                        st.rerun()
                    if b5.button(dislike_label, key=f"dislike_{session['id']}_{i}", help="Yoqmadi"):
                        msg["feedback"] = None if feedback == "dislike" else "dislike"
                        st.rerun()
                    if st.session_state.get(f"show_code_{session['id']}_{i}"):
                        st.code(msg["content"], language=None)

        prompt = st.chat_input("Xabar yozing...") or st.session_state.pending_prompt
        st.session_state.pending_prompt = None

        if prompt:
            if session["title"] == "Yangi suhbat":
                session["title"] = prompt[:40] + ("…" if len(prompt) > 40 else "")

            session["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="🦥"):
                stage_placeholder = st.empty()
                for stage in THINKING_STAGES:
                    stage_placeholder.caption(stage)
                    time.sleep(0.15)
                response, latency = run_generation(
                    prompt, "", selected_adapter, model_key, load_in_4bit,
                    max_new_tokens, temperature, top_p,
                )
                stage_placeholder.empty()
                st.write_stream(stream_words(response))
                st.caption(f"⏱ {latency:.2f}s · {active_label}")

            session["messages"].append({"role": "assistant", "content": response, "latency": latency})
            st.rerun()

    if col_info is not None:
        with col_info:
            st.markdown(
                f'<div class="info-card"><h5>Faol konfiguratsiya</h5>'
                f'<b>Model:</b> {model_key}<br/>'
                f'<b>Adapter:</b> {selected_adapter or "—"}<br/>'
                f'<b>4-bit:</b> {"Ha" if load_in_4bit else "Yo\'q"}<br/>'
                f'<b>Temperature:</b> {temperature}<br/>'
                f'<b>Top-p:</b> {top_p}<br/>'
                f'<b>Max tokens:</b> {max_new_tokens}</div>',
                unsafe_allow_html=True,
            )

            assistant_msgs = [m for m in session["messages"] if m["role"] == "assistant"]
            if assistant_msgs:
                last = assistant_msgs[-1]
                words = len(last["content"].split())
                st.markdown(
                    f'<div class="info-card"><h5>Oxirgi javob</h5>'
                    f'<b>Latency:</b> {last["latency"]:.2f}s<br/>'
                    f'<b>Uzunlik:</b> ~{words} so\'z<br/>'
                    f'<b>Rejim:</b> {"Demo" if not cuda_available() else "Live"}</div>',
                    unsafe_allow_html=True,
                )

            if session["messages"]:
                st.markdown('<div class="info-card"><h5>Suhbat vaqt jadvali</h5>', unsafe_allow_html=True)
                for m in session["messages"][-6:]:
                    role_icon = "🧑" if m["role"] == "user" else "🦥"
                    st.caption(f"{role_icon} {m['content'][:36]}{'…' if len(m['content']) > 36 else ''}")
                st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------- Compare ----
elif st.session_state.nav == "⚖️ Solishtirish":
    st.subheader("Baza model vs. fine-tuned model, bir xil prompt")
    if not adapters:
        st.info("models/adapters/ ostida o'qitilgan adapter topilmadi. Avval `training/train.py` bilan bittasini o'qiting.")
    compare_instruction = st.text_area("Instruction", placeholder="Write a limerick about a programmer who loves coffee.", height=100, key="compare_instruction")
    compare_input = st.text_area("Input (optional context)", placeholder="", height=80, key="compare_input")
    compare_adapter = st.selectbox("Solishtiriladigan adapter", options=adapters, key="compare_adapter") if adapters else None

    if st.button("Solishtirish", type="primary", key="compare_generate", disabled=not adapters):
        with st.spinner("Ikkala modeldan ham generatsiya qilinmoqda..."):
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
            st.markdown(f"**Baza model** ({model_key})")
            st.write(base_response)
            st.caption(f"Latency: {base_latency:.2f}s")
        with col_ft:
            st.markdown(f"**Fine-tuned** ({compare_adapter})")
            st.write(ft_response)
            st.caption(f"Latency: {ft_latency:.2f}s")

# -------------------------------------------------------------- Upload ----
elif st.session_state.nav == "📤 Dataset":
    st.subheader("Alpaca-format dataset yuklash")
    st.caption('Har bir qator JSON bo\'lishi kerak: "instruction", "input", "output". .jsonl yoki .json (obyektlar ro\'yxati) qabul qilinadi.')

    uploaded = st.file_uploader("Fayl tanlang", type=["jsonl", "json"])
    if uploaded is not None:
        raw_text = uploaded.read().decode("utf-8")
        try:
            if uploaded.name.endswith(".json"):
                rows = json.loads(raw_text)
            else:
                rows = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        except json.JSONDecodeError as e:
            st.error(f"JSON/JSONL sifatida o'qib bo'lmadi: {e}")
            rows = []

        valid_rows = [r for r in rows if isinstance(r, dict) and "instruction" in r and "output" in r]
        invalid_count = len(rows) - len(valid_rows)

        if rows:
            st.success(f"{len(rows)} qator o'qildi — {len(valid_rows)} valid, {invalid_count} majburiy maydon yetishmayapti.")
            st.dataframe(pd.DataFrame(valid_rows[:20]), use_container_width=True)

            if st.button("data/raw/ ga saqlash"):
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
                st.success(f"Saqlandi: {out_path.relative_to(PROJECT_ROOT)}")
                st.code(
                    f"python scripts/clean_dataset.py --input data/raw/{out_name} --output data/raw/{out_name.replace('.jsonl', '_clean.jsonl')}\n"
                    f"python scripts/split_dataset.py --input data/raw/{out_name.replace('.jsonl', '_clean.jsonl')} "
                    f"--train-output data/processed/train.jsonl --val-output data/processed/val.jsonl\n"
                    f"python training/train.py --mode qlora --model {model_key}",
                    language="bash",
                )

# --------------------------------------------------------------- Stats ----
elif st.session_state.nav == "📊 Statistika":
    st.subheader("Training statistikasi")

    adapters_dir = PROJECT_ROOT / "models" / "adapters"
    stats_files = sorted(adapters_dir.glob("*/training_stats.json")) if adapters_dir.exists() else []

    if not stats_files:
        st.info("training_stats.json hali topilmadi. `training/train.py` ni ishga tushiring — u avtomatik ravishda models/adapters/<name>/training_stats.json ga yoziladi.")
    else:
        chosen = st.selectbox("O'qitilgan adapterni tanlang", options=[f.parent.name for f in stats_files])
        stats_path = adapters_dir / chosen / "training_stats.json"
        with stats_path.open() as f:
            stats = json.load(f)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Baza model", stats["base_model"].split("/")[-1])
        c2.metric("Rejim", stats["mode"].upper())
        c3.metric("Epochlar", stats["epochs"])
        c4.metric("Yakuniy train loss", f"{stats.get('final_train_loss', 0):.4f}")

        c5, c6, c7 = st.columns(3)
        c5.metric("Train namunalari", stats["train_examples"])
        c6.metric("Training vaqti", f"{stats['training_time_seconds'] / 60:.1f} daq")
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
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=PALETTE["text"]),
                xaxis=dict(title="Step", gridcolor=PALETTE["grid"], linecolor=PALETTE["axis"]),
                yaxis=dict(title="Loss", gridcolor=PALETTE["grid"], linecolor=PALETTE["axis"]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        eval_report_path = PROJECT_ROOT / "evaluation" / "results" / f"comparison_{chosen}.json"
        if eval_report_path.exists():
            st.subheader("Baza vs. fine-tuned baholash")
            with eval_report_path.open() as f:
                report = json.load(f)

            r1, r2 = st.columns(2)
            r1.metric("Baza perplexity", f"{report['base_perplexity']:.2f}")
            r2.metric("Fine-tuned perplexity", f"{report['finetuned_perplexity']:.2f}",
                       delta=f"{report['finetuned_perplexity'] - report['base_perplexity']:.2f}", delta_color="inverse")

            with st.expander("Sifat solishtiruvi"):
                for comp in report["comparisons"]:
                    st.markdown(f"**{comp['instruction']}**")
                    cb, cf = st.columns(2)
                    cb.caption(f"Baza ({comp['base_latency_seconds']:.2f}s)")
                    cb.write(comp["base_response"])
                    cf.caption(f"Fine-tuned ({comp['finetuned_latency_seconds']:.2f}s)")
                    cf.write(comp["finetuned_response"])
                    st.divider()
        else:
            st.caption(f"'{chosen}' uchun baholash hisoboti topilmadi. `python evaluation/evaluate.py --adapter {chosen}` ni ishga tushiring.")
