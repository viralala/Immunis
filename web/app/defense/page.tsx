import type { Metadata } from "next";

import ThresholdExplorer from "@/components/ThresholdExplorer";
import { BarList, Legend, LineChart, ScoreHistogram } from "@/components/charts";
import {
  Badge, Callout, Empty, Panel, PanelHeader, Shell, Stat, Table, Td,
} from "@/components/ui";
import { getDetection, getSimulation, inr, num, pct, vectorShort } from "@/lib/data";

export const metadata: Metadata = {
  title: "Defense Console",
  description:
    "Detection efficacy on a temporal holdout: curves, per-typology recall, " +
    "false positives on benign anomalies, zero-day generalisation and channel ablations.",
};

const BENIGN_LABEL: Record<string, string> = {
  __normal__: "Ordinary legitimate traffic",
  travel: "Genuine travel",
  big_ticket: "Genuine big-ticket purchase",
  new_device: "Device upgrade",
  new_beneficiary: "First payment to a new payee",
  night_activity: "Legitimate late-night payment",
  category_excursion: "Out-of-character category",
  burst: "Retry / split payment burst",
};

export default async function DefensePage() {
  const [det, sim] = await Promise.all([getDetection(), getSimulation()]);

  if (!det) {
    return (
      <Shell>
        <div className="py-16">
          <Empty what="detection results" />
        </div>
      </Shell>
    );
  }

  const ev = det.post_arena ?? det.baseline;
  const op = ev.operating_point;
  const cost = ev.cost_optimal_point;
  const stress = det.narrative_stress_test;
  const novelty = det.novelty_profile;
  const fpRows = Object.entries(ev.false_positives_by_benign_anomaly).sort(
    (a, b) => b[1].false_positive_rate - a[1].false_positive_rate,
  );

  return (
    <Shell>
      {/* header */}
      <div className="border-b border-line py-12 lg:py-16">
        <div className="flex items-baseline gap-4">
          <span className="mono text-[13px] text-mint">03</span>
          <h1 className="mono text-[28px] font-medium leading-tight tracking-tight sm:text-[34px]">
            Defense Console
          </h1>
        </div>
        <p className="mt-4 max-w-3xl pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
          Four channels fused with a noisy-OR: a gradient-boosted model over{" "}
          {sim?.feature_count ?? "~110"} causally-computed features, a graph
          channel for mule structure, an unsupervised novelty channel for strains
          no label describes, and a narrative channel that reads the conversation
          before the payment. The split is temporal, so the model is always
          measured on the future.
        </p>
      </div>

      {/* headline */}
      <section className="border-b border-line py-10">
        <div className="grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-panel p-5">
            <Stat label="ROC-AUC" value={ev.roc_auc.toFixed(4)} accent="mint"
              sub={`PR-AUC ${ev.pr_auc.toFixed(4)} on ${num(ev.n_test)} held-out future transactions`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="Recall" value={pct(op.recall, 1)} accent="mint"
              sub={`${op.tp} of ${op.tp + op.fn} fraudulent transactions caught at a ${pct(op.alert_rate, 1)} alert budget`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="False positive rate" value={pct(op.fpr, 3)}
              sub={`${num(op.fp)} alerts on legitimate traffic — including every benign anomaly`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="Value recall" value={pct(op.value_recall, 1)} accent="mint"
              sub={`${inr(op.value_caught)} of fraudulent value stopped, ${inr(op.value_missed)} missed`} />
          </div>
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <Callout title="Two numbers for precision, because only one of them is honest">
            <p>
              In simulation the fraud rate is {pct(ev.test_fraud_rate, 2)} — hot,
              so that every typology has enough examples to learn from. At that
              prevalence precision is{" "}
              <span className="mono text-fg">{pct(op.precision, 1)}</span>.
            </p>
            <p className="mt-3">
              A real card or UPI portfolio runs nearer{" "}
              {pct(det.realistic_prevalence, 2)}. Bayes-adjusted to that
              prevalence, precision is{" "}
              <span className="mono text-fg">
                {pct(op.precision_at_real_prevalence, 1)}
              </span>{" "}
              — roughly {Math.round(1 / Math.max(0.01, op.precision_at_real_prevalence))}{" "}
              alerts reviewed per fraud found, which is a staffing number a
              real operations team recognises. Reporting only the first figure
              would be flattering and useless.
            </p>
          </Callout>
          <Panel>
            <PanelHeader eyebrow="Calibration" title="Recall at fixed false-positive budgets" />
            <BarList
              items={Object.entries(ev.recall_at_fpr).map(([k, v]) => ({
                label: `FPR ≤ ${(parseFloat(k.replace("fpr_", "")) * 100).toFixed(1)}%`,
                value: v,
              }))}
              max={1}
              format={(n) => pct(n, 1)}
              labelWidth="min-w-[110px]"
            />
            <p className="mt-3 text-[12px] text-fg-faint">
              Brier score {ev.brier.toFixed(5)} — probabilities are isotonically
              calibrated on a held-out temporal slice, so the cost-optimal
              threshold is computed on numbers that mean what they say.
            </p>
          </Panel>
        </div>
      </section>

      {/* curves */}
      <section className="grid gap-5 border-b border-line py-10 lg:grid-cols-3">
        <Panel>
          <PanelHeader eyebrow="Discrimination" title="ROC" />
          <LineChart
            height={230}
            xDomain={[0, 1]}
            yDomain={[0, 1]}
            diagonal
            formatX={(n) => n.toFixed(1)}
            formatY={(n) => n.toFixed(1)}
            series={[{ name: "roc", color: "mint", points: ev.curves.roc }]}
          />
          <div className="mono mt-1 text-[10.5px] text-fg-faint">
            false-positive rate → true-positive rate
          </div>
        </Panel>
        <Panel>
          <PanelHeader eyebrow="At this class imbalance" title="Precision–recall" />
          <LineChart
            height={230}
            xDomain={[0, 1]}
            yDomain={[0, 1]}
            formatX={(n) => n.toFixed(1)}
            formatY={(n) => n.toFixed(1)}
            series={[{ name: "pr", color: "mint", points: ev.curves.pr }]}
          />
          <div className="mono mt-1 text-[10.5px] text-fg-faint">
            recall → precision
          </div>
        </Panel>
        <Panel>
          <PanelHeader eyebrow="Fused score" title="Distribution" />
          <ScoreHistogram
            edges={ev.score_hist.edges}
            fraud={ev.score_hist.fraud}
            legit={ev.score_hist.legit}
            threshold={ev.thresholds.budget}
            height={230}
          />
          <Legend items={[{ name: "fraud", color: "ember" }, { name: "legitimate", color: "faint" }]} />
        </Panel>
      </section>

      {/* threshold explorer */}
      <section className="border-b border-line py-10" id="threshold">
        <ThresholdExplorer
          curve={ev.curves.cost}
          costModel={det.cost_model}
          budgetThreshold={ev.thresholds.budget}
          costThreshold={ev.thresholds.cost_optimal}
          nTest={ev.n_test}
        />
      </section>

      {/* per typology */}
      <section className="grid gap-5 border-b border-line py-10 lg:grid-cols-2" id="per-typology">
        <Panel>
          <PanelHeader
            eyebrow="Detection efficacy"
            title="Recall by typology"
            note="At one shared operating threshold. An average would hide the family you are blind to, so the per-family number is the one that matters."
          />
          <BarList
            items={Object.entries(ev.per_vector)
              .sort((a, b) => a[1].recall - b[1].recall)
              .map(([k, v]) => ({
                label: `${vectorShort(k)}${v.zero_day ? " ◦" : ""}`,
                value: v.recall,
                note: `n=${v.n}`,
                tone: v.recall < 0.85 ? ("ember" as const) : ("mint" as const),
              }))}
            max={1}
            format={(n) => pct(n, 1)}
          />
          <p className="mt-3 text-[12px] text-fg-faint">
            ◦ marks a family held out of training entirely.
          </p>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Where the alerts land"
            title="Per rail"
            note="Alert rate is the share of all traffic on that rail sent for review — a proxy for the operational load each rail creates."
          />
          <Table head={["Rail", "Transactions", "Fraud", "Recall", "Alert rate"]}>
            {Object.entries(ev.per_rail)
              .sort((a, b) => b[1].n - a[1].n)
              .map(([rail, d]) => (
                <tr key={rail}>
                  <Td align="left">
                    <span className="mono text-[12.5px]">{rail}</span>
                  </Td>
                  <Td>{num(d.n)}</Td>
                  <Td>{num(d.fraud)}</Td>
                  <Td className={d.recall < 0.9 ? "text-ember" : "text-mint"}>
                    {d.fraud ? pct(d.recall, 1) : "—"}
                  </Td>
                  <Td>{pct(d.alert_rate, 2)}</Td>
                </tr>
              ))}
          </Table>
        </Panel>
      </section>

      {/* false positives — the honesty section */}
      <section className="border-b border-line py-10" id="false-positives">
        <div className="grid gap-5 lg:grid-cols-[1fr_1.3fr]">
          <div>
            <div className="eyebrow mb-3">The number most demos leave out</div>
            <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[26px]">
              False positives, broken down by <span className="text-mint">what kind
              of legitimate</span> the transaction was.
            </h2>
            <p className="mt-4 text-[14.5px] leading-relaxed text-fg-muted">
              {pct(sim?.summary.benign_anomaly_rate ?? 0, 1)} of legitimate traffic
              in the simulation is deliberately anomalous: real travel, genuine
              first big-ticket purchases, device upgrades, first payments to a new
              landlord. Every one of them mimics a fraud tell.
            </p>
            <p className="mt-4 text-[14.5px] leading-relaxed text-fg-muted">
              A low overall false-positive rate is easy if your legitimate traffic
              is boring. The rate that matters is the one on the hard negatives —
              and it is where our residual errors concentrate, exactly as they do
              in a real portfolio.
            </p>
          </div>
          <Panel>
            <Table head={["Legitimate behaviour", "Transactions", "False-positive rate", "vs baseline"]}>
              {fpRows.map(([k, d]) => {
                const base =
                  ev.false_positives_by_benign_anomaly.__normal__?.false_positive_rate ?? 0;
                const mult = base > 0 ? d.false_positive_rate / base : 0;
                return (
                  <tr key={k}>
                    <Td align="left">
                      <span className={k === "__normal__" ? "text-fg" : "text-fg-muted"}>
                        {BENIGN_LABEL[k] ?? k}
                      </span>
                    </Td>
                    <Td>{num(d.n)}</Td>
                    <Td className={d.false_positive_rate > base * 3 ? "text-ember" : ""}>
                      {pct(d.false_positive_rate, 2)}
                    </Td>
                    <Td className="text-fg-faint">
                      {k === "__normal__" ? "—" : `${mult.toFixed(1)}×`}
                    </Td>
                  </tr>
                );
              })}
            </Table>
          </Panel>
        </div>
      </section>

      {/* zero day */}
      {det.zero_day_journey ? (
        <section className="border-b border-line py-10" id="zero-day">
          <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
            <div>
              <div className="eyebrow mb-3">Cold generalisation</div>
              <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[26px]">
                Zero-day holdout
              </h2>
              <p className="mt-4 text-[14.5px] leading-relaxed text-fg-muted">
                {det.zero_day_journey.explanation}
              </p>
            </div>
            <Panel>
              <Table head={["Held-out family", "Cold start", "After the arena", "Lift"]}>
                {det.zero_day_journey.holdout_families.map((f) => {
                  const b = det.zero_day_journey.before[f];
                  const a = det.zero_day_journey.after[f];
                  return (
                    <tr key={f}>
                      <Td align="left">
                        <span className="mono text-[12.5px]">{vectorShort(f)}</span>
                        <div className="mt-0.5 text-[11.5px] text-fg-faint">{f}</div>
                      </Td>
                      <Td className="text-ember">
                        {typeof b === "number" ? pct(b, 1) : "—"}
                      </Td>
                      <Td className="text-mint">
                        {typeof a === "number" ? pct(a, 1) : "—"}
                      </Td>
                      <Td>
                        {typeof a === "number" && typeof b === "number"
                          ? `${a - b >= 0 ? "+" : ""}${((a - b) * 100).toFixed(1)} pt`
                          : "—"}
                      </Td>
                    </tr>
                  );
                })}
                <tr>
                  <Td align="left">
                    <span className="text-fg-faint">Known families, for reference</span>
                  </Td>
                  <Td colSpan={3}>
                    {det.zero_day.__known_families__?.recall !== undefined &&
                    det.zero_day.__known_families__?.recall !== null
                      ? pct(det.zero_day.__known_families__.recall, 1)
                      : "—"}
                  </Td>
                </tr>
              </Table>
            </Panel>
          </div>
        </section>
      ) : null}

      {/* ablations */}
      <section className="border-b border-line py-10" id="ablations">
        <Panel>
          <PanelHeader
            eyebrow="What each channel is worth"
            title="Ablation study"
            note="Each row is a model retrained from scratch with that channel's features removed. This is the question a bank asks before paying for any of it."
          />
          <Table head={["Channel removed", "Features dropped", "ROC-AUC", "PR-AUC", "Δ PR-AUC", "Recall", "Δ recall"]}>
            <tr>
              <Td align="left">
                <span className="text-fg">Nothing (full model)</span>
              </Td>
              <Td>0</Td>
              <Td>{det.baseline.roc_auc.toFixed(4)}</Td>
              <Td>{det.baseline.pr_auc.toFixed(4)}</Td>
              <Td className="text-fg-faint">—</Td>
              <Td>{pct(det.baseline.operating_point.recall, 1)}</Td>
              <Td className="text-fg-faint">—</Td>
            </tr>
            {Object.entries(det.ablations).map(([tag, a]) => (
              <tr key={tag}>
                <Td align="left">
                  <span className="mono text-[12.5px]">{tag.replace("no_", "")}</span>
                </Td>
                <Td>{a.dropped_features.length}</Td>
                <Td>{a.roc_auc.toFixed(4)}</Td>
                <Td>{a.pr_auc.toFixed(4)}</Td>
                <Td className={a.delta_pr_auc < -0.005 ? "text-ember" : "text-fg-muted"}>
                  {a.delta_pr_auc >= 0 ? "+" : ""}
                  {a.delta_pr_auc.toFixed(4)}
                </Td>
                <Td>{pct(a.recall, 1)}</Td>
                <Td className={a.delta_recall < -0.005 ? "text-ember" : "text-fg-muted"}>
                  {a.delta_recall >= 0 ? "+" : ""}
                  {(a.delta_recall * 100).toFixed(1)} pt
                </Td>
              </tr>
            ))}
          </Table>
          <p className="mt-4 max-w-3xl text-[13px] leading-relaxed text-fg-faint">
            The graph and session channels carry real weight. The narrative
            channel does not move the portfolio number — which is a finding, not
            an omission, and we measured it rather than explaining it away.
          </p>
        </Panel>

        {stress?.sweep?.length ? (
          <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_1.15fr]">
            <div>
              <div className="eyebrow mb-3">A negative result we are keeping</div>
              <h3 className="mono text-[20px] font-medium leading-tight tracking-tight">
                The narrative channel did not earn its place.
              </h3>
              <p className="mt-4 text-[14px] leading-relaxed text-fg-muted">
                Our thesis was that reading the pre-transaction conversation would
                catch coercion payments the transaction side cannot see. At
                portfolio level the ablation says otherwise, so we built the
                experiment that could have rescued it: a high-mimicry operator —
                aged mule beneficiaries, amounts shaped under step-up thresholds,
                the victim taken off screen share before authorising — swept
                across how greedy they are.
              </p>
              <p className="mt-4 text-[14px] leading-relaxed text-fg-muted">
                Even at the low-greed end, where every amount-based signal should
                go quiet, the lift is{" "}
                <span className="mono text-fg">
                  {stress.max_lift !== undefined ? stress.max_lift.toFixed(3) : "0.000"}
                </span>
                . Beneficiary novelty and account age already carry this typology
                in our simulation.
              </p>
              <p className="mt-4 text-[14px] leading-relaxed text-fg-muted">
                We would still ship it — a coercion alert an analyst can justify
                to a regulator is worth more than one they cannot, and the channel
                is the only signal left when session telemetry is missing. But it
                is a design bet, not a measured win, and we are labelling it that
                way.
              </p>
            </div>
            <Panel>
              <PanelHeader
                eyebrow={`n = ${num(stress.n)} generated coercion attacks`}
                title="Narrative lift vs operator greed"
                note={stress.description}
              />
              <Table head={["Aggression", "Mean amount", "Amount z", "With narrative", "Without", "Lift"]}>
                {stress.sweep.map((pt) => (
                  <tr key={pt.aggression}>
                    <Td align="left">
                      <span className="mono">{pt.aggression.toFixed(2)}</span>
                    </Td>
                    <Td>{inr(pt.mean_amount)}</Td>
                    <Td>{pt.mean_amount_z >= 0 ? "+" : ""}{pt.mean_amount_z.toFixed(2)}</Td>
                    <Td className="text-mint">{pct(pt.recall_full, 1)}</Td>
                    <Td>{pct(pt.recall_without_narrative, 1)}</Td>
                    <Td className={pt.lift > 0 ? "text-mint" : "text-fg-faint"}>
                      {pt.lift >= 0 ? "+" : ""}
                      {pt.lift.toFixed(3)}
                    </Td>
                  </tr>
                ))}
              </Table>
            </Panel>
          </div>
        ) : null}

        {novelty ? (
          <Panel className="mt-5">
            <PanelHeader
              eyebrow="Unsupervised channel"
              title="Which strains actually sit outside the legitimate manifold"
              note={`The novelty channel adds nothing when the supervised model already catches everything, so the fair test is whether genuinely unseen strains land in its tail. Legitimate traffic reaches the 99th percentile at ${novelty.legit_p99.toFixed(4)}.`}
            />
            <BarList
              items={Object.entries(novelty.by_family)
                .sort((a, b) => b[1].mean_novelty_percentile - a[1].mean_novelty_percentile)
                .slice(0, 10)
                .map(([k, v]) => ({
                  label: `${vectorShort(k)}${v.zero_day ? " ◦" : ""}`,
                  value: v.mean_novelty_percentile,
                  note: `${pct(v.share_above_legit_p99, 0)} in tail`,
                  tone: v.zero_day ? ("ember" as const) : ("mint" as const),
                }))}
              max={1}
              format={(n) => n.toFixed(3)}
            />
            <p className="mt-3 max-w-3xl text-[12.5px] leading-relaxed text-fg-faint">
              The split result is the honest one: one held-out family sits far
              outside the legitimate manifold and the unsupervised channel sees it
              coming; the other is engineered to look normal and it does not. That
              is precisely the gap the arena exists to close.
            </p>
          </Panel>
        ) : null}
      </section>

      {/* signal + rules */}
      <section className="grid gap-5 py-10 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            eyebrow="Permutation importance on the fused score"
            title="What the model is actually using"
            note="Measured against the fused score, not the GBM alone, so the rule and novelty channels are represented in the attribution."
          />
          <BarList
            items={det.feature_importance.slice(0, 18).map((f) => ({
              label: f.feature,
              value: Math.max(0, f.auc_drop),
            }))}
            format={(n) => n.toFixed(4)}
            labelWidth="min-w-[186px]"
          />
          <p className="mt-3 text-[12px] text-fg-faint">
            Drop in ROC-AUC when the feature is shuffled.
          </p>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="The auditable half of the model"
            title="Rule layer"
            note="High-precision deterministic conjunctions. Every fraud team keeps rules for good reasons: they are auditable, shippable in an afternoon, and a regulator can read them."
          />
          <div className="max-h-[520px] space-y-3 overflow-y-auto pr-1">
            {det.rules.map((r) => (
              <div key={r.code} className="border-b border-line-soft pb-3 last:border-0">
                <div className="flex items-center justify-between gap-3">
                  <span className="mono text-[12px] text-mint">{r.code}</span>
                  <div className="flex items-center gap-2">
                    <Badge tone="dim">{vectorShort(r.vector_hint)}</Badge>
                    <span className="mono tnum text-[11.5px] text-fg-faint">
                      {r.confidence.toFixed(2)}
                    </span>
                  </div>
                </div>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-fg-muted">
                  {r.description}
                </p>
                {ev.channels.rules_fired[r.code] ? (
                  <p className="mono mt-1 text-[11px] text-fg-faint">
                    fired {num(ev.channels.rules_fired[r.code])}× on the test slice
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* cost optimum footnote */}
      <section className="border-t border-line py-10">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Cost-optimal threshold" value={cost.threshold.toFixed(3)}
            sub={`recall ${pct(cost.recall, 1)} · precision ${pct(cost.precision, 1)} · alert rate ${pct(cost.alert_rate, 2)}`} />
          <Stat label="Expected cost there" value={inr(cost.expected_cost)}
            sub={`on ${num(ev.n_test)} transactions, against ${inr(op.expected_cost)} at the review-budget threshold`} />
          <Stat label="Caught only by rules" value={num(ev.channels.fraud_caught_only_by_rules)}
            sub="frauds the supervised model scored below threshold but a deterministic rule caught" />
          <Stat label="Caught only by novelty" value={num(ev.channels.fraud_caught_only_by_novelty)}
            sub="frauds surfaced by the unsupervised channel alone" />
        </div>
        <p className="mt-6 max-w-3xl text-[13px] leading-relaxed text-fg-faint">
          Cost model: {inr(det.cost_model.review_cost, false)} per analyst review,{" "}
          {inr(det.cost_model.false_decline_cost, false)} per false decline,{" "}
          {pct(det.cost_model.fraud_loss_ratio, 0)} of a missed fraud&apos;s value
          borne by the network, {pct(det.cost_model.decline_share, 0)} of alerts
          hard-declined rather than stepped up. Reason codes are produced by
          ablation against the deployed scoring function — see the{" "}
          <a className="text-mint underline underline-offset-2" href="/console">
            live console
          </a>
          .
        </p>
      </section>
    </Shell>
  );
}
