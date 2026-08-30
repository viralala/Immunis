"""Merchant-side and dispute-side injectors."""

from __future__ import annotations

from ...util.geo import CITIES, jitter_geo
from ...util.rng import Rng
from ..entities import MCCS, Merchant
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    attack_window_ts,
    attacker_device,
    apply_device,
    pick_victims,
    register,
    stealth_amount,
)
from .auth import _apply_merchant


class FakeMerchant(Injector):
    """AV-FAKE-MERCH — synthetic merchant onboarding for transaction laundering.

    The tell is never a single transaction; it is the merchant's *population*:
    no repeat customers, a ticket distribution that does not match its declared
    category, and a volume curve that ramps the moment the reserve is released.
    """

    vector_id = "AV-FAKE-MERCH"
    key = "fake_merchant"
    label = "Synthetic merchant / transaction laundering"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth", "dwell")
    defaults = {
        "aggression": 0.70, "velocity": 0.65, "device_hygiene": 0.6,
        "spread": 0.60, "mimicry": 0.40, "stealth": 0.35, "dwell": 0.35,
        "narrative_intensity": 0.0,
    }
    weight = 0.95
    txns_per_campaign = 23.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-FKM-{i:05d}"
            strain_id = f"ST-{self.key}"

            # Declared category: a high-mimicry operator declares something
            # boring; a lazy one declares whatever is convenient.
            declared = rng.weighted(
                [m for m in MCCS if m[3] == 1] or MCCS,
                [1.0] * len([m for m in MCCS if m[3] == 1] or MCCS),
            ) if rng.chance(p["mimicry"]) else rng.choice(MCCS)
            mcc, label, category, tier, mu, sigma, online = declared
            city = rng.weighted(CITIES, [c[4] for c in CITIES])
            mlat, mlon = jitter_geo(city[2], city[3], rng.uniform(1, 20), rng)

            merchant = Merchant(
                merchant_id=f"MF{i:05d}",
                name="Synthetic Trading Co",
                mcc=mcc, label=label, category=category, risk_tier=tier,
                city=city[0], country=city[1], lat=mlat, lon=mlon,
                online_share=0.95,
                amount_mu=mu, amount_sigma=sigma,
                # Business footprint created inside the campaign window.
                age_days=max(1.0, 3.0 + 55.0 * p["dwell"]),
                acquirer=f"ACQ{rng.randint(1, 9):02d}",
                is_synthetic=True,
                chargeback_rate=0.02 + 0.09 * p["aggression"],
            )
            world.merchants.append(merchant)
            world.merchant_index[merchant.merchant_id] = merchant
            world.merchants_by_category.setdefault(category, []).append(merchant)

            # Cardholders: compromised cards, each used once — the absence of
            # repeat customers is what a real merchant can never fake.
            n_cards = max(4, int(round(6 + 34 * p["aggression"] * (0.3 + 0.7 * p["spread"]))))
            cards = pick_victims(world, rng, min(n_cards, len(world.customers)),
                                 by_susceptibility=False)
            dev = attacker_device(rng, p["device_hygiene"], os_hint="web")

            ramp_days = max(2, int(cfg.n_days * (0.15 + 0.45 * (1 - p["velocity"]))))
            start_day = rng.randint(0, max(1, cfg.n_days - ramp_days - 1))
            for j, victim in enumerate(cards):
                # Volume ramps rather than starting flat — the classic curve.
                frac = (j + 1) / len(cards)
                day = start_day + int(ramp_days * (frac ** (0.4 + 0.8 * p["velocity"])))
                day = min(day, cfg.n_days - 1)
                cursor = attack_window_ts(cfg, rng, t0=t0, day=day,
                                          hour=rng.uniform(0.0, 24.0))
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "card_cnp"
                _apply_merchant(rec, merchant)
                base = rng.lognormal(mu, sigma)
                # A laundering merchant's tickets drift above its category norm.
                rec["amount"] = round(stealth_amount(
                    rng, base * (1.0 + 2.2 * p["aggression"] * (1 - p["mimicry"])),
                    p["stealth"]), 2)
                apply_device(rec, dev)
                rec["city"], rec["country"] = merchant.city, merchant.country
                rec["auth_method"] = "3ds"
                rec["threeds_result"] = 1
                rec["step_up_shown"] = 0
                rec["session_duration_s"] = round(rng.lognormal(2.4, 0.5), 1)
                rec["hesitation_ms"] = round(rng.lognormal(4.8, 0.5), 1)
                rec["form_corrections"] = rng.poisson(0.2)
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
            batch.campaigns += 1

        batch.notes = "Merchant-population features, not per-transaction features."
        return batch


