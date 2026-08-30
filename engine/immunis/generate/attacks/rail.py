"""Card and rail-exploitation injectors."""

from __future__ import annotations

from ...util.geo import jitter_geo
from ...util.rng import Rng
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    apply_beneficiary,
    apply_device,
    attack_window_ts,
    attacker_device,
    make_mule_account,
    pick_victims,
    register,
    stealth_amount,
)
from .auth import _apply_merchant, _liquid_merchant


class BinEnumeration(Injector):
    """AV-BIN-ENUM — distributed card testing with humanised cadence.

    The classic velocity rule catches machine cadence, so the interesting
    parameter here is ``mimicry``: how much throughput the operator gives up in
    exchange for inter-arrival times and basket behaviour that look human.  The
    red agent gets to discover that trade-off rather than being told it.
    """

    vector_id = "AV-BIN-ENUM"
    key = "bin_enum"
    label = "BIN enumeration / card testing"
    uses = ("aggression", "velocity", "device_hygiene", "spread", "mimicry")
    defaults = {
        "aggression": 0.25, "velocity": 0.88, "device_hygiene": 0.20,
        "spread": 0.70, "mimicry": 0.35, "dwell": 0.0, "stealth": 0.9,
        "narrative_intensity": 0.0,
    }
    weight = 1.15
    txns_per_campaign = 34.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-BIN-{i:05d}"
            strain_id = f"ST-{self.key}"
            # Device inventory: cheap operators reuse one device across hundreds
            # of cards, which is the strongest graph signal available.
            n_devices = max(1, int(round(1 + 7 * p["spread"] * p["device_hygiene"])))
            devices = [attacker_device(rng, p["device_hygiene"], os_hint="web")
                       for _ in range(n_devices)]
            # Testing merchants: small, low-friction, high online share.
            merch_pool = [m for m in world.merchants
                          if m.category in ("digital", "food", "services", "retail")
                          and m.online_share > 0.5]
            merch_pool = merch_pool or world.merchants
            merchants = rng.sample(merch_pool,
                                   max(1, min(len(merch_pool),
                                              int(2 + 10 * p["spread"]))))

            n_tests = max(4, int(round(8 + 40 * p["aggression"] +
                                       25 * (1 - p["mimicry"]))))
            cards = pick_victims(world, rng, min(n_tests, len(world.customers)),
                                 by_susceptibility=False)

            day = rng.randint(0, max(1, cfg.n_days - 1))
            cursor = attack_window_ts(cfg, rng, t0=t0, day=day,
                                      hour=rng.uniform(0.0, 24.0))
            for j, victim in enumerate(cards):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "card_cnp"
                m = merchants[j % len(merchants)]
                _apply_merchant(rec, m)
                # Micro-authorisation: validation, not monetisation.
                rec["amount"] = round(rng.uniform(1.0, 60.0) * (1 + 4 * p["aggression"]), 2)
                dev = devices[j % len(devices)]
                apply_device(rec, dev)
                lat, lon = jitter_geo(m.lat, m.lon, rng.uniform(5, 400), rng)
                rec["lat"], rec["lon"] = lat, lon
                rec["city"], rec["country"] = m.city, m.country
                rec["auth_method"] = "3ds"
                rec["threeds_result"] = 1        # frictionless: below step-up
                rec["step_up_shown"] = 0
                rec["otp_attempts"] = 1
                rec["session_duration_s"] = round(
                    max(1.5, rng.lognormal(0.9 + 3.4 * p["mimicry"], 0.35)), 1)
                rec["hesitation_ms"] = round(
                    max(15.0, rng.lognormal(3.4 + 3.0 * p["mimicry"], 0.3)), 1)
                rec["form_corrections"] = rng.poisson(0.05 + 1.5 * p["mimicry"])
                rec["app_switches"] = 0
                rec["typing_variance"] = round(max(0.001, 0.01 + 0.16 * p["mimicry"]), 4)
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                # Humanised cadence costs throughput. That is the whole trade.
                gap = rng.lognormal(0.6 + 5.2 * p["mimicry"], 0.5) / max(0.05, p["velocity"])
                cursor += max(1.5, gap)
            batch.campaigns += 1

        batch.notes = "PAN diversity per device is the highest-signal feature."
        return batch


