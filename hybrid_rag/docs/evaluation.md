# Baholash

<sub>[← README'ga qaytish](../README.md)</sub>

## Qidiruv metrikalari

`app/rag/evaluation.py` to'rtta standart axborot-qidiruv metrikasini
qo'lda amalga oshiradi (kutubxonaga topshirilmasdan,
`test_retrieval_metrics.py`da scikit-learn'ning ma'lumotnoma
`ndcg_score`si bilan ham tekshirilgan):

| Metrika | Nimani o'lchaydi |
|---|---|
| **Precision@K** | Topilgan eng yaxshi K bo'lakdan qanchasi haqiqatan tegishli? |
| **Recall@K** | Barcha tegishli bo'laklardan qanchasi eng yaxshi K ichida chiqadi? |
| **MRR** | O'rtacha teskari rang — *birinchi* tegishli natija qanchalik yuqorida chiqadi, so'rovlar bo'yicha o'rtachalashtirilgan |
| **nDCG@K** | Normallashtirilgan chegirmali kumulyativ foyda — tegishli natijalar *ertaroq* chiqishini mukofotlaydi, shunchaki mavjudligini emas |

Tegishlilik **modda darajasida** baholanadi, bo'lak darajasida emas —
topilgan bo'lak, agar u "oltin" so'rov haqiqatda tegishli bo'lgan
moddaga tegishli bo'lsa, tegishli hisoblanadi, chunki foydalanuvchi
aynan shu birlikka iqtibos qiladi va tekshiradi, o'zboshimchalik bilan
bo'lingan bo'lak chegarasiga emas.

## Oltin ma'lumotlar to'plami

`tests/evaluation/golden_dataset.py` 8 ta qo'lda tekshirilgan
(so'rov → tegishli modda) juftlikni saqlaydi, har bir qonun kodeksi
uchun kamida bittadan — har biri haqiqiy manba matnidan xarakterli
faktni topib, u haqida tabiiy o'zbekcha savol tuzish orqali yaratilgan,
sun'iy generatsiya qilinmagan. Indekslangan korpusga nisbatan hozirgi
natijalar:

| Metrika | Ball |
|---|---|
| Precision@5 | 0.20 *(bu to'plam uchun shift — har bir so'rovda aynan 1 ta tegishli modda, 5 ta o'rinda)* |
| Recall@5 | 1.00 |
| MRR | 0.70 |
| nDCG@5 | 0.77 |

`test_retrieval_evaluation.py` bularning ma'lum bir chegaradan
pastga tushmasligini tasdiqlaydi — mukammal ball emas, 8 ta so'rovlik
namuna uchun ataylab bo'sh qoldirilgan — regressiya himoyasi sifatida:
bo'laklash, embedding modeli yoki birlashtirish og'irliklariga
kelajakdagi o'zgarish qidiruv sifatini sezilarli pasaytirsa, bu test
muvaffaqiyatsiz bo'ladi.

## Test falsafasi

Test to'plami haqiqiy komponent tez va deterministik bo'lgan har
joyda mock'lar o'rniga haqiqiy komponentlarni afzal ko'radi — haqiqiy
bo'laklovchi, haqiqiy SQLite repozitoriysi, kichik xotiradagi
korpuslar ustida haqiqiy FAISS/BM25 indekslari. Mock'lar faqat
haqiqatan tashqi, sekin yoki nodeterministik bog'liqliklar
(Ollama/Gemini'ning HTTP chaqiruvlari) uchun ishlatiladi.

Bir qancha testlar ataylab ajratilgan fixture o'rniga loyihaning
haqiqiy, allaqachon indekslangan korpusiga nisbatan ishlaydi — bu
haqiqiy xatti-harakatni aks ettiradi, test ifloslanishi emas, chunki
sun'iy fixture'larga nisbatan qidiruv sifati haqiqiy dunyo sifati
haqida hech narsa demaydi. Bu aniq testlar avval haqiqiy korpus
indekslanishini talab qiladi, generatsiyaga bog'liq testlar uchun esa
— ishlab turgan `ollama serve` (`LLM_MODEL` yuklab olingan) yoki
sozlangan Gemini kaliti kerak.

```bash
python -m pytest                        # to'liq to'plam
python -m pytest -k "not page"           # sekinroq Streamlit AppTest to'plamlarini o'tkazib yuborish
python -m pytest tests/evaluation/ -v    # faqat qidiruv sifati metrikalari
```

## Kichik lokal LLM'lar haqida eslatma

Standart `LLM_MODEL`, `llama3.2:3b`, kichik (3B parametr) va siyrak
kontekst ostida ba'zan takrorlanuvchi yoki o'zaro ziddiyatli javoblar
berishi mumkin (to'liq tadqiqot uchun qarang
`app/llm/ollama_client.py`ning docstring'i). Bu model imkoniyatining
cheklovi, pipeline xatosi emas — amalda buni ko'rsangiz, kattaroq
model (`qwen2.5:7b` yoki shunga o'xshash, RAM imkon bergancha) yoki
`LLM_PROVIDER=gemini`ga o'tish to'g'ridan-to'g'ri yechim.
