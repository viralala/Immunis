"""Agentic-commerce injectors — the 2026-native rail with no fraud history.

These two matter disproportionately for this challenge.  Agent-initiated
payments are being stood up right now across the industry, and there is no
labelled fraud on the rail because the rail is new.  A system that can only
learn from historical losses has, by definition, nothing to learn from here.
Manufacturing the fraud is the *only* way to have a model ready on day one,
which is the entire IMMUNIS thesis in miniature.
"""

from __future__ import annotations

from ...util.geo import jitter_geo
from ...util.rng import Rng
from ..entities import AGENT_PLATFORMS, LIQUID_CATEGORIES
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    attack_window_ts,
    pick_victims,
    register,
    stealth_amount,
)
from .auth import _apply_merchant

_INTENTS = ["retail", "digital", "essentials", "travel", "food", "services"]


class AgentInjection(Injector):
    """AV-AGENT-INJECT — prompt-injected shopping agent.

    The consumer's mandate is real, the credential is real, the agent is the
    genuine registered agent.  What has been subverted is the agent's
    *objective*, so the observable is intent divergence: the mandate said
    "groceries under ₹4,000" and the authorisation is a gift-card purchase at a
    merchant neither the consumer nor the agent platform has ever touched.
    """

    vector_id = "AV-AGENT-INJECT"
    key = "agent_inject"
    label = "Prompt-injected shopping agent"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth")
    defaults = {
        "aggression": 0.72, "velocity": 0.70, "device_hygiene": 1.0,
        "spread": 0.40, "mimicry": 0.35, "stealth": 0.40, "dwell": 0.1,
        "narrative_intensity": 0.0,
    }
    weight = 0.9
    txns_per_campaign = 3.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(
            world, rng, n_campaigns, by_susceptibility=False,
            predicate=lambda c: c.agent_adoption > 0.05,
        )

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-AGI-{i:05d}"
            strain_id = f"ST-{self.key}"
            intent = rng.choice(_INTENTS)
            ceiling = max(3000.0, (victim.amount_mu ** 2) * rng.uniform(30, 90))
            agent_id = f"AG-{rng.randint(1, 6):02d}"

            n_txn = max(1, int(round(1 + 3 * p["aggression"])))
            cursor = attack_window_ts(cfg, rng, t0=t0,
                                      day=rng.randint(1, max(2, cfg.n_days - 1)))
            for _ in range(n_txn):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "agentic"
                rec["is_agentic"] = 1
                rec["agent_id"] = agent_id
                rec["agent_attested"] = 1        # it really is the consumer's agent
                rec["mandate_ceiling"] = round(ceiling, 2)
                rec["mandate_age_h"] = rng.uniform(48.0, 2000.0)
                rec["mandate_scope_breadth"] = round(rng.uniform(0.05, 0.30), 3)
                rec["mandate_intent_category"] = intent

                # A high-mimicry injection keeps the purchase category plausible
                # and takes less; a greedy one goes straight for liquid value.
                if rng.chance(p["mimicry"]):
                    pool = [m for m in world.merchants if m.category == intent]
                else:
                    pool = [m for m in world.merchants
                            if m.category in LIQUID_CATEGORIES]
                m = rng.choice(pool or world.merchants)
                _apply_merchant(rec, m)

                # Amount pushed toward the ceiling rather than to a price point.
                target = ceiling * (0.35 + 0.62 * p["aggression"])
                rec["amount"] = round(min(ceiling * 0.99,
                                          stealth_amount(rng, target, p["stealth"])), 2)
                rec["auth_method"] = "mandate"
                rec["threeds_result"] = 1
                rec["step_up_shown"] = 0
                rec["human_confirmations"] = 0
                # A subverted agent stops comparing and buys immediately.
                rec["session_duration_s"] = round(
                    max(1.0, rng.lognormal(1.4 + 2.6 * p["mimicry"], 0.4)), 1)
                rec["hesitation_ms"] = round(rng.lognormal(3.0, 0.3), 1)
                rec["form_corrections"] = 0
                rec["app_switches"] = 0
                lat, lon = jitter_geo(victim.lat, victim.lon, rng.uniform(0.5, 6.0), rng)
                rec["lat"], rec["lon"] = lat, lon
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                cursor += max(20.0, rng.lognormal(5.4 - 2.4 * p["velocity"], 0.6))
            batch.campaigns += 1

        batch.notes = "Mandate-intent divergence is the primary observable."
        return batch


