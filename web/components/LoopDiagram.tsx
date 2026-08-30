/* The closed loop, drawn once and reused.
   Four stages around a cycle: the red half manufactures, the blue half learns,
   and the return edge is the whole point — evasions become training data. */

export default function LoopDiagram({ compact = false }: { compact?: boolean }) {
  const stages = [
    { n: "01", k: "IDENTIFY", d: "map new vectors", tone: "ember" },
    { n: "02", k: "GENERATE", d: "manufacture it", tone: "ember" },
    { n: "03", k: "DEFEND", d: "score and explain", tone: "mint" },
    { n: "04", k: "MINE", d: "evasions to labels", tone: "mint" },
  ] as const;

  return (
    <div className="w-full">
      <svg
        viewBox="0 0 640 200"
        className="w-full"
        role="img"
        aria-label="The IMMUNIS closed loop: identify, generate, defend, mine evasions, and back to identify"
      >
        <defs>
          <marker id="loop-arrow-e" viewBox="0 0 8 8" refX="6" refY="4"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" fill="var(--color-ember)" />
          </marker>
          <marker id="loop-arrow-m" viewBox="0 0 8 8" refX="6" refY="4"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" fill="var(--color-mint)" />
          </marker>
        </defs>

        {stages.map((s, i) => {
          const x = 14 + i * 156;
          const stroke =
            s.tone === "ember" ? "var(--color-ember-dim)" : "var(--color-mint-dim)";
          const fill = s.tone === "ember" ? "var(--color-ember)" : "var(--color-mint)";
          return (
            <g key={s.k}>
              <rect x={x} y={44} width={134} height={62} fill="var(--color-panel)"
                stroke={stroke} strokeWidth={1} rx={2} />
              <text x={x + 12} y={64} fontSize={9.5} fill="var(--color-fg-faint)"
                fontFamily="var(--font-mono)" letterSpacing="1.4">
                {s.n}
              </text>
              <text x={x + 12} y={82} fontSize={12.5} fill={fill}
                fontFamily="var(--font-mono)" letterSpacing="0.8">
                {s.k}
              </text>
              <text x={x + 12} y={97} fontSize={9.5} fill="var(--color-fg-muted)"
                fontFamily="var(--font-mono)">
                {s.d}
              </text>
              {i < stages.length - 1 ? (
                <line
                  x1={x + 136}
                  y1={75}
                  x2={x + 154}
                  y2={75}
                  stroke={i < 2 ? "var(--color-ember)" : "var(--color-mint)"}
                  strokeWidth={1.2}
                  markerEnd={i < 2 ? "url(#loop-arrow-e)" : "url(#loop-arrow-m)"}
                />
              ) : null}
            </g>
          );
        })}

        {/* the return edge — the part the industry does not have */}
        <path
          d="M615,106 L615,150 Q615,164 601,164 L35,164 Q21,164 21,150 L21,108"
          fill="none"
          stroke="var(--color-mint)"
          strokeWidth={1.2}
          strokeDasharray="5 4"
          markerEnd="url(#loop-arrow-m)"
          opacity={0.85}
        />
        <text x={318} y={182} textAnchor="middle" fontSize={10}
          fill="var(--color-mint-dim)" fontFamily="var(--font-mono)">
          every evasion becomes tomorrow&apos;s training label
        </text>

        {!compact ? (
          <>
            <text x={14} y={24} fontSize={9.5} fill="var(--color-ember)"
              fontFamily="var(--font-mono)" letterSpacing="1.6">
              RED TEAM
            </text>
            <text x={326} y={24} fontSize={9.5} fill="var(--color-mint)"
              fontFamily="var(--font-mono)" letterSpacing="1.6">
              BLUE TEAM
            </text>
            <line x1={14} y1={31} x2={304} y2={31} stroke="var(--color-ember-dim)"
              strokeWidth={1} opacity={0.4} />
            <line x1={326} y1={31} x2={616} y2={31} stroke="var(--color-mint-dim)"
              strokeWidth={1} opacity={0.4} />
          </>
        ) : null}
      </svg>
    </div>
  );
}
