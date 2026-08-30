"use client";

import { useState } from "react";

import type { AtlasData } from "@/lib/types";
import { vectorShort } from "@/lib/format";
import { Radar } from "./charts";
import { Badge, Meter, Panel, PanelHeader } from "./ui";

/**
 * The strain parameters are the contract between the generator and the red
 * agent, so they get their own explorer. Everything here is engine data: the
 * defaults are the documented parameterisation of each typology, and the cost
 * weights are what the evolutionary search pays to move each knob.
 */
export default function StrainLab({ atlas }: { atlas: AtlasData }) {
  const injectors = Object.entries(atlas.injectors ?? {});
  const [sel, setSel] = useState(injectors[0]?.[0] ?? "");
  const inj = atlas.injectors[sel];
  const params = Object.keys(atlas.strain_parameters ?? {});
  const constraint = inj ? atlas.family_constraints?.[inj.key] : undefined;

  if (!inj) return null;

  return (
    <div>
      <div className="mb-6 max-w-3xl">
        <div className="eyebrow mb-2">The contract with the red agent</div>
        <h2 className="mono text-[22px] font-medium leading-tight tracking-tight sm:text-[26px]">
          Eight knobs, and what each one costs
        </h2>
        <p className="mt-3 text-[14.5px] leading-relaxed text-fg-muted">
          Every injector exposes the same parameters — the levers a real operator
          actually controls. The red agent does not invent new code; it discovers
          new <em>parameterisations</em> of known typologies that the current model
          fails on, which is how attack evolution works in the field.
        </p>
      </div>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {injectors.map(([vid, i]) => (
          <button
            key={vid}
            onClick={() => setSel(vid)}
            className={`mono rounded-[4px] border px-2.5 py-1.5 text-[11.5px] transition-colors ${
              sel === vid
                ? "border-ember-dim/60 bg-ember/[0.09] text-ember"
                : "border-line text-fg-muted hover:text-fg"
            }`}
          >
            {vectorShort(vid)}
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1.25fr]">
        <Panel>
          <PanelHeader
            eyebrow={sel}
            title={inj.label}
            right={<Badge tone="dim">{inj.key}</Badge>}
          />
          <div className="flex justify-center">
            <Radar
              axes={params}
              series={[
                {
                  name: "documented default",
                  values: params.map((p) => inj.defaults[p] ?? 0),
                  color: "ember",
                },
              ]}
              size={250}
            />
          </div>
          <p className="mono mt-2 text-center text-[10.5px] text-ember">
            documented parameterisation
          </p>
          <div className="mt-5 border-t border-line-soft pt-4 text-[12.5px] leading-relaxed text-fg-muted">
            Produces roughly{" "}
            <span className="mono text-fg">{inj.txns_per_campaign}</span>{" "}
            transactions per campaign. Parameters this typology is sensitive to:{" "}
            <span className="mono text-fg">{inj.uses.join(", ")}</span>.
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            eyebrow="Parameter space"
            title="What the knobs mean, and where evolution may go"
            note="Bounds are per-family: card testing without velocity is not card testing, and a coercion script with zero narrative intensity never gets the victim to press send."
          />
          <div className="space-y-4">
            {params.map((p) => {
              const v = inj.defaults[p] ?? 0;
              const cost = atlas.red_team_cost_weights?.[p];
              const lo = constraint?.lower?.[p];
              const hi = constraint?.upper?.[p];
              return (
                <div key={p}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="mono text-[12.5px] text-fg">{p}</span>
                    <div className="flex items-center gap-2">
                      {cost ? (
                        <span className="mono text-[10.5px] text-fg-faint">
                          cost {cost.weight.toFixed(2)} when {cost.direction}
                        </span>
                      ) : null}
                      <span className="mono tnum text-[12.5px] text-ember">
                        {v.toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="relative mt-1.5">
                    <Meter value={v} tone="ember" height={6} />
                    {lo !== undefined && lo > 0 ? (
                      <span
                        className="absolute top-0 h-[6px] w-px bg-mint"
                        style={{ left: `${lo * 100}%` }}
                        title={`family floor ${lo}`}
                      />
                    ) : null}
                    {hi !== undefined && hi < 1 ? (
                      <span
                        className="absolute top-0 h-[6px] w-px bg-mint"
                        style={{ left: `${hi * 100}%` }}
                        title={`family ceiling ${hi}`}
                      />
                    ) : null}
                  </div>
                  <p className="mt-1 text-[11.5px] leading-snug text-fg-faint">
                    {atlas.strain_parameters[p]?.description}
                  </p>
                </div>
              );
            })}
          </div>
          <p className="mt-5 border-t border-line-soft pt-3 text-[12px] text-fg-faint">
            Mint ticks mark this family&apos;s hard bounds — the search may not
            leave the typology.
          </p>
        </Panel>
      </div>
    </div>
  );
}
