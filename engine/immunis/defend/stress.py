"""Targeted stress tests.

Portfolio-level ablations answer "what is this channel worth on average", which
is the wrong question for a channel that exists for a minority of cases.  The
narrative channel is a good example: at portfolio level it looks free, because
most coercion payments are already caught by beneficiary novelty and amount
deviation.  Its value — if it has any — lives on the subset where those signals
are gone.

So rather than asserting that, this module measures it.  It generates the hard
subset explicitly (a high-mimicry operator: aged mule accounts, modest amounts,
screen share turned off before the payment) and scores it with the full model
and with the narrative-ablated model side by side.

If the number comes back flat, that is the finding and it gets reported.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..config import Config
from ..generate.attacks.base import REGISTRY
from ..redteam.evader import Arena, ArenaContext, Strain
from ..util.rng import Rng
from .model import Detector
from .narrative import NarrativeChannel

#: A patient, well-resourced coercion operator. Every knob is set to remove the
#: transaction-side signals a conventional stack relies on: aged mules, amounts
#: shaped under thresholds, the victim taken off screen share before paying.
HARD_COERCION_PARAMS: dict[str, float] = {
    "aggression": 0.42,
    "velocity": 0.30,
    "device_hygiene": 1.0,
    "spread": 0.75,
    "mimicry": 0.92,
    "dwell": 0.55,
    "stealth": 0.85,
    "narrative_intensity": 0.70,
}


def narrative_stress_test(
    cfg: Config,
    ctx: ArenaContext,
    full: Detector,
    ablated: Detector,
    narrative: NarrativeChannel | None,
    *,
    narrative_columns: tuple[str, ...],
    families: tuple[str, ...] = ("digital_arrest", "voice_clone"),
    campaigns: int = 70,
    aggression_sweep: tuple[float, ...] = (0.06, 0.12, 0.22, 0.40, 0.65),
) -> dict[str, Any]:
    """Sweep operator greed and measure what the narrative channel is worth.

    A coercion payment that drains half an account is trivially anomalous on
    amount alone — no conversation needed. The interesting question is the
    other end: what happens when the operator simply takes *less*, so the
    transaction sits inside the victim's own spending distribution and every
    amount-based signal goes quiet.

    That is the trade the attacker actually faces, and it is where a
    cross-modal channel either earns its place or does not. This sweep measures
    it directly instead of asserting it.
    """
    rng = Rng(cfg.seed, "stress/narrative")
    arena = Arena(ctx, cfg, narrative)
    names = full.feature_names
    cols = [names.index(c) for c in narrative_columns if c in names]

    th_full = full.budget_threshold
    th_abl = ablated.budget_threshold

    points: list[dict[str, Any]] = []
    for k, aggression in enumerate(aggression_sweep):
        params = {**HARD_COERCION_PARAMS, "aggression": aggression}
        strains = [
            Strain(f"HARD{k}-{i:02d}", fam, REGISTRY[fam].params(params), 0)
            for i, fam in enumerate(families)
        ]
        result = arena.run(strains, full, rng.fork(f"agg{k}"),
                           attacks_per_strain=campaigns)
        if not len(result.X):
            continue

        X = result.X
        X_ablated = X.copy()
        for c in cols:
            X_ablated[:, c] = 0.0

        s_full = full.score(X)
        s_abl = ablated.score(X_ablated)
        amt_col = names.index("amount")
        z_col = names.index("amount_z_customer")

        points.append({
            "aggression": aggression,
            "n": int(len(X)),
            "mean_amount": round(float(X[:, amt_col].mean()), 2),
            "mean_amount_z": round(float(X[:, z_col].mean()), 3),
            "recall_full": round(float((s_full >= th_full).mean()), 4),
            "recall_without_narrative": round(float((s_abl >= th_abl).mean()), 4),
            "lift": round(float((s_full >= th_full).mean())
                          - float((s_abl >= th_abl).mean()), 4),
            "mean_score_full": round(float(s_full.mean()), 4),
            "mean_score_without_narrative": round(float(s_abl.mean()), 4),
        })

    if not points:
        return {"n": 0, "note": "stress test produced no attacks"}

    best = max(points, key=lambda p: p["lift"])
    return {
        "n": sum(p["n"] for p in points),
        "params": HARD_COERCION_PARAMS,
        "sweep": points,
        "max_lift": best["lift"],
        "max_lift_at_aggression": best["aggression"],
        "lift": best["lift"],
        "recall_full": best["recall_full"],
        "recall_without_narrative": best["recall_without_narrative"],
        "description": (
            "High-mimicry coercion — aged mule beneficiaries, amounts shaped "
            "under step-up thresholds, the victim taken off screen share before "
            "authorising, session pacing close to their own baseline — swept "
            "across operator greed. Low aggression is the regime where every "
            "amount-based signal goes quiet and the conversation is the only "
            "evidence left. It is also the regime where the attack earns least, "
            "which is exactly the trade-off the red agent's value floor prices."
        ),
    }


def novelty_profile(detector: Detector, X: np.ndarray, y: np.ndarray,
                    vectors: np.ndarray, holdout: tuple[str, ...]) -> dict[str, Any]:
    """How far outside the legitimate manifold each family sits.

    The unsupervised channel cannot be judged by how much recall it adds when
    the supervised model already catches everything. What it can be judged on is
    whether it puts genuinely novel strains in the tail — which is the only
    situation it exists for.
    """
    nov = detector.novelty(X)
    legit = nov[y == 0]
    out: dict[str, Any] = {
        "legit_p50": round(float(np.percentile(legit, 50)), 4),
        "legit_p99": round(float(np.percentile(legit, 99)), 4),
        "by_family": {},
    }
    for v in sorted({s for s in vectors.tolist() if s}):
        m = (vectors == v) & (y == 1)
        if not m.sum():
            continue
        out["by_family"][v] = {
            "n": int(m.sum()),
            "mean_novelty_percentile": round(float(nov[m].mean()), 4),
            "share_above_legit_p99": round(
                float((nov[m] > np.percentile(legit, 99)).mean()), 4),
            "zero_day": v in holdout,
        }
    return out
