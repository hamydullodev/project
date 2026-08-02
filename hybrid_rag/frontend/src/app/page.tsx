"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { BrandMark } from "@/components/brand-mark";
import { DocumentAnalysisCard } from "@/components/document-analysis-card";
import { ResultCard } from "@/components/result-card";
import { SearchBox } from "@/components/search-box";
import { SourcesPanel } from "@/components/sources-panel";
import { SuggestionChips } from "@/components/suggestion-chips";
import { useAnalyze } from "@/hooks/use-analyze";
import { useAsk } from "@/hooks/use-ask";
import { cn } from "@/lib/utils";

const HERO_VARIANTS = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const ITEM_VARIANTS = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as const } },
};

/** Two large, slow-drifting blurred gradient blobs behind the idle hero — purely decorative, so their drift is skipped for `prefers-reduced-motion` both here (className) and in the underlying CSS keyframes (globals.css belt-and-braces). */
function AmbientBackground({ reduceMotion }: { reduceMotion: boolean | null }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[36rem] overflow-hidden" aria-hidden="true">
      <div
        className={cn("absolute left-1/4 top-8 size-72 rounded-full opacity-30 blur-3xl", !reduceMotion && "animate-ambient-a")}
        style={{ backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))" }}
      />
      <div
        className={cn("absolute right-1/4 top-24 size-80 rounded-full opacity-20 blur-3xl", !reduceMotion && "animate-ambient-b")}
        style={{ backgroundImage: "linear-gradient(135deg, #22c55e, var(--gradient-to))" }}
      />
    </div>
  );
}

/**
 * Search-first home experience: logo/title/subtitle/search/chips,
 * vertically centered, and NOTHING else while idle. Submitting a
 * question does not navigate anywhere; the same page re-flows (hero
 * fades out, search box moves to the top, a two-column grid opens up
 * for the result card + sources panel) via Framer Motion's automatic
 * layout animation (`motion.div layout` — see the width/grid change
 * between the idle and active branches below) rather than an instant
 * CSS-class swap.
 */
export default function Home() {
  const [query, setQuery] = React.useState("");
  const [attachedFile, setAttachedFile] = React.useState<File | null>(null);
  const { status, answer, sources, answerFound, errorMessage, askedAt, doneAt, ask } = useAsk();
  const analysis = useAnalyze();
  const reduceMotion = useReducedMotion();
  // Whichever flow (corpus Q&A vs. single-document analysis) was most
  // recently submitted drives the active view — only one runs at a time
  // (submitting one doesn't cancel the other's request, but the UI only
  // ever shows one result surface, matching "one question/document at a
  // time" being the whole product's interaction model).
  const [mode, setMode] = React.useState<"ask" | "analyze" | null>(null);
  const isActive = mode === "ask" ? status !== "idle" : mode === "analyze" ? analysis.status !== "idle" : false;
  const hasAutoAsked = React.useRef(false);

  function handleAsk(value: string) {
    setQuery(value);
    setMode("ask");
    ask(value);
  }

  function handleSubmit(value: string) {
    if (attachedFile) {
      const file = attachedFile;
      setQuery(value);
      setAttachedFile(null);
      setMode("analyze");
      analysis.analyze(file);
      return;
    }
    handleAsk(value);
  }

  // A shared link (result-card.tsx's Share action appends `?q=`) reopens
  // straight to that answer instead of a blank home page. One-time,
  // mount-only read of `window.location` — the same legitimate client-
  // only-value pattern search-box.tsx's `isMac` detection uses, and
  // avoids the Suspense boundary `useSearchParams()` would require for
  // a value that's only ever read once, on load.
  React.useEffect(() => {
    if (hasAutoAsked.current) return;
    hasAutoAsked.current = true;
    const shared = new URLSearchParams(window.location.search).get("q");
    if (shared && shared.trim()) {
      // One-time sync from the URL (an external system) on initial
      // mount only — the same legitimate exception documented in
      // search-box.tsx's `isMac` detection, not a reactive loop.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuery(shared);
      ask(shared);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative flex w-full flex-1 flex-col items-center px-4 pt-10 pb-16">
      {!isActive ? <AmbientBackground reduceMotion={reduceMotion} /> : null}

      <motion.div layout className={cn("w-full", isActive ? "max-w-5xl" : "max-w-2xl")}>
        <AnimatePresence>
          {!isActive ? (
            <motion.div
              key="hero"
              variants={HERO_VARIANTS}
              initial="hidden"
              animate="show"
              exit={{ opacity: 0, y: -12, transition: { duration: 0.25 } }}
              className="mb-8 flex flex-col items-center gap-3 text-center"
            >
              <motion.div variants={ITEM_VARIANTS}>
                <BrandMark className="size-16" />
              </motion.div>
              <motion.h1 variants={ITEM_VARIANTS} className="text-3xl font-semibold tracking-tight sm:text-4xl">
                UzLaw AI
              </motion.h1>
              <motion.p variants={ITEM_VARIANTS} className="max-w-md text-sm text-muted-foreground sm:text-base">
                Oʻzbekiston Respublikasi qonun hujjatlari asosida savollaringizga javob beruvchi
                mahalliy AI yordamchi.
              </motion.p>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <motion.div
          layout
          className={cn(
            isActive && mode === "ask" && "grid items-start gap-6 md:grid-cols-[1fr_320px] xl:grid-cols-[1fr_380px]",
          )}
        >
          <div className={cn(!isActive && "mx-auto w-full max-w-2xl")}>
            <SearchBox
              value={query}
              onValueChange={setQuery}
              onSubmit={handleSubmit}
              loading={mode === "analyze" ? analysis.status === "loading" : status === "loading"}
              attachedFile={attachedFile}
              onAttachFile={setAttachedFile}
            />

            {!isActive ? (
              <SuggestionChips onSelect={handleAsk} className="mt-5" />
            ) : mode === "analyze" ? (
              <DocumentAnalysisCard
                status={analysis.status}
                info={analysis.info}
                answer={analysis.answer}
                errorMessage={analysis.errorMessage}
                askedAt={analysis.askedAt}
                doneAt={analysis.doneAt}
                className="mt-6"
              />
            ) : (
              <ResultCard
                status={status}
                query={query}
                answer={answer}
                sources={sources}
                answerFound={answerFound}
                errorMessage={errorMessage}
                askedAt={askedAt}
                doneAt={doneAt}
                className="mt-6"
              />
            )}
          </div>

          {isActive && mode === "ask" ? <SourcesPanel sources={sources} className="md:sticky md:top-20" /> : null}
        </motion.div>
      </motion.div>
    </div>
  );
}
