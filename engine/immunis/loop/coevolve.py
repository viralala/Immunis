"""The Arena — red/blue co-evolution, and the Time-to-Immunity metric.

One generation:

    1. the red agent instantiates its population of strains into real
       transactions and injects them into a warm slice of the ledger;
    2. the current blue model scores them; whatever falls below the operating
       threshold has *evaded*;
    3. fitness = evasion net of operating cost, subject to a value floor;
    4. every evaded transaction is mined as a hard negative and folded into the
       training set with an elevated weight;
    5. the blue model retrains;
    6. the same strains are re-scored by the retrained model — the drop from
       pre- to post-retrain evasion is the immunity gained this round;
    7. the blue model is re-measured on a **frozen future test set** at constant
       alert budget, so gains are only counted if they are real and if the
       false-positive cost did not move;
    8. elites survive, the rest are bred.

**Time-to-Immunity (TTI)** is the first generation at which post-retrain
evasion falls below the immunity threshold while the false-positive budget
holds.  It is the number this whole system exists to produce: the industry's
equivalent today is measured in months of chargeback data.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from sklearn.metrics import roc_auc_score

from ..config import Config
from ..defend.model import Detector, Split
from ..defend.narrative import NarrativeChannel
from ..redteam.evader import Arena, ArenaContext, RedAgent, Strain
from ..util.rng import Rng

#: Cap on how many mined rows are carried per generation, so training time
#: stays bounded and the model is not swamped by one prolific strain.
MAX_MINED_PER_GENERATION = 2200
#: Weight multiplier applied to mined evasions. They are the examples the model
#: demonstrably got wrong, so they should count for more than routine rows.
MINED_WEIGHT = 3.0


def _measure(detector: Detector, X: np.ndarray, y: np.ndarray, split: Split,
             alert_budget: float, amounts: np.ndarray) -> dict[str, Any]:
    """Evaluate on the frozen future test slice at a constant alert budget."""
    Xt, yt = X[split.test], y[split.test]
    at = amounts[split.test]
    s = detector.score(Xt)
    th = float(np.quantile(s, 1.0 - alert_budget))
    flag = s >= th
    tp = int((flag & (yt == 1)).sum())
    fp = int((flag & (yt == 0)).sum())
    fn = int((~flag & (yt == 1)).sum())
    tn = int((~flag & (yt == 0)).sum())
    return {
        "auc": round(float(roc_auc_score(yt, s)), 4) if len(set(yt.tolist())) > 1 else None,
        "threshold": round(th, 5),
        "recall": round(tp / max(1, tp + fn), 4),
        "precision": round(tp / max(1, tp + fp), 4),
        "fpr": round(fp / max(1, fp + tn), 5),
        "alert_rate": round(float(flag.mean()), 5),
        "value_recall": round(float(at[flag & (yt == 1)].sum())
                              / max(1.0, float(at[yt == 1].sum())), 4),
    }


def run_coevolution(
    cfg: Config,
    ctx: ArenaContext,
    detector: Detector,
    X: np.ndarray,
    y: np.ndarray,
    meta: dict,
    split: Split,
    *,
    narrative: NarrativeChannel | None = None,
    zero_day_mask: np.ndarray | None = None,
    families: list[str] | None = None,
    eval_y: np.ndarray | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """``y`` is what the blue team observes (noisy); ``eval_y`` is ground truth."""
    rt = cfg.redteam
    rng = Rng(cfg.seed, "coevolution")
    from ..generate.attacks.base import REGISTRY

    families = families or sorted(REGISTRY.keys())
    agent = RedAgent(cfg, families, rng)
    arena = Arena(ctx, cfg, narrative)
    amounts = meta["amount"].astype(np.float64)
    y_true = eval_y if eval_y is not None else y

    baseline = _measure(detector, X, y_true, split, cfg.defend.alert_budget, amounts)
    fpr_budget = baseline["fpr"] * rt.fpr_budget_multiplier
    if verbose:
        print(f"  baseline   : AUC {baseline['auc']}  recall {baseline['recall']}  "
              f"FPR {baseline['fpr']}  (budget ceiling {fpr_budget:.5f})")

    population = agent.seed_population(rt.population_size)
    mined_X: list[np.ndarray] = []
    mined_y: list[np.ndarray] = []
    generations: list[dict[str, Any]] = []
    time_to_immunity: int | None = None
    t_wall = time.perf_counter()

    for gen in range(rt.generations):
        g_start = time.perf_counter()

        # ---- 1-3. red attacks, blue scores, fitness ----------------------
        result = arena.run(population, detector, rng.fork(f"gen{gen}"),
                           attacks_per_strain=rt.attacks_per_strain)
        agent.score_population(population, result)

        ev_rates = np.array([s.metrics.get("evasion_rate", 0.0) for s in population])
        pre_mean = float(ev_rates.mean()) if len(ev_rates) else 0.0
        pre_max = float(ev_rates.max()) if len(ev_rates) else 0.0

        # ---- 4. mine the evasions ----------------------------------------
        ev_mask = result.evaded_mask
        n_evaded = int(ev_mask.sum())
        if n_evaded > MAX_MINED_PER_GENERATION:
            keep = rng.np.choice(np.flatnonzero(ev_mask),
                                 size=MAX_MINED_PER_GENERATION, replace=False)
            sel = np.zeros_like(ev_mask)
            sel[keep] = True
        else:
            sel = ev_mask
        if sel.any():
            mined_X.append(result.X[sel])
            mined_y.append(result.y[sel])
        fam_of_strain = {st.strain_id: st.vector_id for st in population}
        mined_by_vector: dict[str, int] = {}
        for sid in result.strain_of_row[sel]:
            v = fam_of_strain.get(sid, "?")
            mined_by_vector[v] = mined_by_vector.get(v, 0) + 1

        # ---- 5. blue retrains on its own failures ------------------------
        if mined_X:
            Xe = np.vstack(mined_X)
            ye = np.concatenate(mined_y)
            we = np.full(len(ye), MINED_WEIGHT * cfg.defend.class_weight_positive)
            detector.fit(X, y, split, exclude_train_mask=zero_day_mask,
                         extra=(Xe, ye, we), refit_novelty=False)
        cumulative_mined = int(sum(len(a) for a in mined_X))

        # ---- 6. immunity gained on the very strains that just evaded -----
        post_scores = detector.score(result.X) if len(result.X) else np.zeros(0)
        post_th = detector.budget_threshold
        post_by_strain: dict[str, float] = {}
        for s in population:
            m = result.strain_of_row == s.strain_id
            if m.sum():
                post_by_strain[s.strain_id] = float((post_scores[m] < post_th).mean())
        post_mean = (float(np.mean(list(post_by_strain.values())))
                     if post_by_strain else 0.0)

        # ---- 7. did it cost anything on the frozen future? ---------------
        after = _measure(detector, X, y_true, split, cfg.defend.alert_budget, amounts)
        fpr_ok = after["fpr"] <= fpr_budget

        if (time_to_immunity is None and post_mean < rt.immunity_threshold and fpr_ok):
            time_to_immunity = gen + 1

        ranked = sorted(population, key=lambda s: -s.metrics.get("fitness", 0.0))
        centroid = {
            k: round(float(np.mean([s.params[k] for s in ranked[:max(3, len(ranked) // 4)]])), 4)
            for k in ranked[0].params
        } if ranked else {}

        gen_record = {
            "generation": gen,
            "population": len(population),
            "attack_rows": result.n_attack_rows,
            "evasion_pre": round(pre_mean, 4),
            "evasion_pre_max": round(pre_max, 4),
            "evasion_post": round(post_mean, 4),
            "immunity_gain": round(pre_mean - post_mean, 4),
            "mined": int(sel.sum()),
            "mined_cumulative": cumulative_mined,
            "mined_by_vector": dict(sorted(mined_by_vector.items(),
                                           key=lambda kv: -kv[1])),
            "value_evaded": round(float(
                sum(s.metrics.get("value_evaded", 0.0) for s in population)), 2),
            "blue_before": baseline if gen == 0 else generations[-1]["blue_after"],
            "blue_after": after,
            "fpr_within_budget": bool(fpr_ok),
            "elite_centroid": centroid,
            "top_strains": [s.to_dict() for s in ranked[:5]],
            "by_family": _by_family(population),
            "seconds": round(time.perf_counter() - g_start, 2),
        }
        generations.append(gen_record)

        if verbose:
            print(f"  gen {gen}      : evasion {pre_mean:.1%} -> {post_mean:.1%}  "
                  f"mined {int(sel.sum()):>4}  "
                  f"blue AUC {after['auc']} recall {after['recall']} "
                  f"FPR {after['fpr']:.4f}{'' if fpr_ok else '  [BUDGET BREACH]'}  "
                  f"[{gen_record['seconds']}s]")

        if gen < rt.generations - 1:
            population = agent.breed(population, gen + 1)

    final = generations[-1]["blue_after"] if generations else baseline
    return {
        "baseline": baseline,
        "final": final,
        "generations": generations,
        "time_to_immunity_generations": time_to_immunity,
        "time_to_immunity_minutes": (
            round((time.perf_counter() - t_wall) / 60.0 *
                  (time_to_immunity / max(1, len(generations))), 2)
            if time_to_immunity else None),
        "immunity_threshold": rt.immunity_threshold,
        "fpr_budget_ceiling": round(fpr_budget, 5),
        "wall_seconds": round(time.perf_counter() - t_wall, 1),
        "delta": {
            "auc": round((final.get("auc") or 0) - (baseline.get("auc") or 0), 4),
            "recall": round(final["recall"] - baseline["recall"], 4),
            "fpr": round(final["fpr"] - baseline["fpr"], 5),
            "value_recall": round(final["value_recall"] - baseline["value_recall"], 4),
        },
    }


def _by_family(population: list[Strain]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for s in population:
        d = out.setdefault(s.family, {"n": 0, "evasion": 0.0, "fitness": 0.0,
                                      "vector_id": s.vector_id})
        d["n"] += 1
        d["evasion"] += s.metrics.get("evasion_rate", 0.0)
        d["fitness"] += s.metrics.get("fitness", 0.0)
    for d in out.values():
        d["evasion"] = round(d["evasion"] / max(1, d["n"]), 4)
        d["fitness"] = round(d["fitness"] / max(1, d["n"]), 4)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["evasion"]))
