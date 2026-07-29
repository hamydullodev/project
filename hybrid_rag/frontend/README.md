# Qonun AI — frontend

Next.js frontend for the Hybrid RAG Uzbek-law project. Talks to the
FastAPI backend (`../api/`) over HTTP; the Streamlit app (`../app/ui/`)
stays as the project's internal/debug tool (Index management, Retrieval
Debug, Statistics) and is linked to directly from the navbar's Settings
icon and the About dialog, not reimplemented here.

## Setup

```bash
npm install
cp .env.local.example .env.local   # adjust if either backend runs on a non-default port
npm run dev
```

Requires the FastAPI backend running for anything beyond the current
navbar/theme shell (`cd ../ && python run_api.py`, default
`http://localhost:8000`), and the Streamlit debug tool running for the
Settings/About links to resolve (`python run.py` from the project root,
default `http://localhost:8501`).

## Stack

- **Next.js 16** (App Router, Turbopack) + **TypeScript**
- **Tailwind CSS v4** (CSS-first config — see `src/app/globals.css`'s
  `@theme inline` block, not a `tailwind.config.js`)
- **shadcn/ui**, Base UI-backed (`@base-ui/react`) — composition uses a
  `render` prop, not Radix's `asChild`; see
  `node_modules/@base-ui/react/docs/react/handbook/composition.md` and
  the comments in `src/components/navbar.tsx`/`theme-toggle.tsx` for
  concrete examples.
- **next-themes** for light/dark/system theming
- **lucide-react** for icons (note: this major version dropped brand/logo
  icons like GitHub's from its core set — see `navbar.tsx`'s comment)

## Project structure

```
frontend/
├── src/
│   ├── app/           # App Router pages, layout, global styles
│   ├── components/     # Shared components (navbar, theme toggle, ...)
│   │   └── ui/           # shadcn-generated primitives
│   └── lib/            # config.ts (backend URLs), utils.ts (shadcn's cn())
└── .env.local.example
```

## Milestones

Built incrementally alongside the FastAPI backend — see the project
root's conversation history / commit log for the milestone-by-milestone
breakdown (scaffold → home/search → answer rendering → sources panel →
history/sidebar → motion & polish).
