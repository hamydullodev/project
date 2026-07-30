import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Navbar } from "@/components/navbar";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  // Uzbek Latin needs ʻ (U+02BB) and ʼ (U+02BC), both in the Latin
  // Extended-B / Spacing Modifier Letters ranges Inter already covers
  // under the "latin" subset — no extra subset needed.
  display: "swap",
});

export const metadata: Metadata = {
  title: "UzLaw AI — Oʻzbekiston Qonunchiligi boʻyicha AI Yordamchi",
  description:
    "Mahalliy, xavfsiz va oflayn ishlaydigan hybrid RAG tizimi — Oʻzbekiston Respublikasi qonun hujjatlari asosida savollaringizga javob beradi.",
};

// Dark mode only, per the design brief — no toggle, no `prefers-color-scheme`
// branch. The `dark` class is static on `<html>` so there's no client-only
// theme script and nothing to hydrate-mismatch on.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="uz" className={`dark ${inter.variable} antialiased`}>
      <body className="min-h-screen bg-background font-sans text-foreground">
        <TooltipProvider>
          <Navbar />
          <main className="flex min-h-[calc(100vh-3.5rem)] flex-col">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
