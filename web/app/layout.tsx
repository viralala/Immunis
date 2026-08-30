import type { Metadata } from "next";
import type { ReactNode } from "react";

import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "IMMUNIS — Adversarial Immune System for Payment Networks",
    template: "%s · IMMUNIS",
  },
  description:
    "A closed-loop red-team / blue-team system for GenAI-era payment fraud: " +
    "identify emerging attack vectors, generate them at high fidelity, and " +
    "detect them — with a red agent that evolves against the live model until " +
    "the model wins. Mastercard Innovation Challenge 2026.",
  applicationName: "IMMUNIS",
  keywords: [
    "payment fraud", "adversarial machine learning", "red team", "GenAI fraud",
    "UPI", "agentic commerce", "Mastercard Innovation Challenge 2026",
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen antialiased">
        <a
          href="#main"
          className="mono sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-[60] focus:rounded focus:bg-mint focus:px-3 focus:py-1.5 focus:text-[13px] focus:text-ink"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
