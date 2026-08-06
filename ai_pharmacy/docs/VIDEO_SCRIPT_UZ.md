# AI Pharmacy — Video rolik skripti (motion graphics, Huquq AI uslubida)

**Tahlil qilingan manba:** `Huquq AI Video.mp4` (90 sek, 1920×1080, ovozsiz — sof matn/animatsiya bilan hikoya qiluvchi motion-graphics reel).

## Huquq AI videosining vizual tizimi (tahlil natijasi)

| Element | Tavsif |
|---|---|
| Fon | Deyarli qora-to'q-ko'k (`#0a0e1a` atrofida), markazda juda xira binafsha/ko'k nur dog'i |
| Aksent rang | Binafsha-indigo gradient (brend), qizil — muammo/xato uchun, yashil — yechim/muvaffaqiyat uchun |
| Shrift | Qalin, zamonaviy grotesk (Inter/Satoshi uslubida), boshida kichik kulrang UPPERCASE "eyebrow" label (masalan `SAVOL`, `QANDAY ISHLAYDI`, `O'LCHOV`) |
| Fon animatsiyasi | Shaffof "hujjat" kartochkalari sekin suzib yuradi — brendga xos vizual metafora |
| Struktura | 1) Muammo (matn + soxta LLM javobi bilan) → 2) Logo reveal → 3) "Qanday ishlaydi" — raqamlangan node-diagramma → 4) O'lchov/benchmark bar chart → 5) Haqiqiy mahsulot skrinshoti (3D tilt → flat) → 6) Samaradorlik diff-vizual (qizil/yashil) → 7) Yakuniy statistika kartasi + tagline + logo |
| Ovoz | Yo'q — hikoya butunlay ekrandagi matn va animatsiya orqali boriladi (fon musiqasi keyinroq qo'shiladi deb taxmin qilinadi) |

AI Pharmacy uchun bir xil struktura va uslub saqlanadi, faqat: (1) rang — Huquq AI'ning binafshasi o'rniga AI Pharmacy/Avia AI oilasining o'z brend rangi — ko'k→moviy gradient (`#2563EB → #38BDF8`, `app/ui/theme.py`dagi `ACCENT_GRADIENT`); (2) fondagi "hujjat" kartochkalari o'rniga suzib yuruvchi tabletka/kapsula ikonkalari; (3) barcha raqamlar — haqiqiy, loyihada allaqachon tasdiqlangan (masalan, Paracetamol 500mg qidiruvida ilgari sinovdan o'tgan real narxlar).

---

## Skript (90 sekund)

