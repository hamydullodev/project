import { SUGGESTIONS } from "@/lib/suggestions";
import { cn } from "@/lib/utils";

interface SuggestionChipsProps {
  onSelect: (query: string) => void;
  className?: string;
}

/** Clicking a chip fills the search AND submits immediately — see suggestions.ts for why these five specific questions. */
export function SuggestionChips({ onSelect, className }: SuggestionChipsProps) {
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-2", className)}>
      {SUGGESTIONS.map(({ icon: Icon, label, query }) => (
        <button
          key={label}
          type="button"
          onClick={() => onSelect(query)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-sm text-foreground/80 transition-all",
            "hover:-translate-y-0.5 hover:border-transparent hover:text-foreground",
            "hover:shadow-[0_0_0_1px_var(--gradient-from),0_6px_16px_-6px_var(--gradient-from)]",
          )}
        >
          <Icon className="size-3.5" aria-hidden="true" />
          {label}
        </button>
      ))}
    </div>
  );
}
