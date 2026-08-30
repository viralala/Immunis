/** Shapes of the artefacts produced by the IMMUNIS engine. */

export interface AttackVector {
  id: string;
  name: string;
  family: string;
  rails: string[];
  surface: string;
  summary: string;
  genai_uplift: number;
  detection_gap: number;
  impact: number;
  feasibility: number;
  scale_velocity: number;
  uplift_note: string;
  kill_chain: string[];
  observable_signals: string[];
  historical_analogue: string;
  victim_profile: string;
  mitigations: string[];
  status: "documented" | "simulated" | "discovered";
  injector: string | null;
  parents: string[];
  notes: string;
  threat_score: number;
  priority: "critical" | "high" | "medium" | "watch";
}

export interface AtlasData {
  vectors: AttackVector[];
  discovered: number;
  stats: {
    total_vectors: number;
    simulated_vectors: number;
    families: number;
    by_family: Record<string, number>;
    by_surface: Record<string, number>;
    by_rail: Record<string, number>;
    by_priority: Record<string, number>;
    mean_threat_score: number;
  };
  strain_parameters: Record<string, { low: number; high: number; description: string }>;
  injectors: Record<string, {
    key: string;
    label: string;
    defaults: Record<string, number>;
    uses: string[];
    txns_per_campaign: number;
  }>;
  red_team_cost_weights: Record<string, { weight: number; direction: string }>;
  family_constraints: Record<string, { lower: Record<string, number>; upper: Record<string, number> }>;
}

export interface SimulationData {
  generated_at: string;
  config: Record<string, unknown> & {
    population: Record<string, number | string>;
    attacks: Record<string, unknown>;
    defend: Record<string, number>;
    redteam: Record<string, number>;
    costs: Record<string, number>;
    seed: number;
    profile: string;
  };
  label_noise: {
    training_frauds_hidden: number;
    missed_fraud_rate: number;
    false_fraud_rate: number;
    note: string;
  };
  summary: {
    transactions: number;
    fraud_transactions: number;
    fraud_rate: number;
    fraud_value: number;
    total_value: number;
    fraud_value_share: number;
    episodes: number;
    fraud_episodes: number;
    graph_edges: number;
    by_vector: Record<string, number>;
    by_rail: Record<string, number>;
    fraud_by_rail: Record<string, number>;
    benign_anomalies: Record<string, number>;
    benign_anomaly_rate: number;
    per_vector: Record<string, {
      injector: string;
      label: string;
      campaigns: number;
      transactions: number;
      fraud_transactions: number;
      value_extracted: number;
      params: Record<string, number>;
      notes: string;
    }>;
    synthetic_identities: number;
    cover_transactions: number;
    telemetry_coverage: number;
    generation_seconds: number;
    days: number;
  };
  world: {
    customers: number;
    merchants: number;
    accounts: number;
    by_persona: Record<string, number>;
    by_city: Record<string, number>;
    merchant_categories: Record<string, number>;
    devices: number;
  };
  feature_count: number;
  feature_names: string[];
  split: { train_rows: number; calib_rows: number; test_rows: number; split: string };
  narrative_channel: {
    episodes_total: number;
    episodes_train: number;
    train_fraud_share: number;
    in_sample_auc: number | null;
    holdout_auc: number | null;
    caveat?: string;
    fitted: boolean;
  };
}

export interface OperatingPoint {
  threshold: number;
  tp: number; fp: number; fn: number; tn: number;
  precision: number; recall: number; f1: number; fpr: number;
  alert_rate: number;
  value_caught: number; value_missed: number; value_recall: number;
  review_cost: number; false_decline_cost: number; expected_cost: number;
  precision_at_real_prevalence: number;
}

export interface EvalBlock {
  label: string;
  n_test: number;
  n_test_fraud: number;
  test_fraud_rate: number;
  roc_auc: number;
  pr_auc: number;
  brier: number;
  operating_point: OperatingPoint;
  cost_optimal_point: OperatingPoint;
  recall_at_fpr: Record<string, number>;
  per_vector: Record<string, {
    n: number; recall: number; median_score: number;
    value: number; value_recall: number; zero_day: boolean;
  }>;
  per_rail: Record<string, { n: number; fraud: number; recall: number; alert_rate: number }>;
  false_positives_by_benign_anomaly: Record<string, { n: number; false_positive_rate: number }>;
  channels: {
    rules_fired: Record<string, number>;
    fraud_caught_only_by_rules: number;
    fraud_caught_only_by_novelty: number;
    mean_model_score_fraud: number;
    mean_model_score_legit: number;
  };
  curves: {
    roc: { x: number; y: number }[];
    pr: { x: number; y: number }[];
    cost: { threshold: number; alert_rate: number; recall: number; precision: number; expected_cost: number }[];
  };
  score_hist: { edges: number[]; fraud: number[]; legit: number[] };
  thresholds: { cost_optimal: number; budget: number };
}

