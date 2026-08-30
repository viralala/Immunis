"""Central configuration for the IMMUNIS engine.

Everything that shapes a run lives here so that a run is reproducible from a
single seed + profile name.  Profiles trade fidelity for wall-clock time:

    fast    ~35k transactions   (unit tests, CI)
    demo    ~165k transactions  (default; full pipeline ~2 min on a laptop)
    full    ~490k transactions  (submission numbers)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

ENGINE_ROOT = Path(__file__).resolve().parent.parent      # <repo>/engine
REPO_ROOT = ENGINE_ROOT.parent                            # <repo>
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
WEB_DATA_DIR = REPO_ROOT / "web" / "public" / "data"


# --------------------------------------------------------------------------
# Economics — used to pick the operating threshold and to price the pitch
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CostModel:
    """Unit economics of a fraud decision, in INR.

    These are the numbers a risk officer already has on a slide, which is why
    we optimise the operating threshold against them instead of using 0.5.
    """

    # Fraction of a missed fraudulent transaction's value that the network
    # ultimately eats (net of recovery, insurance and merchant liability shift).
    fraud_loss_ratio: float = 0.72
    # Cost of routing an alert to a human analyst.
    review_cost: float = 55.0
    # Cost of a false decline: lost interchange + servicing + attrition risk.
    false_decline_cost: float = 420.0
    # Fraction of transactions above threshold that are hard-declined rather
    # than stepped-up (the rest go to step-up / review).
    decline_share: float = 0.35


# --------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PopulationConfig:
    n_customers: int = 2000
    n_merchants: int = 700
    n_days: int = 35
    start_date: str = "2026-06-15"
    # Share of *legitimate* transactions that are deliberately anomalous
    # (travel, first big-ticket purchase, device upgrade, new beneficiary).
    # This is the single most important fidelity knob in the simulator: it is
    # what stops "unusual == fraud" from being trivially true.
    benign_anomaly_rate: float = 0.031
    # Multi-device households / shared family devices.
    shared_device_rate: float = 0.06
    # Share of the portfolio that is genuinely newly onboarded. Without a real
    # young-account cohort, "account age < 7 days" becomes a perfect mule
    # detector and every metric downstream is a fantasy. Real portfolios are
    # full of legitimate new accounts.
    new_account_share: float = 0.10
    # Same argument on the acceptance side: genuinely new merchants exist.
    new_merchant_share: float = 0.13
    # Cover traffic emitted by attacker-controlled identities. Real mules buy
    # groceries; an identity whose every transaction is fraudulent is a
    # simulation artefact, not a mule.
    cover_traffic_per_synthetic: tuple[int, int] = (2, 9)
    # Share of transactions for which session / behavioural telemetry is
    # actually available. In production it is far from universal: different
    # channels, older app versions, third-party acquirers and browser
    # restrictions all remove it. Assuming full coverage is the most common way
    # a synthetic-fraud benchmark flatters itself, so coverage is modelled
    # explicitly and applied identically to fraud and legitimate traffic.
    telemetry_coverage: float = 0.62


# --------------------------------------------------------------------------
# Attack campaign volume
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class AttackConfig:
    # Target fraud prevalence across the whole ledger.
    target_fraud_rate: float = 0.0145
    # Attack families held out of training entirely, to measure cold
    # generalisation to a genuinely unseen typology ("zero-day holdout").
    zero_day_holdout: tuple[str, ...] = ("AV-AGENT-MANDATE", "AV-BIO-CLONE")
    # Real fraud labels are wrong in both directions. A large share of fraud is
    # never reported at all (especially coercion typologies, where victims are
    # ashamed), and a small share of confirmed-fraud labels are actually
    # first-party misuse or operational error. Training on perfect labels
    # produces a model — and a metric — that does not exist in production.
    # Applied to TRAINING labels only; evaluation always uses ground truth.
    label_noise_missed_fraud: float = 0.14
    label_noise_false_fraud: float = 0.0015


# --------------------------------------------------------------------------
# Detector
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DefendConfig:
    test_size: float = 0.30
    calibration_size: float = 0.18          # carved out of the training split
    max_iter: int = 420
    learning_rate: float = 0.06
    max_leaf_nodes: int = 48
    min_samples_leaf: int = 28
    l2_regularization: float = 0.9
    # Operating point: the review budget a mid-size issuer will actually staff,
    # expressed as a share of all transactions that may be alerted.
    alert_budget: float = 0.020
    # Weight of the unsupervised novelty channel when fusing scores.
    novelty_weight: float = 0.18
    # Weight of the narrative (conversation) channel.
    narrative_weight: float = 1.0
    class_weight_positive: float = 6.0


# --------------------------------------------------------------------------
# Red team / co-evolution
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RedTeamConfig:
    generations: int = 8
    population_size: int = 56
    elite_frac: float = 0.28
    mutation_rate: float = 0.35
    mutation_scale: float = 0.22
    strains_per_family: int = 3
    attacks_per_strain: int = 26
    # An evaded strain is only interesting if it still extracts value; the
    # realism penalty stops the red agent "winning" with unprofitable attacks.
    min_value_extracted: float = 4000.0
    realism_penalty_weight: float = 0.55
    immunity_threshold: float = 0.05        # evasion rate defining "immune"
    fpr_budget_multiplier: float = 1.25     # blue may not blow past this


# --------------------------------------------------------------------------
# Top-level
# --------------------------------------------------------------------------

PROFILES: dict[str, dict[str, Any]] = {
    "fast": {"n_customers": 700, "n_merchants": 260, "n_days": 21},
    "demo": {"n_customers": 2000, "n_merchants": 700, "n_days": 35},
    "full": {"n_customers": 4200, "n_merchants": 1500, "n_days": 50},
}


@dataclass(frozen=True)
class Config:
    seed: int = 20260831
    profile: str = "demo"
    population: PopulationConfig = field(default_factory=PopulationConfig)
    attacks: AttackConfig = field(default_factory=AttackConfig)
    defend: DefendConfig = field(default_factory=DefendConfig)
    redteam: RedTeamConfig = field(default_factory=RedTeamConfig)
    costs: CostModel = field(default_factory=CostModel)

    @classmethod
    def for_profile(cls, profile: str = "demo", seed: int = 20260831) -> "Config":
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}; expected {sorted(PROFILES)}")
        base = PopulationConfig()
        pop = PopulationConfig(
            **{**asdict(base), **PROFILES[profile]}
        )
        rt = RedTeamConfig()
        if profile == "fast":
            rt = RedTeamConfig(generations=3, population_size=16, attacks_per_strain=14)
        return cls(seed=seed, profile=profile, population=pop, redteam=rt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "population": asdict(self.population),
            "attacks": {**asdict(self.attacks),
                        "zero_day_holdout": list(self.attacks.zero_day_holdout)},
            "defend": asdict(self.defend),
            "redteam": asdict(self.redteam),
            "costs": asdict(self.costs),
        }
