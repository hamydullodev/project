import { AlertTriangle, FileText } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { AskStatus, Source } from "@/lib/types";
import { cn } from "@/lib/utils";

interface AnswerPanelProps {
  status: AskStatus;
  answer: string;
  sources: Source[];
  answerFound: boolean;
  errorMessage: string | null;
  className?: string;
}

/**
 * Minimal-but-real result display for this milestone.
 *
 * WHY THIS DOESN'T RENDER MARKDOWN OR A FULL "RESULT CARD" YET
 * ------------------------------------------------------------------
 * Full markdown rendering (tables, code blocks, callouts — react-
 * markdown + rehype) and the result card's metadata row (reading time,
 * confidence, copy/PDF/share buttons) are their own milestone (4), and
 * a rich, per-source collapsible card with a document preview is
 * Milestone 5's. This milestone's job is proving the end-to-end
 * streaming flow works on one page with no navigation — so the answer
 * renders as plain, whitespace-preserving text and sources as compact
 * badges, both genuinely functional, not a mockup, just not yet the
 * final visual treatment.
 */
export function AnswerPanel({ status, answer, sources, answerFound, errorMessage, className }: AnswerPanelProps) {
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

  return (
    <div className={cn("animate-in fade-in-0 slide-in-from-bottom-2 space-y-4 duration-300", className)}>
      {status === "loading" ? (
        <div className="space-y-2 rounded-2xl border border-border bg-card p-5">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ) : (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          {sources.length > 0 ? (
            <div className="mb-4 flex flex-wrap gap-1.5">
              {sources.map((source) => (
                <Badge key={source.chunk_id} variant="secondary" className="gap-1 font-normal">
                  <FileText className="size-3" aria-hidden="true" />
                  {source.law_name ?? "Nomaʼlum qonun"}
                  {source.article_number ? ` · ${source.article_number}-modda` : ""}
                </Badge>
              ))}
            </div>
          ) : null}

          <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-foreground">
            {answer}
            {status === "streaming" ? (
              <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-foreground/60" />
            ) : null}
          </p>

          {status === "done" && !answerFound ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Bu savol uchun tegishli qonun topilmadi — javob umumiy maʼlumot xarakteriga ega.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
