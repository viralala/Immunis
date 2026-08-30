"""Per-transaction reason codes.

An alert an analyst cannot act on is a cost, not a control, so every score
IMMUNIS emits comes with the reasons behind it.

The method is ablation, not SHAP: for the candidate features, substitute the
population median and measure how far the fused score falls.  Whatever moves
the score most is what drove it.  This is exact with respect to the deployed
scoring function — including the rule and novelty channels, which a
tree-explainer would silently ignore — cheap enough to run inline, and simple
enough to describe to a regulator in one sentence.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .features import REASON_TEXT
from .model import Detector


class Explainer:
    def __init__(self, detector: Detector, X_train: np.ndarray,
                 feature_names: list[str], candidates: list[str] | None = None,
                 max_candidates: int = 34) -> None:
        self.detector = detector
        self.names = feature_names
        self.median = np.nan_to_num(
            np.nanmedian(X_train, axis=0), nan=0.0).astype(np.float32)
        pool = candidates or [n for n in feature_names if n in REASON_TEXT]
        self.candidate_idx = [feature_names.index(n) for n in pool
                              if n in feature_names][:max_candidates]

    @staticmethod
    def _logit(p: np.ndarray | float) -> np.ndarray:
        q = np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1 - 1e-6)
        return np.log(q / (1 - q))

    def explain(self, x: np.ndarray, top_k: int = 4) -> dict[str, Any]:
        """Explain one transaction (1-D feature vector).

        Ranking happens in log-odds rather than probability space. A confident
        score sits on a flat part of the probability curve, so a probability
        drop under-reports every driver at once and the explanation collapses to
        a single reason. Log-odds keeps the ordering meaningful all the way to
        0.999, while the reported contribution stays in probability so an
        analyst can read it.
        """
        x = np.asarray(x, dtype=np.float32).reshape(1, -1)
        base, parts = self.detector.score(x, with_parts=True)
        base_score = float(base[0])
        base_logit = float(self._logit(base_score))

        # Build the ablation batch in one shot: one row per candidate feature.
        k = len(self.candidate_idx)
        batch = np.repeat(x, k, axis=0)
        for r, j in enumerate(self.candidate_idx):
            batch[r, j] = self.median[j]
        ablated = self.detector.score(batch)
        drops = base_score - ablated
        logit_drops = base_logit - self._logit(ablated)

        order = np.argsort(-logit_drops)
        reasons = []
        for r in order[:top_k]:
            j = self.candidate_idx[int(r)]
            drop = float(drops[int(r)])
            if float(logit_drops[int(r)]) <= 0.08:
                continue
            name = self.names[j]
            reasons.append({
                "feature": name,
                "text": REASON_TEXT.get(name, name.replace("_", " ")),
                "value": round(float(x[0, j]), 4),
                "population_median": round(float(self.median[j]), 4),
                "contribution": round(drop, 4),
                "log_odds_contribution": round(float(logit_drops[int(r)]), 3),
            })

        return {
            "score": round(base_score, 4),
            "model_score": round(float(parts["model"][0]), 4),
            "novelty_percentile": round(float(parts["novelty"][0]), 4),
            "rule_score": round(float(parts["rules"][0]), 4),
            "rules_fired": parts["fired"][0],
            "reasons": reasons,
            "decision": self.decision(base_score),
        }

    def decision(self, score: float) -> str:
        if score >= max(self.detector.threshold, self.detector.budget_threshold):
            return "decline"
        if score >= min(self.detector.threshold, self.detector.budget_threshold):
            return "step_up"
        if score >= min(self.detector.threshold, self.detector.budget_threshold) * 0.55:
            return "review"
        return "approve"

    def explain_many(self, X: np.ndarray, top_k: int = 4) -> list[dict[str, Any]]:
        return [self.explain(X[i], top_k=top_k) for i in range(len(X))]
