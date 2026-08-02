"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, Check, Clock, Code2, Copy, Eye, FileDown, FileText, Timer } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { copyToClipboard } from "@/lib/clipboard";
import { formatDuration, readingTimeMinutes } from "@/lib/format";
import { spawnRipple } from "@/lib/ripple";
import type { AnalysisInfo, AnalysisStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface DocumentAnalysisCardProps {
  status: AnalysisStatus;
  info: AnalysisInfo | null;
  answer: string;
  errorMessage: string | null;
  askedAt: number | null;
  doneAt: number | null;
  className?: string;
}

function ActionButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      onPointerDown={spawnRipple}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.94 }}
      title={label}
      aria-label={label}
      className="relative flex size-8 items-center justify-center overflow-hidden rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      {children}
    </motion.button>
  );
}

/**
 * The document-analysis counterpart to `result-card.tsx` — same
 * streaming-then-crossfade-to-Markdown rendering and action-bar pattern,
 * but no citation/sources panel (there's no corpus retrieval here, see
 * `api/routers/analyze.py`'s docstring) and no Share/Save actions (both
 * are built around a `?q=` question string / saved query+answer pair
 * that doesn't apply to an uploaded file).
 */
export function DocumentAnalysisCard({
  status,
  info,
  answer,
  errorMessage,
  askedAt,
  doneAt,
  className,
}: DocumentAnalysisCardProps) {
  const [viewMode, setViewMode] = React.useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = React.useState(false);

  if (status === "idle") return null;

  if (status === "error") {
    return (
      <Alert
        variant="destructive"
        className={cn("animate-in fade-in-0 slide-in-from-bottom-2 duration-300", className)}
      >
        <AlertTriangle />
        <AlertTitle>Xatolik yuz berdi</AlertTitle>
        <AlertDescription>{errorMessage}</AlertDescription>
      </Alert>
    );
  }

  if (status === "loading" || (status === "streaming" && answer === "")) {
    return (
      <div
        className={cn(
          "animate-in fade-in-0 flex items-center gap-3 rounded-2xl border border-border bg-card p-5 text-sm text-muted-foreground shadow-sm duration-300",
          className,
        )}
      >
        <FileText className="size-4 shrink-0 animate-pulse" aria-hidden="true" />
        {status === "loading" ? "Hujjat oʻqilmoqda..." : "Hujjat tahlil qilinmoqda..."}
      </div>
    );
  }

  const isDone = status === "done";
  const reading = readingTimeMinutes(answer);
  const responseTime = isDone && askedAt && doneAt ? formatDuration(doneAt - askedAt) : null;

  async function handleCopy() {
    if (await copyToClipboard(answer)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  }

  return (
    <div
      className={cn(
        "print-area animate-in fade-in-0 slide-in-from-bottom-2 rounded-2xl border border-border bg-card p-5 shadow-sm duration-300",
        className,
      )}
    >
      <div className="mb-3 flex items-center gap-2">
        <BrandMark className="size-5" />
        <span className="text-xs font-medium text-muted-foreground">UzLaw AI</span>
        {info ? (
          <span className="ml-1 inline-flex items-center gap-1 truncate rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            <FileText className="size-3 shrink-0" aria-hidden="true" />
            <span className="max-w-40 truncate sm:max-w-64">{info.file_name}</span>
          </span>
        ) : null}
      </div>

      {info && info.warnings.length > 0 ? (
        <p className="mb-3 text-xs text-amber-600 dark:text-amber-400">{info.warnings.join(" ")}</p>
      ) : null}

      <AnimatePresence mode="wait" initial={false}>
        {isDone && viewMode === "rendered" ? (
          <motion.div
            key="rendered"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="markdown-answer prose prose-sm sm:prose-base dark:prose-invert max-w-none"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
          </motion.div>
        ) : (
          <motion.p
            key="raw"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "whitespace-pre-wrap text-[15px] leading-relaxed text-foreground",
              isDone && "font-mono text-[13px]",
            )}
          >
            {answer}
            {status === "streaming" ? (
              <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-foreground/60" />
            ) : null}
          </motion.p>
        )}
      </AnimatePresence>

      {isDone ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3 print:hidden">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
              <Clock className="size-3" aria-hidden="true" />
              {reading} daq oʻqish
            </span>
            {responseTime ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
                <Timer className="size-3" aria-hidden="true" />
                {responseTime}
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-0.5">
            <ActionButton label={copied ? "Nusxalandi!" : "Nusxalash"} onClick={handleCopy}>
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            </ActionButton>
            <ActionButton
              label={viewMode === "rendered" ? "Markdown manbasini koʻrish" : "Formatlangan koʻrinish"}
              onClick={() => setViewMode((v) => (v === "rendered" ? "raw" : "rendered"))}
            >
              {viewMode === "rendered" ? <Code2 className="size-4" /> : <Eye className="size-4" />}
            </ActionButton>
            <ActionButton label="PDF sifatida yuklab olish" onClick={() => window.print()}>
              <FileDown className="size-4" />
            </ActionButton>
          </div>
        </div>
      ) : null}
    </div>
  );
}
