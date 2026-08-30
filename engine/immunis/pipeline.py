"""End-to-end pipeline: identify → generate → defend → co-evolve → artefacts.

One command reproduces every number in the submission and every JSON the web
prototype reads.  Nothing in the UI is hand-written; if a figure appears on the
site, it came out of this file.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .config import ARTIFACTS_DIR, WEB_DATA_DIR, Config
from .defend import (
    Detector,
    Explainer,
    apply_label_noise,
    apply_narrative_channel,
    build_features,
    evaluate,
    narrative_stress_test,
    novelty_profile,
    permutation_importance_report,
    temporal_split,
    zero_day_report,
)
from .defend.evaluate import REALISTIC_PREVALENCE
from .generate import simulate
from .generate.attacks.base import PARAM_SPACE, REGISTRY
from .identify import ATLAS, build_extended_atlas, summary_stats
from .loop import run_coevolution
from .redteam import COST_WEIGHTS, FAMILY_CONSTRAINTS, make_context
from .util.io import write_json
from .util.rng import Rng

# Feature groups used for the ablation study — "what does each channel actually
# buy us?" is the question a bank asks before paying for any of it.
ABLATIONS: dict[str, tuple[str, ...]] = {
    "no_narrative": ("coercion_score", "has_episode", "episode_turns",
                     "episode_duration_s"),
    "no_graph": ("benef_age_days", "benef_in_count_1h", "benef_in_count_24h",
                 "benef_distinct_payers_24h", "benef_in_amt_24h",
                 "benef_out_count_1h", "benef_passthrough_ratio",
                 "benef_dwell_secs", "benef_tenure_days",
                 "sender_passthrough_ratio", "sender_dwell_secs",
                 "sender_in_24h", "device_customer_count"),
    "no_session": ("session_duration_s", "session_ratio_customer", "hesitation_ms",
                   "hesitation_ratio_customer", "app_switches", "form_corrections",
                   "typing_variance", "typing_variance_ratio", "screen_share",
                   "call_active", "screen_share_and_new_benef",
                   "session_per_txn_value"),
}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------

def run_pipeline(profile: str = "demo", seed: int = 20260831,
                 *, out_dir: Path | None = None,
                 mirror_to_web: bool = True,
                 skip_arena: bool = False,
                 skip_ablations: bool = False,
                 discover_k: int = 10,
                 use_llm: bool = False) -> dict[str, Any]:
    cfg = Config.for_profile(profile, seed)
    out = Path(out_dir or ARTIFACTS_DIR)
    t_all = time.perf_counter()
    timings: dict[str, float] = {}

    # ================= 1. IDENTIFY =====================================
    _log("\n[1/5] IDENTIFY — building the attack atlas")
    t = time.perf_counter()
    extended = build_extended_atlas(top_k=discover_k, use_llm=use_llm)
    atlas_payload = {
        "generated_at": _stamp(),
        "stats": summary_stats(),
        "discovered": len(extended) - len(ATLAS),
        "vectors": [v.to_dict() for v in extended],
        "strain_parameters": {
            k: {"low": lo, "high": hi, "description": desc}
            for k, (lo, hi, desc) in PARAM_SPACE.items()
        },
        "injectors": {
            inj.vector_id: {
                "key": inj.key, "label": inj.label,
                "defaults": inj.params(),
                "uses": list(inj.uses),
                "txns_per_campaign": inj.txns_per_campaign,
            } for inj in REGISTRY.values()
        },
        "red_team_cost_weights": {
            k: {"weight": w, "direction": d} for k, (w, d) in COST_WEIGHTS.items()
        },
        "family_constraints": {
            k: {"lower": v.lower, "upper": v.upper}
            for k, v in FAMILY_CONSTRAINTS.items()
        },
    }
    write_json(out / "atlas.json", atlas_payload)
    timings["identify"] = round(time.perf_counter() - t, 2)
    st = atlas_payload["stats"]
    _log(f"      {st['total_vectors']} curated vectors + "
         f"{atlas_payload['discovered']} discovered composites · "
         f"{st['simulated_vectors']} with generators · {st['families']} families")

    # ================= 2. GENERATE =====================================
    _log("\n[2/5] GENERATE — simulating the payment ledger")
    t = time.perf_counter()
    ledger = simulate(cfg)
    timings["generate"] = round(time.perf_counter() - t, 2)
    episodes = {e.episode_id: e.to_dict() for e in ledger.episodes}

    # ================= 3. DEFEND =======================================
    _log("\n[3/5] DEFEND — features, channels, model")
    t = time.perf_counter()
    fs = build_features(ledger.transactions, ledger.world, episodes)
    X, y, meta = fs["X"], fs["y"], fs["meta"]
    names = fs["feature_names"]
    _log(f"      features   : {X.shape[0]:,} rows x {X.shape[1]} causal features "
         f"[{round(time.perf_counter() - t, 1)}s]")

    split = temporal_split(meta["ts"], cfg.defend)
    channel, narrative_report = apply_narrative_channel(
        X, names, ledger.transactions, episodes, split.train)
    _log(f"      narrative  : fitted on {narrative_report['episodes_train']} "
         f"training episodes of {narrative_report['episodes_total']}")

    zero_day_mask = np.isin(meta["vector_id"], list(cfg.attacks.zero_day_holdout))

    # Labels the blue team actually gets to see: imperfect, and only for the
    # past. Evaluation below always uses ground truth.
    y_observed = apply_label_noise(
        y, split.train | split.calib,
        missed_fraud=cfg.attacks.label_noise_missed_fraud,
        false_fraud=cfg.attacks.label_noise_false_fraud, seed=cfg.seed % 100000)
    n_hidden = int(((y == 1) & (y_observed == 0) & split.train).sum())
    _log(f"      labels     : {n_hidden} training frauds hidden by label noise "
         f"({cfg.attacks.label_noise_missed_fraud:.0%} unreported), "
         f"{int(((y == 0) & (y_observed == 1) & split.train).sum())} false labels")

    detector = Detector(cfg=cfg.defend, costs=cfg.costs,
                        feature_names=names, categorical_idx=fs["categorical_idx"])
    detector.fit(X, y_observed, split, exclude_train_mask=zero_day_mask)
    _log(f"      model      : {detector.report}")

    ev = evaluate(detector, X, y, meta, split, cfg.costs,
                  zero_day=cfg.attacks.zero_day_holdout)
    zd = zero_day_report(detector, X, y, meta, split,
                         cfg.attacks.zero_day_holdout, ev["thresholds"]["budget"])
    _log(f"      ROC-AUC {ev['roc_auc']}  PR-AUC {ev['pr_auc']}  "
         f"recall {ev['operating_point']['recall']} @ "
         f"{ev['operating_point']['alert_rate']:.2%} alert rate  "
         f"FPR {ev['operating_point']['fpr']}")
    _log(f"      zero-day   : " + ", ".join(
        f"{k.split('AV-')[-1]} {v['recall']}" for k, v in zd.items()
        if k != "__known_families__" and v.get("recall") is not None))

    importance = permutation_importance_report(detector, X, y, split, names)
    _log(f"      top signal : " +
         ", ".join(f"{d['feature']}" for d in importance[:5]))

    # -- ablations ------------------------------------------------------
    ablation_results: dict[str, Any] = {}
    ablation_models: dict[str, Detector] = {}
    if not skip_ablations:
        for tag, drop in ABLATIONS.items():
            # Constant, not NaN: an all-NaN column has no binning thresholds
            # for the GBM to learn, and a constant column is the cleaner way to
            # say "this channel is not available".
            Xa = X.copy()
            for f in drop:
                if f in names:
                    Xa[:, names.index(f)] = 0.0
            d2 = Detector(cfg=cfg.defend, costs=cfg.costs, feature_names=names,
                          categorical_idx=fs["categorical_idx"])
            d2.fit(Xa, y_observed, split, exclude_train_mask=zero_day_mask)
            e2 = evaluate(d2, Xa, y, meta, split, cfg.costs,
                          zero_day=cfg.attacks.zero_day_holdout, label=tag)
            ablation_models[tag] = d2
            ablation_results[tag] = {
                "dropped_features": list(drop),
                "roc_auc": e2["roc_auc"],
                "pr_auc": e2["pr_auc"],
                "recall": e2["operating_point"]["recall"],
                "precision": e2["operating_point"]["precision"],
                "fpr": e2["operating_point"]["fpr"],
                "per_vector_recall": {k: v["recall"]
                                      for k, v in e2["per_vector"].items()},
                "delta_pr_auc": round(e2["pr_auc"] - ev["pr_auc"], 4),
                "delta_recall": round(e2["operating_point"]["recall"]
                                      - ev["operating_point"]["recall"], 4),
            }
            _log(f"      ablation   : {tag:<14} PR-AUC {e2['pr_auc']} "
                 f"({ablation_results[tag]['delta_pr_auc']:+.4f})  "
                 f"recall {e2['operating_point']['recall']}")
    novelty = novelty_profile(detector, X, y, meta["vector_id"],
                              cfg.attacks.zero_day_holdout)
    _log("      novelty    : legit p99 at "
         f"{novelty['legit_p99']:.4f}; zero-day families "
         + ", ".join(f"{k.split('AV-')[-1]} {v['mean_novelty_percentile']:.3f}"
                     for k, v in novelty["by_family"].items() if v["zero_day"]))

    # A channel that exists for a minority of cases cannot be judged by a
    # portfolio average, so it gets its own targeted measurement.
    stress: dict[str, Any] = {}
    if "no_narrative" in ablation_models:
        stress_ctx = make_context(ledger, cfg, fraction=0.38)
        detector.choose_threshold(detector.score(X[split.test]), y[split.test],
                                  meta["amount"][split.test].astype(float))
        ablation_models["no_narrative"].choose_threshold(
            ablation_models["no_narrative"].score(X[split.test]), y[split.test],
            meta["amount"][split.test].astype(float))
        stress = narrative_stress_test(
            cfg, stress_ctx, detector, ablation_models["no_narrative"], channel,
            narrative_columns=ABLATIONS["no_narrative"])
        for pt in stress.get("sweep", []):
            _log(f"      stress     : aggression {pt['aggression']:.2f} "
                 f"(amount z {pt['mean_amount_z']:+.2f}) recall "
                 f"{pt['recall_full']:.3f} with narrative vs "
                 f"{pt['recall_without_narrative']:.3f} without "
                 f"({pt['lift']:+.3f}, n={pt['n']})")

    timings["defend"] = round(time.perf_counter() - t, 2)

    # ================= 4. CO-EVOLVE ====================================
    arena_payload: dict[str, Any] = {}
    if not skip_arena:
        _log("\n[4/5] ARENA — red vs blue co-evolution")
        t = time.perf_counter()
        ctx = make_context(ledger, cfg, fraction=0.38)
        _log(f"      context    : {len(ctx.transactions):,} warm transactions "
             f"over {ctx.n_days} days")
        arena_payload = run_coevolution(cfg, ctx, detector, X, y_observed, meta,
                                        split, narrative=channel,
                                        zero_day_mask=zero_day_mask,
                                        eval_y=y)
        timings["arena"] = round(time.perf_counter() - t, 2)
        tti = arena_payload["time_to_immunity_generations"]
        _log(f"      Time-to-Immunity: "
             f"{tti if tti else 'not reached'} generations "
             f"({arena_payload['wall_seconds']}s wall clock)")
    else:
        _log("\n[4/5] ARENA — skipped")

    # ================= 5. ARTEFACTS ====================================
    _log("\n[5/5] ARTEFACTS")
    t = time.perf_counter()

    # Post-arena evaluation, so the site can show before/after honestly.
    ev_final = evaluate(detector, X, y, meta, split, cfg.costs,
                        zero_day=cfg.attacks.zero_day_holdout,
                        label="post_arena") if not skip_arena else ev
    zd_final = zero_day_report(detector, X, y, meta, split,
                               cfg.attacks.zero_day_holdout,
                               ev_final["thresholds"]["budget"])

    explainer = Explainer(detector, X[split.train], names)
    stream = _build_stream(detector, explainer, X, y, meta, split,
                           ledger, episodes, names, Rng(seed, "stream"))
    cases = _build_cases(detector, explainer, X, y, meta, split,
                         ledger, episodes, names)

    write_json(out / "simulation.json", {
        "generated_at": _stamp(),
        "config": cfg.to_dict(),
        "label_noise": {
            "training_frauds_hidden": n_hidden,
            "missed_fraud_rate": cfg.attacks.label_noise_missed_fraud,
            "false_fraud_rate": cfg.attacks.label_noise_false_fraud,
            "note": "Applied to training and calibration labels only; every "
                    "metric reported is computed against ground truth.",
        },
        "summary": ledger.summary(),
        "world": ledger.world.stats(),
        "feature_count": len(names),
        "feature_names": names,
        "split": split.to_dict(),
        "narrative_channel": narrative_report,
    })

    write_json(out / "detection.json", {
        "generated_at": _stamp(),
        "baseline": ev,
        "post_arena": ev_final,
        "zero_day": zd,
        "zero_day_post_arena": zd_final,
        "zero_day_journey": {
            "holdout_families": list(cfg.attacks.zero_day_holdout),
            "before": {k: v.get("recall") for k, v in zd.items()
                       if k != "__known_families__"},
            "after": {k: v.get("recall") for k, v in zd_final.items()
                      if k != "__known_families__"},
            "explanation": (
                "BEFORE is a true cold-start holdout: these families were "
                "removed from training entirely, so the number is what a "
                "conventional programme would achieve on a typology it has "
                "never seen a labelled example of. AFTER is the same families "
                "once the red agent has manufactured them in the arena and the "
                "blue model has retrained on those synthetic strains. No real "
                "loss and no real chargeback data was involved in closing that "
                "gap — which is the entire thesis of the system. It is not a "
                "leak: the labels came from attacks IMMUNIS generated itself."),
        },
        "feature_importance": importance,
        "novelty_profile": novelty,
        "narrative_stress_test": stress,
        "ablations": ablation_results,
        "rules": detector.rule_catalogue(),
        "model": detector.report,
        "cost_model": cfg.costs.__dict__,
        "realistic_prevalence": REALISTIC_PREVALENCE,
        "reason_code_method": (
            "Ablation against the deployed scoring function: each candidate "
            "feature is replaced by its training-population median and the drop "
            "in the fused score is measured."),
    })

    if arena_payload:
        write_json(out / "arena.json", {"generated_at": _stamp(), **arena_payload})

    write_json(out / "stream.json", {"generated_at": _stamp(), "transactions": stream})
    write_json(out / "cases.json", {"generated_at": _stamp(), "cases": cases})
    write_json(out / "graph.json", _build_graph(ledger))

    headline = _headline(cfg, ledger, ev, ev_final, zd_final, arena_payload,
                         atlas_payload, timings, stress)
    write_json(out / "run.json", headline)
    timings["artefacts"] = round(time.perf_counter() - t, 2)
    headline["timings"] = timings
    headline["total_seconds"] = round(time.perf_counter() - t_all, 1)
    write_json(out / "run.json", headline)

    if mirror_to_web:
        web = Path(WEB_DATA_DIR)
        for f in ("atlas.json", "simulation.json", "detection.json", "arena.json",
                  "stream.json", "cases.json", "graph.json", "run.json"):
            src = out / f
            if src.exists():
                write_json(web / f, json.loads(src.read_text(encoding="utf-8")),
                           indent=None)
        _log(f"      mirrored to {web}")

    _log(f"\nDone in {headline['total_seconds']}s — artefacts in {out}")
    return headline


# ---------------------------------------------------------------------------
# Artefact builders
# ---------------------------------------------------------------------------

def _mask(v: str, keep: int = 4) -> str:
    return v if len(v) <= keep else f"{v[:2]}…{v[-keep:]}"


def _build_stream(detector, explainer, X, y, meta, split, ledger, episodes,
                  names, rng: Rng, n: int = 220) -> list[dict]:
    """A scored slice of the test set for the live console."""
    idx = np.flatnonzero(split.test)
    scores = detector.score(X[idx])
    fraud = idx[y[idx] == 1]
    legit = idx[y[idx] == 0]
    # Over-sample fraud and high-scoring legitimate traffic: a stream of
    # nothing but approvals is not a demo, and the interesting legitimate rows
    # are the ones near the boundary.
    n_fraud = min(len(fraud), int(n * 0.32))
    take_fraud = rng.sample(list(fraud), n_fraud)
    legit_scores = detector.score(X[legit]) if len(legit) else np.zeros(0)
    order = np.argsort(-legit_scores)
    top_legit = [int(legit[i]) for i in order[:int(n * 0.20)]]
    rest = rng.sample([int(i) for i in legit], max(0, n - n_fraud - len(top_legit)))
    chosen = sorted(set(take_fraud + top_legit + rest),
                    key=lambda i: float(meta["ts"][i]))

    txn_by_id = {t["txn_id"]: t for t in ledger.transactions}
    out = []
    for i in chosen:
        t = txn_by_id.get(str(meta["txn_id"][i]), {})
        exp = explainer.explain(X[i], top_k=4)
        out.append({
            "txn_id": str(meta["txn_id"][i]),
            "ts": float(meta["ts"][i]),
            "customer": _mask(str(meta["customer_id"][i])),
            "persona": t.get("persona"),
            "rail": str(meta["rail"][i]),
            "amount": float(meta["amount"][i]),
            "merchant_category": t.get("merchant_category"),
            "city": t.get("city"),
            "is_fraud": int(y[i]),
            "vector_id": str(meta["vector_id"][i]) or None,
            "benign_anomaly": str(meta["benign_anomaly"][i]) or None,
            **exp,
        })
    return out


def _build_cases(detector, explainer, X, y, meta, split, ledger, episodes,
                 names) -> list[dict]:
    """One worked case per typology, with its conversation where there is one."""
    txn_by_id = {t["txn_id"]: t for t in ledger.transactions}
    idx = np.flatnonzero(split.test)
    want = ["AV-DIGITAL-ARREST", "AV-MULE-LAYER", "AV-AITM-OTP", "AV-BIO-CLONE",
            "AV-AGENT-INJECT", "AV-AGENT-MANDATE", "AV-BIN-ENUM", "AV-QR-SWAP",
            "AV-SYNTH-ID", "AV-TOKEN-PROV", "AV-FAKE-MERCH", "AV-FRIENDLY-FRAUD",
            "AV-DEEPFAKE-KYC", "AV-VOICE-CLONE"]
    cases = []
    for v in want:
        rows = idx[meta["vector_id"][idx] == v]
        if not len(rows):
            continue
        s = detector.score(X[rows])
        # The most instructive example is the highest-value one, not the
        # easiest — a case file should show the model working, not preening.
        pick = int(rows[int(np.argmax(meta["amount"][rows]))])
        t = txn_by_id.get(str(meta["txn_id"][pick]), {})
        exp = explainer.explain(X[pick], top_k=6)
        ep = episodes.get(t.get("narrative_id") or "")
        cases.append({
            "vector_id": v,
            "txn_id": str(meta["txn_id"][pick]),
            "ts": float(meta["ts"][pick]),
            "amount": float(meta["amount"][pick]),
            "rail": t.get("rail"),
            "persona": t.get("persona"),
            "city": t.get("city"),
            "merchant_category": t.get("merchant_category"),
            "family_median_score": round(float(np.median(s)), 4),
            "family_n": int(len(rows)),
            "episode": {
                "kind": ep["kind"], "channel": ep["channel"],
                "duration_s": ep["duration_s"], "turns": ep["turns"],
            } if ep else None,
            **exp,
        })
    return cases


def _build_graph(ledger, max_nodes: int = 420) -> dict:
    """A mule-network subgraph for the UI, drawn from the largest campaign."""
    from collections import Counter, defaultdict

    edges = ledger.edges
    if not edges:
        return {"nodes": [], "edges": [], "note": "no graph edges generated"}
    by_campaign: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        by_campaign[e.get("campaign_id", "?")].append(e)
    campaign, best = max(by_campaign.items(), key=lambda kv: len(kv[1]))
    best = sorted(best, key=lambda e: e["ts"])[:max_nodes]

    accounts = ledger.world.accounts
    node_ids: list[str] = []
    for e in best:
        for k in ("src", "dst"):
            if e[k] not in node_ids:
                node_ids.append(e[k])
    deg_in: Counter[str] = Counter()
    deg_out: Counter[str] = Counter()
    for e in best:
        deg_out[e["src"]] += 1
        deg_in[e["dst"]] += 1

    nodes = []
    for a in node_ids:
        acct = accounts.get(a)
        nodes.append({
            "id": a,
            "label": _mask(a),
            "bank": acct.bank if acct else "?",
            "age_days": round(acct.age_days, 1) if acct else None,
            "is_mule": bool(acct.is_mule) if acct else False,
            "layer": acct.mule_layer if acct else 0,
            "in_degree": deg_in[a],
            "out_degree": deg_out[a],
        })
    return {
        "campaign_id": campaign,
        "nodes": nodes,
        "edges": [{"src": e["src"], "dst": e["dst"], "amount": round(e["amount"], 2),
                   "ts": e["ts"], "layer": e.get("layer", 0)} for e in best],
        "note": ("Largest single mule campaign in the ledger. Layer 0 edges are "
                 "victim inflows; higher layers are onward dispersal."),
    }


def _headline(cfg, ledger, ev, ev_final, zd_final, arena, atlas, timings,
              stress: dict | None = None) -> dict:
    stress = stress or {}
    sim = ledger.summary()
    op = ev_final["operating_point"]
    gens = arena.get("generations", []) if arena else []
    return {
        "generated_at": _stamp(),
        "version": __version__,
        "profile": cfg.profile,
        "seed": cfg.seed,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "identify": {
            "vectors": atlas["stats"]["total_vectors"],
            "discovered": atlas["discovered"],
            "simulated": atlas["stats"]["simulated_vectors"],
            "families": atlas["stats"]["families"],
            "rails": len(atlas["stats"]["by_rail"]),
        },
        "generate": {
            "transactions": sim["transactions"],
            "fraud_transactions": sim["fraud_transactions"],
            "fraud_rate": sim["fraud_rate"],
            "episodes": sim["episodes"],
            "graph_edges": sim["graph_edges"],
            "benign_anomaly_rate": sim["benign_anomaly_rate"],
            "customers": ledger.world.stats()["customers"],
            "merchants": ledger.world.stats()["merchants"],
        },
        "defend": {
            "roc_auc": ev_final["roc_auc"],
            "pr_auc": ev_final["pr_auc"],
            "recall": op["recall"],
            "precision": op["precision"],
            "fpr": op["fpr"],
            "alert_rate": op["alert_rate"],
            "value_recall": op["value_recall"],
            "precision_at_real_prevalence": op["precision_at_real_prevalence"],
            "brier": ev_final["brier"],
            "zero_day_recall": {k: v.get("recall") for k, v in zd_final.items()
                                if k != "__known_families__"},
            "narrative_lift_on_hard_coercion": stress.get("lift"),
        },
        "arena": {
            "generations": len(gens),
            "time_to_immunity_generations": arena.get("time_to_immunity_generations"),
            "evasion_first": gens[0]["evasion_pre"] if gens else None,
            "evasion_last": gens[-1]["evasion_post"] if gens else None,
            "mined_total": gens[-1]["mined_cumulative"] if gens else 0,
            "delta": arena.get("delta"),
            "wall_seconds": arena.get("wall_seconds"),
        } if arena else None,
        "timings": timings,
    }
