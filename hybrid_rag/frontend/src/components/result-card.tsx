"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  Bookmark,
  Check,
  Clock,
  Code2,
  Copy,
  Eye,
  FileDown,
  Gauge,
  Share2,
  Timer,
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { RetrievalStepper } from "@/components/retrieval-stepper";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useSavedAnswers } from "@/hooks/use-saved-answers";
import { copyToClipboard } from "@/lib/clipboard";
import { confidenceInfo, formatDuration, readingTimeMinutes } from "@/lib/format";
import { spawnRipple } from "@/lib/ripple";
import type { AskStatus, Source } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ResultCardProps {
  status: AskStatus;
  query: string;
  answer: string;
  sources: Source[];
  answerFound: boolean;
  errorMessage: string | null;
  askedAt: number | null;
  doneAt: number | null;
  className?: string;
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  medium: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  low: "bg-muted text-muted-foreground",
};

/** A ghost icon-button with the shared ripple + hover/tap micro-interaction every result-card action uses. */
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
 * The result card — the product's core surface once a question has been
 * asked. While streaming it shows plain, whitespace-preserving text (a
 * blinking cursor at the end) since rendering incomplete Markdown mid-
 * stream can flash broken syntax; once `done`, it crossfades into a real
 * `react-markdown` render. The metadata row and action bar only appear
 * once `done` — none of them (reading time, confidence, response time,
 * copy/markdown/PDF/share/save) make sense against a half-finished answer.
 */
export function ResultCard({
  status,
  query,
  answer,
  sources,
  answerFound,
  errorMessage,
  askedAt,
  doneAt,
  className,
}: ResultCardProps) {
  const [viewMode, setViewMode] = React.useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = React.useState(false);
  const [shared, setShared] = React.useState(false);
  const { items, save, remove } = useSavedAnswers();

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

  if (status === "loading") {
    return <RetrievalStepper stage="searching" className={cn("animate-in fade-in-0 duration-300", className)} />;
  }

  if (status === "streaming" && answer === "") {
    return (
      <RetrievalStepper
        stage="generating"
        sourceCount={sources.length}
        className={cn("animate-in fade-in-0 duration-300", className)}
      />
    );
  }

  const isDone = status === "done";
  const savedEntry = items.find((item) => item.query === query && item.answer === answer);
  const isSaved = Boolean(savedEntry);
  const reading = readingTimeMinutes(answer);
  const confidence = isDone ? confidenceInfo(sources[0]?.reranker_score) : null;
  const responseTime = isDone && askedAt && doneAt ? formatDuration(doneAt - askedAt) : null;

  async function handleCopy() {
    if (await copyToClipboard(answer)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  }

  async function handleShare() {
    const url = new URL(window.location.href);
    url.searchParams.set("q", query);
    if (navigator.share) {
      try {
        await navigator.share({ title: "UzLaw AI", text: query, url: url.toString() });
      } catch {
        // user dismissed the native share sheet — nothing to do
      }
      return;
    }
    if (await copyToClipboard(url.toString())) {
      setShared(true);
      window.setTimeout(() => setShared(false), 1500);
    }
  }

  function handleSaveToggle() {
    if (savedEntry) {
      remove(savedEntry.id);
    } else {
      save({ query, answer, sources });
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
      </div>

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

      {isDone && !answerFound ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Bu savol uchun tegishli qonun topilmadi — javob umumiy maʼlumot xarakteriga ega.
        </p>
      ) : null}

      {isDone ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3 print:hidden">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
              <Clock className="size-3" aria-hidden="true" />
              {reading} daq oʻqish
            </span>
            {confidence ? (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs",
                  CONFIDENCE_STYLES[confidence.level],
                )}
              >
                <Gauge className="size-3" aria-hidden="true" />
                {confidence.label}
              </span>
            ) : null}
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
            <ActionButton label={shared ? "Havola nusxalandi!" : "Ulashish"} onClick={handleShare}>
              {shared ? <Check className="size-4" /> : <Share2 className="size-4" />}
            </ActionButton>
            <ActionButton label={isSaved ? "Saqlangandan olib tashlash" : "Saqlash"} onClick={handleSaveToggle}>
              <Bookmark className="size-4" fill={isSaved ? "currentColor" : "none"} />
            </ActionButton>
          </div>
        </div>
      ) : null}
    </div>
  );
}
