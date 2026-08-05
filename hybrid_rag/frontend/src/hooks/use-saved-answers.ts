"use client";

import * as React from "react";

import {
  getSavedAnswers,
  removeSavedAnswer,
  saveAnswer,
  subscribeSavedAnswers,
  type SavedAnswer,
} from "@/lib/saved-answers";
import type { Source } from "@/lib/types";

/**
 * Reactive view over `lib/saved-answers.ts`'s localStorage list.
 *
 * WHY A `CustomEvent` SUBSCRIPTION RATHER THAN LIFTING STATE TO CONTEXT
 * ------------------------------------------------------------------------
 * Two independent places read this list: the result card's Save button
 * (needs to know if the CURRENT answer is already saved) and the navbar's
 * saved-answers dialog (needs the FULL list). Both call this same hook;
 * `lib/saved-answers.ts` broadcasts a `window` event on every mutation so
 * every mounted instance re-reads storage and re-renders — simpler than
 * introducing a Context provider (and the app-wide re-render that would
 * cause) for one small, infrequently-changing list.
 */
export function useSavedAnswers() {
  const [items, setItems] = React.useState<SavedAnswer[]>([]);

  const refresh = React.useCallback(() => {
    setItems(getSavedAnswers());
  }, []);

  React.useEffect(() => {
    // Initial sync from localStorage (an external system) on mount, then
    // subscribe for further changes — the documented shape for this
    // exception, not a reactive setState loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
    return subscribeSavedAnswers(refresh);
  }, [refresh]);

  const save = React.useCallback((entry: { query: string; answer: string; sources: Source[] }) => {
    return saveAnswer(entry);
  }, []);

  const remove = React.useCallback((id: string) => {
    removeSavedAnswer(id);
  }, []);

  return { items, save, remove };
}
