import type { ReactNode } from "react";

/* Hand-rolled SVG charts.
   No charting dependency: the visual language here is specific (hairline grids,
   mono tick labels, two disciplined accents) and every chart is a static render
   of engine output, so a runtime library would only add weight. */

const MINT = "var(--color-mint)";
const EMBER = "var(--color-ember)";
const LINE = "var(--color-line)";
const FAINT = "var(--color-fg-faint)";

export type Point = { x: number; y: number };

function path(points: Point[], sx: (n: number) => number, sy: (n: number) => number) {
  if (!points.length) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(2)},${sy(p.y).toFixed(2)}`)
    .join(" ");
}

/* -------------------------------------------------------------------------
   Line / curve chart
------------------------------------------------------------------------- */

export function LineChart({
  series,
  width = 640,
  height = 260,
  xLabel,
  yLabel,
  xDomain,
  yDomain,
  xTicks = 5,
  yTicks = 4,
  formatX = (n: number) => String(n),
  formatY = (n: number) => n.toFixed(2),
  diagonal = false,
  area = false,
}: {
  series: { name: string; points: Point[]; color?: "mint" | "ember" | "faint"; dashed?: boolean }[];
  width?: number;
  height?: number;
  xLabel?: string;
  yLabel?: string;
  xDomain?: [number, number];
  yDomain?: [number, number];
  xTicks?: number;
  yTicks?: number;
  formatX?: (n: number) => string;
  formatY?: (n: number) => string;
  diagonal?: boolean;
  area?: boolean;
}) {
  const pad = { l: 46, r: 14, t: 14, b: 30 };
  const all = series.flatMap((s) => s.points);
  if (!all.length) return null;
  const [x0, x1] = xDomain ?? [
    Math.min(...all.map((p) => p.x)),
    Math.max(...all.map((p) => p.x)),
  ];
  const [y0, y1] = yDomain ?? [
    Math.min(0, ...all.map((p) => p.y)),
    Math.max(...all.map((p) => p.y)) * 1.06,
  ];
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const sx = (n: number) => pad.l + ((n - x0) / (x1 - x0 || 1)) * iw;
  const sy = (n: number) => pad.t + ih - ((n - y0) / (y1 - y0 || 1)) * ih;

  const colorOf = (c?: string) =>
    c === "ember" ? EMBER : c === "faint" ? FAINT : MINT;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label={`${yLabel ?? "value"} against ${xLabel ?? "index"}`}
    >
      {/* grid */}
      {Array.from({ length: yTicks + 1 }, (_, i) => {
        const v = y0 + ((y1 - y0) * i) / yTicks;
        return (
          <g key={`y${i}`}>
            <line x1={pad.l} x2={width - pad.r} y1={sy(v)} y2={sy(v)} stroke={LINE} strokeWidth={1} />
            <text
              x={pad.l - 8}
              y={sy(v) + 3.5}
              textAnchor="end"
              fontSize={9.5}
              fill={FAINT}
              fontFamily="var(--font-mono)"
            >
              {formatY(v)}
            </text>
          </g>
        );
      })}
      {Array.from({ length: xTicks + 1 }, (_, i) => {
        const v = x0 + ((x1 - x0) * i) / xTicks;
        return (
          <text
            key={`x${i}`}
            x={sx(v)}
            y={height - 10}
            textAnchor="middle"
            fontSize={9.5}
            fill={FAINT}
            fontFamily="var(--font-mono)"
          >
            {formatX(v)}
          </text>
        );
      })}

      {diagonal ? (
        <line
          x1={sx(x0)}
          y1={sy(y0)}
          x2={sx(x1)}
          y2={sy(y1)}
          stroke={FAINT}
          strokeWidth={1}
          strokeDasharray="3 4"
          opacity={0.5}
        />
      ) : null}

      {series.map((s, i) => {
        const c = colorOf(s.color);
        const d = path(s.points, sx, sy);
        return (
          <g key={i}>
            {area ? (
              <path
                d={`${d} L${sx(s.points[s.points.length - 1].x)},${sy(y0)} L${sx(s.points[0].x)},${sy(y0)} Z`}
                fill={c}
                opacity={0.08}
              />
            ) : null}
            <path
              d={d}
              fill="none"
              stroke={c}
              strokeWidth={1.6}
              strokeDasharray={s.dashed ? "4 3" : undefined}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        );
      })}

      {xLabel ? (
        <text
          x={width - pad.r}
          y={height - 10}
          textAnchor="end"
          fontSize={9.5}
          fill={FAINT}
          fontFamily="var(--font-mono)"
        >
          {xLabel}
        </text>
      ) : null}
    </svg>
  );
}

export function Legend({
  items,
}: {
  items: { name: string; color: "mint" | "ember" | "faint"; dashed?: boolean }[];
}) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5">
      {items.map((it) => (
        <span key={it.name} className="mono flex items-center gap-2 text-[11px] text-fg-muted">
          <span
            className="inline-block h-[2px] w-4"
            style={{
              background:
                it.color === "ember" ? EMBER : it.color === "faint" ? FAINT : MINT,
              opacity: it.dashed ? 0.6 : 1,
            }}
          />
          {it.name}
        </span>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------
   Grouped column chart (arena generations)
------------------------------------------------------------------------- */

export function ColumnPairs({
  groups,
  width = 640,
  height = 230,
  formatValue = (n: number) => (n * 100).toFixed(1) + "%",
  labelA = "A",
  labelB = "B",
}: {
  groups: { label: string; a: number; b: number }[];
  width?: number;
  height?: number;
  formatValue?: (n: number) => string;
  labelA?: string;
  labelB?: string;
}) {
  const pad = { l: 40, r: 12, t: 18, b: 28 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const max = Math.max(0.02, ...groups.flatMap((g) => [g.a, g.b])) * 1.18;
  const gw = iw / Math.max(1, groups.length);
  const bw = Math.min(20, gw * 0.32);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img"
      aria-label={`${labelA} versus ${labelB} by generation`}>
      {[0, 0.5, 1].map((f) => (
        <line
          key={f}
          x1={pad.l}
          x2={width - pad.r}
          y1={pad.t + ih - f * ih}
          y2={pad.t + ih - f * ih}
          stroke={LINE}
        />
      ))}
      {[0, 0.5, 1].map((f) => (
        <text
          key={`t${f}`}
          x={pad.l - 7}
          y={pad.t + ih - f * ih + 3.5}
          textAnchor="end"
          fontSize={9.5}
          fill={FAINT}
          fontFamily="var(--font-mono)"
        >
          {formatValue(max * f)}
        </text>
      ))}
      {groups.map((g, i) => {
        const cx = pad.l + gw * i + gw / 2;
        const ha = (g.a / max) * ih;
        const hb = (g.b / max) * ih;
        return (
          <g key={i}>
            <rect
              x={cx - bw - 2}
              y={pad.t + ih - ha}
              width={bw}
              height={Math.max(1, ha)}
              fill={EMBER}
              opacity={0.85}
            />
            <rect
              x={cx + 2}
              y={pad.t + ih - hb}
              width={bw}
              height={Math.max(1, hb)}
              fill={MINT}
              opacity={0.9}
            />
            <text
              x={cx}
              y={height - 9}
              textAnchor="middle"
              fontSize={9.5}
              fill={FAINT}
              fontFamily="var(--font-mono)"
            >
              {g.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* -------------------------------------------------------------------------
   Score histogram — log counts, fraud vs legitimate
------------------------------------------------------------------------- */

export function ScoreHistogram({
  edges,
  fraud,
  legit,
  threshold,
  width = 640,
  height = 210,
}: {
  edges: number[];
  fraud: number[];
  legit: number[];
  threshold?: number;
  width?: number;
  height?: number;
}) {
  const pad = { l: 40, r: 12, t: 12, b: 26 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const n = Math.min(fraud.length, legit.length);
  const lg = (v: number) => Math.log10(v + 1);
  const max = Math.max(1, ...fraud.map(lg), ...legit.map(lg));
  const bw = iw / n;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img"
      aria-label="Distribution of fused risk scores for fraudulent and legitimate transactions">
      <line x1={pad.l} x2={width - pad.r} y1={pad.t + ih} y2={pad.t + ih} stroke={LINE} />
      {Array.from({ length: n }, (_, i) => {
        const hl = (lg(legit[i]) / max) * ih;
        const hf = (lg(fraud[i]) / max) * ih;
        const x = pad.l + i * bw;
        return (
          <g key={i}>
            <rect x={x} y={pad.t + ih - hl} width={Math.max(1, bw - 1)} height={hl}
              fill={FAINT} opacity={0.55} />
            <rect x={x} y={pad.t + ih - hf} width={Math.max(1, bw - 1)} height={hf}
              fill={EMBER} opacity={0.8} />
          </g>
        );
      })}
      {threshold !== undefined ? (
        <g>
          <line
            x1={pad.l + threshold * iw}
            x2={pad.l + threshold * iw}
            y1={pad.t}
            y2={pad.t + ih}
            stroke={MINT}
            strokeWidth={1.2}
            strokeDasharray="4 3"
          />
          <text
            x={pad.l + threshold * iw + 5}
            y={pad.t + 10}
            fontSize={9.5}
            fill={MINT}
            fontFamily="var(--font-mono)"
          >
            operating threshold
          </text>
        </g>
      ) : null}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <text key={f} x={pad.l + f * iw} y={height - 8} textAnchor="middle"
          fontSize={9.5} fill={FAINT} fontFamily="var(--font-mono)">
          {f.toFixed(2)}
        </text>
      ))}
      <text x={pad.l - 7} y={pad.t + 8} textAnchor="end" fontSize={9}
        fill={FAINT} fontFamily="var(--font-mono)">
        log n
      </text>
    </svg>
  );
}

/* -------------------------------------------------------------------------
   Horizontal bar list
------------------------------------------------------------------------- */

export function BarList({
  items,
  max,
  format = (n: number) => n.toFixed(2),
  tone = "mint",
  labelWidth = "min-w-[168px]",
}: {
  items: { label: string; value: number; note?: ReactNode; tone?: "mint" | "ember" }[];
  max?: number;
  format?: (n: number) => string;
  tone?: "mint" | "ember";
  labelWidth?: string;
}) {
  const m = max ?? Math.max(...items.map((i) => i.value), 1e-9);
  return (
    <div className="space-y-2.5">
      {items.map((it) => {
        const t = it.tone ?? tone;
        return (
          <div key={it.label} className="flex items-center gap-3">
            <div className={`${labelWidth} shrink-0 truncate text-[12.5px] text-fg-muted`}
              title={it.label}>
              {it.label}
            </div>
            <div className="h-[7px] flex-1 overflow-hidden rounded-[2px] bg-white/[0.05]">
              <div
                className={t === "ember" ? "h-full bg-ember" : "h-full bg-mint"}
                style={{ width: `${Math.max(1.5, (it.value / m) * 100)}%` }}
              />
            </div>
            <div className="mono tnum w-[62px] shrink-0 text-right text-[12px] text-fg">
              {format(it.value)}
            </div>
            {it.note ? (
              <div className="w-[70px] shrink-0 text-right text-[11px] text-fg-faint">
                {it.note}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------
   Radar — strain parameter fingerprint
------------------------------------------------------------------------- */

export function Radar({
  axes,
  series,
  size = 240,
}: {
  axes: string[];
  series: { name: string; values: number[]; color: "mint" | "ember" | "faint" }[];
  size?: number;
}) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 34;
  const n = axes.length;
  const pt = (i: number, v: number) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * r * v, cy + Math.sin(a) * r * v] as const;
  };
  const colorOf = (c: string) => (c === "ember" ? EMBER : c === "faint" ? FAINT : MINT);

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[280px]" role="img"
      aria-label="Strain parameter fingerprint">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon
          key={f}
          points={axes.map((_, i) => pt(i, f).join(",")).join(" ")}
          fill="none"
          stroke={LINE}
          strokeWidth={1}
        />
      ))}
      {axes.map((a, i) => {
        const [x, y] = pt(i, 1.16);
        return (
          <g key={a}>
            <line x1={cx} y1={cy} x2={pt(i, 1)[0]} y2={pt(i, 1)[1]} stroke={LINE} />
            <text
              x={x}
              y={y}
              textAnchor={Math.abs(x - cx) < 6 ? "middle" : x > cx ? "start" : "end"}
              dominantBaseline="middle"
              fontSize={8.5}
              fill={FAINT}
              fontFamily="var(--font-mono)"
            >
              {a.slice(0, 9)}
            </text>
          </g>
        );
      })}
      {series.map((s) => (
        <polygon
          key={s.name}
          points={s.values.map((v, i) => pt(i, Math.max(0, Math.min(1, v))).join(",")).join(" ")}
          fill={colorOf(s.color)}
          fillOpacity={0.13}
          stroke={colorOf(s.color)}
          strokeWidth={1.4}
        />
      ))}
    </svg>
  );
}

/* -------------------------------------------------------------------------
   Mule network graph — layered layout
------------------------------------------------------------------------- */

export function NetworkGraph({
  nodes,
  edges,
  width = 660,
  height = 380,
}: {
  nodes: { id: string; layer: number; is_mule: boolean; in_degree: number; out_degree: number; age_days: number | null }[];
  edges: { src: string; dst: string; layer: number; amount: number }[];
  width?: number;
  height?: number;
}) {
  if (!nodes.length) return null;
  // Layer a node by its position in the chain: victims on the left, terminal
  // mules on the right. This is the shape a fraud analyst draws by hand.
  const byLayer = new Map<number, string[]>();
  const nodeLayer = new Map<string, number>();
  const srcSet = new Set(edges.map((e) => e.src));
  const dstSet = new Set(edges.map((e) => e.dst));
  for (const n of nodes) {
    const isSource = srcSet.has(n.id) && !dstSet.has(n.id);
    const l = isSource ? 0 : n.layer + 1;
    nodeLayer.set(n.id, l);
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(n.id);
  }
  const layers = [...byLayer.keys()].sort((a, b) => a - b);
  const pad = 26;
  const colW = (width - pad * 2) / Math.max(1, layers.length - 1 || 1);
  const pos = new Map<string, [number, number]>();
  layers.forEach((l, li) => {
    const ids = byLayer.get(l)!;
    ids.forEach((id, i) => {
      const y = pad + ((i + 0.5) / ids.length) * (height - pad * 2);
      pos.set(id, [layers.length === 1 ? width / 2 : pad + colW * li, y]);
    });
  });
  const maxAmt = Math.max(...edges.map((e) => e.amount), 1);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img"
      aria-label="Mule network: victim inflows fanning into a layered dispersal tree">
      {edges.map((e, i) => {
        const a = pos.get(e.src);
        const b = pos.get(e.dst);
        if (!a || !b) return null;
        const mx = (a[0] + b[0]) / 2;
        return (
          <path
            key={i}
            d={`M${a[0]},${a[1]} C${mx},${a[1]} ${mx},${b[1]} ${b[0]},${b[1]}`}
            fill="none"
            stroke={e.layer === 0 ? FAINT : EMBER}
            strokeWidth={0.6 + (e.amount / maxAmt) * 1.8}
            opacity={0.42}
          />
        );
      })}
      {nodes.map((n) => {
        const p = pos.get(n.id);
        if (!p) return null;
        const deg = n.in_degree + n.out_degree;
        const r = 3 + Math.min(6, Math.sqrt(deg) * 1.5);
        const young = (n.age_days ?? 999) < 15;
        return (
          <circle
            key={n.id}
            cx={p[0]}
            cy={p[1]}
            r={r}
            fill={n.is_mule ? (young ? EMBER : "var(--color-ember-dim)") : "var(--color-fg-faint)"}
            fillOpacity={n.is_mule ? 0.9 : 0.55}
            stroke={n.is_mule ? EMBER : LINE}
            strokeWidth={0.8}
          />
        );
      })}
    </svg>
  );
}
