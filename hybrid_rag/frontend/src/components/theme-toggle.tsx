"use client";

import * as React from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const THEME_OPTIONS = [
  { value: "light", label: "Yorugʻ", icon: Sun },
  { value: "dark", label: "Qorongʻi", icon: Moon },
  { value: "system", label: "Tizim", icon: Monitor },
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  // next-themes resolves the actual theme only on the client (it depends
  // on localStorage/the OS) - rendering the "real" active icon during SSR
  // would either mismatch the client's first render or briefly flash the
  // wrong icon. A neutral, invisible placeholder icon avoids both until
  // mounted, matching next-themes' own documented pattern for this.
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    // This is the one-time, mount-only signal that we've reached the
    // client and next-themes' resolved `theme` value can now be trusted;
    // there is no external system to "synchronize with" here, and
    // next-themes' own docs recommend exactly this pattern to avoid an
    // SSR/client mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  const ActiveIcon = THEME_OPTIONS.find((option) => option.value === theme)?.icon ?? Monitor;

  return (
    <DropdownMenu>
      {/* This shadcn build is Base UI-backed, not Radix: composition uses
          a `render` prop (the element to render AS) rather than Radix's
          `asChild` - see node_modules/@base-ui/react/docs/react/handbook/
          composition.md. `children` here become the Button's children. */}
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full"
            aria-label="Mavzuni oʻzgartirish"
            title="Mavzu"
          />
        }
      >
        {mounted ? (
          <ActiveIcon className="size-4" />
        ) : (
          <Monitor className="size-4 opacity-0" aria-hidden="true" />
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={theme} onValueChange={setTheme}>
          {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
            <DropdownMenuRadioItem key={value} value={value} className="gap-2">
              <Icon className="size-4" />
              {label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
