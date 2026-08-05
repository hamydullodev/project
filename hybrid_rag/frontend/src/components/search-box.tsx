"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { ArrowRight, FileText, Loader2, Mic, MicOff, Plus, Search, X } from "lucide-react";

import { useAudioTranscription } from "@/hooks/use-audio-transcription";
import { spawnRipple } from "@/lib/ripple";
import { cn } from "@/lib/utils";

// Mirrors app/ingestion/loaders.py's SUPPORTED_EXTENSIONS on the backend
// (pdf/docx/txt/html) plus common image types for scanned documents (the
// backend's OCR fallback path) — kept here, not imported, since this is a
// static browser `accept` hint, not a contract the backend enforces.
const ACCEPTED_FILE_TYPES = ".pdf,.docx,.txt,.html,.htm,image/*";

interface SearchBoxProps {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit: (value: string) => void;
  loading?: boolean;
  className?: string;
  attachedFile?: File | null;
  onAttachFile?: (file: File | null) => void;
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
export function SearchBox({
  value,
  onValueChange,
  onSubmit,
  loading = false,
  className,
  attachedFile = null,
  onAttachFile,
}: SearchBoxProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [focused, setFocused] = React.useState(false);
  const [isMac, setIsMac] = React.useState(false);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    onAttachFile?.(file);
    // Reset so selecting the same file again still fires onChange.
    event.target.value = "";
  }

  React.useEffect(() => {
    // `navigator` only exists on the client - this is a one-time,
    // mount-only read of a browser API, the same legitimate exception to
    // the "don't setState in an effect" rule documented in
    // theme-toggle.tsx (avoids an SSR/client render mismatch, not a
    // real external-system synchronization case).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMac(/Mac|iPhone|iPad/.test(navigator.platform ?? navigator.userAgent));
  }, []);

  const speech = useAudioTranscription({
    onResult: (transcript) => {
      onValueChange(value ? `${value} ${transcript}` : transcript);
      inputRef.current?.focus();
    },
  });

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
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Hujjat biriktirish"
          title="Hujjat biriktirish (PDF, DOCX, TXT, rasm)"
          className="flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
        >
          <Plus className="size-4" aria-hidden="true" />
        </button>
        {speech.supported ? (
          <button
            type="button"
            onClick={() => (speech.listening ? speech.stop() : speech.start())}
            disabled={speech.transcribing}
            aria-label={speech.listening ? "Ovozli kiritishni to'xtatish" : "Ovoz orqali so'rash"}
            title={
              speech.transcribing
                ? "Matnga o'girilmoqda..."
                : speech.listening
                  ? "Ovozli kiritishni to'xtatish"
                  : "Ovoz orqali so'rash"
            }
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-full border transition-colors",
              "disabled:cursor-not-allowed disabled:opacity-60",
              speech.listening
                ? "border-transparent bg-red-500 text-white"
                : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground",
            )}
          >
            {speech.transcribing ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : speech.listening ? (
              <MicOff className="size-4" aria-hidden="true" />
            ) : (
              <Mic className="size-4" aria-hidden="true" />
            )}
          </button>
        ) : null}
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
          disabled={loading || (!value.trim() && !attachedFile)}
          aria-label="Qidirish"
          onPointerDown={spawnRipple}
          whileHover={loading || (!value.trim() && !attachedFile) ? undefined : { scale: 1.06 }}
          whileTap={loading || (!value.trim() && !attachedFile) ? undefined : { scale: 0.94 }}
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
      {attachedFile ? (
        <div className="mt-2 flex w-fit items-center gap-2 rounded-full border border-border bg-muted/60 py-1 pl-3 pr-1.5 text-sm">
          <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="max-w-48 truncate">{attachedFile.name}</span>
          <button
            type="button"
            onClick={() => onAttachFile?.(null)}
            aria-label="Hujjatni olib tashlash"
            className="flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-border hover:text-foreground"
          >
            <X className="size-3.5" aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </form>
  );
}
