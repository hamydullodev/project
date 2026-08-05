# Hybrid qidiruv

<sub>[← README'ga qaytish](../README.md)</sub>

## Bo'laklash: bitta modda = bitta bo'lak

`app/ingestion/chunker.py` ko'r-ko'rona belgi-soni bo'yicha bo'lishdan
ko'ra huquqiy tuzilmani hisobga oluvchi bo'lishni afzal ko'radi (bitta
modda — "N-modda" — bitta semantik bo'lakka aylanadi), faqat hujjat
tuzilgan qonun kodeksiga o'xshamaganda (masalan, modda belgilarisiz
umumiy yuklangan hujjat) ikkinchisiga o'tadi. Tanasi `CHUNK_SIZE`dan
oshib ketgan har qanday modda rekursiv belgi-bo'luvchi bilan yanada
bo'linadi (`CHUNK_OVERLAP` orqali sozlanuvchi qoplama bilan), har bir
kichik bo'lak esa ota-modda to'liq metama'lumotlarini saqlaydi —
qonun nomi, modda raqami, bo'lim, sahifa raqami — shu bois iqtibos
qaysi moddadan olinganligi haqida hech qachon noaniqlik bo'lmaydi.

## Dense qidiruv — FAISS

Har bir bo'lak ko'p tilli sentence-transformers modeli
(`EMBEDDING_MODEL`) bilan embedding qilinadi va FAISS'da indekslanadi.
So'rov ham xuddi shunday embedding qilinib, kosinus o'xshashligi
bo'yicha solishtiriladi. Dense qidiruv *ma'noni* moslashtirishda
kuchli — boshqacha so'zlar bilan ifodalangan savol ham, manba
matnidan lug'aviy jihatdan farq qilsa ham, to'g'ri moddani topadi.

## Sparse qidiruv — BM25

BM25 bir xil bo'laklarni aniq atama statistikasi bo'yicha indekslaydi.
U *aniq huquqiy atamalar va modda raqamlarini* moslashtirishda kuchli
— buni dense embedding'lar chalkashtirib yuborishi mumkin (`bge`/MiniLM
embedding "56-modda"ni "58-modda"dan ishonchli farqlamaydi — BM25 esa
farqlaydi).

> [!NOTE]
> BM25'ning xom balli **cheklanmagan** tegishlilik balli, ehtimollik
> emas — atama kamdanligiga qarab bir xonali yoki bir necha yuzlik
> bo'lishi mumkin. API dense va sparse ballarning min-max
> **normallashtirilgan** `[0, 1]` variantini ham taqdim etadi
> (`dense_score_normalized` / `sparse_score_normalized`) — aynan shu
> sababdan frontend ularni "3802%" kabi ma'nosiz natija chiqarmasdan
> foiz sifatida ko'rsatishi mumkin.

## Birlashtirish

```
combined_score = DENSE_WEIGHT * dense_score_normalized
               + SPARSE_WEIGHT * sparse_score_normalized
```

Ikkala kirish ham birlashtirishdan oldin *joriy nomzodlar to'plami
ichida* min-max normallashtiriladi, shu bois ikki mexanizmning juda
farqli ball shkalasi (kosinus o'xshashligi va BM25) bittasi
ikkinchisini shkala hisobiga ustun qilib qo'ymaydi. Har bir
mexanizmdan `TOP_K` nomzod birlashtiriladi, qo'shiladi va
`combined_score` bo'yicha saralanadi.

## Kolleksiya bo'yicha filtrlash

`collection_ids` berilganda (masalan, foydalanuvchi faqat Oila
kodeksi bo'yicha qidirmoqchi bo'lsa), qidiruv har bir mexanizmdan
odatdagidan ko'proq nomzod so'raydi (`RETRIEVAL_FILTER_OVERSAMPLE`
karrali), so'ng ruxsat etilgan kolleksiyalarga tegishli bo'lmagan
nomzodlarni chiqarib tashlaydi — bu FAISS/BM25 darajasidagi haqiqiy
metama'lumot filtri emas, balki oddiy va shu korpus hajmi uchun
yetarlicha ishonchli post-filtr yondashuvi.

## Qayta saralash — cross-encoder

Birlashtirilgan nomzodlar cross-encoder (`RERANKER_MODEL`) orqali
o'tadi, u *haqiqiy so'rov-bo'lak juftligini* birgalikda baholaydi
(dense/sparse qidiruvdan farqli, ular so'rov va bo'lakni mustaqil
baholaydi) — ancha kichik nomzodlar to'plami ustida ikkinchi, aniqroq
o'tish. Uning xom chiqishi sigmoid orqali haqiqiy `[0, 1]` tegishlilik
ehtimoliga (`reranker_score`) aylantiriladi — mahsulot buni
guruhlangan "ishonch" yorlig'i sifatida ko'rsatadi (Yuqori ≥ 0.75,
O'rta ≥ 0.5, Past — aks holda), xom, haddan tashqari da'vogar foiz
emas.

## Kontekst siqish

LLM'ga prompt yuborishdan oldin deyarli bir xil bo'laklar chiqarib
tashlanadi va qolgan kontekst `MAX_CONTEXT_CHARS`bilan cheklanadi —
prompt eng yuqori signalli, takrorlanmaydigan manbalarga
qaratilgan bo'lib qoladi, takrorlash bilan to'ldirilmaydi.

## Ma'lum cheklov: o'zbek tili morfologiyasi

BM25 stemming qilmaydi, standart yengil embedding modelining semantik
o'xshashligi ham so'rov kalit so'zning manba matnidagi bilan boshqa
grammatik kelishikda ishlatilgan holatni o'tkazib yuborishi mumkin.
Bu yengil standart modellarning o'zbek tilining boy morfologiyasidagi
haqiqiy, hujjatlashtirilgan cheklovi (aynan shu sababdan
muvaffaqiyatsiz bo'lgan aniq misol uchun qarang
`tests/evaluation/golden_dataset.py`dagi izohlar) — qidiruv
mantiqining o'zidagi xato emas. Kattaroq embedding modeli
(`BAAI/bge-m3`, `intfloat/multilingual-e5-large`) buni RAM hisobiga
yumshatadi — qarang [`configuration.md`](configuration.md).
