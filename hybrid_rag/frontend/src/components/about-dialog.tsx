"use client";

import { Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { STREAMLIT_URL } from "@/lib/config";

export function AboutDialog() {
  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full"
            aria-label="Loyiha haqida"
            title="Loyiha haqida"
          />
        }
      >
        <Info className="size-4" />
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Oʻzbekiston Qonunchiligi boʻyicha AI Yordamchi</DialogTitle>
          <DialogDescription>
            Toʻliq mahalliy (offline) Hybrid RAG tizimi — Oʻzbekiston Respublikasi qonun
            hujjatlari asosida savollaringizga javob beradi. Barcha maʼlumotlar faqat sizning
            kompyuteringizda saqlanadi, hech qanday maʼlumot tashqi serverlarga yuborilmaydi.
          </DialogDescription>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Qidiruv FAISS (dense) va BM25 (sparse) usullarini birlashtirgan hybrid retrieval,
          cross-encoder qayta tartiblash va mahalliy LLM (Ollama) yordamida amalga oshiriladi.
        </p>
        <p className="text-sm text-muted-foreground">
          Indeksni boshqarish, qidiruv tahlili va statistika kabi texnik vositalar{" "}
          <a
            href={STREAMLIT_URL}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary underline underline-offset-4"
          >
            ichki boshqaruv panelida
          </a>{" "}
          mavjud.
        </p>
      </DialogContent>
    </Dialog>
  );
}
