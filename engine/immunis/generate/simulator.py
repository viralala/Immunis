"""Simulation orchestrator — builds the full ledger the detector is trained on."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..util.rng import Rng
from . import attacks as attack_pkg
from .attacks.base import REGISTRY, AttackBatch
from .behaviour import epoch_of, generate_cover_traffic, generate_legit
from .narrative import Episode, attach_benign_episodes, reset_counter
from .population import World, build_world


@dataclass
class Ledger:
    """One complete simulated payment ledger."""

    transactions: list[dict]
    episodes: list[Episode]
    edges: list[dict]
    world: World
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.transactions)

    @property
    def n_fraud(self) -> int:
        return sum(t["is_fraud"] for t in self.transactions)

    def summary(self) -> dict:
        by_vector = Counter(t["vector_id"] for t in self.transactions if t["is_fraud"])
        by_rail = Counter(t["rail"] for t in self.transactions)
        fraud_by_rail = Counter(t["rail"] for t in self.transactions if t["is_fraud"])
        benign_anom = Counter(t["benign_anomaly"] for t in self.transactions
                              if t.get("benign_anomaly"))
        fraud_value = sum(t["amount"] for t in self.transactions if t["is_fraud"])
        total_value = sum(t["amount"] for t in self.transactions)
        return {
            "transactions": self.n,
            "fraud_transactions": self.n_fraud,
            "fraud_rate": round(self.n_fraud / max(1, self.n), 5),
            "fraud_value": round(fraud_value, 2),
            "total_value": round(total_value, 2),
            "fraud_value_share": round(fraud_value / max(1.0, total_value), 5),
            "episodes": len(self.episodes),
            "fraud_episodes": sum(e.is_fraud for e in self.episodes),
            "graph_edges": len(self.edges),
            "by_vector": dict(by_vector.most_common()),
            "by_rail": dict(by_rail),
            "fraud_by_rail": dict(fraud_by_rail),
            "benign_anomalies": dict(benign_anom),
            "benign_anomaly_rate": round(
                sum(benign_anom.values()) / max(1, self.n - self.n_fraud), 5),
            **self.meta,
        }


#: Telemetry that is only present when the channel actually captures it.
_OPTIONAL_TELEMETRY = ("session_duration_s", "hesitation_ms", "app_switches",
                       "form_corrections", "typing_variance", "screen_share",
                       "call_active")


def _mask_telemetry(transactions: list[dict], rng: Rng, coverage: float) -> int:
    """Remove session/behavioural telemetry from a share of the ledger.

    Applied independently of the label, so it degrades the detector's advantage
    exactly the way missing telemetry does in production — and forces the model
    to work from authorisation-only features on a third of the traffic.
    """
    if coverage >= 0.999:
        return 0
    masked = 0
    for t in transactions:
        if rng.chance(1.0 - coverage):
            for f in _OPTIONAL_TELEMETRY:
                t[f] = None
            masked += 1
    return masked


def allocate_budget(total_fraud_txns: int, keys: list[str]) -> dict[str, int]:
    """Split the fraud budget across injectors by weight, in *campaigns*."""
    weights = {k: REGISTRY[k].weight for k in keys}
    total_w = sum(weights.values())
    out: dict[str, int] = {}
    for k in keys:
        share = weights[k] / total_w
        txns = total_fraud_txns * share
        out[k] = max(1, int(round(txns / max(0.5, REGISTRY[k].txns_per_campaign))))
    return out


def simulate(cfg: Config, *, injector_keys: list[str] | None = None,
             param_overrides: dict[str, dict[str, float]] | None = None,
             verbose: bool = True) -> Ledger:
    """Run one full simulation: world → legitimate traffic → attack overlay."""
    t_start = time.perf_counter()
    rng = Rng(cfg.seed, "sim")
    reset_counter()
    attack_pkg.reset_sequences()

    world = build_world(cfg.population, rng)
    base_customer_ids = {c.customer_id for c in world.customers}
    if verbose:
        print(f"  world      : {len(world.customers)} customers, "
              f"{len(world.merchants)} merchants")

    legit = generate_legit(world, rng, cfg.population)
    if verbose:
        print(f"  legitimate : {len(legit):,} transactions")

    keys = injector_keys if injector_keys is not None else sorted(REGISTRY.keys())
    target_fraud = int(len(legit) * cfg.attacks.target_fraud_rate /
                       max(1e-6, 1 - cfg.attacks.target_fraud_rate))
    budget = allocate_budget(target_fraud, keys)

    t0 = epoch_of(cfg.population.start_date)
    merged = AttackBatch()
    per_vector: dict[str, dict] = {}

    for key in keys:
        inj = REGISTRY[key]
        params = inj.params((param_overrides or {}).get(key))
        r = rng.fork(f"attack/{key}")
        batch = inj.run(world, r, cfg.population, params, budget[key], t0)
        per_vector[inj.vector_id] = {
            "injector": key,
            "label": inj.label,
            "campaigns": batch.campaigns,
            "transactions": len(batch.transactions),
            "fraud_transactions": sum(t["is_fraud"] for t in batch.transactions),
            "value_extracted": round(batch.value_extracted, 2),
            "params": params,
            "notes": batch.notes,
        }
        merged.extend(batch)
        if verbose:
            print(f"  attack     : {inj.vector_id:<22} "
                  f"{len(batch.transactions):>6,} txns  "
                  f"{batch.campaigns:>4} campaigns")

    # Attacker-controlled identities also live ordinary lives — see
    # generate_cover_traffic for why this matters to the metrics.
    synthetic_ids = [c.customer_id for c in world.customers
                     if c.customer_id not in base_customer_ids]
    cover = generate_cover_traffic(world, rng, cfg.population, synthetic_ids, t0)
    if verbose and cover:
        print(f"  cover      : {len(cover):,} legitimate transactions from "
              f"{len(synthetic_ids):,} attacker-controlled identities")

    transactions = legit + merged.transactions + cover
    transactions.sort(key=lambda x: x["ts"])

    _mask_telemetry(transactions, rng.fork("telemetry"),
                    cfg.population.telemetry_coverage)

    benign_eps = attach_benign_episodes(transactions, rng)
    episodes = merged.episodes + benign_eps

    ledger = Ledger(
        transactions=transactions,
        episodes=episodes,
        edges=merged.edges,
        world=world,
        meta={
            "profile": cfg.profile,
            "seed": cfg.seed,
            "days": cfg.population.n_days,
            "start_date": cfg.population.start_date,
            "per_vector": per_vector,
            "synthetic_identities": len(synthetic_ids),
            "cover_transactions": len(cover),
            "telemetry_coverage": cfg.population.telemetry_coverage,
            "generation_seconds": round(time.perf_counter() - t_start, 2),
        },
    )
    if verbose:
        s = ledger.summary()
        print(f"  ledger     : {s['transactions']:,} txns, "
              f"{s['fraud_transactions']:,} fraud "
              f"({s['fraud_rate'] * 100:.2f}%), "
              f"{s['episodes']:,} episodes, {s['graph_edges']:,} edges "
              f"[{ledger.meta['generation_seconds']}s]")
    return ledger
