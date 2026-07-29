import { Library } from "lucide-react";

import { CitationCard } from "@/components/citation-card";
import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SourcesPanelProps {
  sources: Source[];
  className?: string;
}

/**
 * The right-side sources panel — sticky next to the result card on `md+`
 * screens, and simply the next block in document flow (stacking below
 * the result card) on narrow screens, since `page.tsx`'s single-column
 * grid on mobile puts it there for free with no extra collapse logic.
 */
export function SourcesPanel({ sources, className }: SourcesPanelProps) {
  if (sources.length === 0) return null;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-2 px-1 text-sm font-medium text-foreground">
        <Library className="size-4 text-muted-foreground" aria-hidden="true" />
        Manbalar
        <span className="rounded-full bg-accent px-1.5 py-0.5 text-xs font-normal text-accent-foreground">
          {sources.length}
        </span>
      </div>
      <div className="space-y-2">
        {sources.map((source, index) => (
          <CitationCard key={source.chunk_id} source={source} index={index} />
        ))}
      </div>
    </div>
  );
}