class FriendlyFraud(Injector):
    """AV-FRIENDLY-FRAUD — first-party misuse with generated dispute narratives.

    The hardest possible negative-space problem: the transaction is *genuine*.
    Right customer, right device, right location, real goods delivered.  The
    only thing that separates it from an honest purchase is what the cardholder
    does afterwards — and, at authorisation time, what they have done before.

    So this injector deliberately builds up a per-customer dispute history over
    the window.  Early events in a campaign are close to undetectable; later
    ones are catchable from the customer's own accumulated behaviour.  That
    gradient is realistic and it is what stops the metric being a fantasy.
    """

    vector_id = "AV-FRIENDLY-FRAUD"
    key = "friendly_fraud"
    label = "First-party misuse / generated disputes"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth")
    defaults = {
        "aggression": 0.60, "velocity": 0.40, "device_hygiene": 1.0,
        "spread": 0.45, "mimicry": 0.80, "stealth": 0.35, "dwell": 0.5,
        "narrative_intensity": 0.0,
    }
    weight = 1.0
    txns_per_campaign = 7.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        abusers = pick_victims(world, rng, n_campaigns, by_susceptibility=False)

        for i, cust in enumerate(abusers):
            campaign_id = f"CMP-FF-{i:05d}"
            strain_id = f"ST-{self.key}"
            n_events = max(2, int(round(2 + 8 * p["aggression"])))
            # Resellable categories: electronics, apparel, travel, gift cards.
            pool = [m for m in world.merchants
                    if m.category in ("retail", "travel", "liquid", "luxury")] \
                or world.merchants
            merchants = rng.sample(pool, min(len(pool),
                                             max(1, int(1 + 6 * p["spread"]))))

            days = sorted(rng.sample(list(range(1, max(3, cfg.n_days))),
                                     min(n_events, max(2, cfg.n_days - 1))))
            for j, day in enumerate(days):
                cursor = attack_window_ts(cfg, rng, t0=t0, day=day,
                                          hour=rng.clip_normal(20.0, 3.0, 8.0, 23.9))
                rec = self.new_record(world, cust, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "card_cnp" if rng.chance(0.85) else "card_cp"
                m = merchants[j % len(merchants)]
                _apply_merchant(rec, m)
                rec["amount"] = round(stealth_amount(
                    rng, rng.lognormal(m.amount_mu + 0.5 + 0.9 * p["aggression"],
                                       m.amount_sigma), p["stealth"]), 2)
                # Perfect continuity — it really is the customer.
                lat, lon = jitter_geo(cust.lat, cust.lon, rng.uniform(0.1, 8.0), rng)
                rec["lat"], rec["lon"] = lat, lon
                rec["session_duration_s"] = round(rng.lognormal(4.9, 0.6), 1)
                rec["hesitation_ms"] = round(rng.lognormal(6.5, 0.45), 1)
                rec["form_corrections"] = rng.poisson(1.0)
                rec["auth_method"] = "3ds"
                rec["threeds_result"] = 2 if rec["amount"] > 5000 else 1
                rec["step_up_shown"] = int(rec["amount"] > 5000)
                # The dispute is filed afterwards; the model only ever sees the
                # customer's *prior* dispute history as a feature.
                rec["dispute_filed"] = 1 if rng.chance(0.75 + 0.2 * p["aggression"]) else 0
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
            batch.campaigns += 1

        batch.notes = ("Prior-dispute history is causal and legitimate; the first "
                       "event of a campaign is intentionally near-undetectable.")
        return batch


register(FakeMerchant())
register(FriendlyFraud())
