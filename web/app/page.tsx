import Link from "next/link";

import { ColumnPairs, LineChart, ScoreHistogram } from "@/components/charts";
import LoopDiagram from "@/components/LoopDiagram";
import { Badge, Panel, Shell, Stat } from "@/components/ui";
import { getArena, getAtlas, getDetection, getRun, getSimulation, num, pct } from "@/lib/data";

export default async function Home() {
  const [run, atlas, sim, det, arena] = await Promise.all([
    getRun(), getAtlas(), getSimulation(), getDetection(), getArena(),
  ]);

  const gens = arena?.generations ?? [];
  const tti = arena?.time_to_immunity_generations ?? null;
  const pre = det?.baseline;
  const post = det?.post_arena;

  return (
    <>
      {/* ================= HERO ================= */}
      <section className="border-b border-line">
        <Shell>
          <div className="grid gap-0 lg:grid-cols-[1.05fr_1fr]">
            {/* left */}
            <div className="border-line py-16 pr-0 lg:border-r lg:py-24 lg:pr-12">
              <div className="mono inline-flex items-center gap-2 rounded-[5px] border border-line bg-panel px-3 py-1.5 text-[12.5px] text-fg-muted">
                <span className="text-mint">$</span>
                python -m immunis.cli run
                <span className="kbd ml-1">R</span>
              </div>

              <h1 className="mono mt-8 text-[40px] font-medium leading-[1.06] tracking-[-0.02em] sm:text-[52px] lg:text-[58px]">
                The fraud that
                <br />
                hasn&apos;t happened
                <br />
                <span className="text-mint">yet.</span>
              </h1>

              <p className="mt-7 max-w-[30rem] text-[15.5px] leading-relaxed text-fg-muted">
                Payment defence is reactive because labels arrive after the
                losses. IMMUNIS manufactures the attack first — {atlas.stats.total_vectors}{" "}
                GenAI fraud vectors, {atlas.stats.simulated_vectors} of them
                simulated end-to-end — then lets a red agent evolve against the
                live model until the model wins.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/arena"
                  className="mono inline-flex items-center gap-2.5 rounded-[6px] bg-mint px-4 py-2.5 text-[14px] font-medium text-ink transition-opacity hover:opacity-90"
                >
                  Enter the arena
                  <span className="kbd border-black/20 bg-black/10 text-ink">A</span>
                </Link>
                <Link
                  href="/atlas"
                  className="mono inline-flex items-center gap-2.5 rounded-[6px] border border-line bg-panel px-4 py-2.5 text-[14px] font-medium text-fg transition-colors hover:bg-panel-2"
                >
                  Read the atlas
                  <span className="kbd">T</span>
                </Link>
              </div>

              <p className="mono mt-6 text-[12px] text-fg-faint">
                Reproducible from one seed · CPU-only · no real cardholder data
              </p>
            </div>

            {/* right — a live bento of engine output, not decoration */}
            <div className="grid grid-cols-2 border-l border-line lg:border-l-0">
              <div className="border-b border-r border-line p-5">
                <div className="eyebrow mb-2">Time-to-Immunity</div>
                <div className="mono text-[34px] leading-none text-mint">
                  {tti ?? "—"}
                  <span className="ml-1.5 text-[13px] text-fg-faint">gen</span>
                </div>
                <p className="mt-2 text-[12px] leading-snug text-fg-faint">
                  Generations to drive a novel strain family below 5% evasion.
                  The industry equivalent is months of chargeback data.
                </p>
              </div>
              <div className="border-b border-line p-5">
                <div className="eyebrow mb-2">Detection</div>
                <div className="mono text-[34px] leading-none">
                  {post ? post.roc_auc.toFixed(3) : "—"}
                </div>
                <p className="mt-2 text-[12px] leading-snug text-fg-faint">
                  ROC-AUC on a frozen future test slice, with{" "}
                  {pct(post?.operating_point.recall ?? 0, 1)} recall at a{" "}
                  {pct(post?.operating_point.alert_rate ?? 0, 1)} alert budget.
                </p>
              </div>

              <div className="col-span-2 border-b border-line bg-panel p-5">
                <div className="mb-3 flex items-center justify-between">
                  <div className="eyebrow">Red agent evasion, by generation</div>
                  <div className="flex items-center gap-1.5">
                    <span className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-ember" />
                    <span className="mono text-[10.5px] text-fg-faint">arena</span>
                  </div>
                </div>
                {gens.length ? (
                  <LineChart
                    height={132}
                    yTicks={2}
                    xTicks={Math.min(7, gens.length - 1)}
                    formatX={(n) => `g${Math.round(n)}`}
                    formatY={(n) => (n * 100).toFixed(0) + "%"}
                    yDomain={[0, Math.max(0.02, ...gens.map((g) => g.evasion_pre)) * 1.15]}
                    series={[
                      {
                        name: "found",
                        color: "ember",
                        points: gens.map((g) => ({ x: g.generation, y: g.evasion_pre })),
                      },
                      {
                        name: "after retrain",
                        color: "mint",
                        points: gens.map((g) => ({ x: g.generation, y: g.evasion_post })),
                      },
                    ]}
                  />
                ) : (
                  <div className="h-[132px]" />
                )}
                <div className="mono mt-1 flex justify-between text-[10.5px]">
                  <span className="text-ember">evasion found by red</span>
                  <span className="text-mint">evasion after blue retrains</span>
                </div>
              </div>

              <div className="border-r border-line p-5">
                <div className="eyebrow mb-2">Ledger simulated</div>
                <div className="mono text-[22px] leading-none">
                  {num(run?.generate.transactions)}
                </div>
                <p className="mt-2 text-[12px] leading-snug text-fg-faint">
                  transactions across {run?.generate.customers ?? "—"} customers
                  and 7 payment rails, at {pct(run?.generate.fraud_rate ?? 0, 2)}{" "}
                  fraud prevalence.
                </p>
              </div>
              <div className="p-5">
                <div className="eyebrow mb-2">Zero-day recall</div>
                <div className="mono text-[22px] leading-none text-mint">
                  {det?.zero_day_journey
                    ? pct(
                        Object.values(det.zero_day_journey.after).filter(
                          (v): v is number => typeof v === "number",
                        )[1] ?? 0,
                        0,
                      )
                    : "—"}
                </div>
                <p className="mt-2 text-[12px] leading-snug text-fg-faint">
                  on an attack family removed from training entirely — after the
                  red agent manufactured it.
                </p>
              </div>
            </div>
          </div>
        </Shell>
      </section>

      {/* ================= TRUST STRIP ================= */}
      <section className="border-b border-line bg-panel">
        <Shell>
          <div className="grid divide-y divide-line sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4 lg:divide-x">
            {[
              {
                k: "Attacks identified",
                v: `${atlas.stats.total_vectors} + ${atlas.discovered}`,
                s: "curated vectors plus machine-composed hybrids, across 8 families and 7 rails",
              },
              {
                k: "Fidelity",
                v: pct(sim?.summary.benign_anomaly_rate ?? 0, 1),
                s: "of legitimate traffic is deliberately anomalous — the false-positive pressure that makes precision mean something",
              },
              {
                k: "Detection efficacy",
                v: post ? post.pr_auc.toFixed(3) : "—",
                s: `PR-AUC at ${pct(post?.operating_point.fpr ?? 0, 2)} false-positive rate on a temporal holdout`,
              },
              {
                k: "Closed loop",
                v: num(arena?.generations.at(-1)?.mined_cumulative ?? 0),
                s: "evading transactions mined by the red agent and folded back into training",
              },
            ].map((c) => (
              <div key={c.k} className="px-1 py-6 lg:px-6">
                <div className="eyebrow mb-2">{c.k}</div>
                <div className="mono text-[26px] leading-none">{c.v}</div>
                <p className="mt-2.5 max-w-[15rem] text-[12.5px] leading-snug text-fg-faint">
                  {c.s}
                </p>
              </div>
            ))}
          </div>
        </Shell>
      </section>

      {/* ================= THE LOOP ================= */}
      <section className="border-b border-line">
        <Shell>
          <div className="py-16 lg:py-20">
            <div className="mb-10 max-w-3xl">
              <div className="eyebrow mb-3">The mechanism</div>
              <h2 className="mono text-[26px] font-medium leading-tight tracking-tight sm:text-[32px]">
                A vaccine, not an autopsy.
              </h2>
              <p className="mt-4 text-[15px] leading-relaxed text-fg-muted">
                Immunology gets this right and payments gets it wrong. A vaccine
                manufactures a safe replica of a pathogen <em>before</em> exposure,
                so the antibody already exists on day zero. Payment fraud defence
                does the opposite: it waits for losses, waits 45–90 days for
                disputes to settle, labels them, and only then retrains. The
                industry is permanently one outbreak behind — and GenAI just cut
                the attacker&apos;s iteration cycle from months to hours.
              </p>
            </div>
            <Panel className="bg-surface">
              <LoopDiagram />
            </Panel>
          </div>
        </Shell>
      </section>

      {/* ================= 01 IDENTIFY ================= */}
      <NumberedSection
        n="01"
        title="Map the attacks that don't have a name yet"
        href="/atlas"
        cta="Open the Attack Atlas"
        lede={`The atlas is ${atlas.stats.total_vectors} machine-readable vectors — rail, surface, kill chain, GenAI uplift, observable signals, detection gap — plus a discovery agent that composes them into hybrids that straddle observability boundaries. Not a list of prose; a data structure the generator keys off and the detector is measured against.`}
      >
        <div className="grid gap-px bg-line sm:grid-cols-3">
          {Object.entries(atlas.stats.by_family ?? {})
            .sort((a, b) => b[1] - a[1])
            .map(([family, n]) => (
              <div key={family} className="bg-panel p-4">
                <div className="mono text-[19px] leading-none">{n}</div>
                <div className="mt-2 text-[12.5px] leading-snug text-fg-muted">
                  {family}
                </div>
              </div>
            ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Badge tone="ember">
            {atlas.stats.by_priority?.critical ?? 0} critical
          </Badge>
          <Badge>{atlas.stats.by_priority?.high ?? 0} high</Badge>
          <Badge tone="mint">{atlas.stats.simulated_vectors} with generators</Badge>
          <Badge tone="dim">{atlas.discovered} discovered composites</Badge>
        </div>
        <p className="mt-5 text-[13.5px] leading-relaxed text-fg-muted">
          Including the 2026-native vectors most catalogues miss: prompt-injected
          shopping agents, over-scoped agent mandates, behavioural-biometric
          cloning, and coercion-authorised payments where the transaction is
          technically perfect — right customer, right device, right OTP.
        </p>
      </NumberedSection>

      {/* ================= 02 GENERATE ================= */}
      <NumberedSection
        n="02"
        title="Manufacture them at fidelity worth training on"
        href="/studio"
        cta="Open the Simulation Studio"
        lede="Attacks are injected into a calibrated base population — persona archetypes, circadian rhythms, salary-day spikes, shared household devices — not generated in isolation. Fraud is only anomalous relative to a baseline, so the baseline has to be real."
      >
        <div className="grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-4">
          <Cell k="Transactions" v={num(sim?.summary.transactions)}
            s={`${num(sim?.summary.fraud_transactions)} fraudulent across ${sim?.summary.days ?? "—"} days`} />
          <Cell k="Conversations" v={num(sim?.summary.episodes)}
            s="scam and genuine transcripts, because only fraud having a transcript would be a leak" />
          <Cell k="Graph edges" v={num(sim?.summary.graph_edges)}
            s="mule inflows and layered dispersal" />
          <Cell k="Telemetry coverage" v={pct(sim?.summary.telemetry_coverage ?? 0, 0)}
            s="session data is missing on the rest — as it is in production" />
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="border border-line bg-panel p-4">
            <div className="mono mb-2 text-[13px]">The hard part is the negatives</div>
            <p className="text-[13px] leading-relaxed text-fg-muted">
              {pct(sim?.summary.benign_anomaly_rate ?? 0, 1)} of legitimate traffic
              is deliberately anomalous: genuine travel, first big-ticket purchases,
              device upgrades, first payments to a new landlord. Every one of them
              mimics a fraud tell. Without them, &ldquo;unusual equals fraud&rdquo;
              is trivially true and every metric downstream is fiction.
            </p>
          </div>
          <div className="border border-line bg-panel p-4">
            <div className="mono mb-2 text-[13px]">And the labels are wrong on purpose</div>
            <p className="text-[13px] leading-relaxed text-fg-muted">
              {pct(sim?.label_noise.missed_fraud_rate ?? 0, 0)} of training fraud is
              hidden — coercion victims rarely report — and a slice of legitimate
              traffic carries a false fraud label.{" "}
              {num(sim?.label_noise.training_frauds_hidden)} frauds are invisible to
              the model during training. Every metric reported is still computed
              against ground truth.
            </p>
          </div>
        </div>
      </NumberedSection>

      {/* ================= 03 DEFEND ================= */}
      <NumberedSection
        n="03"
        title="Detect them without burying the review queue"
        href="/defense"
        cta="Open the Defense Console"
        lede="Four channels fused with a noisy-OR: a gradient-boosted model over ~100 causally-computed features, a graph channel for mule structure, an unsupervised novelty channel for strains no label describes, and a narrative channel that reads the conversation before the payment."
      >
        <div className="grid gap-5 lg:grid-cols-[1.15fr_1fr]">
          <Panel className="bg-surface">
            <div className="eyebrow mb-3">Score distribution — test slice</div>
            {pre ? (
              <ScoreHistogram
                edges={pre.score_hist.edges}
                fraud={pre.score_hist.fraud}
                legit={pre.score_hist.legit}
                threshold={pre.thresholds.budget}
                height={190}
              />
            ) : null}
            <div className="mono mt-1 flex gap-5 text-[10.5px]">
              <span className="text-ember">fraud</span>
              <span className="text-fg-faint">legitimate</span>
            </div>
          </Panel>
          <div className="grid grid-cols-2 gap-px bg-line">
            <div className="bg-panel p-4">
              <Stat label="Recall" size="sm" accent="mint"
                value={pct(post?.operating_point.recall ?? 0, 1)}
                sub={`at a ${pct(post?.operating_point.alert_rate ?? 0, 1)} alert budget`} />
            </div>
            <div className="bg-panel p-4">
              <Stat label="False positive rate" size="sm"
                value={pct(post?.operating_point.fpr ?? 0, 2)}
                sub="on legitimate traffic including benign anomalies" />
            </div>
            <div className="bg-panel p-4">
              <Stat label="Value recall" size="sm" accent="mint"
                value={pct(post?.operating_point.value_recall ?? 0, 1)}
                sub="share of fraudulent rupees stopped" />
            </div>
            <div className="bg-panel p-4">
              <Stat label="Brier score" size="sm"
                value={post ? post.brier.toFixed(4) : "—"}
                sub="isotonic-calibrated probabilities" />
            </div>
          </div>
        </div>
        <p className="mt-5 text-[13.5px] leading-relaxed text-fg-muted">
          The split is temporal, not random — the model is always evaluated on the
          future, the only split that predicts production. Two attack families are
          removed from training entirely to measure cold generalisation, and
          precision is reported twice: in-simulation, and Bayes-adjusted to the{" "}
          {pct(det?.realistic_prevalence ?? 0.0012, 2)} prevalence a real portfolio
          actually sees.
        </p>
      </NumberedSection>

      {/* ================= 04 ARENA ================= */}
      <NumberedSection
        n="04"
        title="Then let the attacker have a go at it"
        href="/arena"
        cta="Open the Red vs Blue Arena"
        accent="ember"
        lede="The red agent runs a constrained evolutionary search against the live decision boundary. Fitness is evasion net of operating cost, subject to a value floor — so it cannot cheat by evolving attacks nobody would bother running. Every evasion is mined as a hard negative and the blue model retrains."
      >
        {gens.length ? (
          <>
            <Panel className="bg-surface">
              <div className="eyebrow mb-3">
                Evasion found vs evasion remaining after retraining
              </div>
              <ColumnPairs
                groups={gens.map((g) => ({
                  label: `g${g.generation}`,
                  a: g.evasion_pre,
                  b: g.evasion_post,
                }))}
                height={200}
              />
              <div className="mono mt-1 flex gap-5 text-[10.5px]">
                <span className="text-ember">red finds</span>
                <span className="text-mint">blue closes</span>
              </div>
            </Panel>
            <div className="mt-5 grid gap-px bg-line sm:grid-cols-4">
              <Cell k="Generations" v={String(gens.length)}
                s={`${arena?.wall_seconds ?? "—"}s of wall clock`} />
              <Cell k="Peak evasion" v={pct(gens[0]?.evasion_pre ?? 0, 1)}
                s="found by the red agent against the shipped model" />
              <Cell k="Final evasion" v={pct(gens.at(-1)?.evasion_post ?? 0, 1)}
                s="after the loop closed" />
              <Cell k="Blue recall change"
                v={`${(arena?.delta.recall ?? 0) >= 0 ? "+" : ""}${((arena?.delta.recall ?? 0) * 100).toFixed(1)} pt`}
                s={`false positives moved ${((arena?.delta.fpr ?? 0) * 100).toFixed(2)} pt`} />
            </div>
          </>
        ) : null}
      </NumberedSection>

      {/* ================= ZERO-DAY PROOF ================= */}
      {det?.zero_day_journey ? (
        <section className="border-b border-line bg-panel">
          <Shell>
            <div className="py-16 lg:py-20">
              <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr]">
                <div>
                  <div className="eyebrow mb-3">The result that matters</div>
                  <h2 className="mono text-[26px] font-medium leading-tight tracking-tight sm:text-[30px]">
                    A typology with zero
                    <br />
                    historical labels.
                  </h2>
                  <p className="mt-5 text-[15px] leading-relaxed text-fg-muted">
                    Two attack families were removed from training entirely. The
                    &ldquo;before&rdquo; column is what a conventional programme
                    achieves on a typology it has never seen a labelled example of.
                    The &ldquo;after&rdquo; column is the same families once the red
                    agent manufactured them in the arena and the blue model
                    retrained on those synthetic strains.
                  </p>
                  <p className="mt-4 text-[15px] leading-relaxed text-fg-muted">
                    No real loss, no chargeback data, and no customer was defrauded
                    to close that gap. That is the entire product in one table.
                  </p>
                </div>
                <div className="border border-line bg-surface p-6">
                  <div className="grid grid-cols-[1fr_auto_auto] gap-x-6 gap-y-4">
                    <div className="eyebrow">Held-out family</div>
                    <div className="eyebrow text-right">Cold start</div>
                    <div className="eyebrow text-right">After arena</div>
                    {det.zero_day_journey.holdout_families.map((f) => {
                      const before = det.zero_day_journey.before[f];
                      const after = det.zero_day_journey.after[f];
                      return (
                        <div key={f} className="contents">
                          <div className="mono border-t border-line-soft pt-3 text-[13px]">
                            {f}
                          </div>
                          <div className="mono tnum border-t border-line-soft pt-3 text-right text-[15px] text-ember">
                            {typeof before === "number" ? pct(before, 1) : "—"}
                          </div>
                          <div className="mono tnum border-t border-line-soft pt-3 text-right text-[15px] text-mint">
                            {typeof after === "number" ? pct(after, 1) : "—"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="mt-6 border-t border-line pt-4 text-[12.5px] leading-relaxed text-fg-faint">
                    Not a leak: the labels came from attacks IMMUNIS generated
                    itself, in a sandbox, against its own detector.
                  </p>
                </div>
              </div>
            </div>
          </Shell>
        </section>
      ) : null}

      {/* ================= BUSINESS ================= */}
      <section className="border-b border-line">
        <Shell>
          <div className="py-16 lg:py-20">
            <div className="mb-10 max-w-3xl">
              <div className="eyebrow mb-3">Why a network, and why now</div>
              <h2 className="mono text-[26px] font-medium leading-tight tracking-tight sm:text-[32px]">
                Herd immunity is the moat.
              </h2>
            </div>
            <div className="grid gap-px bg-line md:grid-cols-3">
              {[
                {
                  t: "Pre-breach immunisation",
                  b: "Subscription, per issuer or acquirer",
                  d: "Today a bank learns a new typology from its own losses. We ship the attack before it arrives: a monthly stream of synthetic strains for emerging vectors, plus retrained weights and the evaluation evidence. Priced against basis points of fraud saved — a number every risk officer already has on a slide.",
                },
                {
                  t: "Adversarial assurance",
                  b: "Per engagement, and a compliance line item",
                  d: "Model-risk and cyber-resilience expectations increasingly require evidence a model was stress-tested, not just backtested. IMMUNIS emits exactly that pack: which vectors were tried, at what parameter ranges, what evaded, what residual risk remains.",
                },
                {
                  t: "Network herd immunity",
                  b: "The part only a network can build",
                  d: "When the red agent finds a gap against one participant's configuration, the antibody propagates to every participant — no customer data moves, only synthetic strains and model updates. Value grows superlinearly with participants, and no single bank or point vendor can replicate it.",
                },
              ].map((c) => (
                <div key={c.t} className="bg-panel p-6">
                  <div className="mono text-[15px] font-medium">{c.t}</div>
                  <div className="mono mt-1.5 text-[11.5px] uppercase tracking-[0.09em] text-mint-dim">
                    {c.b}
                  </div>
                  <p className="mt-4 text-[13.5px] leading-relaxed text-fg-muted">
                    {c.d}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-8 max-w-3xl text-[14px] leading-relaxed text-fg-muted">
              Three curves cross in 2026: GenAI collapses the attacker&apos;s cost
              per novel attack, agentic commerce opens a rail with no fraud history
              to train on, and regulators start asking for adversarial evidence. A
              system that manufactures labelled fraud on demand is the only answer
              to a rail that has no labels yet.
            </p>
          </div>
        </Shell>
      </section>

      {/* ================= CTA ================= */}
      <section className="border-b border-line">
        <Shell>
          <div className="my-14 overflow-hidden border border-line bg-mint-deep">
            <div className="relative px-6 py-14 sm:px-10">
              <h2 className="mono max-w-2xl text-[26px] font-medium leading-tight tracking-tight sm:text-[32px]">
                One command. {run ? `${Math.round(run.total_seconds)} seconds.` : ""}{" "}
                <span className="text-fg-muted">
                  The whole loop, reproducible from a single seed.
                </span>
              </h2>
              <div className="mono mt-7 inline-flex flex-wrap items-center gap-2 rounded-[5px] border border-mint-dim/40 bg-ink/60 px-3.5 py-2 text-[13px]">
                <span className="text-mint">$</span>
                <span>cd engine &amp;&amp; python -m immunis.cli run --profile full</span>
              </div>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  href="/console"
                  className="mono inline-flex items-center gap-2.5 rounded-[6px] bg-mint px-4 py-2.5 text-[14px] font-medium text-ink"
                >
                  Watch it score live
                  <span className="kbd border-black/20 bg-black/10 text-ink">L</span>
                </Link>
                <Link
                  href="/defense"
                  className="mono inline-flex items-center gap-2.5 rounded-[6px] border border-line bg-panel px-4 py-2.5 text-[14px] font-medium"
                >
                  See the evidence
                </Link>
              </div>
              <p className="mono mt-6 text-[12px] text-fg-faint">
                Python {run?.environment.python ?? "3.12"} · scikit-learn · no GPU ·
                artefacts regenerate this entire site
              </p>
              <Dither />
            </div>
          </div>
        </Shell>
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ */

function NumberedSection({
  n, title, lede, children, href, cta, accent = "mint",
}: {
  n: string;
  title: string;
  lede: string;
  children: React.ReactNode;
  href: string;
  cta: string;
  accent?: "mint" | "ember";
}) {
  return (
    <section className="border-b border-line">
      <Shell>
        <div className="py-14 lg:py-16">
          <div className="mb-8 grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
            <div className="max-w-3xl">
              <div className="flex items-baseline gap-4">
                <span
                  className={`mono text-[13px] tabular-nums ${accent === "ember" ? "text-ember" : "text-mint"}`}
                >
                  {n}
                </span>
                <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[27px]">
                  {title}
                </h2>
              </div>
              <p className="mt-4 pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
                {lede}
              </p>
            </div>
            <Link
              href={href}
              className="mono shrink-0 whitespace-nowrap rounded-[6px] border border-line bg-panel px-3.5 py-2 text-[13px] text-fg transition-colors hover:bg-panel-2"
            >
              {cta} →
            </Link>
          </div>
          <div className="lg:pl-[2.1rem]">{children}</div>
        </div>
      </Shell>
    </section>
  );
}

function Cell({ k, v, s }: { k: string; v: string; s: string }) {
  return (
    <div className="bg-panel p-4">
      <div className="eyebrow mb-2">{k}</div>
      <div className="mono tnum text-[20px] leading-none">{v}</div>
      <p className="mt-2 text-[12px] leading-snug text-fg-faint">{s}</p>
    </div>
  );
}

/** The dithered gradient from the design language, drawn deterministically. */
function Dither() {
  const cols = 58;
  const rows = 13;
  const cells: { x: number; y: number; o: number }[] = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const nx = (x / cols) * 2 - 1;
      const h = Math.exp(-(nx * nx) * 2.6) * rows;
      const depth = rows - y;
      if (depth <= h) {
        const p = 1 - depth / Math.max(1, h);
        // Deterministic hash instead of Math.random so SSR and client agree.
        const r = ((x * 73856093) ^ (y * 19349663)) % 1000 / 1000;
        if (r < 0.25 + p * 0.85) cells.push({ x, y, o: 0.25 + p * 0.75 });
      }
    }
  }
  return (
    <svg
      className="pointer-events-none absolute bottom-0 right-0 hidden h-[150px] w-[520px] md:block"
      viewBox={`0 0 ${cols * 6} ${rows * 6}`}
      aria-hidden="true"
    >
      {cells.map((c, i) => (
        <rect key={i} x={c.x * 6} y={c.y * 6} width={4.4} height={4.4}
          fill="var(--color-mint)" opacity={c.o * 0.85} />
      ))}
    </svg>
  );
}
