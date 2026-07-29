"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { ArrowRight, Loader2, Search } from "lucide-react";

import { spawnRipple } from "@/lib/ripple";
import { cn } from "@/lib/utils";

interface SearchBoxProps {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit: (value: string) => void;
  loading?: boolean;
  className?: string;
}

/**
 * The large, centered search input — the whole product's main focus, per
 * the design brief. A few deliberate details:
 *
 * - Global Ctrl+K / Cmd+K focuses it from anywhere on the page (a
 *   command-palette-style convention users of ChatGPT/Linear/Raycast
 *   already expect), shown as a `<kbd>` hint inside the input itself
 *   that hides once the input has content or is focused (it would
 *   otherwise visually collide with what's being typed).
 * - The glow/border on focus uses the theme's gradient tokens
 *   (`--gradient-from`/`--gradient-to`, defined in globals.css) rather
 *   than the plain `--ring` shadcn default, for the specific "premium AI
 *   product" look the brief asks for.
 */
export function SearchBox({ value, onValueChange, onSubmit, loading = false, className }: SearchBoxProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [focused, setFocused] = React.useState(false);
  const [isMac, setIsMac] = React.useState(false);

  React.useEffect(() => {
    // `navigator` only exists on the client - this is a one-time,
    // mount-only read of a browser API, the same legitimate exception to
    // the "don't setState in an effect" rule documented in
    // theme-toggle.tsx (avoids an SSR/client render mismatch, not a
    // real external-system synchronization case).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMac(/Mac|iPhone|iPad/.test(navigator.platform ?? navigator.userAgent));
  }, []);

  React.useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit(value);
  }

  return (
    <form onSubmit={handleSubmit} className={cn("w-full", className)}>
      <div
        className={cn(
          "group relative flex items-center gap-2 rounded-2xl border bg-card px-4 py-3.5 shadow-sm transition-all duration-200",
          "hover:shadow-md",
          focused
            ? "border-transparent shadow-lg ring-2 ring-offset-0"
            : "border-border",
        )}
        style={
          focused
            ? {
                boxShadow: `0 0 0 2px var(--gradient-from), 0 8px 30px -8px var(--gradient-from)`,
              }
            : undefined
        }
      >
        <Search className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Oʻzbekiston qonunlari haqida istalgan narsani soʻrang..."
          aria-label="Savol"
          autoComplete="off"
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground/70 sm:text-lg"
        />
        {!focused && !value ? (
          <kbd className="hidden shrink-0 items-center gap-0.5 rounded-md border border-border bg-muted px-1.5 py-1 font-mono text-xs text-muted-foreground sm:flex">
            {isMac ? "⌘" : "Ctrl"}K
          </kbd>
        ) : null}
        <motion.button
          type="submit"
          disabled={loading || !value.trim()}
          aria-label="Qidirish"
          onPointerDown={spawnRipple}
          whileHover={loading || !value.trim() ? undefined : { scale: 1.06 }}
          whileTap={loading || !value.trim() ? undefined : { scale: 0.94 }}
          className={cn(
            "relative flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-xl text-white transition-all",
            "disabled:cursor-not-allowed disabled:opacity-40",
          )}
          style={{
            backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))",
          }}
        >
          {loading ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight className="size-4" aria-hidden="true" />
          )}
        </motion.button>
      </div>
    </form>
  );
}