class AgentMandateAbuse(Injector):
    """AV-AGENT-MANDATE — over-scoped mandate drawn down in full.

    Held out of training in the zero-day evaluation.

    Nothing here is technically unauthorised: the consumer clicked accept.  The
    fraud is that the ceiling bears no relationship to how that consumer
    actually spends, and it is consumed to the last rupee inside the first
    mandate period, across a merchant scope far wider than the stated purpose,
    with no human confirmation event anywhere in its life.
    """

    vector_id = "AV-AGENT-MANDATE"
    key = "agent_mandate"
    label = "Over-scoped agent payment mandate"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth")
    defaults = {
        "aggression": 0.80, "velocity": 0.75, "device_hygiene": 1.0,
        "spread": 0.65, "mimicry": 0.30, "stealth": 0.35, "dwell": 0.05,
        "narrative_intensity": 0.0,
    }
    weight = 0.8
    txns_per_campaign = 6.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(world, rng, n_campaigns)

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-AGM-{i:05d}"
            strain_id = f"ST-{self.key}"
            # A ceiling calibrated to what can be taken, not to what the
            # consumer spends. High mimicry sets a less absurd ceiling.
            typical = max(200.0, victim.balance * 0.02)
            ceiling = typical * rng.uniform(18, 60) * (1.2 - 0.7 * p["mimicry"])
            ceiling = min(ceiling, victim.balance * 1.4)
            agent_id = rng.choice(AGENT_PLATFORMS)
            mandate_age = 0.5 + 36.0 * p["mimicry"] * rng.lognormal(0, 0.4)

            n_txn = max(2, int(round(2 + 7 * p["aggression"] * (0.4 + 0.6 * p["spread"]))))
            drawn = 0.0
            cursor = attack_window_ts(cfg, rng, t0=t0,
                                      day=rng.randint(1, max(2, cfg.n_days - 1)))
            for j in range(n_txn):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "agentic"
                rec["is_agentic"] = 1
                rec["agent_id"] = agent_id
                rec["agent_attested"] = int(rng.chance(0.35 + 0.6 * p["mimicry"]))
                rec["mandate_ceiling"] = round(ceiling, 2)
                rec["mandate_age_h"] = round(mandate_age + j * 0.6, 3)
                # Scope breadth: "anything, anywhere" rather than "this shop".
                rec["mandate_scope_breadth"] = round(
                    min(1.0, 0.55 + 0.45 * p["spread"] - 0.25 * p["mimicry"]), 3)
                rec["mandate_intent_category"] = rng.choice(_INTENTS)
                rec["human_confirmations"] = 0

                m = rng.choice([mm for mm in world.merchants
                                if mm.category in LIQUID_CATEGORIES] or world.merchants)
                _apply_merchant(rec, m)
                remaining = max(200.0, ceiling - drawn)
                rec["amount"] = round(min(
                    remaining,
                    stealth_amount(rng, remaining / max(1, n_txn - j) *
                                   rng.lognormal(0.1, 0.25), p["stealth"])), 2)
                drawn += rec["amount"]
                rec["auth_method"] = "mandate"
                rec["threeds_result"] = 1
                rec["step_up_shown"] = 0
                rec["session_duration_s"] = round(rng.lognormal(1.6, 0.35), 1)
                rec["hesitation_ms"] = round(rng.lognormal(2.9, 0.3), 1)
                rec["form_corrections"] = 0
                rec["instrument_age_days"] = round(mandate_age / 24.0, 4)
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                cursor += max(15.0, rng.lognormal(5.0 - 2.6 * p["velocity"], 0.6))
                if drawn >= ceiling * 0.98:
                    break
            batch.campaigns += 1

        batch.notes = ("Zero-day holdout family. Ceiling-to-spend ratio and "
                       "drawdown velocity must generalise from other typologies.")
        return batch


register(AgentInjection())
register(AgentMandateAbuse())
