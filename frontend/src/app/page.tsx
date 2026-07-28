import { Sparkles } from "lucide-react";

/**
 * Placeholder — the real search-first home experience (large search box,
 * suggestion chips, in-page streamed answer) is Milestone 3. This
 * milestone's job is the app shell (theme system, navbar) proven out
 * with something real, not the final page content.
 */
export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
      <span
        className="flex size-12 items-center justify-center rounded-2xl text-white shadow-md"
        style={{
          backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))",
        }}
      >
        <Sparkles className="size-6" strokeWidth={2.25} />
      </span>
      <h1 className="text-2xl font-semibold tracking-tight">Qonun AI</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Qidiruv sahifasi (Milestone 3) tez orada — hozircha ilova qobigʻi (navbar, mavzu
        tizimi) tayyor.
      </p>
    </div>
  );
}
