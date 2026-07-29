/**
 * Public, browser-visible configuration.
 *
 * WHY `NEXT_PUBLIC_` PREFIXED ENV VARS
 * -------------------------------------
 * Next.js only inlines env vars prefixed `NEXT_PUBLIC_` into the client
 * bundle at build time — anything else stays server-only, which matters
 * here since these two URLs (the FastAPI backend, the Streamlit debug
 * tool) are read directly in client components (the theme/settings menu,
 * and Milestone 3's search page fetching `/api/ask`).
 *
 * WHY A STREAMLIT URL LIVES HERE AT ALL
 * ----------------------------------------
 * Per the frontend-rebuild decision (Streamlit stays as the internal/
 * debug tool for Index management, Retrieval Debug, and Statistics), the
 * navbar's Settings icon deep-links there rather than to a page that
 * doesn't exist in this new frontend — see `components/navbar.tsx`.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const STREAMLIT_URL =
  process.env.NEXT_PUBLIC_STREAMLIT_URL ?? "http://localhost:8501";

// Unset by default (no public repo yet) - the navbar hides its GitHub
// button entirely rather than linking somewhere broken. Set once the
// project has a real remote.
export const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL;
