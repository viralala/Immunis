"""Guardrail tests.

These are not coverage tests. Each one pins an invariant that, if it broke,
would silently turn every headline number into a lie — which is the specific
failure mode a synthetic-fraud benchmark is prone to.

Run with:  pytest -q   (from engine/)
"""

from __future__ import annotations

import numpy as np
import pytest

from immunis.config import Config
from immunis.defend import (
    Detector, apply_label_noise, apply_narrative_channel, build_features,
    temporal_split,
)
from immunis.defend.features import FORBIDDEN
from immunis.generate import simulate
from immunis.generate.attacks.base import PARAM_NAMES, REGISTRY
from immunis.identify import ATLAS, build_extended_atlas, summary_stats


@pytest.fixture(scope="module")
def ledger():
    return simulate(Config.for_profile("fast"), verbose=False)


@pytest.fixture(scope="module")
def features(ledger):
    eps = {e.episode_id: e.to_dict() for e in ledger.episodes}
    return build_features(ledger.transactions, ledger.world, eps), eps


# ---------------------------------------------------------------------------
# Identify
# ---------------------------------------------------------------------------

def test_atlas_is_complete_and_unique():
    ids = [v.id for v in ATLAS]
    assert len(ids) == len(set(ids)), "duplicate vector ids in the atlas"
    assert len(ATLAS) >= 42
    for v in ATLAS:
        assert v.kill_chain and v.observable_signals and v.mitigations
        assert 1 <= v.detection_gap <= 5 and 1 <= v.genai_uplift <= 5
        assert 0 < v.threat_score <= 100


def test_every_simulated_vector_has_a_working_injector():
    sim_ids = {v.id for v in ATLAS if v.status.value == "simulated"}
    sim_ids.discard("AV-ADV-PERTURB")   # implemented as the red agent itself
    injector_ids = {inj.vector_id for inj in REGISTRY.values()}
    assert sim_ids == injector_ids


def test_discovery_produces_novel_composites():
    extended = build_extended_atlas(top_k=6)
    hybrids = [v for v in extended if v.status.value == "discovered"]
    assert len(hybrids) == 6
    for h in hybrids:
        assert len(h.parents) == 2
        assert h.parents[0] != h.parents[1]


def test_summary_stats_agree_with_the_atlas():
    s = summary_stats()
    assert s["total_vectors"] == len(ATLAS)
    assert sum(s["by_family"].values()) == len(ATLAS)


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

def test_ledger_is_ordered_and_plausible(ledger):
    ts = [t["ts"] for t in ledger.transactions]
    assert ts == sorted(ts), "ledger must be in timestamp order"
    s = ledger.summary()
    assert 0.005 < s["fraud_rate"] < 0.05, "fraud prevalence outside a sane band"
    assert s["benign_anomaly_rate"] > 0.02, (
        "legitimate traffic must contain benign anomalies, or precision is fiction"
    )


def test_benign_and_fraud_episodes_both_exist(ledger):
    kinds = {e.is_fraud for e in ledger.episodes}
    assert kinds == {0, 1}, (
        "if only fraud had a transcript, the narrative channel would be a label leak"
    )


def test_every_attack_family_is_represented(ledger):
    seen = {t["vector_id"] for t in ledger.transactions if t["is_fraud"]}
    expected = {inj.vector_id for inj in REGISTRY.values()}
    assert expected - seen == set(), f"missing families: {expected - seen}"


def test_strain_parameters_are_bounded():
    for inj in REGISTRY.values():
        p = inj.params()
        assert set(p) == set(PARAM_NAMES)
        assert all(0.0 <= v <= 1.0 for v in p.values())


def test_telemetry_is_partially_missing(ledger):
    missing = sum(1 for t in ledger.transactions if t["session_duration_s"] is None)
    share = missing / len(ledger.transactions)
    assert 0.2 < share < 0.6, "telemetry coverage should be realistic, not total"
    # ...and missing at the same rate for fraud and legitimate traffic.
    fraud = [t for t in ledger.transactions if t["is_fraud"]]
    fraud_missing = sum(1 for t in fraud if t["session_duration_s"] is None) / len(fraud)
    assert abs(fraud_missing - share) < 0.12, "masking must not correlate with the label"


# ---------------------------------------------------------------------------
# Defend — the leakage guardrails
# ---------------------------------------------------------------------------

def test_no_simulator_internals_are_featurised(features):
    fs, _ = features
    for name in fs["feature_names"]:
        assert name not in FORBIDDEN, f"{name} must never be a feature"
    assert "susceptibility" not in fs["feature_names"]
    assert "dispute_filed" not in fs["feature_names"]


def test_features_are_causal(features, ledger):
    """A feature must not know about transactions that have not happened yet.

    Truncating the ledger must leave the surviving rows' features unchanged.
    """
    fs, eps = features
    n = len(ledger.transactions)
    cut = int(n * 0.6)
    partial = build_features(ledger.transactions[:cut], ledger.world, eps)
    a = fs["X"][:cut]
    b = partial["X"]
    assert np.allclose(np.nan_to_num(a), np.nan_to_num(b), atol=1e-4), (
        "features changed when future rows were removed — the pipeline leaks"
    )


def test_temporal_split_does_not_overlap(features):
    fs, _ = features
    split = temporal_split(fs["meta"]["ts"], Config().defend)
    ts = fs["meta"]["ts"]
    assert ts[split.train].max() <= ts[split.calib].min()
    assert ts[split.calib].max() <= ts[split.test].min()
    assert not (split.train & split.test).any()


def test_label_noise_touches_training_only(features):
    fs, _ = features
    y = fs["y"]
    split = temporal_split(fs["meta"]["ts"], Config().defend)
    noisy = apply_label_noise(y, split.train | split.calib,
                              missed_fraud=0.2, false_fraud=0.002)
    assert (noisy[split.test] == y[split.test]).all(), "test labels must stay pristine"
    assert (noisy[split.train] != y[split.train]).any(), "training labels should move"


def test_detector_trains_and_calibrates(features):
    fs, eps = features
    cfg = Config.for_profile("fast")
    X, y = fs["X"], fs["y"]
    split = temporal_split(fs["meta"]["ts"], cfg.defend)
    det = Detector(cfg=cfg.defend, costs=cfg.costs,
                   feature_names=fs["feature_names"],
                   categorical_idx=fs["categorical_idx"])
    det.fit(X, y, split)
    scores = det.score(X[split.test])
    assert scores.shape == (int(split.test.sum()),)
    assert 0.0 <= scores.min() and scores.max() <= 1.0
    assert scores[y[split.test] == 1].mean() > scores[y[split.test] == 0].mean()


def test_narrative_channel_never_sees_test_episodes(features, ledger):
    fs, eps = features
    cfg = Config.for_profile("fast")
    split = temporal_split(fs["meta"]["ts"], cfg.defend)
    X = fs["X"].copy()
    channel, report = apply_narrative_channel(
        X, fs["feature_names"], ledger.transactions, eps, split.train)
    assert report["episodes_train"] < report["episodes_total"], (
        "some episodes must be held out or the channel is fitted on its own test set"
    )
