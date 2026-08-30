import type { Metadata } from "next";

import StrainLab from "@/components/StrainLab";
import TranscriptViewer from "@/components/TranscriptViewer";
import { BarList, NetworkGraph } from "@/components/charts";
import {
  Badge, Callout, Empty, KeyValue, Panel, PanelHeader, Shell, Stat, Table, Td,
} from "@/components/ui";
import {
  getAtlas, getCases, getGraph, getSimulation, inr, num, pct, RAIL_LABEL, vectorShort,
} from "@/lib/data";

export const metadata: Metadata = {
  title: "Simulation Studio",
  description:
    "How IMMUNIS manufactures attacks: the base population, the strain parameters, " +
    "the conversations, and the mule graph.",
};

const BENIGN_LABEL: Record<string, string> = {
  travel: "Genuine travel",
  big_ticket: "Genuine big-ticket purchase",
  new_device: "Device upgrade",
  new_beneficiary: "First payment to a new payee",
  night_activity: "Legitimate late-night payment",
  category_excursion: "Out-of-character category",
  burst: "Retry / split payment burst",
};

export default async function StudioPage() {
  const [sim, atlas, graph, cases] = await Promise.all([
    getSimulation(), getAtlas(), getGraph(), getCases(),
  ]);

  if (!sim) {
    return (
      <Shell>
        <div className="py-16">
          <Empty what="simulation data" />
        </div>
      </Shell>
    );
  }

  const s = sim.summary;
  const perVector = Object.entries(s.per_vector ?? {}).sort(
    (a, b) => b[1].value_extracted - a[1].value_extracted,
  );
  const episodeCases = cases.cases.filter((c) => c.episode);

  return (
    <Shell>
      {/* header */}
      <div className="border-b border-line py-12 lg:py-16">
        <div className="flex items-baseline gap-4">
          <span className="mono text-[13px] text-ember">02</span>
          <h1 className="mono text-[28px] font-medium leading-tight tracking-tight sm:text-[34px]">
            Simulation Studio
          </h1>
        </div>
        <p className="mt-4 max-w-3xl pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
          Attacks are injected into a calibrated base population, not generated in
          isolation. Fraud is only anomalous relative to a baseline, so the
          baseline carries persona archetypes, circadian rhythms, salary-day
          spikes, festival demand, shared household devices, a genuine
          new-account cohort, and cover traffic from the attacker&apos;s own mule
          identities.
        </p>
      </div>

      {/* ledger */}
      <section className="border-b border-line py-10">
        <div className="grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-panel p-5">
            <Stat label="Transactions" value={num(s.transactions)}
              sub={`over ${s.days} days · ${inr(s.total_value)} of value`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="Fraudulent" value={num(s.fraud_transactions)} accent="ember"
              sub={`${pct(s.fraud_rate, 2)} by count · ${pct(s.fraud_value_share, 1)} by value`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="Conversations" value={num(s.episodes)}
              sub={`${num(s.fraud_episodes)} scam scripts, ${num(s.episodes - s.fraud_episodes)} genuine threads`} />
          </div>
          <div className="bg-panel p-5">
            <Stat label="Graph edges" value={num(s.graph_edges)}
              sub={`across ${num(s.synthetic_identities)} attacker-controlled identities`} />
          </div>
        </div>
      </section>

      {/* fidelity argument */}
      <section className="grid gap-5 border-b border-line py-10 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-5">
          <Callout tone="ember" title="The hard part is the negatives, not the positives">
            <p>
              A synthetic fraud dataset whose legitimate traffic is homogeneous
              makes &ldquo;unusual equals fraud&rdquo; trivially true, and every
              model trained on it reports a meaningless AUC. So{" "}
              {pct(s.benign_anomaly_rate, 1)} of legitimate traffic here is
              deliberately anomalous — and each type mimics a different fraud tell.
            </p>
          </Callout>
          <Panel>
            <PanelHeader eyebrow="Benign anomalies in the ledger"
              title="Legitimate traffic that looks like fraud" />
            <BarList
              items={Object.entries(s.benign_anomalies)
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => ({ label: BENIGN_LABEL[k] ?? k, value: v }))}
              format={(n) => num(n)}
              labelWidth="min-w-[190px]"
            />
          </Panel>
        </div>

        <div className="space-y-5">
          <Panel>
            <PanelHeader eyebrow="Base population" title="Who is in the portfolio" />
            <BarList
              items={Object.entries(sim.world.by_persona)
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => ({ label: k.replace(/_/g, " "), value: v }))}
              format={(n) => num(n)}
              labelWidth="min-w-[150px]"
            />
          </Panel>
          <Panel>
            <PanelHeader eyebrow="Realism constraints" title="What the model does not get" />
            <KeyValue
              dense
              rows={[
                ["Session telemetry coverage", pct(s.telemetry_coverage, 0)],
                ["Training fraud hidden by label noise", num(sim.label_noise.training_frauds_hidden)],
                ["Unreported-fraud rate assumed", pct(sim.label_noise.missed_fraud_rate, 0)],
                ["False fraud labels", pct(sim.label_noise.false_fraud_rate, 2)],
                ["Cover traffic from mule identities", num(s.cover_transactions)],
                ["Split", sim.split.split],
              ]}
            />
            <p className="mt-3 text-[12px] leading-relaxed text-fg-faint">
              {sim.label_noise.note}
            </p>
          </Panel>
        </div>
      </section>

      {/* per vector */}
      <section className="border-b border-line py-10">
        <Panel>
          <PanelHeader
            eyebrow="Generate"
            title="What each injector produced"
            note="Every injector takes the same eight strain parameters. These runs used the documented defaults; the arena mutates them."
          />
          <Table
            head={["Typology", "Campaigns", "Transactions", "Labelled fraud", "Value extracted", "Rail signature"]}
          >
            {perVector.map(([vid, d]) => (
              <tr key={vid}>
                <Td align="left">
                  <div className="mono text-[11px] text-fg-faint">{vid}</div>
                  <div className="mt-0.5 max-w-[38ch] truncate text-[12.5px]">
                    {d.label}
                  </div>
                </Td>
                <Td>{num(d.campaigns)}</Td>
                <Td>{num(d.transactions)}</Td>
                <Td className="text-ember">{num(d.fraud_transactions)}</Td>
                <Td>{inr(d.value_extracted)}</Td>
                <Td align="left">
                  <span className="text-[11.5px] text-fg-faint">{d.notes}</span>
                </Td>
              </tr>
            ))}
          </Table>
          <p className="mt-4 text-[12.5px] leading-relaxed text-fg-faint">
            Note the gap between transactions and labelled fraud on{" "}
            <span className="mono">AV-SYNTH-ID</span> and{" "}
            <span className="mono">AV-DEEPFAKE-KYC</span>: the nurture phase of a
            synthetic identity is real, settled, repaid activity and is labelled
            legitimate. Labelling the whole account as fraud from birth would leak
            the answer into training and inflate every metric downstream.
          </p>
        </Panel>
      </section>

      {/* strain lab */}
      <section className="border-b border-line py-10">
        <StrainLab atlas={atlas} />
      </section>

      {/* transcripts */}
      {episodeCases.length ? (
        <section className="border-b border-line py-10">
          <div className="mb-6 max-w-3xl">
            <div className="eyebrow mb-2">Cross-modal generation</div>
            <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[26px]">
              The conversation before the payment
            </h2>
            <p className="mt-3 text-[14.5px] leading-relaxed text-fg-muted">
              Coercion typologies produce a transcript as well as a transaction,
              because that is what the fraud actually looks like end to end. The
              engine also generates genuine conversations for legitimate payments
              — including urgent, emotional ones — so that &ldquo;has a
              transcript&rdquo; is a signal rather than a label.
            </p>
          </div>
          <TranscriptViewer cases={episodeCases} />
        </section>
      ) : null}

      {/* graph */}
      {graph.nodes.length ? (
        <section className="border-b border-line py-10">
          <Panel>
            <PanelHeader
              eyebrow={`Campaign ${graph.campaign_id ?? ""}`}
              title="A mule network, as generated"
              note={graph.note}
              right={
                <div className="flex gap-2">
                  <Badge tone="dim">{graph.nodes.length} accounts</Badge>
                  <Badge tone="ember">{graph.edges.length} transfers</Badge>
                </div>
              }
            />
            <NetworkGraph nodes={graph.nodes} edges={graph.edges} height={360} />
            <div className="mt-4 grid gap-4 border-t border-line-soft pt-4 sm:grid-cols-3">
              <MiniNote k="Left column" v="Victim accounts paying in — ordinary customers, ordinary sessions." />
              <MiniNote k="Amber nodes" v="Attacker-controlled receiving accounts. Brighter means younger than 15 days." />
              <MiniNote k="Edge weight" v="Transfer value. Notice value decaying by a constant fee margin at each hop." />
            </div>
          </Panel>
        </section>
      ) : null}

      {/* rails */}
      <section className="py-10">
        <div className="grid gap-5 lg:grid-cols-2">
          <Panel>
            <PanelHeader eyebrow="Volume" title="Transactions by rail" />
            <BarList
              items={Object.entries(s.by_rail)
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => ({ label: RAIL_LABEL[k] ?? k, value: v }))}
              format={(n) => num(n)}
              labelWidth="min-w-[150px]"
            />
          </Panel>
          <Panel>
            <PanelHeader eyebrow="Where the fraud is" title="Fraud share by rail" />
            <BarList
              tone="ember"
              items={Object.entries(s.fraud_by_rail)
                .sort((a, b) => (b[1] / (s.by_rail[b[0]] || 1)) - (a[1] / (s.by_rail[a[0]] || 1)))
                .map(([k, v]) => ({
                  label: RAIL_LABEL[k] ?? k,
                  value: v / (s.by_rail[k] || 1),
                  note: `${num(v)} txns`,
                }))}
              format={(n) => pct(n, 2)}
              labelWidth="min-w-[150px]"
            />
            <p className="mt-3 text-[12px] leading-relaxed text-fg-faint">
              Agentic commerce carries the highest fraud share by a wide margin —
              which is exactly the point. It is a rail with no fraud history to
              train on, so the only way to have a model ready on day one is to
              manufacture the fraud yourself.
            </p>
          </Panel>
        </div>
      </section>
    </Shell>
  );
}

function MiniNote({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="eyebrow mb-1.5">{k}</div>
      <p className="text-[12.5px] leading-relaxed text-fg-muted">{v}</p>
    </div>
  );
}
