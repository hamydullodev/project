"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bookmark, BookmarkX, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useSavedAnswers } from "@/hooks/use-saved-answers";
import { cn } from "@/lib/utils";

/**
 * The navbar's "Saqlanganlar" entry: a self-contained trigger + dialog
 * (same pattern as `about-dialog.tsx`) listing every answer saved via the
 * result card's Save action. Each entry is a frozen snapshot — clicking
 * one expands it inline to show the full saved answer/sources; it never
 * re-queries the backend, since a saved answer is meant to reflect what
 * the model said at save time, not the current index state.
 */
export function SavedPanel() {
  const { items, remove } = useSavedAnswers();
  const [openId, setOpenId] = React.useState<string | null>(null);

  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full"
            aria-label="Saqlangan javoblar"
            title="Saqlangan javoblar"
          />
        }
      >
        <Bookmark className="size-4" />
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Saqlangan javoblar</DialogTitle>
          <DialogDescription>
            Faqat shu brauzerda saqlanadi — hech qanday serverga yuborilmaydi.
          </DialogDescription>
        </DialogHeader>

        {items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
            <BookmarkX className="size-6" aria-hidden="true" />
            Hozircha hech narsa saqlanmagan.
          </div>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => {
              const isOpen = openId === item.id;
              return (
                <li key={item.id} className="rounded-lg border border-border">
                  <div className="flex items-start gap-2 p-3">
                    <button
                      type="button"
                      onClick={() => setOpenId(isOpen ? null : item.id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="line-clamp-2 text-sm font-medium text-foreground">{item.query}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {new Date(item.savedAt).toLocaleString()}
                      </p>
                    </button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                      aria-label="Oʻchirish"
                      title="Oʻchirish"
                      onClick={() => {
                        remove(item.id);
                        if (isOpen) setOpenId(null);
                      }}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                  {isOpen ? (
                    <div
                      className={cn(
                        "markdown-answer prose prose-sm dark:prose-invert max-w-none border-t border-border/60 px-3 py-3 text-[13px]",
                      )}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.answer}</ReactMarkdown>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}
