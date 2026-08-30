import { readFile } from "node:fs/promises";
import path from "node:path";

import type {
  ArenaData,
  AtlasData,
  CasesData,
  DetectionData,
  GraphData,
  RunData,
  SimulationData,
  StreamData,
} from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

/**
 * Artefacts are produced by `python -m immunis.cli run` and mirrored into
 * public/data. Reading them here (rather than fetching at runtime) means every
 * page is statically generated and the whole prototype deploys as static files
 * with no backend — while still being derived entirely from the engine.
 */
async function loadJSON<T>(name: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(path.join(DATA_DIR, name), "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export const getRun = () =>
  loadJSON<RunData | null>("run.json", null);

export const getAtlas = () =>
  loadJSON<AtlasData>("atlas.json", {
    vectors: [],
    stats: {} as AtlasData["stats"],
    discovered: 0,
    strain_parameters: {},
    injectors: {},
    red_team_cost_weights: {},
    family_constraints: {},
  });

export const getSimulation = () =>
  loadJSON<SimulationData | null>("simulation.json", null);

export const getDetection = () =>
  loadJSON<DetectionData | null>("detection.json", null);

export const getArena = () =>
  loadJSON<ArenaData | null>("arena.json", null);

export const getStream = () =>
  loadJSON<StreamData>("stream.json", { transactions: [] });

export const getCases = () =>
  loadJSON<CasesData>("cases.json", { cases: [] });

export const getGraph = () =>
  loadJSON<GraphData>("graph.json", { nodes: [], edges: [] });

export * from "./format";
