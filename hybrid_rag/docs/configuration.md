# Konfiguratsiya

<sub>[← README'ga qaytish](../README.md)</sub>

Barcha sozlamalar `.env` faylida (boshlash uchun `.env.example`dan
nusxa oling). Quyidagi har bir kalit jarayon boshlanishida bir marta
`app/config/` (Pydantic settings) tomonidan o'qiladi — `.env`ni
o'zgartirish jarayonni qayta ishga tushirishni talab qiladi.

## Asosiy o'zgaruvchilar

| O'zgaruvchi | Vazifasi | Izoh |
|---|---|---|
| `LLM_PROVIDER` | `ollama` (to'liq lokal) yoki `gemini` (bulutli) | Ikkalasi ham bir xil `generate()`/`stream()` interfeysini ishlatadi |
| `LLM_MODEL` | Generatsiya uchun Ollama model nomi | Oldindan yuklab olingan bo'lishi kerak (`ollama pull <nom>`) |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Gemini API kaliti va model nomi | `LLM_PROVIDER=gemini` bo'lganda talab qilinadi |
| `LLM_MAX_TOKENS` | `/api/ask` javoblari uchun token byudjeti | Ba'zi bulutli modellar (masalan, Gemini) ichki "fikrlash" tokenlarini ham shu byudjetdan sarflaydi — juda past qiymat javobni bo'sh/kesik qoldirishi mumkin |
| `DOCUMENT_ANALYSIS_MAX_TOKENS` | Hujjat tahlili uchun alohida, kattaroq token byudjeti | Ko'p bo'limli tahlil uchun `LLM_MAX_TOKENS`dan ancha katta bo'lishi kerak |
| `EMBEDDING_MODEL` | Dense qidiruv uchun ko'p tilli embedding modeli | O'zgartirishdan oldin pastdagi RAM eslatmasini o'qing |
| `RERANKER_MODEL` | Hybrid natijalarni qayta saralovchi cross-encoder | Sigmoid-normallashtirilgan chiqish, qarang [`hybrid-retrieval.md`](hybrid-retrieval.md) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Matnni bo'laklash parametrlari | Faqat huquqiy tuzilma chegarasidan oshgan moddalarga taalluqli |
| `TOP_K` / `RERANK_TOP_K` | Qayta saralashdan oldin/keyingi nomzodlar soni | `TOP_K` — birlashtirishdan oldin har bir mexanizm (dense + sparse) uchun; `RERANK_TOP_K` — qayta saralashdan keyin |
| `DENSE_WEIGHT` / `SPARSE_WEIGHT` | Hybrid ball birlashtirish og'irliklari | Min-max *normallashtirilgan* ballarga qo'llaniladi, xom ballarga emas |
| `VECTOR_PATH` / `BM25_PATH` / `SQLITE_PATH` | Indeks/metama'lumotlar saqlanadigan joy | Indekslash pipeline tomonidan qayta yaratiladi — to'liq qayta qurish uchun o'chirish xavfsiz |
| `MAX_DOCUMENT_ANALYSIS_CHARS` | Hujjat tahliliga yuboriladigan matn hajmi chegarasi | Undan uzun hujjatlar kesiladi, bu haqda javobda eslatma beriladi |
| `MAX_CONTEXT_CHARS` | Kontekst siqish byudjeti | Dublikatlar olib tashlangandan keyin prompt hajmini cheklaydi |
| `LOG_LEVEL` | Loglash darajasi | Har bir bosqich `app/utils/logger.py` orqali `logs/app.log`ga va konsolga yoziladi |

## RAM va embedding modeli

Loyihaning dastlabki spetsifikatsiyasi `BAAI/bge-m3` (~2.3GB og'irlik,
yuklash paytida vaqtincha taxminan ikki barobar RAM) modelini namuna
sifatida ko'rsatgan edi. 8GB RAM'li mashinada `bge-m3`ni yuklash
`EMBEDDING_DEVICE=mps`da cheksiz osilib qolgan, `EMBEDDING_DEVICE=cpu`da
esa qattiq swap-thrashing (10+ daqiqa tugamasdan) yuzaga kelgan — bu
resurs cheklovi, xato emas.

Shu sababli **standart `EMBEDDING_MODEL` — ancha yengil
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(~470MB)** bo'lib, cheklangan uskunada tez va to'g'ri yuklanadi va test
to'plami ham shuni ishlatadi. Agar RAM zaxirangiz ko'proq bo'lsa (16GB+
tavsiya etiladi) va qidiruv sifatini oshirmoqchi bo'lsangiz (ayniqsa
o'zbek tilining boy morfologiyasi uchun — qarang
[`hybrid-retrieval.md`](hybrid-retrieval.md)), `BAAI/bge-m3` yoki
`intfloat/multilingual-e5-large`ga o'ting — ikkalasi ham to'liq
qo'llab-quvvatlanadi. Agar og'irroq model osilib qolsa yoki
thrashing yuzaga kelsa:

- Birinchi yuklashdan oldin xotira talab qiladigan boshqa dasturlarni yoping.
- `mps` o'rniga `EMBEDDING_DEVICE=cpu`ni afzal ko'ring — testlarda `mps`
  butunlay osilib qolgan; `cpu` hech bo'lmasa (sekin) ilgarilagan.
- `intfloat/multilingual-e5-base` (~1.1GB) maqbul o'rtacha variant.

## Frontend konfiguratsiyasi

Next.js frontend o'zining `frontend/.env.local` faylini o'qiydi
(`.env.local.example`dan nusxa oling):

| O'zgaruvchi | Vazifasi |
|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI backend manzili (standart `http://localhost:8000`) |
| `NEXT_PUBLIC_STREAMLIT_URL` | Streamlit diagnostika vositasi manzili, navbar'dagi Sozlamalar havolasi uchun (standart `http://localhost:8501`) |
| `NEXT_PUBLIC_GITHUB_URL` | Ixtiyoriy — o'rnatilsa navbar'da GitHub tugmasi ko'rsatiladi |
