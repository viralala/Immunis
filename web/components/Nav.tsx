"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/atlas", label: "Atlas", n: "01" },
  { href: "/studio", label: "Studio", n: "02" },
  { href: "/defense", label: "Defense", n: "03" },
  { href: "/arena", label: "Arena", n: "04" },
  { href: "/console", label: "Console", n: "05" },
];

export function Mark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      {/* A shield built from a closed loop — the product in one glyph. */}
      <path
        d="M12 2.5 20 5.6v6.1c0 4.6-3.2 8.4-8 9.8-4.8-1.4-8-5.2-8-9.8V5.6L12 2.5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M8.6 12.6a3.4 3.4 0 1 1 1.6 2.9"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M9.4 13.2 8.4 15.8l2.7-.5" fill="none" stroke="currentColor"
        strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ink/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-[1320px] items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <Mark className="h-[22px] w-[22px] text-mint" />
          <span className="mono text-[15px] font-semibold tracking-tight">
            IMMUNIS
            <sup className="ml-0.5 text-[9px] font-normal text-fg-faint">TM</sup>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`mono rounded-[4px] px-3 py-1.5 text-[13px] transition-colors ${
                  active
                    ? "bg-white/[0.07] text-fg"
                    : "text-fg-muted hover:bg-white/[0.04] hover:text-fg"
                }`}
              >
                <span className="mr-1.5 text-[10px] text-fg-faint">{l.n}</span>
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/console"
            className="mono hidden items-center gap-2 rounded-[5px] bg-mint px-3 py-1.5 text-[13px] font-medium text-ink transition-opacity hover:opacity-90 sm:inline-flex"
          >
            Live console
            <span className="kbd border-black/20 bg-black/10 text-ink">L</span>
          </Link>
          <button
            type="button"
            aria-label="Toggle navigation"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="mono rounded-[4px] border border-line px-2.5 py-1.5 text-[12px] text-fg-muted md:hidden"
          >
            {open ? "close" : "menu"}
          </button>
        </div>
      </div>

      {open ? (
        <nav className="border-t border-line bg-surface px-4 py-2 md:hidden">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="mono block px-2 py-2.5 text-[14px] text-fg-muted"
            >
              <span className="mr-2 text-[10px] text-fg-faint">{l.n}</span>
              {l.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}
