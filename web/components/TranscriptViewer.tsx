"use client";

import { useState } from "react";

import type { CaseFile } from "@/lib/types";
import { inr, pct, vectorShort } from "@/lib/format";
import { Badge, Panel, PanelHeader } from "./ui";

const SPEAKER_STYLE: Record<string, string> = {
  caller: "border-l-ember text-fg",
  victim: "border-l-line text-fg-muted",
  customer: "border-l-line text-fg-muted",
  payee: "border-l-mint-dim text-fg",
  support: "border-l-mint-dim text-fg",
};

export default function TranscriptViewer({ cases }: { cases: CaseFile[] }) {
  const [i, setI] = useState(0);
  const c = cases[Math.min(i, cases.length - 1)];
  if (!c?.episode) return null;

  return (
    <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
      <div className="space-y-1.5">
        {cases.map((x, idx) => (
          <button
            key={x.txn_id}
            onClick={() => setI(idx)}
            className={`w-full rounded-[5px] border px-3 py-2.5 text-left transition-colors ${
              idx === i
                ? "border-ember-dim/50 bg-ember/[0.07]"
                : "border-line bg-panel hover:bg-panel-2"
            }`}
          >
            <div className="mono text-[11px] text-fg-faint">{x.vector_id}</div>
            <div className="mt-0.5 text-[13px]">{vectorShort(x.vector_id)}</div>
            <div className="mono mt-1 text-[11px] text-fg-faint">
              {x.episode?.kind.replace(/_/g, " ")} · {x.episode?.channel}
            </div>
          </button>
        ))}
      </div>

      <Panel>
        <PanelHeader
          eyebrow={`${c.episode.channel} · ${Math.round(c.episode.duration_s / 60)} minutes on the call`}
          title={vectorShort(c.vector_id)}
          right={
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Badge tone="ember">score {c.score.toFixed(3)}</Badge>
              <Badge tone="dim">{inr(c.amount)}</Badge>
              <Badge tone="dim">{c.rail}</Badge>
            </div>
          }
          note="Generated transcript. The transaction that follows it is technically perfect — right customer, right device, right PIN — which is precisely why the conversation has to be part of the signal."
        />

        <div className="max-h-[420px] space-y-2.5 overflow-y-auto pr-1">
          {c.episode.turns.map((t, idx) => (
            <div
              key={idx}
              className={`border-l-2 pl-3 ${SPEAKER_STYLE[t.speaker] ?? "border-l-line text-fg-muted"}`}
            >
              <div className="mono text-[10.5px] uppercase tracking-[0.1em] text-fg-faint">
                {t.speaker}
              </div>
              <p className="mt-0.5 text-[13.5px] leading-relaxed">{t.text}</p>
            </div>
          ))}
        </div>

        <div className="mt-5 border-t border-line-soft pt-4">
          <div className="eyebrow mb-2.5">Why the model flagged the payment</div>
          <ul className="space-y-1.5">
            {c.reasons.map((r) => (
              <li key={r.feature} className="flex items-start gap-2.5 text-[12.5px]">
                <span className="mono mt-[3px] w-[46px] shrink-0 text-right text-[11px] text-mint">
                  +{r.contribution.toFixed(3)}
                </span>
                <span className="text-fg-muted">{r.text}</span>
              </li>
            ))}
          </ul>
          {c.rules_fired.length ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {c.rules_fired.map((r) => (
                <Badge key={r} tone="mint">
                  {r}
                </Badge>
              ))}
            </div>
          ) : null}
          <p className="mono mt-3 text-[11px] text-fg-faint">
            family median score {c.family_median_score.toFixed(3)} over {c.family_n}{" "}
            test-slice examples · novelty percentile{" "}
            {pct(c.novelty_percentile, 1)}
          </p>
        </div>
      </Panel>
    </div>
  );
}