class QrSwap(Injector):
    """AV-QR-SWAP — static QR tampering / collect-request abuse.

    Structurally distinctive: many unrelated payers, each behaving completely
    normally, converging on one young beneficiary inside a tight geographic
    radius.  No individual transaction is anomalous; the *population* is.
    """

    vector_id = "AV-QR-SWAP"
    key = "qr_swap"
    label = "QR tampering / collect-request abuse"
    uses = ("aggression", "velocity", "spread", "mimicry", "dwell")
    defaults = {
        "aggression": 0.40, "velocity": 0.55, "device_hygiene": 1.0,
        "spread": 0.35, "mimicry": 0.50, "dwell": 0.20, "stealth": 0.30,
        "narrative_intensity": 0.0,
    }
    weight = 1.0
    txns_per_campaign = 10.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-QR-{i:05d}"
            strain_id = f"ST-{self.key}"
            site = rng.choice([m for m in world.merchants if m.online_share < 0.5]
                              or world.merchants)
            # A patient operator rotates VPAs so no single one accumulates a
            # detectable payer count.
            n_vpa = max(1, int(round(1 + 4 * p["spread"])))
            vpas = [make_mule_account(world, rng, layer=1,
                                      max_age_days=2.0 + 45.0 * p["mimicry"])
                    for _ in range(n_vpa)]

            # Victims are whoever walks past — proximity, not susceptibility.
            near = sorted(world.customers,
                          key=lambda c: (c.lat - site.lat) ** 2 + (c.lon - site.lon) ** 2
                          )[:max(12, int(len(world.customers) * 0.03))]
            n_payers = max(3, int(round(4 + 16 * p["aggression"])))
            payers = rng.sample(near, min(n_payers, len(near)))

            day = rng.randint(0, max(1, cfg.n_days - 2))
            cursor = attack_window_ts(cfg, rng, t0=t0, day=day,
                                      hour=rng.clip_normal(13.0, 3.5, 7.0, 22.0))
            for j, payer in enumerate(payers):
                rec = self.new_record(world, payer, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "upi_p2p"          # payer thinks it is a merchant payment
                apply_beneficiary(rec, vpas[j % len(vpas)])
                # Ticket size matches the merchant, because the victim believes
                # they are paying that merchant.
                rec["amount"] = round(rng.lognormal(site.amount_mu, site.amount_sigma), 2)
                lat, lon = jitter_geo(site.lat, site.lon, rng.uniform(0.01, 0.15), rng)
                rec["lat"], rec["lon"] = lat, lon
                rec["city"], rec["country"] = site.city, site.country
                # Everything about the payer's session is completely normal.
                rec["session_duration_s"] = round(rng.lognormal(3.5, 0.45), 1)
                rec["hesitation_ms"] = round(rng.lognormal(6.3, 0.4), 1)
                rec["auth_method"] = "pin"
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                batch.edges.append({
                    "src": payer.self_account, "dst": rec["beneficiary_id"],
                    "ts": cursor, "amount": rec["amount"], "layer": 0,
                    "campaign_id": campaign_id,
                })
                cursor += max(30.0, rng.lognormal(6.8 - 2.6 * p["velocity"], 0.7))
            batch.campaigns += 1

        batch.notes = "Detectable only at the beneficiary population level."
        return batch


class TokenProvisioning(Injector):
    """AV-TOKEN-PROV — push provisioning of a stolen card into an attacker wallet."""

    vector_id = "AV-TOKEN-PROV"
    key = "token_prov"
    label = "Wallet token provisioning fraud"
    uses = ("aggression", "velocity", "device_hygiene", "spread", "mimicry", "stealth")
    defaults = {
        "aggression": 0.78, "velocity": 0.82, "device_hygiene": 0.65,
        "spread": 0.40, "mimicry": 0.35, "stealth": 0.45, "dwell": 0.05,
        "narrative_intensity": 0.0,
    }
    weight = 0.9
    txns_per_campaign = 4.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(world, rng, n_campaigns, by_susceptibility=False,
                               predicate=lambda c: c.balance > 25_000)

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-TOK-{i:05d}"
            strain_id = f"ST-{self.key}"
            dev = attacker_device(rng, p["device_hygiene"], os_hint="android")
            # Time between provisioning and first use: the single cleanest
            # feature on this typology, and one the operator can pay to widen.
            token_age_h = 0.05 + 60.0 * p["dwell"] * rng.lognormal(0, 0.5)

            if rng.chance(p["mimicry"]):
                lat, lon = jitter_geo(victim.lat, victim.lon, rng.uniform(5, 90), rng)
                city, country = victim.city, victim.country
            else:
                other = rng.choice(world.customers)
                lat, lon = jitter_geo(other.lat, other.lon, rng.uniform(1, 40), rng)
                city, country = other.city, other.country

            n_txn = max(1, int(round(2 + 5 * p["aggression"] * (0.4 + 0.6 * p["spread"]))))
            budget = victim.balance * (0.35 + 0.6 * p["aggression"])
            cursor = attack_window_ts(cfg, rng, t0=t0,
                                      day=rng.randint(1, max(2, cfg.n_days - 1)))
            for _ in range(n_txn):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = rng.weighted(["card_cp", "wallet"], [0.6, 0.4])
                m = _liquid_merchant(world, rng, 0.75)
                _apply_merchant(rec, m)
                rec["amount"] = round(
                    stealth_amount(rng, budget / n_txn * rng.lognormal(0, 0.28),
                                   p["stealth"]), 2)
                apply_device(rec, dev)
                rec["lat"], rec["lon"] = lat, lon
                rec["city"], rec["country"] = city, country
                rec["auth_method"] = "biometric"
                rec["threeds_result"] = 0
                rec["step_up_shown"] = 0
                # A token minutes old, on a device that has never seen this card.
                rec["instrument_age_days"] = round(token_age_h / 24.0, 4)
                rec["session_duration_s"] = round(rng.lognormal(2.2, 0.4), 1)
                rec["hesitation_ms"] = round(rng.lognormal(4.6, 0.4), 1)
                rec["form_corrections"] = 0
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                cursor += max(45.0, rng.lognormal(6.2 - 2.8 * p["velocity"], 0.7))
            batch.campaigns += 1

        batch.notes = "Instrument age at first high-value use is the key feature."
        return batch


register(BinEnumeration())
register(QrSwap())
register(TokenProvisioning())
