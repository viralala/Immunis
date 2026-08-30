"use client";

import { useMemo, useState } from "react";

import type { AtlasData, AttackVector } from "@/lib/types";
import { RAIL_LABEL, SURFACE_LABEL } from "@/lib/format";
import { Badge, Meter } from "./ui";

type SortKey = "threat" | "gap" | "uplift" | "impact";

const PRIORITY_TONE: Record<string, "ember" | "warn" | "neutral" | "dim"> = {
  critical: "ember",
  high: "warn",
  medium: "neutral",
  watch: "dim",
};

export default function AtlasExplorer({ atlas }: { atlas: AtlasData }) {
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState<string | null>(null);
  const [rail, setRail] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("threat");
  const [selected, setSelected] = useState<AttackVector | null>(
    atlas.vectors[0] ?? null,
  );

  const families = useMemo(
    () => [...new Set(atlas.vectors.map((v) => v.family))],
    [atlas.vectors],
  );
  const rails = useMemo(
    () => [...new Set(atlas.vectors.flatMap((v) => v.rails))],
    [atlas.vectors],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const key: Record<SortKey, (v: AttackVector) => number> = {
      threat: (v) => v.threat_score,
      gap: (v) => v.detection_gap * 100 + v.threat_score / 100,
      uplift: (v) => v.genai_uplift * 100 + v.threat_score / 100,
      impact: (v) => v.impact * 100 + v.threat_score / 100,
    };
    return atlas.vectors
      .filter((v) => (family ? v.family === family : true))
      .filter((v) => (rail ? v.rails.includes(rail) : true))
      .filter((v) => (status ? v.status === status : true))
      .filter((v) =>
        q
          ? (v.name + v.id + v.summary + v.observable_signals.join(" "))
              .toLowerCase()
              .includes(q)
          : true,
      )
      .sort((a, b) => key[sort](b) - key[sort](a));
  }, [atlas.vectors, query, family, rail, status, sort]);

  return (
    <div className="py-10">
      {/* controls */}
      <div className="mb-6 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search vectors, signals, summaries…"
            className="mono w-full max-w-[320px] rounded-[5px] border border-line bg-panel px-3 py-2 text-[13px] text-fg placeholder:text-fg-faint"
            aria-label="Search the atlas"
          />
          <div className="flex items-center gap-1.5">
            {(["threat", "gap", "uplift", "impact"] as SortKey[]).map((k) => (
              <button
                key={k}
                onClick={() => setSort(k)}
                className={`mono rounded-[4px] border px-2.5 py-1.5 text-[11.5px] transition-colors ${
                  sort === k
                    ? "border-mint-dim/50 bg-mint/[0.08] text-mint"
                    : "border-line text-fg-muted hover:text-fg"
                }`}
              >
                sort: {k}
              </button>
            ))}
          </div>
          <span className="mono ml-auto text-[12px] text-fg-faint">
            {filtered.length} / {atlas.vectors.length}
          </span>
        </div>

        <FilterRow label="family" value={family} onChange={setFamily} options={families} />
        <FilterRow
          label="rail"
          value={rail}
          onChange={setRail}
          options={rails}
          render={(r) => RAIL_LABEL[r] ?? r}
        />
        <FilterRow
          label="status"
          value={status}
          onChange={setStatus}
          options={["simulated", "documented", "discovered"]}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
        {/* list */}
        <div className="max-h-[76vh] overflow-y-auto border border-line">
          <table className="w-full border-collapse text-[13px]">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr className="border-b border-line">
                <th className="eyebrow px-3 py-2.5 text-left">Vector</th>
                <th className="eyebrow px-3 py-2.5 text-right">Gap</th>
                <th className="eyebrow px-3 py-2.5 text-right">Uplift</th>
                <th className="eyebrow px-3 py-2.5 text-right">Threat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {filtered.map((v) => {
                const active = selected?.id === v.id;
                return (
                  <tr
                    key={v.id}
                    onClick={() => setSelected(v)}
                    className={`cursor-pointer transition-colors ${
                      active ? "bg-white/[0.05]" : "hover:bg-white/[0.025]"
                    }`}
                  >
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="mono text-[11px] text-fg-faint">{v.id}</span>
                        {v.status === "simulated" ? (
                          <span className="h-1.5 w-1.5 rounded-full bg-mint" title="has a generator" />
                        ) : null}
                        {v.status === "discovered" ? (
                          <span className="h-1.5 w-1.5 rounded-full bg-ember" title="discovered composite" />
                        ) : null}
                      </div>
                      <div className="mt-0.5 max-w-[30ch] truncate text-fg sm:max-w-[46ch]">
                        {v.name}
                      </div>
                    </td>
                    <td className="mono tnum px-3 py-2.5 text-right text-fg-muted">
                      {v.detection_gap}
                    </td>
                    <td className="mono tnum px-3 py-2.5 text-right text-fg-muted">
                      {v.genai_uplift}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="mono tnum text-fg">{v.threat_score}</div>
                      <div className="ml-auto mt-1 w-16">
                        <Meter
                          value={v.threat_score / 100}
                          height={3}
                          tone={v.priority === "critical" ? "ember" : "mint"}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!filtered.length ? (
                <tr>
                  <td colSpan={4} className="px-3 py-10 text-center text-fg-faint">
                    Nothing matches those filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {/* detail */}
        <div className="lg:sticky lg:top-20 lg:self-start">
          {selected ? <VectorDetail v={selected} /> : null}
        </div>
      </div>
    </div>
  );
}

function FilterRow({
  label, value, onChange, options, render,
}: {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  options: string[];
  render?: (v: string) => string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="eyebrow mr-1 w-12 shrink-0">{label}</span>
      <button
        onClick={() => onChange(null)}
        className={`mono rounded-[4px] border px-2 py-1 text-[11.5px] transition-colors ${
          value === null
            ? "border-line bg-white/[0.06] text-fg"
            : "border-line-soft text-fg-faint hover:text-fg-muted"
        }`}
      >
        all
      </button>
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(value === o ? null : o)}
          className={`mono rounded-[4px] border px-2 py-1 text-[11.5px] transition-colors ${
            value === o
              ? "border-mint-dim/50 bg-mint/[0.08] text-mint"
              : "border-line-soft text-fg-faint hover:text-fg-muted"
          }`}
        >
          {render ? render(o) : o}
        </button>
      ))}
    </div>
  );
}

