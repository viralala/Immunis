"use client";

import { useMemo, useState } from "react";

import type { Generation } from "@/lib/types";
import { inr, num, pct, vectorShort } from "@/lib/format";
import { Radar } from "./charts";
import { Badge, Meter, Panel, PanelHeader, Table, Td } from "./ui";

export default function ArenaGenerations({
  generations,
  paramSpace,
}: {
  generations: Generation[];
  paramSpace: Record<string, { description: string }>;
}) {
  const [gi, setGi] = useState(0);
  const gen = generations[Math.min(gi, generations.length - 1)];
  const [si, setSi] = useState(0);
  const strain = gen.top_strains[Math.min(si, gen.top_strains.length - 1)];

  const axes = useMemo(
    () => Object.keys(strain?.params ?? paramSpace ?? {}),
    [strain, paramSpace],
  );

  if (!strain) return null;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="eyebrow mr-1">Generation</span>
        {generations.map((g, i) => (
          <button
            key={g.generation}
            onClick={() => {
              setGi(i);
              setSi(0);
            }}
            className={`mono rounded-[4px] border px-2.5 py-1.5 text-[12px] transition-colors ${
              i === gi
                ? "border-ember-dim/60 bg-ember/[0.1] text-ember"
                : "border-line text-fg-muted hover:text-fg"
            }`}
          >
            g{g.generation}
          </button>
        ))}
        <span className="mono ml-auto text-[12px] text-fg-faint">
          elite centroid drift shows what the search learned to prefer
        </span>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Panel>
          <PanelHeader
            eyebrow={`Generation ${gen.generation} · top ${gen.top_strains.length} by fitness`}
            title="Fittest strains"
            note="Fitness is evasion rate discounted by operating cost and by a per-attack value floor. A strain that evades but earns nothing scores near zero."
          />
          <Table head={["Strain", "Evasion", "Fitness", "Cost", "Value/attack", "n"]}>
            {gen.top_strains.map((s, i) => (
              <tr
                key={s.strain_id}
                onClick={() => setSi(i)}
                className={`cursor-pointer transition-colors ${
                  i === si ? "bg-white/[0.05]" : "hover:bg-white/[0.025]"
                }`}
              >
                <Td align="left">
                  <div className="flex items-center gap-2">
                    <span className="mono text-[11px] text-fg-faint">{s.strain_id}</span>
                    {s.archetype ? <Badge tone="dim">{s.archetype}</Badge> : null}
                  </div>
                  <div className="mt-0.5 max-w-[34ch] truncate text-[12.5px]">
                    {vectorShort(s.vector_id)}
                  </div>
                </Td>
                <Td className={s.evasion_rate ? "text-ember" : ""}>
                  {pct(s.evasion_rate ?? 0, 1)}
                </Td>
                <Td>{(s.fitness ?? 0).toFixed(3)}</Td>
                <Td>{s.operational_cost.toFixed(2)}</Td>
                <Td>{inr(s.value_per_attack ?? 0)}</Td>
                <Td>{s.n ?? 0}</Td>
              </tr>
            ))}
          </Table>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow={strain.strain_id}
            title={vectorShort(strain.vector_id)}
            note={`Generation ${strain.generation}${strain.parents.length ? ` · bred from ${strain.parents.join(" × ")}` : " · seeded"}`}
          />
          <div className="flex justify-center">
            <Radar
              axes={axes}
              series={[
                {
                  name: strain.strain_id,
                  values: axes.map((a) => strain.params[a] ?? 0),
                  color: "ember",
                },
                {
                  name: "elite centroid",
                  values: axes.map((a) => gen.elite_centroid[a] ?? 0),
                  color: "mint",
                },
              ]}
              size={260}
            />
          </div>
          <div className="mono mt-1 flex justify-center gap-5 text-[10.5px]">
            <span className="text-ember">this strain</span>
            <span className="text-mint">elite centroid</span>
          </div>

          <div className="mt-5 space-y-2 border-t border-line-soft pt-4">
            {axes.map((a) => (
              <div key={a} className="flex items-center gap-3" title={paramSpace?.[a]?.description}>
                <span className="w-[124px] shrink-0 truncate text-[12px] text-fg-faint">
                  {a}
                </span>
                <Meter value={strain.params[a] ?? 0} tone="ember" height={5} />
                <span className="mono tnum w-9 shrink-0 text-right text-[11.5px] text-fg-muted">
                  {(strain.params[a] ?? 0).toFixed(2)}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-3 gap-3 border-t border-line-soft pt-4">
            <MiniStat k="Mined this gen" v={num(gen.mined)} />
            <MiniStat k="Value evaded" v={inr(gen.value_evaded)} />
            <MiniStat k="Attacks scored" v={num(gen.attack_rows)} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function MiniStat({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="eyebrow mb-1.5">{k}</div>
      <div className="mono tnum text-[15px]">{v}</div>
    </div>
  );
}
