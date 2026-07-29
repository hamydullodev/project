import { motion } from "framer-motion";

import { SUGGESTIONS } from "@/lib/suggestions";
import { cn } from "@/lib/utils";

interface SuggestionChipsProps {
  onSelect: (query: string) => void;
  className?: string;
}

const CONTAINER_VARIANTS = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.15 } },
};

const CHIP_VARIANTS = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

/** Clicking a chip fills the search AND submits immediately — see suggestions.ts for why these five specific questions. */
export function SuggestionChips({ onSelect, className }: SuggestionChipsProps) {
  return (
    <motion.div
      variants={CONTAINER_VARIANTS}
      initial="hidden"
      animate="show"
      className={cn("flex flex-wrap items-center justify-center gap-2", className)}
    >
      {SUGGESTIONS.map(({ icon: Icon, label, query }) => (
        <motion.button
          key={label}
          type="button"
          variants={CHIP_VARIANTS}
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onSelect(query)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-sm text-foreground/80 transition-colors",
            "hover:border-transparent hover:text-foreground",
            "hover:shadow-[0_0_0_1px_var(--gradient-from),0_6px_16px_-6px_var(--gradient-from)]",
          )}
        >
          <Icon className="size-3.5" aria-hidden="true" />
          {label}
        </motion.button>
      ))}
    </motion.div>
  );
}
