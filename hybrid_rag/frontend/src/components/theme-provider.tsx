"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

/**
 * Thin wrapper around next-themes' provider.
 *
 * WHY next-themes AT ALL, RATHER THAN A HAND-ROLLED useState TOGGLE
 * ---------------------------------------------------------------------
 * Three real problems a naive `useState("light")` toggle gets wrong,
 * which next-themes already solves: (1) persisting the choice across
 * reloads (localStorage), (2) respecting the OS-level preference for the
 * "system" option (`prefers-color-scheme`, kept in sync if the OS setting
 * changes while the tab is open), and (3) avoiding a flash of the wrong
 * theme on first paint — next-themes injects a tiny blocking inline
 * script (via `suppressHydrationWarning` on `<html>` in layout.tsx) that
 * sets the `dark` class before React hydrates, so there's no visible
 * flash from "server's guess" to "client's actual preference."
 */
export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