| Vaqt | Ekranda matn | Vizual | Rang / harakat |
|---|---|---|---|
| 0:00–0:04 | Eyebrow: `SAVOL` <br> Sarlavha (yozilayotgan kursor bilan): **"Eng arzon Vitamin D3 qayerda?"** | Qora-ko'k fon, pastda ingichka gradient chiziq, orqa fonda xira suzuvchi kapsula ikonkalari | Matn harf-harf yoziladi (typing effekti), kursor ko'k rangda miltillaydi |
| 0:04–0:07 | (matnsiz o'tish) | Fon to'lib ketadi: o'nlab shaffof mahsulot-kartochkalari tartibsiz suzib chiqadi — narxlar bir-biriga mos kelmaydi | Xira kulrang kartochkalar, sekin parallaks harakat |
| 0:07–0:10 | **"Narx har dorixonada boshqacha. Javob bor — lekin qaysi do'konda?"** | Kartochkalar orasidan markazga zoom | Oq qalin matn, pastida ingichka ko'k chiziq |
| 0:10–0:14 | Logo reveal: **AI Pharmacy** (P + kapsula belgisi, dumaloq kvadrat ichida, ko'k→moviy gradient, atrofida yumshoq nur) | Fon qorayadi, markazda faqat logo va nom qoladi | Logo yengil "glow pulse" bilan paydo bo'ladi, pastida tor gradient chiziq chizila boshlaydi |
| 0:14–0:18 | Eyebrow: `SOF LLM` <br> **"Bu dori taxminan 40 000 so'm turadi"** <br> kichik matn: `source: null · confidence: —` | Yarim shaffof karta — xuddi Huquq AI'dagi "SOF LLM" kartasi kabi, lekin narx mavzusida | Karta oq/kulrang, pastki texnik qator xira kulrang monospace shrift bilan |
| 0:18–0:22 | **"Sof LLM narxni o'ylab topadi."** (oq) <br> **"Bu — pulingizni yo'qotish demak."** (qizil, qalin) | Yuqoridagi karta pasayib ketadi, ikki qatorli matn markazda qoladi | Ikkinchi qator qizil rangda, chapida qizil vertikal chiziqcha (accent bar) |
| 0:22–0:26 | Eyebrow: `QANDAY ISHLAYDI` <br> **"Savoldan real narxgacha"** | Fon tozalanadi, sarlavha chap yuqori burchakda logotip bilan birga | Oq qalin sarlavha, kulrang eyebrow tepada |
| 0:26–0:34 | Node-diagramma, ketma-ket paydo bo'ladi: `1 Savol` (foydalanuvchi tilida) → `2 Skreyperlar` (OXYmed · PharmaClick · Europharm — parallel) → `3 Kesh` (SQLite, 15 daqiqa) → `4 Grounding safeguard` (tool JSON'dan qayta quriladi) → `5 Javob + narx + do'kon` | Huquq AI'dagi Dense/Sparse/RRF zanjiriga o'xshash — bog'lovchi chiziqlar bilan ulangan kartochkalar, chapdan o'ngga | Har karta paydo bo'lganda ulanish chizig'i ham "chizilib" boradi (ko'k/moviy gradient chiziq); pastda kichik izoh: `— Uchala dorixona bir vaqtda so'raladi` |
| 0:34–0:38 | Eyebrow: `O'LCHOV` <br> **"Bir xil so'rov. Uch xil dorixona."** | Bar chart: `Eng qimmat` / `O'rtacha` / `Eng arzon` — real son bilan (masalan, Paracetamol 500mg: 118 400 / 50 709 / 3 500 UZS) | Eng arzon ustun yashil-moviy gradient bilan ajratiladi va ustiga `-93%` belgisi chiqadi (Huquq AI'dagi `0.95` kabi katta raqam urg'usi) |
| 0:38–0:46 | (matnsiz, real interfeys) | Haqiqiy AI Pharmacy skrinshoti — 3D tilt burchakda: bosh sahifa (hero + qidiruv) → chat: "Paracetamol 500mg" yozilyapti → mahsulot kartalari chiqadi (Eng arzon / Eng yaxshi tanlov belgilari bilan) | Skrinshot asta-sekin tekislanadi (3D tilt → flat), soft shadow bilan |
| 0:46–0:52 | (matnsiz, davomi) | Bitta kartaning "Batafsil" tugmasi bosiladi → tafsilotlar ochiladi → "Compare Prices" sahifasiga o'tiladi, jadval ko'rinadi | Kursor harakati sekin va aniq, klik joyida yengil "ripple" effekti |
| 0:52–0:56 | **"Faqat narx o'zgargan mahsulot qayta so'raladi."** | Ikki mini-karta yonma-yon: chapda qizil chiziq (`Har safar qayta skreyplash`), o'ngda yashil chiziq (`15 daqiqalik kesh`) | Huquq AI'dagi "Faqat o'zgargan modda qayta indexlanadi" bilan bir xil vizual andoza |
| 0:56–0:64 | To'rtta pastki chip: `6 ta AI tool` · `3 ta real dorixona` · `Narx taqqoslash` · `Veb-qidiruv (qo'shimcha)` | Pastki markazda gorizontal joylashgan pill-shakldagi chiplar, ketma-ket paydo bo'ladi | Huquq AI'dagi "5 ta LLM vositasi / jonli lex.uz qidiruvi / suhbat tarixi / hujjat yuklash" qatoriga to'g'ridan-to'g'ri mos |
| 0:64–0:78 | Eyebrow yo'q — statistik qator: **"3 dorixona · 6 AI tool · 8 GB RAM'da ishlaydi · Lokal LLM"** | Logo markazda, ostida statistik qator (Huquq AI'dagi "1 283 hujjat · 22 513 chunk · recall@5 = 0.95 · MRR 0.780 · 8 GB RAM'da ishlaydi" bilan bir xil format) | Statistik raqamlar kichik, tekis, monospace-ga yaqin shrift |
| 0:78–0:86 | **"Har narx ostida — haqiqiy do'kon va uning havolasi."** | Logo tepada kichrayib qoladi, tagline markazda katta harflarda | Oq qalin matn, ko'k gradient chiziq ostida |
| 0:86–0:90 | Pastda kichik matn: *"Javoblar tavsiya xarakterga ega. Tibbiy maslahat emas — faqat narx va mahsulot qidiruv."* | Ekran asta-sekin qorayib, faqat shu ogohlantirish matni qoladi | Xira kulrang, kichik, sekin fade-out bilan tugaydi |

---

## Amalga oshirish uchun eslatmalar

- **Ovoz:** manba video kabi bu ham ovozsiz, sof matn/animatsiya orqali hikoya qiladigan reel sifatida mo'ljallangan — fon musiqasi (past tempoli, "corporate tech" uslubida) alohida qo'shiladi, gapiruvchi diktor kerak emas.
- **Raqamlar haqiqiyligi:** benchmark blokidagi narxlar (3 500 / 50 709 / 118 400 UZS) — shu suhbatda avval jonli sinovdan o'tgan haqiqiy Paracetamol 500mg natijalari. Ekranga chiqarishdan oldin joriy narxlar bilan qayta tekshiring (dorixona narxlari vaqt o'tishi bilan o'zgaradi).
- **Skrinshot manbasi:** 0:38–0:52 oralig'idagi interfeys — ilgari brauzerda sinovdan o'tkazilgan haqiqiy AI Pharmacy UI (Home, Search natijalari, Compare Prices). Yangi ekran yozib olish kerak bo'lsa, xuddi shu uch bosqichni takrorlash kifoya.
- **Shrift/rang fayli:** `app/ui/theme.py` va `styles.py`dagi tokenlar (`ACCENT_GRADIENT`, `RADIUS_MD`, `SHADOW_MD` va h.k.) — video dizaynerga to'g'ridan-to'g'ri rang/radius manbai sifatida berilishi mumkin, shunda video va ilova bir xil "oilaviy" ko'rinishda qoladi.
