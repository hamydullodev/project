import Link from "next/link";

import { BrandMark } from "@/components/brand-mark";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 outline-none">
      <BrandMark className="size-8" />
      <span className="hidden text-sm font-semibold tracking-tight sm:inline">
        UzLaw AI
      </span>
    </Link>
  );
}
