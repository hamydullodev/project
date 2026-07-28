import { Sparkles } from "lucide-react";
import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 outline-none">
      <span
        className="flex size-8 shrink-0 items-center justify-center rounded-xl text-white shadow-sm"
        style={{
          backgroundImage:
            "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))",
        }}
      >
        <Sparkles className="size-4" strokeWidth={2.25} />
      </span>
      <span className="hidden text-sm font-semibold tracking-tight sm:inline">
        Qonun AI
      </span>
    </Link>
  );
}
