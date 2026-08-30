"""The Antibody — IMMUNIS's hybrid detector.

Four channels, fused with a noisy-OR:

  1. **Supervised GBM** over ~100 causal features. Gradient boosting, not a deep
     net, because an issuer has to deploy, monitor and explain this thing, and
     because trees are what actually win on tabular payment data.
  2. **Novelty channel** (isolation forest fitted on legitimate training traffic
     only). Supervised models cannot fire on a strain no label has ever
     described; this can. It only contributes in its extreme tail, so it adds
     recall on zero-days without flooding the alert queue.
  3. **Rule layer** — a small set of high-precision, deterministic conjunctions.
     Every fraud team keeps rules, for good reasons: they are auditable, they
     can be shipped in an afternoon when a new typology lands, and a regulator
     can read them. They are part of the model, not an embarrassment.
  4. **Narrative channel** — the conversation score, entering as a feature of
     channel 1 (see ``narrative.py``).

Two deliberate choices about honesty:

  * the train/test split is **temporal**, not random, so the model is always
    evaluated on the future — the only split that predicts production;
  * probabilities are **isotonically calibrated** on a held-out slice, so the
    cost-optimal threshold is computed on numbers that mean what they say.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.calibration import IsotonicRegression
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest

from ..config import CostModel, DefendConfig

# ---------------------------------------------------------------------------
# Rule layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    code: str
    description: str
    confidence: float
    vector_hint: str

    def evaluate(self, X: np.ndarray, c: dict[str, int]) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError


def _rules() -> list[tuple[str, str, float, str, Any]]:
    """(code, description, confidence, vector hint, predicate)."""
    return [
        ("R-COERCION-01",
         "Screen share active while paying a first-ever beneficiary above 3x the "
         "customer's own p95 ticket",
         0.88, "AV-DIGITAL-ARREST",
         lambda X, c: (X[:, c["screen_share"]] > 0)
                      & (X[:, c["is_new_beneficiary"]] > 0)
                      & (X[:, c["amount_to_p95"]] > 3.0)),

        ("R-COERCION-02",
         "Long in-call session, new beneficiary under 7 days old, amount above "
         "5x the customer's p95",
         0.82, "AV-DIGITAL-ARREST",
         lambda X, c: (X[:, c["call_active"]] > 0)
                      & (X[:, c["is_new_beneficiary"]] > 0)
                      & (X[:, c["benef_age_days"]] < 7.0)
                      & (X[:, c["amount_to_p95"]] > 5.0)),

        ("R-MULE-01",
         "Beneficiary passing funds through within 5 minutes on an account under "
         "30 days old",
         0.85, "AV-MULE-LAYER",
         lambda X, c: (X[:, c["benef_dwell_secs"]] < 300.0)
                      & (X[:, c["benef_passthrough_ratio"]] > 0.75)
                      & (X[:, c["benef_age_days"]] < 30.0)),

        ("R-MULE-02",
         "Young beneficiary receiving from 8+ unrelated payers within 24 hours",
         0.80, "AV-QR-SWAP",
         lambda X, c: (X[:, c["benef_distinct_payers_24h"]] >= 8.0)
                      & (X[:, c["benef_age_days"]] < 15.0)),

        ("R-MULE-03",
         "Sending account relaying value it received minutes earlier",
         0.78, "AV-MULE-LAYER",
         lambda X, c: (X[:, c["sender_dwell_secs"]] < 900.0)
                      & (X[:, c["sender_passthrough_ratio"]] > 0.80)
                      & (X[:, c["customer_account_age_days"]] < 60.0)),

        ("R-TESTING-01",
         "Micro-authorisation from a device already seen across 8+ unrelated "
         "customers",
         0.86, "AV-BIN-ENUM",
         lambda X, c: (X[:, c["device_customer_count"]] >= 8.0)
                      & (X[:, c["amount"]] < 250.0)),

        ("R-TAKEOVER-01",
         "Impossible travel: implied speed above 900 km/h between transactions",
         0.72, "AV-AITM-OTP",
         lambda X, c: (X[:, c["travel_speed_kmh"]] > 900.0)
                      & (X[:, c["dist_from_last_km"]] > 400.0)),

        ("R-TAKEOVER-02",
         "New device, emulated or unattested, transacting above 4x the "
         "customer's p95",
         0.80, "AV-AITM-OTP",
         lambda X, c: (X[:, c["is_new_device"]] > 0)
                      & ((X[:, c["device_is_emulator"]] > 0)
                         | (X[:, c["device_attested"]] < 1))
                      & (X[:, c["amount_to_p95"]] > 4.0)),

        ("R-TOKEN-01",
         "Instrument or token provisioned under an hour ago used for a "
         "high-value purchase",
         0.83, "AV-TOKEN-PROV",
         lambda X, c: (X[:, c["instrument_age_days"]] < 0.042)
                      & (X[:, c["amount_to_p95"]] > 2.5)),

        ("R-CLONE-01",
         "Interaction cadence variance collapsed below a quarter of the "
         "customer's norm with zero correction events",
         0.74, "AV-BIO-CLONE",
         lambda X, c: (X[:, c["typing_variance_ratio"]] < 0.25)
                      & (X[:, c["form_corrections"]] < 1.0)
                      & (X[:, c["is_new_merchant"]] > 0)),

        ("R-AGENT-01",
         "Agent purchase diverges from mandate intent and is pinned near the "
         "mandate ceiling",
         0.84, "AV-AGENT-INJECT",
         lambda X, c: (X[:, c["is_agentic"]] > 0)
                      & (X[:, c["mandate_intent_match"]] < 1.0)
                      & (X[:, c["amount_to_mandate_ceiling"]] > 0.7)),

        ("R-AGENT-02",
         "Mandate ceiling more than 20x the customer's typical ticket, drawn "
         "down without any human confirmation",
         0.80, "AV-AGENT-MANDATE",
         lambda X, c: (X[:, c["is_agentic"]] > 0)
                      & (X[:, c["mandate_ceiling_to_typical"]] > 20.0)
                      & (X[:, c["human_confirmations"]] < 1.0)
                      & (X[:, c["mandate_drawdown_ratio"]] > 0.5)),

        ("R-MERCHANT-01",
         "Merchant under 30 days old with effectively no repeat customers "
         "taking above-category tickets",
         0.70, "AV-FAKE-MERCH",
         lambda X, c: (X[:, c["merchant_age_days"]] < 30.0)
                      & (X[:, c["merchant_repeat_rate"]] < 0.05)
                      & (X[:, c["merchant_distinct_customers"]] > 6.0)
                      & (X[:, c["amount_to_merchant_mean"]] > 1.6)),

        ("R-DISPUTE-01",
         "Customer with 3+ disputes in 90 days transacting in a high-resale "
         "category",
         0.68, "AV-FRIENDLY-FRAUD",
         lambda X, c: (X[:, c["cust_prior_disputes_90d"]] >= 3.0)
                      & (X[:, c["merchant_is_liquid"]] + X[:, c["amount_to_p95"]] > 2.0)),
    ]


class RuleLayer:
    def __init__(self, feature_names: list[str]) -> None:
        self.cols = {n: i for i, n in enumerate(feature_names)}
        self.rules = _rules()

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, list[list[str]]]:
        """Return (max confidence per row, list of fired rule codes per row)."""
        score = np.zeros(len(X), dtype=np.float32)
        fired: list[list[str]] = [[] for _ in range(len(X))]
        for code, _desc, conf, _hint, pred in self.rules:
            mask = pred(X, self.cols)
            score = np.maximum(score, mask.astype(np.float32) * conf)
            for i in np.flatnonzero(mask):
                fired[int(i)].append(code)
        return score, fired

    def catalogue(self) -> list[dict]:
        return [{"code": c, "description": d, "confidence": conf, "vector_hint": h}
                for c, d, conf, h, _ in self.rules]


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------

@dataclass
class Split:
    train: np.ndarray
    calib: np.ndarray
    test: np.ndarray
    boundary_ts: float
    calib_boundary_ts: float

    def to_dict(self) -> dict:
        return {
            "train_rows": int(self.train.sum()),
            "calib_rows": int(self.calib.sum()),
            "test_rows": int(self.test.sum()),
            "split": "temporal",
        }


def apply_label_noise(y: np.ndarray, train_mask: np.ndarray, *,
                      missed_fraud: float, false_fraud: float,
                      seed: int = 31) -> np.ndarray:
    """Corrupt TRAINING labels the way reality corrupts them.

    A large share of fraud is never reported — coercion victims in particular
    rarely come forward — and a small share of confirmed-fraud labels are
    actually first-party misuse. Training on perfect labels produces a model
    that cannot exist. Evaluation always uses ground truth, so what this
    changes is the difficulty of the learning problem, not the honesty of the
    measurement.
    """
    rng = np.random.default_rng(seed)
    y_noisy = y.copy()
    fraud_rows = np.flatnonzero(train_mask & (y == 1))
    if len(fraud_rows) and missed_fraud > 0:
        flip = rng.random(len(fraud_rows)) < missed_fraud
        y_noisy[fraud_rows[flip]] = 0
    legit_rows = np.flatnonzero(train_mask & (y == 0))
    if len(legit_rows) and false_fraud > 0:
        flip = rng.random(len(legit_rows)) < false_fraud
        y_noisy[legit_rows[flip]] = 1
    return y_noisy


def temporal_split(ts: np.ndarray, cfg: DefendConfig) -> Split:
    """Train on the past, calibrate on the recent past, test on the future.

    A random split on payment data leaks: the same campaign, the same mule
    account, the same device appears on both sides. Time is the only split that
    answers the question a bank actually asks — will this work next week?
    """
    order = np.argsort(ts, kind="stable")
    n = len(ts)
    test_start = int(n * (1 - cfg.test_size))
    calib_start = int(test_start * (1 - cfg.calibration_size))

    train = np.zeros(n, dtype=bool)
    calib = np.zeros(n, dtype=bool)
    test = np.zeros(n, dtype=bool)
    train[order[:calib_start]] = True
    calib[order[calib_start:test_start]] = True
    test[order[test_start:]] = True
    return Split(train, calib, test,
                 boundary_ts=float(ts[order[test_start]]),
                 calib_boundary_ts=float(ts[order[calib_start]]))


# ---------------------------------------------------------------------------
# The detector
# ---------------------------------------------------------------------------

@dataclass
class Detector:
    cfg: DefendConfig
    costs: CostModel
    feature_names: list[str] = field(default_factory=list)
    categorical_idx: list[int] = field(default_factory=list)
    gbm: HistGradientBoostingClassifier | None = None
    iso: IsolationForest | None = None
    calibrator: IsotonicRegression | None = None
    rules: RuleLayer | None = None
    novelty_ref: np.ndarray | None = None
    _nov_median: np.ndarray | None = None
    threshold: float = 0.5
    budget_threshold: float = 0.5
    report: dict[str, Any] = field(default_factory=dict)

    # -- fit ---------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray, split: Split,
            *, exclude_train_mask: np.ndarray | None = None,
            sample_weight_extra: np.ndarray | None = None,
            extra: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
            refit_novelty: bool = True) -> "Detector":
        """Fit the four channels.

        ``extra`` is the co-evolution hook: (X, y, sample_weight) rows mined by
        the red agent in previous generations. They join the training set with
        their own weights so that yesterday's evasions become today's hard
        negatives — the mechanism that closes the loop.
        """
        self.rules = RuleLayer(self.feature_names)

        train_mask = split.train.copy()
        if exclude_train_mask is not None:
            train_mask &= ~exclude_train_mask

        Xtr, ytr = X[train_mask], y[train_mask]
        w = np.where(ytr == 1, self.cfg.class_weight_positive, 1.0).astype(np.float64)
        if sample_weight_extra is not None:
            w *= sample_weight_extra[train_mask]

        if extra is not None and len(extra[0]):
            Xe, ye, we = extra
            Xtr = np.vstack([Xtr, Xe.astype(np.float32)])
            ytr = np.concatenate([ytr, ye.astype(np.int8)])
            w = np.concatenate([w, we.astype(np.float64)])

        self.gbm = HistGradientBoostingClassifier(
            max_iter=self.cfg.max_iter,
            learning_rate=self.cfg.learning_rate,
            max_leaf_nodes=self.cfg.max_leaf_nodes,
            min_samples_leaf=self.cfg.min_samples_leaf,
            l2_regularization=self.cfg.l2_regularization,
            categorical_features=self.categorical_idx or None,
            early_stopping=True,
            validation_fraction=0.12,
            n_iter_no_change=25,
            random_state=7,
        )
        self.gbm.fit(Xtr, ytr, sample_weight=w)

        # -- novelty channel: legitimate training traffic only --------------
        # In the co-evolution loop this is reused across generations: the
        # channel is fitted on legitimate traffic, which the red agent never
        # changes, so refitting it every round would only burn time.
        if not refit_novelty and self.iso is not None and self.novelty_ref is not None:
            self._finish_fit(X, y, split, train_mask, ytr, extra)
            return self

        legit = Xtr[ytr == 0]
        if len(legit) > 3000:
            idx = np.random.default_rng(11).choice(len(legit), size=min(40_000, len(legit)),
                                                   replace=False)
            legit = legit[idx]
        # The isolation forest has no native missing-value handling, so it sees
        # a median-imputed view. The GBM keeps the honest NaNs.
        self._nov_median = np.nanmedian(legit, axis=0)
        self._nov_median = np.nan_to_num(self._nov_median, nan=0.0)
        legit = self._impute(legit)
        self.iso = IsolationForest(
            n_estimators=180, max_samples=min(4096, len(legit)),
            contamination="auto", random_state=13, n_jobs=-1,
        )
        self.iso.fit(legit)
        # Reference distribution for percentile normalisation.
        self.novelty_ref = np.sort(-self.iso.score_samples(legit))

        self._finish_fit(X, y, split, train_mask, ytr, extra)
        return self

    def _finish_fit(self, X, y, split, train_mask, ytr, extra) -> None:
        # -- calibration on a held-out temporal slice -----------------------
        raw_cal = self._raw(X[split.calib])
        self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.calibrator.fit(raw_cal, y[split.calib])

        self.report = {
            "n_train": int(len(ytr)),
            "n_train_base": int(train_mask.sum()),
            "n_train_fraud": int(ytr.sum()),
            "n_train_mined": int(len(extra[0])) if extra is not None else 0,
            "n_calib": int(split.calib.sum()),
            "gbm_iterations": int(getattr(self.gbm, "n_iter_", 0)),
            "novelty_reference_size": (0 if self.novelty_ref is None
                                       else int(len(self.novelty_ref))),
            "rules": len(self.rules.rules) if self.rules else 0,
        }

    # -- scoring -----------------------------------------------------------
    def _raw(self, X: np.ndarray) -> np.ndarray:
        assert self.gbm is not None
        return self.gbm.predict_proba(X)[:, 1]

    def _impute(self, X: np.ndarray) -> np.ndarray:
        if not np.isnan(X).any():
            return X
        Xi = X.copy()
        idx = np.where(np.isnan(Xi))
        med = getattr(self, "_nov_median", None)
        Xi[idx] = 0.0 if med is None else np.take(med, idx[1])
        return Xi

    def novelty(self, X: np.ndarray) -> np.ndarray:
        """Percentile of the anomaly score against legitimate training traffic."""
        if self.iso is None or self.novelty_ref is None:
            return np.zeros(len(X), dtype=np.float32)
        s = -self.iso.score_samples(self._impute(X))
        pct = np.searchsorted(self.novelty_ref, s, side="left") / max(1, len(self.novelty_ref))
        return pct.astype(np.float32)

    def score(self, X: np.ndarray, *, with_parts: bool = False):
        """Fuse the channels into one calibrated probability."""
        p_model = self._raw(X)
        if self.calibrator is not None:
            p_model = self.calibrator.predict(p_model)
        nov = self.novelty(X)
        # Only the extreme tail of novelty contributes, so the channel adds
        # zero-day recall without flooding the queue with merely-unusual traffic.
        nov_excess = np.clip((nov - 0.985) / 0.015, 0.0, 1.0) * self.cfg.novelty_weight
        rule_score, fired = self.rules.evaluate(X) if self.rules else (
            np.zeros(len(X), dtype=np.float32), [[] for _ in range(len(X))])

        fused = 1.0 - (1.0 - p_model) * (1.0 - nov_excess) * (1.0 - rule_score)
        fused = np.clip(fused, 0.0, 1.0)
        if with_parts:
            return fused, {"model": p_model, "novelty": nov,
                           "novelty_contrib": nov_excess,
                           "rules": rule_score, "fired": fired}
        return fused

    # -- operating point ---------------------------------------------------
    def choose_threshold(self, scores: np.ndarray, y: np.ndarray,
                         amounts: np.ndarray) -> dict[str, Any]:
        """Pick the threshold that minimises expected cost, and report the
        budget-constrained alternative next to it."""
        grid = np.unique(np.quantile(scores, np.linspace(0.90, 0.9999, 220)))
        best = None
        curve = []
        for th in grid:
            flag = scores >= th
            tp = int((flag & (y == 1)).sum())
            fp = int((flag & (y == 0)).sum())
            fn = int((~flag & (y == 1)).sum())
            missed_value = float(amounts[(~flag) & (y == 1)].sum())
            loss = missed_value * self.costs.fraud_loss_ratio
            review = (tp + fp) * self.costs.review_cost
            declines = fp * self.costs.decline_share * self.costs.false_decline_cost
            total = loss + review + declines
            curve.append({
                "threshold": float(th), "alert_rate": float(flag.mean()),
                "tp": tp, "fp": fp, "fn": fn,
                "recall": tp / max(1, tp + fn),
                "precision": tp / max(1, tp + fp),
                "expected_cost": round(total, 2),
            })
            if best is None or total < best["expected_cost"]:
                best = curve[-1]

        budget_th = float(np.quantile(scores, 1.0 - self.cfg.alert_budget))
        self.threshold = float(best["threshold"]) if best else 0.5
        self.budget_threshold = budget_th
        return {"cost_optimal": best, "budget_threshold": budget_th, "curve": curve}

    def rule_catalogue(self) -> list[dict]:
        return self.rules.catalogue() if self.rules else []


def prevalence_adjusted_precision(precision: float, observed_rate: float,
                                  target_rate: float) -> float:
    """Re-express precision at a realistic production fraud prevalence.

    Simulations run at an elevated fraud rate so that every typology has enough
    examples to learn from. Reporting the resulting precision as if it were a
    production number would be dishonest, so IMMUNIS reports both: the
    in-simulation figure and this Bayes-adjusted figure at the prevalence an
    issuer actually sees.
    """
    if precision <= 0 or precision >= 1:
        return precision
    lr = (precision / (1 - precision)) * ((1 - observed_rate) / observed_rate)
    post_odds = lr * (target_rate / (1 - target_rate))
    return float(post_odds / (1 + post_odds))
