# UzLaw AI — frontend

Hybrid RAG o'zbek qonunchiligi loyihasining Next.js frontend qismi.
FastAPI backend (`../api/`) bilan HTTP orqali muloqot qiladi; Streamlit
ilova (`../app/ui/`) loyihaning ichki/diagnostika vositasi bo'lib
qoladi (indeks boshqaruvi, qidiruv diagnostikasi, statistika) va
navbar'dagi Sozlamalar belgisi hamda "Loyiha haqida" oynasidan
to'g'ridan-to'g'ri havola qilinadi, bu yerda qayta yozilmaydi.

## O'rnatish

```bash
npm install
cp .env.local.example .env.local   # ikkala backend ham standart bo'lmagan portda ishlasa moslang
npm run dev
```

Joriy navbar/tema qobig'idan tashqari hamma narsa uchun FastAPI
backend ishlab turishi kerak (`cd ../ && python run_api.py`, standart
`http://localhost:8000`), Sozlamalar/"Loyiha haqida" havolalari
ishlashi uchun esa Streamlit diagnostika vositasi ishlab turishi kerak
(loyiha ildizidan `python run.py`, standart `http://localhost:8501`).

## Texnologiyalar

- **Next.js 16** (App Router, Turbopack) + **TypeScript**
- **Tailwind CSS v4** (CSS-birinchi konfiguratsiya — qarang
  `src/app/globals.css`dagi `@theme inline` bloki, `tailwind.config.js`
  emas)
- **shadcn/ui**, Base UI asosida (`@base-ui/react`) — kompozitsiya
  `render` prop orqali, Radix'ning `asChild`i emas; qarang
  `node_modules/@base-ui/react/docs/react/handbook/composition.md` va
  `src/components/navbar.tsx`/`theme-toggle.tsx`dagi izohlarni aniq
  misollar uchun
- **next-themes** — och/qorong'i/tizim mavzulari uchun
- **lucide-react** — belgilar uchun (eslatma: bu asosiy versiya
  GitHub kabi brend/logotip belgilarini o'z yadrosidan olib
  tashlagan — qarang `navbar.tsx`dagi izoh)

## Loyiha tuzilishi

```
frontend/
├── src/
│   ├── app/           # App Router sahifalari, layout, global stillar
│   ├── components/     # Umumiy komponentlar (navbar, tema tugmasi, ...)
│   │   └── ui/           # shadcn tomonidan generatsiya qilingan primitivlar
│   └── lib/            # config.ts (backend manzillari), utils.ts (shadcn'ning cn())
└── .env.local.example
```