export interface DetectionData {
  generated_at: string;
  baseline: EvalBlock;
  post_arena: EvalBlock;
  zero_day: Record<string, { n: number; recall: number | null; median_score?: number; mean_score?: number; note?: string }>;
  zero_day_post_arena: Record<string, { n: number; recall: number | null; median_score?: number; mean_score?: number; note?: string }>;
  zero_day_journey: {
    holdout_families: string[];
    before: Record<string, number | null>;
    after: Record<string, number | null>;
    explanation: string;
  };
  feature_importance: { feature: string; auc_drop: number }[];
  novelty_profile: {
    legit_p50: number;
    legit_p99: number;
    by_family: Record<string, {
      n: number; mean_novelty_percentile: number;
      share_above_legit_p99: number; zero_day: boolean;
    }>;
  };
  narrative_stress_test: {
    n: number;
    description?: string;
    max_lift?: number;
    max_lift_at_aggression?: number;
    sweep?: {
      aggression: number; n: number; mean_amount: number; mean_amount_z: number;
      recall_full: number; recall_without_narrative: number; lift: number;
      mean_score_full: number; mean_score_without_narrative: number;
    }[];
  };
  ablations: Record<string, {
    dropped_features: string[];
    roc_auc: number; pr_auc: number; recall: number; precision: number; fpr: number;
    per_vector_recall: Record<string, number>;
    delta_pr_auc: number; delta_recall: number;
  }>;
  rules: { code: string; description: string; confidence: number; vector_hint: string }[];
  model: Record<string, number>;
  cost_model: Record<string, number>;
  realistic_prevalence: number;
  reason_code_method: string;
}

export interface StrainRecord {
  strain_id: string;
  family: string;
  vector_id: string;
  label: string;
  generation: number;
  parents: string[];
  params: Record<string, number>;
  operational_cost: number;
  evasion_rate?: number;
  mean_score?: number;
  median_score?: number;
  fitness?: number;
  viability?: number;
  value_extracted?: number;
  value_evaded?: number;
  value_per_attack?: number;
  n?: number;
  archetype?: string;
}

export interface BlueMetrics {
  auc: number | null;
  threshold: number;
  recall: number;
  precision: number;
  fpr: number;
  alert_rate: number;
  value_recall: number;
}

export interface Generation {
  generation: number;
  population: number;
  attack_rows: number;
  evasion_pre: number;
  evasion_pre_max: number;
  evasion_post: number;
  immunity_gain: number;
  mined: number;
  mined_cumulative: number;
  mined_by_vector: Record<string, number>;
  value_evaded: number;
  blue_before: BlueMetrics;
  blue_after: BlueMetrics;
  fpr_within_budget: boolean;
  elite_centroid: Record<string, number>;
  top_strains: StrainRecord[];
  by_family: Record<string, { n: number; evasion: number; fitness: number; vector_id: string }>;
  seconds: number;
}

export interface ArenaData {
  generated_at: string;
  baseline: BlueMetrics;
  final: BlueMetrics;
  generations: Generation[];
  time_to_immunity_generations: number | null;
  time_to_immunity_minutes: number | null;
  immunity_threshold: number;
  fpr_budget_ceiling: number;
  wall_seconds: number;
  delta: { auc: number; recall: number; fpr: number; value_recall: number };
}

export interface Reason {
  feature: string;
  text: string;
  value: number;
  population_median: number;
  contribution: number;
  log_odds_contribution?: number;
}

export interface ScoredTxn {
  txn_id: string;
  ts: number;
  customer: string;
  persona: string | null;
  rail: string;
  amount: number;
  merchant_category: string | null;
  city: string | null;
  is_fraud: number;
  vector_id: string | null;
  benign_anomaly: string | null;
  score: number;
  model_score: number;
  novelty_percentile: number;
  rule_score: number;
  rules_fired: string[];
  reasons: Reason[];
  decision: "approve" | "review" | "step_up" | "decline";
}

export interface StreamData {
  generated_at?: string;
  transactions: ScoredTxn[];
}

export interface CaseFile extends ScoredTxn {
  vector_id: string;
  family_median_score: number;
  family_n: number;
  episode: {
    kind: string;
    channel: string;
    duration_s: number;
    turns: { speaker: string; text: string }[];
  } | null;
}

export interface CasesData {
  generated_at?: string;
  cases: CaseFile[];
}

export interface GraphData {
  campaign_id?: string;
  note?: string;
  nodes: {
    id: string; label: string; bank: string; age_days: number | null;
    is_mule: boolean; layer: number; in_degree: number; out_degree: number;
  }[];
  edges: { src: string; dst: string; amount: number; ts: number; layer: number }[];
}

export interface RunData {
  generated_at: string;
  version: string;
  profile: string;
  seed: number;
  environment: { python: string; platform: string };
  identify: { vectors: number; discovered: number; simulated: number; families: number; rails: number };
  generate: {
    transactions: number; fraud_transactions: number; fraud_rate: number;
    episodes: number; graph_edges: number; benign_anomaly_rate: number;
    customers: number; merchants: number;
  };
  defend: {
    roc_auc: number; pr_auc: number; recall: number; precision: number;
    fpr: number; alert_rate: number; value_recall: number;
    precision_at_real_prevalence: number; brier: number;
    zero_day_recall: Record<string, number | null>;
  };
  arena: {
    generations: number;
    time_to_immunity_generations: number | null;
    evasion_first: number | null;
    evasion_last: number | null;
    mined_total: number;
    delta: { auc: number; recall: number; fpr: number; value_recall: number } | null;
    wall_seconds: number;
  } | null;
  timings: Record<string, number>;
  total_seconds: number;
}
