import type { Metadata } from "next";

import ArenaGenerations from "@/components/ArenaGenerations";
import { ColumnPairs, LineChart, Legend, BarList } from "@/components/charts";
import { Badge, Callout, Empty, Panel, PanelHeader, Shell, Stat, Table, Td } from "@/components/ui";
import { getArena, getAtlas, num, pct, vectorShort } from "@/lib/data";

export const metadata: Metadata = {
  title: "Red vs Blue Arena",
  description:
    "Constrained evolutionary search against the live detector: evasion found, " +
    "evasion closed, and Time-to-Immunity.",
};

export default async function ArenaPage() {
  const [arena, atlas] = await Promise.all([getArena(), getAtlas()]);

  if (!arena || !arena.generations.length) {
    return (
      <Shell>
        <div className="py-16">
          <Empty what="arena data" />
        </div>
      </Shell>
    );
  }

  const gens = arena.generations;
  const last = gens[gens.length - 1];
  const tti = arena.time_to_immunity_generations;

  const minedTotals = gens.reduce<Record<string, number>>((acc, g) => {
    for (const [k, v] of Object.entries(g.mined_by_vector ?? {})) {
      acc[k] = (acc[k] ?? 0) + v;
    }
    return acc;
  }, {});

  return (
    <Shell>
      {/* header */}
      <div className="border-b border-line py-12 lg:py-16">
        <div className="flex items-baseline gap-4">
          <span className="mono text-[13px] text-ember">04</span>
          <h1 className="mono text-[28px] font-medium leading-tight tracking-tight sm:text-[34px]">
            Red vs Blue Arena
          </h1>
        </div>
        <p className="mt-4 max-w-3xl pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
          The red agent runs a constrained evolutionary search against the live
          decision boundary, using only the feedback a real attacker has: does
          this get through? Fitness is evasion net of operating cost and subject
          to a value floor, so it cannot win by evolving attacks nobody would
          bother running. Every evasion is mined as a hard negative and the blue
          model retrains on it.
        </p>
      </div>

      {/* headline */}
      <section className="border-b border-line py-10">
        <div className="grid gap-px bg-line md:grid-cols-4">
          <div className="bg-panel p-5">
            <Stat
              label="Time-to-Immunity"
              accent="mint"
              value={tti ? `${tti} gen` : "not reached"}
              sub={`First generation where post-retrain evasion fell below ${pct(arena.immunity_threshold, 0)} with the false-positive budget intact.`}
            />
          </div>
          <div className="bg-panel p-5">
            <Stat
              label="Peak evasion found"
              accent="ember"
              value={pct(Math.max(...gens.map((g) => g.evasion_pre)), 1)}
              sub="against the shipped model, by strains it had never scored"
            />
          </div>
          <div className="bg-panel p-5">
            <Stat
              label="Evasion remaining"
              value={pct(last.evasion_post, 2)}
              sub={`after ${gens.length} generations and ${num(last.mined_cumulative)} mined hard negatives`}
            />
          </div>
          <div className="bg-panel p-5">
            <Stat
              label="Cost to the blue team"
              value={`${arena.delta.fpr >= 0 ? "+" : ""}${(arena.delta.fpr * 100).toFixed(3)} pt`}
              sub={`change in false-positive rate, against a ceiling of ${pct(arena.fpr_budget_ceiling, 2)}. Recall moved ${arena.delta.recall >= 0 ? "+" : ""}${(arena.delta.recall * 100).toFixed(1)} pt.`}
            />
          </div>
        </div>
      </section>

      {/* the two charts */}
      <section className="grid gap-5 py-10 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            eyebrow="The loop, generation by generation"
            title="Evasion found vs evasion closed"
            note="Amber is what the red agent got past the model this round. Mint is what survived after the blue model retrained on those same transactions."
          />
          <ColumnPairs
            groups={gens.map((g) => ({
              label: `g${g.generation}`,
              a: g.evasion_pre,
              b: g.evasion_post,
            }))}
            height={230}
          />
          <div className="mono mt-1 flex gap-5 text-[10.5px]">
            <span className="text-ember">red finds</span>
            <span className="text-mint">blue closes</span>
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Frozen future test slice"
            title="Blue team, at constant alert budget"
            note="Measured every generation on the same held-out future transactions, at the same 2% review capacity — so a recall gain is only counted if the false-positive cost did not move."
          />
          <LineChart
            height={230}
            yDomain={[
              Math.min(...gens.map((g) => g.blue_after.recall)) - 0.02,
              1.005,
            ]}
            formatX={(n) => `g${Math.round(n)}`}
            formatY={(n) => (n * 100).toFixed(1) + "%"}
            xTicks={Math.min(7, gens.length - 1)}
            series={[
              {
                name: "recall",
                color: "mint",
                points: gens.map((g) => ({ x: g.generation, y: g.blue_after.recall })),
              },
              {
                name: "value recall",
                color: "faint",
                dashed: true,
                points: gens.map((g) => ({ x: g.generation, y: g.blue_after.value_recall })),
              },
            ]}
          />
          <Legend
            items={[
              { name: "recall on fraud count", color: "mint" },
              { name: "recall on fraud value", color: "faint", dashed: true },
            ]}
          />
          <div className="mt-4 border-t border-line-soft pt-3">
            <BarList
              items={gens.map((g) => ({
                label: `g${g.generation} false-positive rate`,
                value: g.blue_after.fpr,
                tone: g.fpr_within_budget ? "mint" : "ember",
              }))}
              max={arena.fpr_budget_ceiling}
              format={(n) => (n * 100).toFixed(3) + "%"}
              labelWidth="min-w-[150px]"
            />
            <p className="mt-2.5 text-[12px] text-fg-faint">
              Full bar = the {pct(arena.fpr_budget_ceiling, 2)} ceiling the blue
              team is not allowed to exceed while chasing the red agent.
            </p>
          </div>
        </Panel>
      </section>

      {/* generation explorer */}
      <section className="border-t border-line py-10">
        <ArenaGenerations generations={gens} paramSpace={atlas.strain_parameters} />
      </section>

      {/* what got mined */}
      <section className="grid gap-5 border-t border-line py-10 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            eyebrow="Hard negatives"
            title="Which typologies the red agent actually broke"
            note="Every one of these is a transaction the shipped model approved. They became training labels without a single real customer losing money."
          />
          <BarList
            items={Object.entries(minedTotals)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => ({ label: vectorShort(k), value: v, tone: "ember" as const }))}
            format={(n) => num(n)}
          />
          {!Object.keys(minedTotals).length ? (
            <p className="text-[13px] text-fg-faint">
              No strain evaded the model in any generation.
            </p>
          ) : null}
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow={`Generation ${last.generation}`}
            title="Where the pressure ended up"
            note="Mean evasion rate by attack family in the final population — the residual soft spots the next release should target."
          />
          <BarList
            items={Object.entries(last.by_family)
              .slice(0, 12)
              .map(([, d]) => ({
                label: vectorShort(d.vector_id),
                value: d.evasion,
                note: `fit ${d.fitness.toFixed(3)}`,
                tone: d.evasion > 0.02 ? ("ember" as const) : ("mint" as const),
              }))}
            max={Math.max(0.02, ...Object.values(last.by_family).map((d) => d.evasion))}
            format={(n) => pct(n, 1)}
          />
        </Panel>
      </section>

      {/* the rules of the game */}
      <section className="border-t border-line py-10">
        <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
          <Callout tone="ember" title="Why the red agent cannot cheat">
            <p>
              Unconstrained adversarial search always finds the same degenerate
              answer: make the attack so small, so slow and so expensive that it
              evades everything and earns nothing. That is a surrender, not an
              evasion, and a defence hardened against it learns nothing.
            </p>
            <p className="mt-3">
              So every strain is costed the way an operator would cost it. Clean
              attested devices have to be bought and warmed. A deep mule inventory
              has to be recruited and burned. High mimicry costs operator hours per
              victim. Patience ties up working capital. A strain that fails to
              clear a{" "}
              <span className="mono text-fg">
                ₹{num(4000)} per-attack value floor
              </span>{" "}
              is heavily discounted.
            </p>
            <p className="mt-3">
              The strains that survive are the ones a real crew would actually run
              — which is what makes retraining on them worth anything.
            </p>
          </Callout>

          <Panel>
            <PanelHeader
              eyebrow="Fitness model"
              title="Operating cost weights"
              note="Marginal cost of pushing each strain parameter toward its expensive direction."
            />
            <Table head={["Parameter", "Weight", "Expensive when"]}>
              {Object.entries(atlas.red_team_cost_weights ?? {})
                .sort((a, b) => b[1].weight - a[1].weight)
                .map(([k, v]) => (
                  <tr key={k}>
                    <Td align="left">
                      <span className="mono text-[12.5px]">{k}</span>
                      <div className="mt-0.5 max-w-[34ch] text-[11.5px] text-fg-faint">
                        {atlas.strain_parameters?.[k]?.description}
                      </div>
                    </Td>
                    <Td>{v.weight.toFixed(2)}</Td>
                    <Td>
                      <Badge tone="dim">{v.direction}</Badge>
                    </Td>
                  </tr>
                ))}
            </Table>
          </Panel>
        </div>
      </section>

      {/* raw generations */}
      <section className="border-t border-line py-10">
        <Panel pad={false} className="p-5 sm:p-6">
          <PanelHeader
            eyebrow="Audit trail"
            title="Every generation, every number"
            note="This table is the evidence pack a model-risk function would ask for: what was tried, what evaded, what it cost to close, and whether the false-positive budget held."
          />
          <Table
            head={["Gen", "Strains", "Attacks", "Evasion pre", "Evasion post", "Mined", "Blue AUC", "Recall", "FPR", "Budget", "Secs"]}
          >
            {gens.map((g) => (
              <tr key={g.generation}>
                <Td align="left">
                  <span className="mono">g{g.generation}</span>
                </Td>
                <Td>{g.population}</Td>
                <Td>{num(g.attack_rows)}</Td>
                <Td className="text-ember">{pct(g.evasion_pre, 2)}</Td>
                <Td className="text-mint">{pct(g.evasion_post, 2)}</Td>
                <Td>{num(g.mined)}</Td>
                <Td>{g.blue_after.auc?.toFixed(4) ?? "—"}</Td>
                <Td>{pct(g.blue_after.recall, 2)}</Td>
                <Td>{(g.blue_after.fpr * 100).toFixed(3)}%</Td>
                <Td>
                  <Badge tone={g.fpr_within_budget ? "mint" : "ember"}>
                    {g.fpr_within_budget ? "ok" : "breach"}
                  </Badge>
                </Td>
                <Td>{g.seconds}</Td>
              </tr>
            ))}
          </Table>
        </Panel>
      </section>
    </Shell>
  );
}
