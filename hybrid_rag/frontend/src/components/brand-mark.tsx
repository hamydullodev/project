import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  glow?: boolean;
}

/**
 * The UzLaw AI mark: a circular seal with the Uzbekistan flag (blue /
 * white / green bands, red pinstripes, crescent + stars) filling the
 * badge, and a scales-of-justice emblem — drawn as original line art,
 * not traced from any stock asset — resting on a small ivory medallion
 * in the center so it stays legible against all
 * three flag colors behind it. Wordless by design (no "LAWYER"-style
 * text baked into the mark) so it reads correctly at favicon size too.
 */
export function BrandMark({ className, glow = false }: BrandMarkProps) {
  return (
    <span className={cn("relative inline-flex shrink-0", className)}>
      {glow ? (
        <span
          aria-hidden="true"
          className="absolute inset-0 -z-10 scale-125 rounded-full opacity-70 blur-xl"
          style={{
            backgroundImage: "linear-gradient(135deg, #1eb5e0, #22c55e)",
          }}
        />
      ) : null}
      <svg viewBox="0 0 40 40" className="size-full" role="img" aria-label="UzLaw AI">
        <defs>
          <clipPath id="brandCircleClip">
            <circle cx="20" cy="20" r="19" />
          </clipPath>
          <radialGradient id="brandMedallion" cx="40%" cy="35%" r="70%">
            <stop offset="0%" stopColor="#fffdf6" />
            <stop offset="100%" stopColor="#f1ead8" />
          </radialGradient>
        </defs>

        <g clipPath="url(#brandCircleClip)">
          {/* Uzbekistan flag bands: blue / red / white / red / green */}
          <rect x="0" y="0" width="40" height="15" fill="#1eb5e0" />
          <rect x="0" y="15" width="40" height="1.6" fill="#ce1126" />
          <rect x="0" y="16.6" width="40" height="6.8" fill="#ffffff" />
          <rect x="0" y="23.4" width="40" height="1.6" fill="#ce1126" />
          <rect x="0" y="25" width="40" height="15" fill="#0f9b4f" />

          {/* Crescent + 12 stars, upper-left of the blue band, scaled down */}
          <g transform="translate(3.5 2.5) scale(0.34)">
            <path
              d="M 15 4 A 9 9 0 1 1 14 22 A 6.8 6.8 0 1 0 15 4 Z"
              fill="#ffffff"
            />
            <g fill="#ffffff">
              <circle cx="27" cy="4" r="1.15" />
              <circle cx="33.5" cy="4" r="1.15" />
              <circle cx="40" cy="4" r="1.15" />
              <circle cx="23.5" cy="10" r="1.15" />
              <circle cx="30" cy="10" r="1.15" />
              <circle cx="36.5" cy="10" r="1.15" />
              <circle cx="43" cy="10" r="1.15" />
              <circle cx="19" cy="16" r="1.15" />
              <circle cx="25.5" cy="16" r="1.15" />
              <circle cx="32" cy="16" r="1.15" />
              <circle cx="38.5" cy="16" r="1.15" />
              <circle cx="45" cy="16" r="1.15" />
            </g>
          </g>

          <circle cx="20" cy="20" r="19" fill="none" stroke="#00000022" strokeWidth="0.5" />
        </g>

        {/* Ivory medallion carrying the emblem, so it reads against every flag color behind it */}
        <circle cx="20" cy="21" r="12.5" fill="url(#brandMedallion)" stroke="#ffffff" strokeWidth="0.6" />

        {/* Scales of justice, centered on the medallion */}
        <g fill="none" stroke="#1c2b4a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="20" cy="12.4" r="1" fill="#1c2b4a" stroke="none" />
          <line x1="20" y1="13.4" x2="20" y2="27.5" />
          <line x1="13.5" y1="15.8" x2="26.5" y2="15.8" />
          <line x1="13.5" y1="15.8" x2="13.5" y2="19.8" />
          <line x1="26.5" y1="15.8" x2="26.5" y2="19.8" />
          <path d="M 11 19.8 Q 13.5 22.9 16 19.8" />
          <path d="M 24 19.8 Q 26.5 22.9 29 19.8" />
          <path d="M 20 27.5 L 16.3 30.9 L 23.7 30.9 Z" />
          <line x1="15.3" y1="31.2" x2="24.7" y2="31.2" strokeWidth="1.7" />
        </g>
      </svg>
    </span>
  );
}
