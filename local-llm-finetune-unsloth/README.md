<div align="center">

# 🦥 Local LLM Fine-Tuning Studio

### Lokal LLM'larni LoRA/QLoRA bilan fine-tune qilish va sinash platformasi

*Unsloth · PEFT · Hugging Face Transformers · Streamlit*

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Unsloth](https://img.shields.io/badge/Unsloth-black?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

<br>

[Loyiha haqida](#-loyiha-haqida) ·
[Qanday ishlaydi](#-qanday-ishlaydi) ·
[Texnologiyalar](#-texnologiyalar) ·
[Tez boshlash](#-tez-boshlash) ·
[Loyiha tuzilmasi](#-loyiha-tuzilmasi)

</div>

---

## 📌 Loyiha haqida

> **Fine-Tuning Studio** — kichik LLM'larni (Llama 3.2, Qwen 2.5) o'z ma'lumotlaringiz bilan **LoRA/QLoRA** usulida o'qitib, natijani asl model bilan solishtirib ko'rish uchun to'liq lokal platforma.

Bitta training skriptidan farqli o'laroq, bu loyiha butun tsiklni qamrab oladi: ma'lumotni tayyorlash → o'qitish → baholash → chat interfeys orqali sinash.

**Qayerda foydali:**
- Domenga xos chatbot yoki yordamchi yaratish (masalan, huquqiy, tibbiy, mijozlarga xizmat)
- Kichik GPU'da (8–16GB) katta modellarni arzon fine-tune qilish
- PEFT/LoRA'ni portfolio loyihasi sifatida namoyish qilish

---

## ⚙️ Qanday ishlaydi

```mermaid
flowchart LR
    A[📄 Dataset] --> B[🧹 Tozalash]
    B --> C[✂️ Train/Val split]
    C --> D[🦥 Unsloth + LoRA/QLoRA]
    D --> E[💾 Adapter saqlanadi]
    E --> F[📊 Baza vs Fine-tuned baholash]
    E --> G[💬 Streamlit chat]
```

| Qadam | Tavsif |
|:-----:|--------|
| **1** | Alpaca-format dataset tozalanadi va train/val'ga bo'linadi |
| **2** | Unsloth orqali baza model 4-bit yuklanadi, LoRA adapter qo'shiladi |
| **3** | Adapter (nafaqat butun model) `models/adapters/`ga saqlanadi |
| **4** | Fine-tuned model baza model bilan perplexity va sifat bo'yicha solishtiriladi |
| **5** | Streamlit ilova orqali ikkalasi ham real vaqtda sinaladi |

---

## 🎬 Demo

<div align="center">
<img src="docs/demo.gif" alt="Fine-Tuning Studio demo" width="100%" />
</div>

> GPU'siz muhitda (masalan shu screenshot) ilova **Demo Mode**da ishlaydi — interfeys va training statistikasi to'liq ishlaydi, faqat jonli generatsiya o'rniga placeholder javob ko'rsatiladi.

<div align="center">

| Chat | Solishtirish | Statistika |
|---|---|---|
| ![Chat](docs/screenshots/chat.jpg) | ![Solishtirish](docs/screenshots/compare.jpg) | ![Statistika](docs/screenshots/stats.jpg) |

</div>

---

## 🧱 Texnologiyalar

<div align="center">

![Unsloth](https://img.shields.io/badge/Unsloth-black?style=flat-square)
![PEFT](https://img.shields.io/badge/PEFT-FFD21E?style=flat-square)
![Transformers](https://img.shields.io/badge/🤗_Transformers-FFD21E?style=flat-square)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![bitsandbytes](https://img.shields.io/badge/bitsandbytes-4f8ef7?style=flat-square)
![TRL](https://img.shields.io/badge/TRL-4f8ef7?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

</div>

| Qatlam | Vosita |
|---|---|
| **Fine-tuning** | Unsloth (LoRA/QLoRA) + PEFT + Transformers |
| **Quantization** | bitsandbytes (4-bit NF4) |
| **Training loop** | Hugging Face TRL (`SFTTrainer`) |
| **Baza modellar** | Llama 3.2 3B, Qwen 2.5 7B (4-bit Unsloth checkpoint) |
| **Interfeys** | Streamlit + Plotly |
| **Test** | Pytest |

---

## 🚀 Tez boshlash

```bash
pip install -r requirements.txt

# Fine-tune qilish (CUDA GPU kerak)
python training/train.py --mode qlora --model llama3.2

# Baza vs fine-tuned solishtirish
python evaluation/evaluate.py --adapter llama3.2-qlora

# Interfeysni ishga tushirish
streamlit run app/streamlit_app.py
```

GPU yo'qmi? [`notebooks/colab_finetune.ipynb`](notebooks/colab_finetune.ipynb) orqali bepul Colab T4'da to'liq pipeline'ni ishga tushiring. To'liq qo'llanma: [docs/](docs/).

---

## 📁 Loyiha tuzilmasi

```
local-llm-finetune-unsloth/
├── app/            # Streamlit interfeys (chat, solishtirish, statistika)
├── configs/        # LoRA/QLoRA hyperparametrlari (YAML)
├── scripts/        # Dataset konvert/tozalash/bo'lish
├── training/        # Unsloth + TRL training entrypoint
├── inference/        # CLI orqali generatsiya
├── evaluation/       # Baza vs fine-tuned baholash
├── tests/             # Pytest suite
└── notebooks/          # Colab uchun tayyor notebook
```

---

## 📄 Litsenziya

MIT

