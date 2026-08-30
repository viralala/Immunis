"""Evaluation — including the numbers most synthetic-fraud demos leave out.

Anyone can report AUC on synthetic data.  The measurements that actually
predict production behaviour are:

  * **per-typology recall** at one shared operating threshold — an average hides
    the family you are blind to;
  * **false positives on benign anomalies** specifically — real travel, real
    big-ticket purchases, real device upgrades. If your FPR is only low on
    boring traffic, it is not low;
  * **zero-day recall** on attack families removed from training entirely;
  * **prevalence-adjusted precision** at a realistic production fraud rate,
    rather than at the elevated rate the simulation is run at;
  * **expected cost in rupees**, because that is the language the decision is
    actually made in.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from ..config import CostModel
from .model import Detector, prevalence_adjusted_precision

#: The fraud prevalence a real card/UPI portfolio sees, used to re-express
#: precision honestly. The simulation runs hotter so every typology is learnable.
REALISTIC_PREVALENCE = 0.0012


def _at_threshold(scores: np.ndarray, y: np.ndarray, amounts: np.ndarray,
                  th: float, costs: CostModel) -> dict[str, Any]:
    flag = scores >= th
    tp = int((flag & (y == 1)).sum())
    fp = int((flag & (y == 0)).sum())
    fn = int((~flag & (y == 1)).sum())
    tn = int((~flag & (y == 0)).sum())
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    caught_value = float(amounts[flag & (y == 1)].sum())
    missed_value = float(amounts[(~flag) & (y == 1)].sum())
    total_fraud_value = caught_value + missed_value
    review_cost = (tp + fp) * costs.review_cost
    decline_cost = fp * costs.decline_share * costs.false_decline_cost
    return {
        "threshold": float(th),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fp / max(1, fp + tn), 5),
        "alert_rate": round(float(flag.mean()), 5),
        "value_caught": round(caught_value, 2),
        "value_missed": round(missed_value, 2),
        "value_recall": round(caught_value / max(1.0, total_fraud_value), 4),
        "review_cost": round(review_cost, 2),
        "false_decline_cost": round(decline_cost, 2),
        "expected_cost": round(missed_value * costs.fraud_loss_ratio
                               + review_cost + decline_cost, 2),
        "precision_at_real_prevalence": round(prevalence_adjusted_precision(
            precision, float((y == 1).mean()), REALISTIC_PREVALENCE), 5),
    }


def _curve_points(x: np.ndarray, y: np.ndarray, k: int = 160) -> list[dict]:
    if len(x) <= k:
        idx = np.arange(len(x))
    else:
        idx = np.unique(np.linspace(0, len(x) - 1, k).astype(int))
    return [{"x": round(float(x[i]), 5), "y": round(float(y[i]), 5)} for i in idx]


def evaluate(detector: Detector, X: np.ndarray, y: np.ndarray, meta: dict,
             split, costs: CostModel, *, zero_day: tuple[str, ...] = (),
             label: str = "test") -> dict[str, Any]:
    test = split.test
    Xt, yt = X[test], y[test]
    scores, parts = detector.score(Xt, with_parts=True)
    amounts = meta["amount"][test].astype(np.float64)
    vectors = meta["vector_id"][test]
    benign = meta["benign_anomaly"][test]
    rails = meta["rail"][test]

    thresholds = detector.choose_threshold(scores, yt, amounts)
    th_cost = thresholds["cost_optimal"]["threshold"]
    th_budget = thresholds["budget_threshold"]

    roc_auc = float(roc_auc_score(yt, scores)) if len(set(yt.tolist())) > 1 else float("nan")
    pr_auc = float(average_precision_score(yt, scores))
    brier = float(brier_score_loss(yt, np.clip(scores, 0, 1)))

    op = _at_threshold(scores, yt, amounts, th_budget, costs)
    op_cost = _at_threshold(scores, yt, amounts, th_cost, costs)

    # -- per-typology recall at the shared operating threshold -------------
    flag = scores >= th_budget
    per_vector: dict[str, dict] = {}
    for v in sorted({s for s in vectors.tolist() if s}):
        m = vectors == v
        n_v = int(m.sum())
        if n_v == 0:
            continue
        caught = int((flag & m).sum())
        per_vector[v] = {
            "n": n_v,
            "recall": round(caught / n_v, 4),
            "median_score": round(float(np.median(scores[m])), 4),
            "value": round(float(amounts[m].sum()), 2),
            "value_recall": round(float(amounts[m & flag].sum())
                                  / max(1.0, float(amounts[m].sum())), 4),
            "zero_day": v in zero_day,
        }

    # -- the false-positive story -----------------------------------------
    legit = yt == 0
    fp_by_benign: dict[str, dict] = {}
    normal_legit = legit & (benign == "")
    fp_by_benign["__normal__"] = {
        "n": int(normal_legit.sum()),
        "false_positive_rate": round(float((flag & normal_legit).sum())
                                     / max(1, int(normal_legit.sum())), 5),
    }
    for b in sorted({s for s in benign.tolist() if s}):
        m = legit & (benign == b)
        if m.sum() == 0:
            continue
        fp_by_benign[b] = {
            "n": int(m.sum()),
            "false_positive_rate": round(float((flag & m).sum()) / int(m.sum()), 5),
        }

    # -- recall at fixed false-positive budgets ---------------------------
    fpr_c, tpr_c, th_c = roc_curve(yt, scores)
    recall_at_fpr = {}
    for target in (0.001, 0.005, 0.01, 0.02, 0.05):
        i = int(np.searchsorted(fpr_c, target, side="right") - 1)
        i = max(0, min(i, len(tpr_c) - 1))
        recall_at_fpr[f"fpr_{target}"] = round(float(tpr_c[i]), 4)

    prec_c, rec_c, _ = precision_recall_curve(yt, scores)

    # -- per-rail ----------------------------------------------------------
    per_rail = {}
    for r in sorted(set(rails.tolist())):
        m = rails == r
        if m.sum() == 0:
            continue
        mf = m & (yt == 1)
        per_rail[r] = {
            "n": int(m.sum()),
            "fraud": int(mf.sum()),
            "recall": round(float((flag & mf).sum()) / max(1, int(mf.sum())), 4),
            "alert_rate": round(float(flag[m].mean()), 5),
        }

    # -- channel attribution ----------------------------------------------
    fired_counter: Counter[str] = Counter()
    for codes in parts["fired"]:
        fired_counter.update(codes)
    caught_only_by_rules = int(((parts["rules"] >= th_budget)
                                & (parts["model"] < th_budget) & (yt == 1)).sum())
    caught_only_by_novelty = int(((parts["novelty"] > 0.985)
                                  & (parts["model"] < th_budget) & (yt == 1)).sum())

    return {
        "label": label,
        "n_test": int(test.sum()),
        "n_test_fraud": int(yt.sum()),
        "test_fraud_rate": round(float(yt.mean()), 5),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier": round(brier, 5),
        "operating_point": op,
        "cost_optimal_point": op_cost,
        "recall_at_fpr": recall_at_fpr,
        "per_vector": per_vector,
        "per_rail": per_rail,
        "false_positives_by_benign_anomaly": fp_by_benign,
        "channels": {
            "rules_fired": dict(fired_counter.most_common()),
            "fraud_caught_only_by_rules": caught_only_by_rules,
            "fraud_caught_only_by_novelty": caught_only_by_novelty,
            "mean_model_score_fraud": round(float(parts["model"][yt == 1].mean()), 4),
            "mean_model_score_legit": round(float(parts["model"][yt == 0].mean()), 4),
        },
        "curves": {
            "roc": _curve_points(fpr_c, tpr_c),
            "pr": _curve_points(rec_c[::-1], prec_c[::-1]),
            "cost": [
                {"threshold": round(p["threshold"], 5),
                 "alert_rate": round(p["alert_rate"], 5),
                 "recall": round(p["recall"], 4),
                 "precision": round(p["precision"], 4),
                 "expected_cost": p["expected_cost"]}
                for p in thresholds["curve"][::3]
            ],
        },
        "score_hist": _histogram(scores, yt),
        "thresholds": {"cost_optimal": float(th_cost), "budget": float(th_budget)},
    }


def _histogram(scores: np.ndarray, y: np.ndarray, bins: int = 40) -> dict:
    edges = np.linspace(0.0, 1.0, bins + 1)
    h_f, _ = np.histogram(scores[y == 1], bins=edges)
    h_l, _ = np.histogram(scores[y == 0], bins=edges)
    return {
        "edges": [round(float(e), 4) for e in edges],
        "fraud": [int(v) for v in h_f],
        "legit": [int(v) for v in h_l],
    }


def zero_day_report(detector: Detector, X: np.ndarray, y: np.ndarray, meta: dict,
                    split, holdout: tuple[str, ...], threshold: float) -> dict:
    """Recall on attack families that were removed from training entirely."""
    test = split.test
    Xt, yt = X[test], y[test]
    vectors = meta["vector_id"][test]
    scores = detector.score(Xt)
    flag = scores >= threshold
    out = {}
    for v in holdout:
        m = (vectors == v) & (yt == 1)
        n = int(m.sum())
        if n == 0:
            out[v] = {"n": 0, "recall": None,
                      "note": "no test-split examples for this family"}
            continue
        out[v] = {
            "n": n,
            "recall": round(float((flag & m).sum()) / n, 4),
            "median_score": round(float(np.median(scores[m])), 4),
            "mean_score": round(float(scores[m].mean()), 4),
        }
    known = (~np.isin(vectors, list(holdout))) & (yt == 1)
    out["__known_families__"] = {
        "n": int(known.sum()),
        "recall": round(float((flag & known).sum()) / max(1, int(known.sum())), 4),
    }
    return out


def permutation_importance_report(detector: Detector, X: np.ndarray, y: np.ndarray,
                                  split, feature_names: list[str],
                                  *, n_sample: int = 9000, top_k: int = 28,
                                  seed: int = 5) -> list[dict]:
    """Permutation importance of the fused score, on a test subsample.

    Measured against the *fused* score rather than the GBM alone, so the rule
    and novelty channels are represented in the attribution.
    """
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(split.test)
    if len(idx) > n_sample:
        # Keep every fraud row — they are what the metric is sensitive to.
        pos = idx[y[idx] == 1]
        neg = idx[y[idx] == 0]
        keep_neg = rng.choice(neg, size=max(0, n_sample - len(pos)), replace=False)
        idx = np.concatenate([pos, keep_neg])
    Xs, ys = X[idx], y[idx]
    if len(set(ys.tolist())) < 2:
        return []

    base = float(roc_auc_score(ys, detector.score(Xs)))
    out = []
    for j, name in enumerate(feature_names):
        Xp = Xs.copy()
        rng.shuffle(Xp[:, j])
        try:
            drop = base - float(roc_auc_score(ys, detector.score(Xp)))
        except Exception:
            drop = 0.0
        out.append({"feature": name, "auc_drop": round(drop, 5)})
    out.sort(key=lambda d: -d["auc_drop"])
    return out[:top_k]
