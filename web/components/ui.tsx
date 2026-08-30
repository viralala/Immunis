import type { ReactNode } from "react";

/* -------------------------------------------------------------------------
   Layout primitives
------------------------------------------------------------------------- */

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1320px] px-4 sm:px-6 lg:px-8">
      {children}
    </div>
  );
}

export function Panel({
  children,
  className = "",
  pad = true,
}: {
  children: ReactNode;
  className?: string;
  pad?: boolean;
}) {
  return (
    <div className={`panel ${pad ? "p-5 sm:p-6" : ""} ${className}`}>{children}</div>
  );
}

export function PanelHeader({
  eyebrow,
  title,
  right,
  note,
}: {
  eyebrow?: string;
  title: string;
  right?: ReactNode;
  note?: string;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        {eyebrow ? <div className="eyebrow mb-1.5">{eyebrow}</div> : null}
        <h3 className="mono text-[15px] font-medium tracking-tight text-fg">
          {title}
        </h3>
        {note ? (
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-fg-muted">
            {note}
          </p>
        ) : null}
      </div>
      {right}
    </div>
  );
}

export function SectionMarker({
  n,
  title,
  lede,
  accent = "mint",
}: {
  n: string;
  title: string;
  lede?: string;
  accent?: "mint" | "ember";
}) {
  const color = accent === "ember" ? "text-ember" : "text-mint";
  return (
    <div className="mb-8 border-t border-line pt-6">
      <div className="flex items-baseline gap-4">
        <span className={`mono text-[13px] tabular-nums ${color}`}>{n}</span>
        <h2 className="mono text-xl font-medium tracking-tight sm:text-2xl">
          {title}
        </h2>
      </div>
      {lede ? (
        <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-fg-muted">
          {lede}
        </p>
      ) : null}
    </div>
  );
}

/* -------------------------------------------------------------------------
   Data display
------------------------------------------------------------------------- */

export function Stat({
  label,
  value,
  sub,
  accent = "none",
  size = "md",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "none" | "mint" | "ember";
  size?: "sm" | "md" | "lg";
}) {
  const color =
    accent === "mint" ? "text-mint" : accent === "ember" ? "text-ember" : "text-fg";
  const sizes = {
    sm: "text-lg",
    md: "text-2xl sm:text-[28px]",
    lg: "text-3xl sm:text-[40px]",
  } as const;
  return (
    <div>
      <div className="eyebrow mb-2">{label}</div>
      <div className={`mono tnum leading-none ${sizes[size]} ${color}`}>{value}</div>
      {sub ? (
        <div className="mt-2 text-[12.5px] leading-snug text-fg-faint">{sub}</div>
      ) : null}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "mint" | "ember" | "warn" | "dim";
}) {
  const tones = {
    neutral: "border-line text-fg-muted bg-white/[0.03]",
    mint: "border-mint-dim/40 text-mint bg-mint/[0.07]",
    ember: "border-ember-dim/40 text-ember bg-ember/[0.07]",
    warn: "border-ember-dim/60 text-ember bg-ember-deep",
    dim: "border-line-soft text-fg-faint bg-transparent",
  } as const;
  return (
    <span
      className={`mono inline-flex items-center gap-1.5 whitespace-nowrap rounded-[3px] border px-1.5 py-[3px] text-[10.5px] uppercase tracking-[0.09em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Meter({
  value,
  tone = "mint",
  height = 6,
  title,
}: {
  value: number;
  tone?: "mint" | "ember" | "neutral";
  height?: number;
  title?: string;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const bg =
    tone === "ember" ? "bg-ember" : tone === "neutral" ? "bg-fg-faint" : "bg-mint";
  return (
    <div
      className="w-full overflow-hidden rounded-[2px] bg-white/[0.06]"
      style={{ height }}
      title={title}
    >
      <div className={`h-full ${bg}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function KeyValue({
  rows,
  dense = false,
}: {
  rows: [string, ReactNode][];
  dense?: boolean;
}) {
  return (
    <dl className="divide-y divide-line-soft">
      {rows.map(([k, v]) => (
        <div
          key={k}
          className={`flex items-baseline justify-between gap-6 ${dense ? "py-1.5" : "py-2.5"}`}
        >
          <dt className="text-[13px] text-fg-muted">{k}</dt>
          <dd className="mono tnum shrink-0 text-[13px] text-fg">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Table({
  head,
  children,
  className = "",
}: {
  head: ReactNode[];
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`-mx-1 overflow-x-auto ${className}`}>
      <table className="w-full min-w-[560px] border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-line">
            {head.map((h, i) => (
              <th
                key={i}
                className={`eyebrow whitespace-nowrap px-3 pb-2.5 ${
                  i === 0 ? "text-left" : "text-right"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line-soft">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({
  children,
  align = "right",
  className = "",
  colSpan,
}: {
  children: ReactNode;
  align?: "left" | "right";
  className?: string;
  colSpan?: number;
}) {
  return (
    <td
      colSpan={colSpan}
      className={`whitespace-nowrap px-3 py-2.5 ${
        align === "left" ? "text-left" : "mono tnum text-right"
      } ${className}`}
    >
      {children}
    </td>
  );
}

export function Callout({
  tone = "mint",
  title,
  children,
}: {
  tone?: "mint" | "ember";
  title: string;
  children: ReactNode;
}) {
  const border = tone === "ember" ? "border-l-ember" : "border-l-mint";
  return (
    <div className={`border border-line border-l-2 ${border} bg-panel p-5`}>
      <div className="mono mb-2 text-[13px] font-medium">{title}</div>
      <div className="text-[13.5px] leading-relaxed text-fg-muted">{children}</div>
    </div>
  );
}

export function DecisionPill({ decision }: { decision: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    approve: { label: "approve", cls: "border-line text-fg-faint" },
    review: { label: "review", cls: "border-mint-dim/40 text-mint-dim" },
    step_up: { label: "step-up", cls: "border-ember-dim/50 text-ember" },
    decline: { label: "decline", cls: "border-ember/70 text-ember bg-ember-deep" },
  };
  const d = map[decision] ?? map.approve;
  return (
    <span
      className={`mono inline-flex rounded-[3px] border px-1.5 py-[2px] text-[10.5px] uppercase tracking-[0.09em] ${d.cls}`}
    >
      {d.label}
    </span>
  );
}

export function Empty({ what }: { what: string }) {
  return (
    <div className="panel p-8 text-center">
      <div className="mono text-[13px] text-fg-muted">No {what} yet.</div>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-fg-faint">
        Run{" "}
        <code className="mono rounded bg-white/[0.06] px-1.5 py-0.5 text-mint">
          python -m immunis.cli run
        </code>{" "}
        in <code className="mono">engine/</code> to generate the artefacts this
        page reads.
      </p>
    </div>
  );
}
