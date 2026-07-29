"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, FileText } from "lucide-react";

import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CitationCardProps {
  source: Source;
  index: number;
}

/** `reranker_score` (the final, post-rerank relevance signal — see `format.ts#confidenceInfo`'s docstring on why it's the one surfaced to users) as a 0-100 integer percentage. */
function relevancePercent(source: Source): number {
  return Math.round(Math.min(1, Math.max(0, source.reranker_score)) * 100);
}

/**
 * One expandable source citation — collapsed shows just the law/article
 * and a relevance bar; expanded reveals the actual retrieved chunk text,
 * so a user can verify the answer against the source themselves instead
 * of trusting a citation blindly.
 */
export function CitationCard({ source, index }: CitationCardProps) {
  const [expanded, setExpanded] = React.useState(false);
  const percent = relevancePercent(source);

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <motion.button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        whileHover={{ backgroundColor: "var(--accent)" }}
        whileTap={{ scale: 0.99 }}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left"
      >
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-accent text-[10px] font-semibold text-accent-foreground">
          {index + 1}
        </span>

        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1 truncate text-[13px] font-medium text-foreground">
            <FileText className="size-3 shrink-0 text-muted-foreground" aria-hidden="true" />
            {source.law_name ?? "Nomaʼlum qonun"}
          </p>
          {source.article_number || source.section ? (
            <p className="truncate text-xs text-muted-foreground">
              {source.article_number ? `${source.article_number}-modda` : null}
              {source.article_number && source.section ? " · " : null}
              {source.section ?? null}
            </p>
          ) : null}
        </div>

        <div className="hidden shrink-0 items-center gap-1.5 sm:flex">
          <div className="h-1.5 w-10 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full"
              style={{
                width: `${percent}%`,
                backgroundImage: "linear-gradient(90deg, var(--gradient-from), var(--gradient-to))",
              }}
            />
          </div>
          <span className="w-8 text-right text-xs tabular-nums text-muted-foreground">{percent}%</span>
        </div>

        <ChevronDown
          className={cn("size-4 shrink-0 text-muted-foreground transition-transform duration-200", expanded && "rotate-180")}
          aria-hidden="true"
        />
      </motion.button>

      <AnimatePresence initial={false}>
        {expanded ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/60 px-3 py-3">
              <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-muted-foreground">{source.text}</p>
              <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground/80">
                {source.page_number ? <span>Sahifa {source.page_number}</span> : null}
                {source.dense_score != null ? <span>Zichlik: {Math.round(source.dense_score * 100)}%</span> : null}
                {source.sparse_score != null ? <span>Siyrak: {Math.round(source.sparse_score * 100)}%</span> : null}
                <span>Birlashgan: {Math.round(source.combined_score * 100)}%</span>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
