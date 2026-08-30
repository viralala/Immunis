"""Authentication and session-takeover injectors."""

from __future__ import annotations

from ...util.geo import CITIES, haversine_km, jitter_geo
from ...util.rng import Rng
from ..entities import LIQUID_CATEGORIES
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    apply_device,
    attack_window_ts,
    attacker_device,
    pick_victims,
    register,
    stealth_amount,
)


def _liquid_merchant(world: World, rng: Rng, prefer_liquid: float = 0.8):
    """Fraud converts value into something fungible. Merchant choice reflects that."""
    pool = [m for m in world.merchants if m.category in LIQUID_CATEGORIES]
    if pool and rng.chance(prefer_liquid):
        return rng.choice(pool)
    return rng.choice(world.merchants)


def _apply_merchant(rec: dict, m) -> None:
    rec["merchant_id"] = m.merchant_id
    rec["mcc"] = m.mcc
    rec["merchant_category"] = m.category
    rec["merchant_risk_tier"] = m.risk_tier
    rec["merchant_age_days"] = m.age_days
    rec["merchant_country"] = m.country


class AitmOtp(Injector):
    """AV-AITM-OTP — real-time adversary-in-the-middle session hijack."""

    vector_id = "AV-AITM-OTP"
    key = "aitm_otp"
    label = "Adversary-in-the-middle OTP relay"
    uses = ("aggression", "velocity", "device_hygiene", "spread", "mimicry", "stealth")
    defaults = {
        "aggression": 0.70, "velocity": 0.80, "device_hygiene": 0.35,
        "spread": 0.45, "mimicry": 0.35, "stealth": 0.40,
        "dwell": 0.05, "narrative_intensity": 0.3,
    }
    weight = 1.2
    txns_per_campaign = 4.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(
            world, rng, n_campaigns,
            predicate=lambda c: c.digital_maturity > 0.35,
        )

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-AITM-{i:05d}"
            strain_id = f"ST-{self.key}"
            dev = attacker_device(rng, p["device_hygiene"])

            # Where the attacker actually is. High mimicry buys a proxy near the
            # victim; low mimicry runs from wherever is cheapest.
            if rng.chance(p["mimicry"]):
                alat, alon = jitter_geo(victim.lat, victim.lon, rng.uniform(3, 60), rng)
                acity, acountry = victim.city, victim.country
            else:
                city = rng.weighted(CITIES, [c[4] for c in CITIES])
                acity, acountry = city[0], city[1]
                alat, alon = jitter_geo(city[2], city[3], rng.uniform(1, 25), rng)

            ts = attack_window_ts(cfg, rng, t0=t0,
                                  day=rng.randint(1, max(2, cfg.n_days - 1)))
            n_txn = max(1, int(round(1 + 5 * p["aggression"] * (0.5 + 0.5 * p["spread"]))))
            budget = victim.balance * (0.30 + 0.65 * p["aggression"])

            cursor = ts
            for j in range(n_txn):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "card_cnp" if rng.chance(0.7) else "upi_p2m"
                m = _liquid_merchant(world, rng, 0.55 + 0.35 * p["aggression"])
                _apply_merchant(rec, m)
                rec["amount"] = round(
                    stealth_amount(rng, budget / n_txn * rng.lognormal(0, 0.3),
                                   p["stealth"]), 2)
                apply_device(rec, dev)
                rec["city"], rec["country"] = acity, acountry
                rec["lat"], rec["lon"] = alat, alon

                rec["auth_method"] = "3ds" if rec["rail"] == "card_cnp" else "pin"
                rec["threeds_result"] = 2      # challenge presented AND passed
                rec["otp_attempts"] = 1
                rec["step_up_shown"] = 1

                # The tell: a hijacked session has no browsing before it. The
                # attacker knows exactly what they are buying.
                pace = 1.0 - 0.85 * p["velocity"]
                rec["session_duration_s"] = round(
                    max(3.0, rng.lognormal(2.6 + 2.4 * pace + 1.6 * p["mimicry"], 0.4)), 1)
                rec["hesitation_ms"] = round(
                    max(40.0, rng.lognormal(5.0 + 1.5 * p["mimicry"], 0.35)), 1)
                rec["app_switches"] = rng.poisson(0.2 + 1.4 * p["mimicry"])
                rec["form_corrections"] = rng.poisson(0.15 + 1.6 * p["mimicry"])
                rec["typing_variance"] = round(
                    max(0.005, victim.bio_variance * (0.35 + 0.65 * p["mimicry"])
                        * rng.lognormal(0, 0.2)), 4)
                rec["instrument_age_days"] = victim.account_age_days

                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                # Tight bursts at high velocity; patient spacing at low velocity.
                cursor += max(8.0, rng.lognormal(3.0 + 4.2 * (1 - p["velocity"]), 0.7))
            batch.campaigns += 1
        batch.notes = "Session continuity break is the primary observable."
        return batch


