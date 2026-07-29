"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { FileSearch2, Search, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

type Stage = "searching" | "generating";

const STAGES: Record<Stage, { icon: typeof Search; label: string }> = {
  searching: { icon: Search, label: "Qonunlar orasidan qidirilmoqda…" },
  generating: { icon: Sparkles, label: "Manbalar topildi. Javob tayyorlanmoqda…" },
};

const STAGE_ORDER: Stage[] = ["searching", "generating"];

interface RetrievalStepperProps {
  stage: Stage;
  sourceCount?: number;
  className?: string;
}

/**
 * The staged "searching" state shown between submit and the first answer
 * token — replaces a generic skeleton block with real pipeline stages.
 * No fake progress: `stage` is driven directly by `useAsk`'s actual
 * status (`loading` = no sources yet, `streaming` with an empty answer =
 * sources in hand but no tokens yet) — see `page.tsx` for how it derives
 * `stage` from that hook's state.
 */
export function RetrievalStepper({ stage, sourceCount, className }: RetrievalStepperProps) {
  const reduceMotion = useReducedMotion();
  const { icon: Icon, label } = STAGES[stage];
  const stageIndex = STAGE_ORDER.indexOf(stage);

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-2xl border border-border bg-card px-5 py-4 shadow-sm",
        className,
      )}
    >
      <span className="relative flex size-8 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
        <motion.span
          animate={reduceMotion ? undefined : { scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 rounded-xl"
          style={{ backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))", opacity: 0.25 }}
          aria-hidden="true"
        />
        <Icon className="size-4" strokeWidth={2.25} />
      </span>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <AnimatePresence mode="wait">
          <motion.span
            key={stage}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="truncate text-sm text-foreground"
          >
            {stage === "generating" && sourceCount ? (
              <>
                <FileSearch2 className="mr-1 inline size-3.5 -translate-y-px text-muted-foreground" aria-hidden="true" />
                {sourceCount} ta manba topildi — {label}
              </>
            ) : (
              label
            )}
          </motion.span>
        </AnimatePresence>

        <div className="flex gap-1.5" aria-hidden="true">
          {STAGE_ORDER.map((s, i) => (
            <span
              key={s}
              className={cn(
                "h-1 flex-1 rounded-full bg-muted transition-colors duration-300",
                i <= stageIndex && "bg-primary",
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
