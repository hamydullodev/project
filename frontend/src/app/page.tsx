"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";

import { AnswerPanel } from "@/components/answer-panel";
import { SearchBox } from "@/components/search-box";
import { SuggestionChips } from "@/components/suggestion-chips";
import { useAsk } from "@/hooks/use-ask";
import { cn } from "@/lib/utils";

/**
 * Search-first home experience: logo/title/subtitle/search/chips,
 * vertically centered, and NOTHING else while idle — per the design
 * brief. Submitting a question does not navigate anywhere; the same
 * page re-flows (hero fades out, search box moves to the top, the
 * answer streams in below) rather than routing to a results page.
 */
export default function Home() {
  const [query, setQuery] = React.useState("");
  const { status, answer, sources, answerFound, errorMessage, ask } = useAsk();
  const isActive = status !== "idle";

  function handleAsk(value: string) {
    setQuery(value);
    ask(value);
  }

  return (
    <div
      className={cn(
        "flex w-full flex-1 flex-col items-center px-4",
        isActive ? "pt-10 pb-16" : "justify-center py-10",
      )}
    >
      <div className="w-full max-w-2xl">
        {!isActive ? (
          <div className="mb-8 flex flex-col items-center gap-3 text-center duration-500 animate-in fade-in-0">
            <span
              className="flex size-14 items-center justify-center rounded-2xl text-white shadow-md"
              style={{
                backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))",
              }}
            >
              <Sparkles className="size-7" strokeWidth={2.25} />
            </span>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Qonun AI</h1>
            <p className="max-w-md text-sm text-muted-foreground sm:text-base">
              Oʻzbekiston Respublikasi qonun hujjatlari asosida savollaringizga javob beruvchi
              mahalliy AI yordamchi.
            </p>
          </div>
        ) : null}

        <SearchBox value={query} onValueChange={setQuery} onSubmit={handleAsk} loading={status === "loading"} />

        {!isActive ? (
          <SuggestionChips onSelect={handleAsk} className="mt-5" />
        ) : (
          <AnswerPanel
            status={status}
            answer={answer}
            sources={sources}
            answerFound={answerFound}
            errorMessage={errorMessage}
            className="mt-6"
          />
        )}
      </div>
    </div>
  );
}
