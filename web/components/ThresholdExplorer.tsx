"use client";

import { useMemo, useState } from "react";

import { inr, num, pct } from "@/lib/format";
import { LineChart, Legend } from "./charts";
import { Meter, Panel, PanelHeader } from "./ui";

type CostPoint = {
  threshold: number;
  alert_rate: number;
  recall: number;
  precision: number;
  expected_cost: number;
};

/**
 * The operating point is a business decision, not a modelling one, so it gets
 * a control rather than a footnote. Drag the threshold and watch recall,
 * review load and expected cost move together — this is the conversation a
 * fraud strategy team actually has.
 */
export default function ThresholdExplorer({
  curve,
  costModel,
  budgetThreshold,
  costThreshold,
  nTest,
}: {
  curve: CostPoint[];
  costModel: Record<string, number>;
  budgetThreshold: number;
  costThreshold: number;
  nTest: number;
}) {
  const sorted = useMemo(
    () => [...curve].sort((a, b) => a.threshold - b.threshold),
    [curve],
  );
  const defaultIdx = useMemo(() => {
    let best = 0;
    let d = Infinity;
    sorted.forEach((p, i) => {
      const dd = Math.abs(p.threshold - budgetThreshold);
      if (dd < d) {
        d = dd;
        best = i;
      }
    });
    return best;
  }, [sorted, budgetThreshold]);

  const [idx, setIdx] = useState(defaultIdx);
  const p = sorted[Math.min(idx, sorted.length - 1)];
  if (!p) return null;

  const minCost = Math.min(...sorted.map((c) => c.expected_cost));
  const optimal = sorted.find((c) => c.expected_cost === minCost);
  const perDay = Math.round((p.alert_rate * nTest) / 30);

  return (
    <Panel>
      <PanelHeader
        eyebrow="Operating point"
        title="Where you set the threshold is a business decision"
        note="Recall, review load and expected cost move together. The engine picks the cost-optimal point against an explicit cost matrix, and reports the review-budget point next to it — because most institutions are staffed, not optimised."
      />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <div>
          <LineChart
            height={240}
            xDomain={[sorted[0].threshold, sorted[sorted.length - 1].threshold]}
            yDomain={[0, 1.02]}
            formatX={(n) => n.toFixed(2)}
            formatY={(n) => (n * 100).toFixed(0) + "%"}
            series={[
              { name: "recall", color: "mint", points: sorted.map((c) => ({ x: c.threshold, y: c.recall })) },
              { name: "precision", color: "faint", points: sorted.map((c) => ({ x: c.threshold, y: c.precision })) },
              {
                name: "cost",
                color: "ember",
                dashed: true,
                points: sorted.map((c) => ({
                  x: c.threshold,
                  y: c.expected_cost / Math.max(1, Math.max(...sorted.map((s) => s.expected_cost))),
                })),
              },
            ]}
          />
          <Legend
            items={[
              { name: "recall", color: "mint" },
              { name: "precision", color: "faint" },
              { name: "expected cost (normalised)", color: "ember", dashed: true },
            ]}
          />

          <div className="mt-6">
            <label
              htmlFor="threshold-slider"
              className="eyebrow mb-2 block"
            >
              Threshold · {p.threshold.toFixed(4)}
            </label>
            <input
              id="threshold-slider"
              type="range"
              min={0}
              max={sorted.length - 1}
              value={idx}
              onChange={(e) => setIdx(Number(e.target.value))}
              className="w-full accent-[var(--color-mint)]"
            />
            <div className="mono mt-2 flex justify-between text-[11px] text-fg-faint">
              <span>looser · more alerts</span>
              <span>tighter · fewer alerts</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => setIdx(defaultIdx)}
                className="mono rounded-[4px] border border-line px-2.5 py-1.5 text-[11.5px] text-fg-muted transition-colors hover:text-fg"
              >
                review budget ({budgetThreshold.toFixed(3)})
              </button>
              {optimal ? (
                <button
                  onClick={() => setIdx(sorted.indexOf(optimal))}
                  className="mono rounded-[4px] border border-mint-dim/50 bg-mint/[0.08] px-2.5 py-1.5 text-[11.5px] text-mint"
                >
                  cost optimum ({costThreshold.toFixed(3)})
                </button>
              ) : null}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <Readout k="Recall" v={pct(p.recall, 1)} meter={p.recall} tone="mint"
            sub="share of fraudulent transactions stopped" />
          <Readout k="Precision" v={pct(p.precision, 1)} meter={p.precision}
            sub="share of alerts that are genuinely fraud, at simulation prevalence" />
          <Readout k="Alert rate" v={pct(p.alert_rate, 2)} meter={p.alert_rate * 12}
            tone="ember"
            sub={`≈ ${num(Math.round(p.alert_rate * nTest))} alerts on this test slice · ~${num(perDay)}/day at this volume`} />
          <div className="border-t border-line-soft pt-4">
            <div className="eyebrow mb-2">Expected cost at this point</div>
            <div className="mono tnum text-[26px] leading-none">
              {inr(p.expected_cost)}
            </div>
            <p className="mt-2 text-[12px] leading-snug text-fg-faint">
              Missed-fraud loss at {pct(costModel.fraud_loss_ratio, 0)} of value +{" "}
              {inr(costModel.review_cost, false)} per review +{" "}
              {inr(costModel.false_decline_cost, false)} per false decline on the{" "}
              {pct(costModel.decline_share, 0)} of alerts that are hard-declined.
              {optimal && p.expected_cost > minCost ? (
                <>
                  {" "}
                  <span className="text-ember">
                    {inr(p.expected_cost - minCost)} above the optimum.
                  </span>
                </>
              ) : (
                <> This is the optimum.</>
              )}
            </p>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function Readout({
  k, v, sub, meter, tone = "mint",
}: {
  k: string;
  v: string;
  sub: string;
  meter: number;
  tone?: "mint" | "ember";
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="eyebrow">{k}</span>
        <span className="mono tnum text-[18px]">{v}</span>
      </div>
      <div className="mt-1.5">
        <Meter value={Math.min(1, meter)} tone={tone} height={5} />
      </div>
      <p className="mt-1.5 text-[11.5px] leading-snug text-fg-faint">{sub}</p>
    </div>
  );
}
