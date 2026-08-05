# Joylashtirish

<sub>[← README'ga qaytish](../README.md)</sub>

UzLaw AI to'liq lokal ishlashga mo'ljallangan — hozircha boshqariluvchi
bulutli joylashtirish nishoni yo'q. Ushbu hujjat uni bitta mashinada
(ish stansiyasi yoki o'z tarmog'ingizdagi self-hosted server) ishonchli
ishga tushirishni yoritadi.

## Uchta jarayon

| Jarayon | Buyruq | Port | Nima uchun kerak |
|---|---|---|---|
| FastAPI backend | `python run_api.py` | `8000` | Mahsulot (frontend shunga bog'liq) |
| Next.js frontend | `npm run dev` (yoki `npm run build && npm start`) | `3000` | Mahsulot |
| Ollama *(agar `LLM_PROVIDER=ollama` bo'lsa)* | `ollama serve` | `11434` | Javob generatsiyasi |
| Streamlit diagnostika vositasi *(ixtiyoriy)* | `python run.py` | `8501` | Faqat indeks boshqaruvi / qidiruv diagnostikasi / statistika |

`run_api.py` `uvicorn.run(...)`ni bevosita chaqiradi (uvicorn'ning
o'zining hujjatlashtirilgan dasturiy ishga tushirish usuli), `run.py`
esa `subprocess` orqali `streamlit run`ni chaqiradi — chunki
Streamlit'ning o'z ichki API'si (`streamlit.web.bootstrap`)
hujjatlashtirilgan barqaror ochiq API emas.

`LLM_PROVIDER=gemini` bo'lsa, Ollama umuman kerak emas — faqat
`.env`da `GEMINI_API_KEY` bo'lishi kifoya.

## Production frontend qurilishi

Ishlab chiqish rejimi (`npm run dev`) Turbopack va hot reload'dan
foydalanadi — lokal uchun yaxshi, lekin uzoq muddatli joylashtirish
uchun mos emas:

```bash
cd frontend
npm run build
npm start            # production qurilmani :3000 portida taqdim etadi
```

## Indekslash

Indeks (FAISS + BM25 + SQLite metama'lumotlari) generatsiya qilinadi,
git'ga commit qilinmaydi — `indexes/*` va `data/*.db` gitignore
qilingan. Yangi klondan keyin:

- Streamlit vositasi orqali: **Indeksni boshqarish** → **Indeksni qurish
  / yangilash** (har doim inkremental; to'liq qayta qurish / o'chirish
  ikki bosqichli tasdiqlash ortida, chunki bu buzg'unchi amal).
- Yoki to'g'ridan-to'g'ri: `IndexingPipeline().sync()`.

O'zgarmagan faylni qayta indekslash tez, hech narsa qilmaydi — kontent
xeshiga asoslangan dublikatlarni aniqlash uni o'tkazib yuboradi.

## Salomatlik tekshiruvi

`GET /api/health` faol LLM provayder holatini (Ollama ulanishi yoki
Gemini kaliti mavjudligi), sozlangan `LLM_MODEL`/`EMBEDDING_MODEL`ni va
korpus hajmini (`total_documents`, `total_chunks`) ko'rsatadi — buni
process supervisor ortida jonlilik/tayyorlik probasi sifatida
ishlatish mumkin.

## Production'da xatolarni boshqarish

Har bir qatlam xom kutubxona xatolarini foydalanuvchiga
oshkor qilmasdan, o'zining tipdagi istisnolarini belgilaydi:
buzilgan yoki yo'q indekslar uchun `VectorStoreError` / `BM25IndexError`
(pipeline halokatga uchramasdan bo'sh indeksga qaytadi), buzilgan/dekod
qilib bo'lmaydigan manba fayllar uchun `DocumentLoadError`, mavjud
bo'lmagan LLM ulanishi/yuklab olinmagan Ollama modeli yoki bulutli
provayder xatosi (kvota, ulanish) uchun `LLMError` iyerarxiyasi — bular
aniq xabar sifatida ko'rsatiladi (API'dan HTTP 503, yoki Streamlit'da
interfeys ichidagi xabar), hech qachon xom stack trace emas.

## Ataylab qamrovdan tashqarida qoldirilgan narsalar

Bu yerda autentifikatsiya, ko'p-ijarachilik yoki boshqariluvchi
joylashtirish yo'q — bu ataylab yagona foydalanuvchi, lokal-birinchi
vosita ("sozlashdan keyin tashqi xizmatlarga bog'liq emas" g'oyasiga
ko'ra, Gemini tanlangan holatda bundan mustasno). Bularni qo'shish
katta arxitektura o'zgarishi bo'lar edi, oddiy joylashtirish tafsiloti
emas.
