import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  glow?: boolean;
}

/**
 * The Qonun AI mark: one integrated glyph, not two emoji side by side.
 *
 * A rounded badge in the app's brand gradient (the same `--gradient-from`/
 * `--gradient-to` tokens every other gradient accent in this app uses, so
 * it always matches) contains a minimal scale-of-justice glyph drawn in
 * the Lucide icon style already used throughout the UI (round caps/joins,
 * ~2.2 stroke weight) so it reads as "part of the same design system,"
 * not an imported stock icon. Uzbekistan is folded in as a small
 * crescent-and-star detail resting above the beam (an abstraction of the
 * flag's crescent+twelve-stars, not a literal flag rectangle glued on)
 * rendered in the flag's blue/green, and a thin blue-to-green arc along
 * the badge's lower edge — a restrained nod, not a second logo competing
 * with the first.
 */
export function BrandMark({ className, glow = false }: BrandMarkProps) {
  return (
    <span className={cn("relative inline-flex shrink-0", className)}>
      {glow ? (
        <span
          aria-hidden="true"
          className="absolute inset-0 -z-10 scale-125 rounded-[28%] opacity-70 blur-xl"
          style={{
            backgroundImage: "linear-gradient(135deg, var(--gradient-from), var(--gradient-to))",
          }}
        />
      ) : null}
      <svg viewBox="0 0 40 40" className="size-full" role="img" aria-label="Qonun AI">
        <defs>
          <linearGradient id="brandBadge" x1="4" y1="2" x2="36" y2="38" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="var(--gradient-from)" />
            <stop offset="100%" stopColor="var(--gradient-to)" />
          </linearGradient>
          <linearGradient id="brandFlagArc" x1="8" y1="34" x2="32" y2="34" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1eb5e0" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>

        <rect x="2" y="2" width="36" height="36" rx="10" fill="url(#brandBadge)" />

        {/* Restrained Uzbekistan-blue-to-green arc along the lower edge */}
        <path
          d="M 9 33.5 Q 20 37.5 31 33.5"
          fill="none"
          stroke="url(#brandFlagArc)"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* Scale of justice, drawn in the app's own icon style */}
        <g fill="none" stroke="#ffffff" strokeWidth="2.15" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="20" cy="10.4" r="1.35" fill="#ffffff" stroke="none" />
          <line x1="20" y1="11.9" x2="20" y2="25.5" />
          <line x1="11.5" y1="14.4" x2="28.5" y2="14.4" />
          <line x1="11.5" y1="14.4" x2="11.5" y2="19.4" />
          <line x1="28.5" y1="14.4" x2="28.5" y2="19.4" />
          <path d="M 8 19.4 Q 11.5 23.4 15 19.4" />
          <path d="M 25 19.4 Q 28.5 23.4 32 19.4" />
          <path d="M 20 25.5 L 15.2 30.2 L 24.8 30.2 Z" />
          <line x1="14" y1="30.6" x2="26" y2="30.6" strokeWidth="2.4" />
        </g>

        {/* Crescent + star, resting above the beam */}
        <g>
          <path
            d="M 24.6 7.3 A 3.1 3.1 0 1 1 24.1 6.1 A 2.35 2.35 0 1 0 24.6 7.3 Z"
            fill="#eafff3"
          />
          <path
            d="M 27.3 6.6 L 27.75 7.55 L 28.75 7.7 L 28 8.4 L 28.2 9.4 L 27.3 8.9 L 26.4 9.4 L 26.6 8.4 L 25.85 7.7 L 26.85 7.55 Z"
            fill="#eafff3"
          />
        </g>
      </svg>
    </span>
  );
}
