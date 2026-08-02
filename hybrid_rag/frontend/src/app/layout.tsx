import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Navbar } from "@/components/navbar";
import { ThemeProvider } from "@/components/theme-provider";
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
  title: "UzLaw AI — AI-powered Legal Intelligence for Uzbekistan",
  description:
    "Mahalliy, xavfsiz va oflayn ishlaydigan hybrid RAG tizimi — Oʻzbekiston Respublikasi qonun hujjatlari asosida savollaringizga javob beradi.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning is next-themes' own documented requirement:
    // it sets the `dark` class on <html> via a pre-hydration inline
    // script (to avoid a flash of the wrong theme), which means the
    // server-rendered className and the client's first-paint className
    // legitimately differ for this one attribute — this tells React that
    // mismatch is expected, not a bug to warn about.
    <html lang="uz" suppressHydrationWarning className={`${inter.variable} antialiased`}>
      <body className="min-h-screen bg-background font-sans text-foreground">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <TooltipProvider>
            <Navbar />
            <main className="flex min-h-[calc(100vh-3.5rem)] flex-col">{children}</main>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
