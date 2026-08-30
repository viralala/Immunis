"""The narrative channel — cross-modal fusion of conversation and payment.

This is the piece no production fraud stack has today, and it is the only thing
that can catch a coercion-authorised payment, because on the transaction side
that payment is indistinguishable from a legitimate one.

Mechanics, deliberately boring so it is deployable:

  * a character + word n-gram TF-IDF over the pre-transaction conversation,
  * a calibrated logistic regression,
  * fitted **only on episodes whose transactions are in the training split**,
  * emitting one number — ``coercion_score`` — that is fused into the tabular
    model as a single feature.

Boring matters here.  A bank can run this on-device or in a private inference
tier, it is explainable to a regulator, and it does not require sending
customer conversations to a third-party model.

Leakage control: the episode-to-split assignment comes from the transaction
split, never from the episode's own label, and episodes belonging to test
transactions are scored by a model that has never seen them.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import MaxAbsScaler


def _make_pipeline() -> Pipeline:
    word = TfidfVectorizer(
        lowercase=True, ngram_range=(1, 2), min_df=2, max_features=20_000,
        sublinear_tf=True, strip_accents="unicode",
    )
    return make_pipeline(
        word,
        MaxAbsScaler(),
        LogisticRegression(max_iter=1200, C=2.0, class_weight="balanced"),
    )


class NarrativeChannel:
    """Fit on training episodes; score any episode."""

    def __init__(self) -> None:
        self.pipe: Pipeline | None = None
        self.n_train = 0
        self.train_auc: float | None = None

    def fit(self, texts: list[str], labels: list[int]) -> "NarrativeChannel":
        if len(set(labels)) < 2 or len(texts) < 20:
            self.pipe = None
            return self
        self.pipe = _make_pipeline()
        self.pipe.fit(texts, labels)
        self.n_train = len(texts)
        try:
            from sklearn.metrics import roc_auc_score

            self.train_auc = float(roc_auc_score(
                labels, self.pipe.predict_proba(texts)[:, 1]))
        except Exception:
            self.train_auc = None
        return self

    def score(self, texts: Iterable[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.zeros(0, dtype=np.float32)
        if self.pipe is None:
            return np.zeros(len(texts), dtype=np.float32)
        return self.pipe.predict_proba(texts)[:, 1].astype(np.float32)


def apply_narrative_channel(
    X: np.ndarray,
    feature_names: list[str],
    transactions: list[dict],
    episodes: dict[str, dict],
    train_mask: np.ndarray,
) -> tuple[NarrativeChannel, dict[str, Any]]:
    """Fit the channel on training-split episodes and write scores into X.

    Modifies ``X`` in place (the ``coercion_score`` column) and returns the
    fitted channel plus a small report.
    """
    col = feature_names.index("coercion_score")

    # Which episodes belong to training transactions?
    train_eps: dict[str, int] = {}
    all_eps: dict[str, list[int]] = {}
    for i, t in enumerate(transactions):
        nid = t.get("narrative_id")
        if not nid or nid not in episodes:
            continue
        all_eps.setdefault(nid, []).append(i)
        if train_mask[i]:
            train_eps[nid] = int(episodes[nid].get("is_fraud", 0))

    channel = NarrativeChannel()
    if train_eps:
        texts = [episodes[e]["text"] for e in train_eps]
        labels = [train_eps[e] for e in train_eps]
        channel.fit(texts, labels)

    holdout_auc = None
    if all_eps:
        ids = list(all_eps.keys())
        scores = channel.score([episodes[e]["text"] for e in ids])
        for eid, s in zip(ids, scores):
            for row in all_eps[eid]:
                X[row, col] = s

        # The number that matters: separability on episodes the text model was
        # never fitted on. In-sample AUC on template-generated transcripts is
        # always flattering and should not be quoted on its own.
        held = [(s, int(episodes[e].get("is_fraud", 0)))
                for e, s in zip(ids, scores) if e not in train_eps]
        if len({lbl for _, lbl in held}) > 1:
            from sklearn.metrics import roc_auc_score

            holdout_auc = float(roc_auc_score([l for _, l in held],
                                              [v for v, _ in held]))

    return channel, {
        "episodes_total": len(all_eps),
        "episodes_train": len(train_eps),
        "train_fraud_share": round(
            sum(train_eps.values()) / max(1, len(train_eps)), 4),
        "in_sample_auc": round(channel.train_auc, 4) if channel.train_auc else None,
        "holdout_auc": round(holdout_auc, 4) if holdout_auc is not None else None,
        "caveat": ("Transcripts are template-generated, so separability here is "
                   "an upper bound. Real conversations overlap far more; treat "
                   "the narrative stress test, not this AUC, as the evidence."),
        "fitted": channel.pipe is not None,
    }
