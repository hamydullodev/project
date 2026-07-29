import { Settings, SquareCode } from "lucide-react";
import Link from "next/link";

import { AboutDialog } from "@/components/about-dialog";
import { Logo } from "@/components/logo";
import { SavedPanel } from "@/components/saved-panel";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { GITHUB_URL, STREAMLIT_URL } from "@/lib/config";

/**
 * The one persistent chrome element every page sits under (Home, and
 * whatever pages later milestones add) — deliberately minimal, per the
 * design brief: logo, project name, GitHub, settings, theme toggle,
 * about, nothing more.
 *
 * WHY "SETTINGS" LINKS OUT TO STREAMLIT INSTEAD OF A LOCAL PAGE
 * -------------------------------------------------------------------
 * There is no settings page in this frontend (and none is planned per
 * the frontend-rebuild decision: Index management, Retrieval Debug, and
 * Statistics all stay on the Streamlit internal/debug tool). Rather than
 * a dead placeholder button, this deep-links to that tool's own Settings
 * page directly — real, working behavior instead of a stub.
 *
 * WHY `Button render={<Link .../>}`
 * --------------------------------------
 * This shadcn build is Base UI-backed: `render` is how a primitive is
 * told to render AS a different element while keeping its own styling/
 * behavior (see node_modules/@base-ui/react/docs/react/handbook/
 * composition.md) — the Radix-style `asChild` prop doesn't exist here.
 * `Button`'s own classes end up on next/link's rendered `<a>`. Base UI's
 * `Button` also defaults to `nativeButton` (it assumes it's rendering a
 * real `<button>` and warns in the console otherwise, since that changes
 * keyboard/form semantics) — set `nativeButton={false}` whenever `render`
 * points at a link instead.
 *
 * WHY THE GITHUB BUTTON USES A GENERIC ICON, NOT A GITHUB LOGO
 * ------------------------------------------------------------------
 * The installed lucide-react (v1.x) dropped brand/logo icons (GitHub,
 * X/Twitter, etc.) from its core set entirely — confirmed by grepping
 * its exports; only generic "git concept" icons (GitBranch, GitFork,
 * ...) remain, no wordmark/logo. `SquareCode` stands in as a neutral
 * "source code" icon until a dedicated brand-icon package is added.
 */
export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />

        <nav className="flex items-center gap-0.5">
          {GITHUB_URL ? (
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full"
              title="GitHub"
              nativeButton={false}
              render={<Link href={GITHUB_URL} target="_blank" rel="noreferrer" aria-label="GitHub" />}
            >
              <SquareCode className="size-4" />
            </Button>
          ) : null}

          <Button
            variant="ghost"
            size="icon"
            className="rounded-full"
            title="Sozlamalar (ichki boshqaruv paneli)"
            nativeButton={false}
            render={
              <Link
                href={`${STREAMLIT_URL}/settings`}
                target="_blank"
                rel="noreferrer"
                aria-label="Sozlamalar"
              />
            }
          >
            <Settings className="size-4" />
          </Button>

          <SavedPanel />
          <ThemeToggle />
          <AboutDialog />
        </nav>
      </div>
    </header>
  );
}
