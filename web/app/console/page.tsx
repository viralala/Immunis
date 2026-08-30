import type { Metadata } from "next";

import LiveConsole from "@/components/LiveConsole";
import TranscriptViewer from "@/components/TranscriptViewer";
import { Empty, Panel, PanelHeader, Shell, Table, Td } from "@/components/ui";
import { getCases, getDetection, getStream, inr, num, pct, vectorShort } from "@/lib/data";

export const metadata: Metadata = {
  title: "Live Console",
  description:
    "Watch the detector score a replayed transaction stream, with reason codes " +
    "and the decision it would return at authorisation time.",
};

export default async function ConsolePage() {
  const [stream, cases, det] = await Promise.all([
    getStream(), getCases(), getDetection(),
  ]);

  if (!stream.transactions.length) {
    return (
      <Shell>
        <div className="py-16">
          <Empty what="scored transactions" />
        </div>
      </Shell>
    );
  }

  const ev = det?.post_arena ?? det?.baseline;

  return (
    <Shell>
      <div className="border-b border-line py-12 lg:py-16">
        <div className="flex items-baseline gap-4">
          <span className="mono text-[13px] text-mint">05</span>
          <h1 className="mono text-[28px] font-medium leading-tight tracking-tight sm:text-[34px]">
            Live Console
          </h1>
        </div>
        <p className="mt-4 max-w-3xl pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
          A replay of {num(stream.transactions.length)} scored transactions from
          the held-out future slice — fraud over-sampled so the demo is worth
          watching, and the highest-scoring legitimate traffic included so the
          false positives are visible too. Every score, reason code and decision
          shown here came out of the engine; nothing is re-computed in the browser.
        </p>
      </div>

      <section className="py-10">
        <LiveConsole
          transactions={stream.transactions}
          budgetThreshold={ev?.thresholds.budget ?? 0.5}
        />
      </section>

      {det ? (
        <section className="border-t border-line py-10">
          <Panel>
            <PanelHeader
              eyebrow="How a reason code is produced"
              title="Ablation against the deployed scoring function"
              note={det.reason_code_method}
            />
            <p className="max-w-3xl text-[13.5px] leading-relaxed text-fg-muted">
              Not SHAP: substituting the population median and measuring the drop
              is exact with respect to the function actually deployed — including
              the rule and novelty channels, which a tree explainer would silently
              ignore. It is cheap enough to run inline at authorisation time, and
              simple enough to describe to a regulator in one sentence. An alert an
              analyst cannot act on is a cost, not a control.
            </p>
          </Panel>
        </section>
      ) : null}

      {cases.cases.length ? (
        <section className="border-t border-line py-10" id="cases">
          <div className="mb-6 max-w-3xl">
            <div className="eyebrow mb-2">Worked examples</div>
            <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[26px]">
              Case files
            </h2>
            <p className="mt-3 text-[14.5px] leading-relaxed text-fg-muted">
              One case per typology, picked as the highest-value example in the
              test slice rather than the easiest — a case file should show the
              model working, not preening.
            </p>
          </div>

          <Panel className="mb-5">
            <Table
              head={["Typology", "Amount", "Rail", "Score", "Decision", "Family median", "Top reason"]}
            >
              {cases.cases.map((c) => (
                <tr key={c.txn_id}>
                  <Td align="left">
                    <div className="mono text-[11px] text-fg-faint">{c.vector_id}</div>
                    <div className="mt-0.5 text-[12.5px]">{vectorShort(c.vector_id)}</div>
                  </Td>
                  <Td>{inr(c.amount)}</Td>
                  <Td>{c.rail}</Td>
                  <Td className={c.score > 0.5 ? "text-mint" : "text-ember"}>
                    {c.score.toFixed(3)}
                  </Td>
                  <Td>{c.decision.replace("_", "-")}</Td>
                  <Td>{c.family_median_score.toFixed(3)}</Td>
                  <Td align="left">
                    <span className="text-[11.5px] text-fg-muted">
                      {c.reasons[0]?.text ?? "—"}
                    </span>
                  </Td>
                </tr>
              ))}
            </Table>
          </Panel>

          {cases.cases.some((c) => c.episode) ? (
            <TranscriptViewer cases={cases.cases.filter((c) => c.episode)} />
          ) : null}
        </section>
      ) : null}
    </Shell>
  );
}
