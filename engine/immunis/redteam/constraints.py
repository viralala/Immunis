"""Realism and profitability constraints on the red agent.

Without constraints, adversarial search always finds the same degenerate
answer: make the attack so small, so slow and so expensive that it evades
everything and earns nothing.  That is not an evasion, it is a surrender, and a
defence hardened against it learns nothing useful.

So every strain the red agent proposes is costed the way an operator would cost
it.  Clean attested devices have to be bought and warmed.  A deep mule
inventory has to be recruited and burned.  High mimicry costs operator time per
victim.  Patience costs working capital.  Fitness is evasion *net of* that
cost, and a strain that fails to clear a value floor is heavily discounted.

The result is that the strains which survive are the ones a real crew would
actually run — which is what makes retraining on them worth anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..generate.attacks.base import PARAM_NAMES, clamp_params

#: Marginal operational cost weight of pushing each knob toward 1.0
#: (or toward 0.0 where the expensive direction is downward).
COST_WEIGHTS: dict[str, tuple[float, str]] = {
    # knob: (weight, direction) — "up" means high values are expensive
    "device_hygiene":      (0.30, "up"),    # attested handsets, warmed profiles
    "spread":              (0.26, "up"),    # mule and card inventory
    "mimicry":             (0.24, "up"),    # operator hours per victim
    "dwell":               (0.14, "up"),    # working capital tied up, freeze risk
    "velocity":            (0.06, "down"),  # patience has an opportunity cost
    "stealth":             (0.05, "up"),    # shaping amounts caps the take
    "aggression":          (0.00, "up"),
    "narrative_intensity": (0.04, "down"),  # softer scripts convert worse
}


@dataclass(frozen=True)
class Constraint:
    """Per-family bounds, so evolution stays inside the typology."""
    lower: dict[str, float]
    upper: dict[str, float]

    def clip(self, params: dict[str, float]) -> dict[str, float]:
        out = dict(params)
        for k in PARAM_NAMES:
            lo = self.lower.get(k, 0.0)
            hi = self.upper.get(k, 1.0)
            out[k] = min(hi, max(lo, float(out.get(k, 0.5))))
        return clamp_params(out)


#: Family-specific bounds. These encode what the typology *is*: card testing
#: without velocity is not card testing, a coercion script with zero narrative
#: intensity does not get the victim to press send.
FAMILY_CONSTRAINTS: dict[str, Constraint] = {
    "digital_arrest": Constraint(
        lower={"narrative_intensity": 0.25, "aggression": 0.20},
        upper={"device_hygiene": 1.0}),
    "voice_clone": Constraint(
        lower={"narrative_intensity": 0.20, "aggression": 0.10},
        upper={}),
    "aitm_otp": Constraint(
        lower={"velocity": 0.20, "aggression": 0.15}, upper={}),
    "bio_clone": Constraint(
        lower={"mimicry": 0.40, "aggression": 0.15}, upper={}),
    "synth_id": Constraint(
        lower={"aggression": 0.30, "dwell": 0.15}, upper={}),
    "deepfake_kyc": Constraint(
        lower={"aggression": 0.20, "spread": 0.10}, upper={}),
    "bin_enum": Constraint(
        lower={"velocity": 0.30, "spread": 0.15}, upper={"aggression": 0.55}),
    "qr_swap": Constraint(
        lower={"aggression": 0.15}, upper={}),
    "token_prov": Constraint(
        lower={"aggression": 0.25}, upper={"dwell": 0.75}),
    "fake_merchant": Constraint(
        lower={"aggression": 0.25, "spread": 0.20}, upper={}),
    "friendly_fraud": Constraint(
        lower={"aggression": 0.20, "mimicry": 0.50}, upper={}),
    "mule_layer": Constraint(
        lower={"aggression": 0.20, "spread": 0.15}, upper={}),
    "agent_inject": Constraint(
        lower={"aggression": 0.20}, upper={}),
    "agent_mandate": Constraint(
        lower={"aggression": 0.25}, upper={}),
}

DEFAULT_CONSTRAINT = Constraint(lower={}, upper={})


def constraint_for(key: str) -> Constraint:
    return FAMILY_CONSTRAINTS.get(key, DEFAULT_CONSTRAINT)


def operational_cost(params: dict[str, float]) -> float:
    """Normalised [0, 1] operating cost of running a strain."""
    total = 0.0
    denom = 0.0
    for k, (w, direction) in COST_WEIGHTS.items():
        v = float(params.get(k, 0.5))
        x = v if direction == "up" else (1.0 - v)
        total += w * x
        denom += w
    return total / max(1e-9, denom)


def fitness(evasion_rate: float, value_extracted: float, params: dict[str, float],
            *, min_value: float, penalty_weight: float,
            n_attacks: int = 1) -> dict[str, float]:
    """Red-team objective.

    ``evasion_rate`` is the share of the strain's transactions the current
    detector scored below its operating threshold.  It is discounted by the
    strain's operating cost and by a value floor, so evading with a strain that
    earns nothing scores near zero.
    """
    cost = operational_cost(params)
    per_attack_value = value_extracted / max(1, n_attacks)
    # Smooth viability ramp rather than a hard floor, so the search still has a
    # usable gradient just below the threshold.
    viability = 1.0 / (1.0 + pow(2.718281828, -(per_attack_value - min_value) / max(1.0, min_value * 0.45)))
    score = evasion_rate * (0.35 + 0.65 * viability) - penalty_weight * cost * evasion_rate
    return {
        "fitness": round(max(0.0, score), 5),
        "operational_cost": round(cost, 4),
        "viability": round(viability, 4),
        "value_per_attack": round(per_attack_value, 2),
    }
