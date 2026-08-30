import type { Metadata } from "next";

import AtlasExplorer from "@/components/AtlasExplorer";
import { Empty, Shell } from "@/components/ui";
import { getAtlas } from "@/lib/data";

export const metadata: Metadata = {
  title: "Attack Atlas",
  description:
    "42 curated GenAI payment fraud vectors plus machine-composed hybrids — " +
    "rail, surface, kill chain, observable signals, detection gap and threat score.",
};

export default async function AtlasPage() {
  const atlas = await getAtlas();

  return (
    <Shell>
      <div className="border-b border-line py-12 lg:py-16">
        <div className="flex items-baseline gap-4">
          <span className="mono text-[13px] text-mint">01</span>
          <h1 className="mono text-[28px] font-medium leading-tight tracking-tight sm:text-[34px]">
            Attack Atlas
          </h1>
        </div>
        <p className="mt-4 max-w-3xl pl-[2.1rem] text-[15px] leading-relaxed text-fg-muted">
          The atlas is deliberately machine-readable rather than prose: every
          vector is a record the generator keys off, the detector is measured
          against, and the discovery agent recombines. Threat score is computed —{" "}
          <span className="mono text-fg">
            0.30·gap + 0.24·uplift + 0.20·impact + 0.15·velocity + 0.11·feasibility
          </span>{" "}
          — weighted so that what we cannot currently see dominates.
        </p>
        <p className="mt-3 max-w-3xl pl-[2.1rem] text-[13px] leading-relaxed text-fg-faint">
          Entries describe observable behaviour and telemetry signatures — what a
          defender can model. They deliberately contain no operational playbooks,
          tooling or infrastructure.
        </p>
      </div>

      {atlas.vectors.length ? (
        <AtlasExplorer atlas={atlas} />
      ) : (
        <div className="py-12">
          <Empty what="atlas data" />
        </div>
      )}
    </Shell>
  );
}
