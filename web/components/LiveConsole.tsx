"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { ScoredTxn } from "@/lib/types";
import { inr, num, pct, RAIL_LABEL, ts, vectorShort } from "@/lib/format";
import { Badge, DecisionPill, Meter, Panel, PanelHeader } from "./ui";

const SPEEDS = [
  { label: "1×", ms: 900 },
  { label: "4×", ms: 260 },
  { label: "12×", ms: 90 },
];

export default function LiveConsole({
  transactions,
  budgetThreshold,
}: {
  transactions: ScoredTxn[];
  budgetThreshold: number;
}) {
  const [cursor, setCursor] = useState(14);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [selected, setSelected] = useState<ScoredTxn | null>(null);
  const [onlyAlerts, setOnlyAlerts] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setCursor((c) => (c >= transactions.length ? c : c + 1));
    }, SPEEDS[speed].ms);
    return () => window.clearInterval(id);
  }, [playing, speed, transactions.length]);

  useEffect(() => {
    if (cursor >= transactions.length) setPlaying(false);
  }, [cursor, transactions.length]);

  const visible = useMemo(() => {
    const slice = transactions.slice(0, cursor).reverse();
    return onlyAlerts ? slice.filter((t) => t.score >= budgetThreshold) : slice;
  }, [transactions, cursor, onlyAlerts, budgetThreshold]);

  const seen = transactions.slice(0, cursor);
  const alerts = seen.filter((t) => t.score >= budgetThreshold);
  const caught = alerts.filter((t) => t.is_fraud === 1).length;
  const missed = seen.filter((t) => t.is_fraud === 1 && t.score < budgetThreshold);
  const detail = selected ?? visible[0] ?? null;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
      {/* stream */}
      <Panel pad={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
          <div className="flex items-center gap-2.5">
            <span
              className={`inline-block h-2 w-2 rounded-full ${playing ? "pulse-dot bg-mint" : "bg-fg-faint"}`}
            />
            <span className="mono text-[13px]">
              {playing ? "streaming" : cursor >= transactions.length ? "replay complete" : "paused"}
            </span>
            <span className="mono tnum text-[12px] text-fg-faint">
              {num(cursor)} / {num(transactions.length)}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => {
                if (cursor >= transactions.length) setCursor(14);
                setPlaying((p) => !p);
              }}
              className="mono rounded-[4px] border border-line px-2.5 py-1.5 text-[11.5px] text-fg-muted transition-colors hover:text-fg"
            >
              {playing ? "pause" : cursor >= transactions.length ? "restart" : "play"}
            </button>
            {SPEEDS.map((s, i) => (
              <button
                key={s.label}
                onClick={() => setSpeed(i)}
                className={`mono rounded-[4px] border px-2 py-1.5 text-[11.5px] transition-colors ${
                  speed === i
                    ? "border-mint-dim/50 bg-mint/[0.08] text-mint"
                    : "border-line text-fg-muted hover:text-fg"
                }`}
              >
                {s.label}
              </button>
            ))}
            <button
              onClick={() => setOnlyAlerts((v) => !v)}
              className={`mono rounded-[4px] border px-2.5 py-1.5 text-[11.5px] transition-colors ${
                onlyAlerts
                  ? "border-ember-dim/50 bg-ember/[0.08] text-ember"
                  : "border-line text-fg-muted hover:text-fg"
              }`}
            >
              alerts only
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 divide-x divide-line border-b border-line sm:grid-cols-4">
          <Tile k="Scored" v={num(cursor)} />
          <Tile k="Alerted" v={num(alerts.length)} sub={pct(alerts.length / Math.max(1, cursor), 1)} />
          <Tile k="Fraud caught" v={num(caught)} tone="mint" />
          <Tile k="Fraud missed" v={num(missed.length)} tone={missed.length ? "ember" : undefined} />
        </div>

        <div ref={listRef} className="max-h-[560px] overflow-y-auto">
          <table className="w-full border-collapse text-[12.5px]">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr className="border-b border-line">
                <th className="eyebrow px-3 py-2 text-left">Time</th>
                <th className="eyebrow px-3 py-2 text-left">Rail</th>
                <th className="eyebrow px-3 py-2 text-right">Amount</th>
                <th className="eyebrow px-3 py-2 text-right">Score</th>
                <th className="eyebrow px-3 py-2 text-right">Decision</th>
                <th className="eyebrow px-3 py-2 text-right">Truth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {visible.slice(0, 140).map((t, i) => {
                const alerted = t.score >= budgetThreshold;
                const isMiss = t.is_fraud === 1 && !alerted;
                const isFp = t.is_fraud === 0 && alerted;
                return (
                  <tr
                    key={t.txn_id}
                    onClick={() => setSelected(t)}
                    className={`cursor-pointer transition-colors ${
                      detail?.txn_id === t.txn_id ? "bg-white/[0.05]" : "hover:bg-white/[0.025]"
                    } ${i === 0 ? "rise" : ""}`}
                  >
                    <td className="mono whitespace-nowrap px-3 py-2 text-fg-faint">
                      {ts(t.ts).slice(5)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-fg-muted">
                      {RAIL_LABEL[t.rail] ?? t.rail}
                    </td>
                    <td className="mono tnum whitespace-nowrap px-3 py-2 text-right">
                      {inr(t.amount)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="mono tnum">{t.score.toFixed(3)}</div>
                      <div className="ml-auto mt-1 w-14">
                        <Meter value={t.score} height={3} tone={alerted ? "ember" : "neutral"} />
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      <DecisionPill decision={t.decision} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      {t.is_fraud ? (
                        <Badge tone={isMiss ? "ember" : "warn"}>
                          {isMiss ? "missed" : "fraud"}
                        </Badge>
                      ) : isFp ? (
                        <Badge tone="neutral">false alert</Badge>
                      ) : (
                        <span className="mono text-[10.5px] text-fg-faint">ok</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* detail */}
      <div className="lg:sticky lg:top-20 lg:self-start">
        {detail ? <Detail t={detail} budgetThreshold={budgetThreshold} /> : null}
      </div>
    </div>
  );
}

function Tile({
  k, v, sub, tone,
}: {
  k: string;
  v: string;
  sub?: string;
  tone?: "mint" | "ember";
}) {
  const color = tone === "mint" ? "text-mint" : tone === "ember" ? "text-ember" : "text-fg";
  return (
    <div className="p-3.5">
      <div className="eyebrow mb-1.5">{k}</div>
      <div className={`mono tnum text-[17px] leading-none ${color}`}>
        {v}
        {sub ? <span className="ml-1.5 text-[11px] text-fg-faint">{sub}</span> : null}
      </div>
    </div>
  );
}

function Detail({ t, budgetThreshold }: { t: ScoredTxn; budgetThreshold: number }) {
  const alerted = t.score >= budgetThreshold;
  return (
    <Panel>
      <PanelHeader
        eyebrow={t.txn_id}
        title={inr(t.amount, false)}
        right={<DecisionPill decision={t.decision} />}
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        <Badge tone="dim">{RAIL_LABEL[t.rail] ?? t.rail}</Badge>
        {t.merchant_category ? <Badge tone="dim">{t.merchant_category}</Badge> : null}
        {t.persona ? <Badge tone="dim">{t.persona.replace(/_/g, " ")}</Badge> : null}
        {t.city ? <Badge tone="dim">{t.city}</Badge> : null}
        {t.is_fraud ? (
          <Badge tone="ember">{vectorShort(t.vector_id)}</Badge>
        ) : t.benign_anomaly ? (
          <Badge tone="warn">benign: {t.benign_anomaly.replace(/_/g, " ")}</Badge>
        ) : (
          <Badge tone="mint">legitimate</Badge>
        )}
      </div>

      <div className="space-y-3 border-y border-line-soft py-4">
        <Channel k="Fused score" v={t.score} tone={alerted ? "ember" : "mint"} />
        <Channel k="Supervised model" v={t.model_score} />
        <Channel k="Novelty percentile" v={t.novelty_percentile} />
        <Channel k="Rule layer" v={t.rule_score} />
      </div>

      <div className="mt-4">
        <div className="eyebrow mb-2.5">Reason codes</div>
        {t.reasons.length ? (
          <ul className="space-y-2.5">
            {t.reasons.map((r) => (
              <li key={r.feature}>
                <div className="flex items-start gap-2.5">
                  <span className="mono tnum mt-[2px] w-[48px] shrink-0 text-right text-[11px] text-mint">
                    +{r.contribution.toFixed(3)}
                  </span>
                  <span className="text-[12.5px] leading-snug text-fg-muted">
                    {r.text}
                  </span>
                </div>
                <div className="mono ml-[58px] mt-0.5 text-[10.5px] text-fg-faint">
                  {r.feature} = {r.value} · population median {r.population_median}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[12.5px] text-fg-faint">
            Nothing moved the score materially — this transaction looks entirely
            ordinary to every channel.
          </p>
        )}
      </div>

      {t.rules_fired.length ? (
        <div className="mt-4 border-t border-line-soft pt-3">
          <div className="eyebrow mb-2">Rules fired</div>
          <div className="flex flex-wrap gap-1.5">
            {t.rules_fired.map((r) => (
              <Badge key={r} tone="mint">
                {r}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mono mt-4 border-t border-line-soft pt-3 text-[10.5px] text-fg-faint">
        customer {t.customer} · {ts(t.ts)} · operating threshold{" "}
        {budgetThreshold.toFixed(3)}
      </p>
    </Panel>
  );
}

function Channel({
  k, v, tone = "neutral",
}: {
  k: string;
  v: number;
  tone?: "mint" | "ember" | "neutral";
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-[12px] text-fg-muted">{k}</span>
        <span className="mono tnum text-[12.5px]">{v.toFixed(4)}</span>
      </div>
      <div className="mt-1">
        <Meter value={v} tone={tone} height={4} />
      </div>
    </div>
  );
}