function VectorDetail({ v }: { v: AttackVector }) {
  const scales: [string, number][] = [
    ["Detection gap", v.detection_gap],
    ["GenAI uplift", v.genai_uplift],
    ["Impact", v.impact],
    ["Scale velocity", v.scale_velocity],
    ["Feasibility", v.feasibility],
  ];
  return (
    <div className="max-h-[76vh] overflow-y-auto border border-line bg-panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mono text-[11px] text-fg-faint">{v.id}</div>
          <h2 className="mono mt-1 text-[16px] font-medium leading-snug">{v.name}</h2>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Badge tone={PRIORITY_TONE[v.priority]}>{v.priority}</Badge>
          <div className="mono text-[20px] leading-none">{v.threat_score}</div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge tone={v.status === "simulated" ? "mint" : v.status === "discovered" ? "ember" : "dim"}>
          {v.status}
        </Badge>
        <Badge tone="dim">{SURFACE_LABEL[v.surface] ?? v.surface}</Badge>
        {v.rails.map((r) => (
          <Badge key={r} tone="dim">
            {RAIL_LABEL[r] ?? r}
          </Badge>
        ))}
      </div>

      <p className="mt-4 text-[13.5px] leading-relaxed text-fg-muted">{v.summary}</p>

      <div className="mt-5 space-y-2">
        {scales.map(([k, n]) => (
          <div key={k} className="flex items-center gap-3">
            <span className="w-[104px] shrink-0 text-[12px] text-fg-faint">{k}</span>
            <Meter value={n / 5} tone={k === "Detection gap" ? "ember" : "mint"} height={5} />
            <span className="mono tnum w-5 shrink-0 text-right text-[12px] text-fg-muted">
              {n}
            </span>
          </div>
        ))}
      </div>

      <Section title="Why GenAI changes this">
        <p className="text-[13px] leading-relaxed text-fg-muted">{v.uplift_note}</p>
      </Section>

      <Section title="Kill chain">
        <ol className="space-y-1.5">
          {v.kill_chain.map((k, i) => (
            <li key={i} className="flex gap-2.5 text-[12.5px] leading-relaxed text-fg-muted">
              <span className="mono shrink-0 text-[10.5px] text-fg-faint">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{k}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Observable signals" accent>
        <ul className="space-y-1.5">
          {v.observable_signals.map((s, i) => (
            <li key={i} className="flex gap-2.5 text-[12.5px] leading-relaxed text-fg-muted">
              <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-mint" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Mitigations">
        <ul className="space-y-1.5">
          {v.mitigations.map((s, i) => (
            <li key={i} className="flex gap-2.5 text-[12.5px] leading-relaxed text-fg-muted">
              <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-fg-faint" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      </Section>

      <div className="mt-5 space-y-2.5 border-t border-line pt-4">
        <Row k="Family" v={v.family} />
        <Row k="Historical analogue" v={v.historical_analogue} />
        <Row k="Who it hits" v={v.victim_profile} />
        {v.parents.length ? <Row k="Composed from" v={v.parents.join(" + ")} /> : null}
        {v.injector ? <Row k="Generator" v={v.injector} /> : null}
        {v.notes ? <Row k="Notes" v={v.notes} /> : null}
      </div>
    </div>
  );
}

function Section({
  title, children, accent = false,
}: {
  title: string;
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="mt-5 border-t border-line-soft pt-4">
      <div className={`eyebrow mb-2.5 ${accent ? "text-mint-dim" : ""}`}>{title}</div>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3 text-[12px]">
      <span className="w-[132px] shrink-0 text-fg-faint">{k}</span>
      <span className="text-fg-muted">{v}</span>
    </div>
  );
}
