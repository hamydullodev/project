import type { Source } from "@/lib/types";

export interface SavedAnswer {
  id: string;
  query: string;
  answer: string;
  sources: Source[];
  savedAt: number;
}

const STORAGE_KEY = "qonun-ai:saved-answers";
/** Fired on `window` after every mutation so any mounted `useSavedAnswers()` instance re-reads — see that hook's docstring for why this beats a state-management library for one small localStorage-backed list. */
const CHANGE_EVENT = "qonun-ai:saved-answers-changed";

function readAll(): SavedAnswer[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as SavedAnswer[]) : [];
  } catch {
    return [];
  }
}

function writeAll(items: SavedAnswer[]): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function getSavedAnswers(): SavedAnswer[] {
  return readAll().sort((a, b) => b.savedAt - a.savedAt);
}

export function saveAnswer(entry: Omit<SavedAnswer, "id" | "savedAt">): SavedAnswer {
  const saved: SavedAnswer = { ...entry, id: crypto.randomUUID(), savedAt: Date.now() };
  writeAll([...readAll(), saved]);
  return saved;
}

export function removeSavedAnswer(id: string): void {
  writeAll(readAll().filter((item) => item.id !== id));
}

export function subscribeSavedAnswers(callback: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(CHANGE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
