"""The Red Agent — constrained evolutionary search against the live detector.

This is the half of the loop that most fraud programmes never build.  The blue
model has a decision boundary; the red agent's job is to find where that
boundary is wrong, using only the feedback an attacker would actually have
(does this get through or not?) and staying inside what a real crew could
afford to run.

Mechanics:

  * a **strain** is (attack family, parameter vector) — the same eight knobs the
    injectors expose;
  * each generation, every strain is instantiated into real transactions,
    injected into a warm slice of the ledger, featurised causally, and scored by
    the *current* detector;
  * fitness is evasion rate net of operating cost and subject to a value floor
    (``constraints.py``);
  * elites survive, the rest are produced by crossover and Gaussian mutation
    inside the family's bounds.

The evaded transactions are the output that matters: they are exactly the blind
spots, and they become the next training batch.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from ..config import Config
from ..defend.features import build_features
from ..defend.model import Detector
from ..defend.narrative import NarrativeChannel
from ..generate.attacks.base import PARAM_NAMES, REGISTRY, clamp_params
from ..generate.population import World
from ..util.rng import Rng
from .constraints import constraint_for, fitness as fitness_fn, operational_cost


# ---------------------------------------------------------------------------
# Strain
# ---------------------------------------------------------------------------

@dataclass
class Strain:
    strain_id: str
    family: str                       # injector key
    params: dict[str, float]
    generation: int = 0
    parents: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def vector_id(self) -> str:
        return REGISTRY[self.family].vector_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "strain_id": self.strain_id,
            "family": self.family,
            "vector_id": self.vector_id,
            "label": REGISTRY[self.family].label,
            "generation": self.generation,
            "parents": list(self.parents),
            "params": {k: round(v, 4) for k, v in self.params.items()},
            "operational_cost": round(operational_cost(self.params), 4),
            **self.metrics,
        }


# ---------------------------------------------------------------------------
# World checkpointing
# ---------------------------------------------------------------------------

def _checkpoint(world: World) -> dict:
    return {
        "n_customers": len(world.customers),
        "n_merchants": len(world.merchants),
        "accounts": set(world.accounts.keys()),
        "by_cat": {k: len(v) for k, v in world.merchants_by_category.items()},
    }


def _restore(world: World, ck: dict) -> None:
    """Undo the entities an arena evaluation planted.

    Injectors legitimately mutate the world (new mules, new synthetic merchants,
    new identities). For repeated evaluation that has to be reversible, or the
    tenth candidate is scored against a very different world from the first.
    """
    for c in world.customers[ck["n_customers"]:]:
        world.customer_index.pop(c.customer_id, None)
    del world.customers[ck["n_customers"]:]
    for m in world.merchants[ck["n_merchants"]:]:
        world.merchant_index.pop(m.merchant_id, None)
    del world.merchants[ck["n_merchants"]:]
    for k in list(world.accounts.keys()):
        if k not in ck["accounts"]:
            del world.accounts[k]
    for cat, n in ck["by_cat"].items():
        del world.merchants_by_category[cat][n:]
    for cat in list(world.merchants_by_category.keys()):
        if cat not in ck["by_cat"]:
            del world.merchants_by_category[cat]


# ---------------------------------------------------------------------------
# Arena harness
# ---------------------------------------------------------------------------

@dataclass
class ArenaContext:
    """A warm slice of the ledger that attacks are injected into.

    Features are causal, so a candidate attack has to land inside real history
    or its velocity, novelty and graph features are meaningless. The context is
    the tail of the base ledger; arena attacks are placed inside its time span.
    """
    transactions: list[dict]
    episodes: dict[str, dict]
    t0: int
    n_days: int
    world: World


def make_context(ledger, cfg: Config, fraction: float = 0.38) -> ArenaContext:
    txns = ledger.transactions
    cut = int(len(txns) * (1 - fraction))
    slice_ = txns[cut:]
    t_start = slice_[0]["ts"]
    t_end = slice_[-1]["ts"]
    span_days = max(2, int((t_end - t_start) // 86_400))
    eps = {e.episode_id: e.to_dict() for e in ledger.episodes}
    return ArenaContext(
        transactions=slice_,
        episodes=eps,
        t0=int(t_start),
        n_days=span_days,
        world=ledger.world,
    )


class _ArenaPopCfg:
    """Minimal population-config shim so injectors place attacks in-window."""

    def __init__(self, n_days: int, start_date: str) -> None:
        self.n_days = n_days
        self.start_date = start_date


@dataclass
class ArenaResult:
    per_strain: dict[str, dict[str, Any]]
    X: np.ndarray
    y: np.ndarray
    strain_of_row: np.ndarray
    scores: np.ndarray
    evaded_mask: np.ndarray
    n_attack_rows: int
    seconds: float


class Arena:
    """Instantiate a whole population, score it in one causal pass."""

    def __init__(self, ctx: ArenaContext, cfg: Config,
                 narrative: NarrativeChannel | None = None) -> None:
        self.ctx = ctx
        self.cfg = cfg
        self.narrative = narrative
        self.pop_cfg = _ArenaPopCfg(ctx.n_days, cfg.population.start_date)

    def run(self, strains: list[Strain], detector: Detector, rng: Rng,
            *, attacks_per_strain: int) -> ArenaResult:
        import time

        t_start = time.perf_counter()
        world = self.ctx.world
        ck = _checkpoint(world)

        attack_txns: list[dict] = []
        attack_eps: dict[str, dict] = {}
        owner: list[str] = []

        for s in strains:
            inj = REGISTRY[s.family]
            r = rng.fork(f"arena/{s.strain_id}")
            n_camp = max(1, int(round(attacks_per_strain /
                                      max(1.0, inj.txns_per_campaign * 0.5))))
            batch = inj.run(world, r, self.pop_cfg, s.params, n_camp, self.ctx.t0)
            rows = [t for t in batch.transactions if t["is_fraud"] == 1]
            for t in rows:
                t["strain_id"] = s.strain_id
            attack_txns.extend(rows)
            owner.extend([s.strain_id] * len(rows))
            for ep in batch.episodes:
                attack_eps[ep.episode_id] = ep.to_dict()
            s.metrics["value_extracted"] = round(batch.value_extracted, 2)
            s.metrics["n_attacks"] = len(rows)

        if not attack_txns:
            _restore(world, ck)
            return ArenaResult({}, np.zeros((0, 1), np.float32), np.zeros(0, np.int8),
                               np.array([]), np.zeros(0), np.zeros(0, bool), 0,
                               time.perf_counter() - t_start)

        merged = self.ctx.transactions + attack_txns
        merged.sort(key=lambda x: x["ts"])
        episodes = {**self.ctx.episodes, **attack_eps}

        fs = build_features(merged, world, episodes)
        X = fs["X"]

        # Score arena episodes with the *already fitted* narrative model — the
        # blue team does not get to refit on the attack it has not seen yet.
        if self.narrative is not None and self.narrative.pipe is not None:
            col = fs["feature_names"].index("coercion_score")
            by_ep: dict[str, list[int]] = {}
            for i, t in enumerate(merged):
                nid = t.get("narrative_id")
                if nid and nid in episodes:
                    by_ep.setdefault(nid, []).append(i)
            if by_ep:
                ids = list(by_ep)
                sc = self.narrative.score([episodes[e]["text"] for e in ids])
                for eid, v in zip(ids, sc):
                    for row in by_ep[eid]:
                        X[row, col] = v

        # Restrict to this run's strains only. Base-ledger rows carry their own
        # strain ids from the original simulation, so membership in this
        # population is the only safe test.
        strain_col = np.array([t.get("strain_id") or "" for t in merged])
        valid = {s.strain_id for s in strains}
        is_attack = np.array([t["is_fraud"] == 1 and (t.get("strain_id") or "") in valid
                              for t in merged])

        Xa = X[is_attack]
        ya = fs["y"][is_attack]
        owners = strain_col[is_attack]
        scores = detector.score(Xa) if len(Xa) else np.zeros(0)
        th = detector.budget_threshold
        evaded = scores < th

        per_strain: dict[str, dict[str, Any]] = {}
        for s in strains:
            m = owners == s.strain_id
            n = int(m.sum())
            if n == 0:
                per_strain[s.strain_id] = {
                    "n": 0, "evasion_rate": 0.0, "mean_score": 0.0,
                    "value_extracted": s.metrics.get("value_extracted", 0.0)}
                continue
            ev_rate = float(evaded[m].mean())
            per_strain[s.strain_id] = {
                "n": n,
                "evasion_rate": round(ev_rate, 4),
                "mean_score": round(float(scores[m].mean()), 4),
                "median_score": round(float(np.median(scores[m])), 4),
                "value_extracted": s.metrics.get("value_extracted", 0.0),
                "value_evaded": round(float(
                    fs["meta"]["amount"][is_attack][m][evaded[m]].sum()), 2),
            }

        _restore(world, ck)
        return ArenaResult(
            per_strain=per_strain,
            X=Xa,
            y=ya,
            strain_of_row=owners,
            scores=scores,
            evaded_mask=evaded,
            n_attack_rows=int(is_attack.sum()),
            seconds=round(time.perf_counter() - t_start, 2),
        )


# ---------------------------------------------------------------------------
# Evolutionary search
# ---------------------------------------------------------------------------

class RedAgent:
    """Population manager: initialise, score, select, breed."""

    def __init__(self, cfg: Config, families: list[str], rng: Rng) -> None:
        self.cfg = cfg
        self.families = families
        self.rng = rng
        self._seq = 0

    def _sid(self, gen: int) -> str:
        self._seq += 1
        return f"S{gen:02d}-{self._seq:04d}"

    #: Operator archetypes the initial population is seeded from. Seeding only
    #: from documented defaults would measure the detector against the attack as
    #: it is written up today, which is precisely the mistake this whole system
    #: exists to avoid. A real emerging campaign is run by someone who has
    #: already made different trade-offs.
    ARCHETYPES: dict[str, dict[str, float]] = {
        # As documented in the atlas — the typology as the industry knows it.
        "documented": {},
        # Well-resourced crew: clean attested devices, deep mule inventory,
        # patient, heavily mimicking the victim's own behaviour.
        "professional": {"device_hygiene": 0.88, "mimicry": 0.85, "spread": 0.75,
                         "dwell": 0.65, "velocity": 0.25, "stealth": 0.75,
                         "aggression": 0.45, "narrative_intensity": 0.40},
        # Cheap and fast: emulator farms, smash and grab.
        "opportunist": {"device_hygiene": 0.10, "mimicry": 0.12, "spread": 0.25,
                        "dwell": 0.05, "velocity": 0.92, "stealth": 0.15,
                        "aggression": 0.90, "narrative_intensity": 0.85},
        # Threshold hugger: everything shaped to sit inside exemptions.
        "shaper": {"stealth": 0.95, "aggression": 0.30, "spread": 0.60,
                   "velocity": 0.40, "mimicry": 0.60, "device_hygiene": 0.6,
                   "dwell": 0.45, "narrative_intensity": 0.55},
    }

    def seed_population(self, size: int) -> list[Strain]:
        """Seed from operator archetypes, then scatter.

        Generation 0 therefore measures the detector not against one
        parameterisation but against a spread of plausible operators — which is
        what a live portfolio actually faces.
        """
        out: list[Strain] = []
        archetypes = list(self.ARCHETYPES.items())
        per_family = max(1, size // len(self.families))

        for fam in self.families:
            base = REGISTRY[fam].params()
            con = constraint_for(fam)
            for i in range(per_family):
                name, overrides = archetypes[i % len(archetypes)]
                p = dict(base)
                p.update(overrides)
                if i >= len(archetypes):
                    p = {k: float(np.clip(p[k] + self.rng.normal(0, 0.22), 0, 1))
                         for k in PARAM_NAMES}
                st = Strain(self._sid(0), fam, con.clip(clamp_params(p)), 0)
                st.metrics["archetype"] = name
                out.append(st)

        while len(out) < size:
            fam = self.rng.choice(self.families)
            con = constraint_for(fam)
            p = {k: self.rng.uniform(0, 1) for k in PARAM_NAMES}
            st = Strain(self._sid(0), fam, con.clip(clamp_params(p)), 0)
            st.metrics["archetype"] = "random"
            out.append(st)
        return out[:size]

    def score_population(self, strains: list[Strain], result: ArenaResult) -> None:
        rt = self.cfg.redteam
        for s in strains:
            m = result.per_strain.get(s.strain_id, {})
            ev = float(m.get("evasion_rate", 0.0))
            val = float(m.get("value_extracted", 0.0))
            n = int(m.get("n", 0))
            f = fitness_fn(ev, val, s.params,
                           min_value=rt.min_value_extracted,
                           penalty_weight=rt.realism_penalty_weight,
                           n_attacks=max(1, n))
            s.metrics.update(m)
            s.metrics.update(f)

    def breed(self, strains: list[Strain], generation: int) -> list[Strain]:
        rt = self.cfg.redteam
        ranked = sorted(strains, key=lambda s: -s.metrics.get("fitness", 0.0))
        n_elite = max(2, int(len(ranked) * rt.elite_frac))
        elites = ranked[:n_elite]

        # Elites carry forward unchanged so the best known evasion is never lost.
        nxt: list[Strain] = [replace(s, generation=generation, metrics={})
                             for s in elites]

        while len(nxt) < len(strains):
            a = self._tournament(ranked)
            b = self._tournament(ranked)
            if a.family != b.family:
                # Cross-family crossover is not meaningful — the parameters mean
                # different things — so the fitter parent's family wins and only
                # its shared knobs are blended.
                b = a if a.metrics.get("fitness", 0) >= b.metrics.get("fitness", 0) else b
            child = self._crossover(a, b, generation)
            nxt.append(self._mutate(child))

        # Diversity injection: a fully random strain each generation stops the
        # search collapsing onto one local optimum the blue model then overfits.
        fam = self.rng.choice(self.families)
        con = constraint_for(fam)
        nxt[-1] = Strain(self._sid(generation), fam,
                         con.clip({k: self.rng.uniform(0, 1) for k in PARAM_NAMES}),
                         generation)
        return nxt

    def _tournament(self, ranked: list[Strain], k: int = 3) -> Strain:
        picks = self.rng.sample(ranked, min(k, len(ranked)))
        return max(picks, key=lambda s: s.metrics.get("fitness", 0.0))

    def _crossover(self, a: Strain, b: Strain, generation: int) -> Strain:
        p = {}
        for k in PARAM_NAMES:
            w = self.rng.uniform(0.0, 1.0)
            p[k] = w * a.params[k] + (1 - w) * b.params.get(k, a.params[k])
        con = constraint_for(a.family)
        return Strain(self._sid(generation), a.family, con.clip(p), generation,
                      parents=(a.strain_id, b.strain_id))

    def _mutate(self, s: Strain) -> Strain:
        rt = self.cfg.redteam
        p = dict(s.params)
        for k in PARAM_NAMES:
            if self.rng.chance(rt.mutation_rate):
                p[k] = float(np.clip(p[k] + self.rng.normal(0, rt.mutation_scale), 0, 1))
        s.params = constraint_for(s.family).clip(p)
        return s
