# AI Pharmacy — Taqdimot skripti

## 0:00
### Muammo
O'zbekistonda odam dori-darmon kerak bo'lganda, odatda uni bir nechta internet dorixona saytida alohida-alohida qidiradi — narxlar har xil, ba'zisida mavjud, ba'zisida yo'q, va hech qaysi sayt sizga "eng arzoni shu, eng yaqin mavjudi shu" deb ko'rsatib bermaydi. Vaqt ketadi, va baribir eng yaxshi variantni tanlaganingizga ishonchingiz bo'lmaydi. Men shu muammoni hal qilish uchun AI Pharmacy'ni qurdim.

## 0:10
### Loyiha haqida
AI Pharmacy — O'zbekistondagi internet dorixonalaridan dori va vitaminlarni qidiradigan, narxlarini taqqoslaydigan AI yordamchi. Uchta real dorixona — OXYmed, PharmaClick, Europharm — bitta suhbat oynasida birlashtirilgan. Muhimi: bu tibbiy maslahat beruvchi emas — tashxis qo'ymaydi, davolash usulini tavsiya qilmaydi, faqat xarid qarorida yordam beradi. Va har bir narx, har bir mahsulot nomi hech qachon o'ylab topilmaydi — faqat tool orqali haqiqiy saytdan olingan natijaga asoslanadi.

## 0:22
### Texnik qism
Tizim ikki qatlamdan iborat: FastAPI backend va Streamlit interfeysi, ular orasida oddiy REST chaqiruv orqali gaplashadi. Markazda — LangGraph agenti, u Ollama orqali to'liq lokal LLM'ni ishlatadi, hech qanday bulutli API'ga bog'liq emas. Har bir suhbat burilishida model majburiy ravishda tool chaqirishga undaladi — shunda kichik lokal model to'g'ridan-to'g'ri, ehtimol noto'g'ri javob berib yubormaydi.

Tool'lar haqiqiy saytlarni BeautifulSoup bilan skreyplaydi, natijalar 15 daqiqaga SQLite'da keshlanadi — takroriy so'rovlar tezroq ishlaydi. Va eng muhim qism — grounding safeguard: model natijani og'zaki qayta hikoya qilganda xato qilsa ham, yakuniy javob tool'ning xom JSON natijasidan qayta deterministik tarzda quriladi — foydalanuvchi hech qachon to'qilgan narxni ko'rmaydi.

Ulangan uchta dorixonada topilmagan qo'shimcha, tibbiy bo'lmagan ma'lumot uchun (masalan, ishlab chiqaruvchi qaysi davlatdan) alohida veb-qidiruv tool'i ham bor — lekin narx va mavjudlik hech qachon undan olinmaydi.

## 0:48
### Kuchli tomonlar
Interfeys komponentlarga bo'lingan — sidebar, hero, chat, karta, taqqoslash jadvali, animatsiyalar — har biri alohida modul. Mahsulotlar chiroyli kartalarda chiqadi: narx, brend, doza, qadoq, mavjudlik, va "eng arzon" hamda "eng yaxshi tanlov" (narx/qadoq nisbati bo'yicha hisoblangan) belgilari bilan. Bir nechta mahsulotni tanlab, Compare Prices sahifasida yonma-yon solishtirish mumkin. Va bularning barchasi — Avia AI va UzLaw AI bilan bir xil dizayn tizimida qurilgan, ya'ni uchala mahsulot bitta kompaniyaning mahsulotlari kabi ko'rinadi.

## 0:58
### Kelajak
Keyingi bosqichda price alert qatlamini avtomatik ishga tushiruvchi background job qo'shmoqchiman — narx kerakli darajaga tushganda foydalanuvchiga xabar boradi. Shuningdek, dorixonalar uchun jonli masofa va filial joylashuvini qo'shish, va skreyperlar uchun to'liq test qamrovini yozishni rejalashtiryapman.