class BioClone(Injector):
    """AV-BIO-CLONE — behavioural-biometric cloning.

    Held out of training in the zero-day evaluation.  The strain deliberately
    satisfies every silent control: the device fingerprint is spoofed to the
    victim's, the geolocation is proxied close to home, and the interaction
    cadence reproduces the victim's mean.

    Its one irreducible tell is *variance collapse* — a model of a human is
    more consistent than the human is.  Whether the detector finds that on its
    own, having never seen this family, is the honest test of generalisation.
    """

    vector_id = "AV-BIO-CLONE"
    key = "bio_clone"
    label = "Behavioural-biometric cloning"
    uses = ("aggression", "velocity", "mimicry", "stealth", "spread")
    defaults = {
        "aggression": 0.55, "velocity": 0.45, "device_hygiene": 0.9,
        "spread": 0.3, "mimicry": 0.85, "stealth": 0.55,
        "dwell": 0.2, "narrative_intensity": 0.1,
    }
    weight = 0.75
    txns_per_campaign = 3.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(
            world, rng, n_campaigns, by_susceptibility=False,
            predicate=lambda c: c.digital_maturity > 0.5 and c.balance > 40_000,
        )

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-BIO-{i:05d}"
            strain_id = f"ST-{self.key}"
            ts = attack_window_ts(cfg, rng, t0=t0,
                                  day=rng.randint(2, max(3, cfg.n_days - 1)))
            n_txn = max(1, int(round(1 + 4 * p["aggression"])))
            budget = victim.balance * (0.25 + 0.6 * p["aggression"])

            cursor = ts
            for _ in range(n_txn):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = rng.weighted(["card_cnp", "upi_p2m", "wallet"],
                                           [0.55, 0.30, 0.15])
                m = _liquid_merchant(world, rng, 0.6)
                _apply_merchant(rec, m)
                rec["amount"] = round(
                    stealth_amount(rng, budget / n_txn * rng.lognormal(0, 0.25),
                                   p["stealth"]), 2)

                # Device fingerprint spoofed to the victim's own primary device.
                rec["device_id"] = victim.primary_device
                rec["device_age_days"] = victim.devices[0].age_days
                rec["device_os"] = victim.devices[0].os
                rec["device_is_emulator"] = 0
                rec["device_is_rooted"] = int(victim.devices[0].is_rooted)
                rec["device_attested"] = 1
                lat, lon = jitter_geo(victim.lat, victim.lon,
                                      rng.uniform(1, 30) * (1.2 - p["mimicry"]), rng)
                rec["lat"], rec["lon"] = lat, lon

                # The cloned motor signature: centred on the victim's mean,
                # with variance collapsed by the quality of the clone.
                collapse = 0.06 + 0.55 * (1 - p["mimicry"])
                rec["typing_variance"] = round(
                    max(0.001, victim.bio_variance * collapse * rng.lognormal(0, 0.10)), 5)
                rec["hesitation_ms"] = round(
                    max(80.0, rng.normal(900.0, 900.0 * 0.04)), 1)   # eerily stable
                rec["form_corrections"] = 0 if rng.chance(0.86) else 1
                rec["app_switches"] = rng.poisson(0.25)
                rec["session_duration_s"] = round(rng.lognormal(4.3, 0.22), 1)
                rec["auth_method"] = "biometric" if rec["rail"] == "wallet" else "3ds"
                rec["threeds_result"] = 1      # frictionless: behavioural score passed
                rec["step_up_shown"] = 0

                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                cursor += max(30.0, rng.lognormal(6.0 + 3.0 * (1 - p["velocity"]), 0.8))
            batch.campaigns += 1
        batch.notes = ("Zero-day holdout family. Detection must come from generic "
                       "variance and novelty features, never from a memorised label.")
        return batch


register(AitmOtp())
register(BioClone())
