"""Identity and onboarding injectors.

Both of these attacks manufacture *people* rather than transactions, which is
what makes them structurally different from everything else in the library:
the fraud is committed by an account that never had a victim, so no customer
ever disputes it and the institution discovers it only from its own losses.

Labelling note (and this matters for honesty): the nurture-phase transactions
of a synthetic identity are labelled **legitimate**, because they are — real
goods, real settlement, real repayment.  Only the bust-out is labelled fraud.
Labelling the whole account as fraud from birth would leak the answer into the
training set and inflate every metric downstream.
"""

from __future__ import annotations

from ...util.geo import jitter_geo
from ...util.rng import Rng
from ..entities import LIQUID_CATEGORIES
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    SECONDS_PER_DAY,
    apply_beneficiary,
    apply_device,
    attack_window_ts,
    attacker_device,
    make_mule_account,
    make_synthetic_customer,
    pick_victims,
    register,
    stealth_amount,
)
from .auth import _apply_merchant, _liquid_merchant


class SyntheticIdentity(Injector):
    """AV-SYNTH-ID — synthetic identity manufacture and credit bust-out."""

    vector_id = "AV-SYNTH-ID"
    key = "synth_id"
    label = "Synthetic identity bust-out"
    uses = ("aggression", "velocity", "device_hygiene", "spread", "mimicry", "dwell")
    defaults = {
        "aggression": 0.85, "velocity": 0.75, "device_hygiene": 0.55,
        "spread": 0.55, "mimicry": 0.60, "dwell": 0.70, "stealth": 0.30,
        "narrative_intensity": 0.0,
    }
    weight = 0.9
    txns_per_campaign = 9.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-SID-{i:05d}"
            strain_id = f"ST-{self.key}"
            # Longer nurture (high dwell) buys a bigger limit and a much more
            # convincing history — at the cost of tying up capital for weeks.
            nurture_days = int(4 + (cfg.n_days * 0.55) * p["dwell"])
            nurture_days = max(3, min(nurture_days, max(4, cfg.n_days - 4)))
            limit = 40_000 + 260_000 * p["dwell"] * rng.lognormal(0, 0.35)

            cust = make_synthetic_customer(
                world, rng, hygiene=p["device_hygiene"],
                persona=rng.weighted(["salaried_urban", "sme_owner", "student"],
                                     [0.5, 0.3, 0.2]),
                account_age_days=rng.uniform(20.0, 90.0),
                balance=limit,
            )
            dev = cust.devices[0]

            # -- nurture phase: genuine, well-behaved, labelled legitimate ---
            n_nurture = max(3, int(nurture_days * rng.uniform(0.5, 1.1)))
            for j in range(n_nurture):
                day = int(j / max(1, n_nurture) * nurture_days) + 1
                ts = attack_window_ts(cfg, rng, t0=t0, day=day,
                                      hour=rng.clip_normal(15.0, 4.0, 7.0, 23.0))
                rec = self.new_record(world, cust, ts, rng, campaign_id, strain_id)
                rec["is_fraud"] = 0
                rec["vector_id"] = None
                rec["campaign_id"] = campaign_id
                m = rng.choice([m for m in world.merchants
                                if m.category not in LIQUID_CATEGORIES] or world.merchants)
                _apply_merchant(rec, m)
                rec["rail"] = rng.weighted(["card_cnp", "upi_p2m", "card_cp"],
                                           [0.45, 0.40, 0.15])
                # Statistically *too* well-behaved — small, regular, punctual.
                rec["amount"] = round(limit * rng.uniform(0.008, 0.05), 2)
                apply_device(rec, dev)
                rec["session_duration_s"] = round(rng.lognormal(4.2, 0.45), 1)
                rec["hesitation_ms"] = round(rng.lognormal(6.5, 0.35), 1)
                rec["instrument_age_days"] = cust.account_age_days + day
                batch.transactions.append(rec)

            # -- bust-out: coordinated maximum drawdown ----------------------
            burst_day = nurture_days + 1
            n_burst = max(2, int(round(3 + 9 * p["aggression"] * (0.4 + 0.6 * p["spread"]))))
            drawn = 0.0
            cursor = attack_window_ts(cfg, rng, t0=t0, day=min(burst_day, cfg.n_days - 1),
                                      hour=rng.uniform(1.0, 23.0))
            for _ in range(n_burst):
                rec = self.new_record(world, cust, cursor, rng, campaign_id, strain_id)
                m = _liquid_merchant(world, rng, 0.85)
                _apply_merchant(rec, m)
                rec["rail"] = rng.weighted(["card_cnp", "card_cp", "wallet"],
                                           [0.55, 0.30, 0.15])
                amt = stealth_amount(rng, (limit - drawn) / max(1, n_burst) *
                                     rng.lognormal(0.15, 0.3), p["stealth"])
                rec["amount"] = round(min(amt, max(500.0, limit - drawn)), 2)
                drawn += rec["amount"]
                apply_device(rec, dev)
                lat, lon = jitter_geo(cust.lat, cust.lon,
                                      rng.uniform(2, 120) * (1 - p["mimicry"]) + 2, rng)
                rec["lat"], rec["lon"] = lat, lon
                rec["session_duration_s"] = round(rng.lognormal(2.9, 0.4), 1)
                rec["hesitation_ms"] = round(rng.lognormal(5.4, 0.4), 1)
                rec["form_corrections"] = rng.poisson(0.3)
                rec["instrument_age_days"] = cust.account_age_days + burst_day
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                cursor += max(60.0, rng.lognormal(6.6 - 2.4 * p["velocity"], 0.8))
                if drawn >= limit * 0.97:
                    break
            batch.campaigns += 1

        batch.notes = ("Nurture transactions are labelled legitimate — only the "
                       "bust-out is fraud. Utilisation acceleration is the signal.")
        return batch


class DeepfakeKyc(Injector):
    """AV-DEEPFAKE-KYC — synthetic onboarding producing first-layer mule accounts.

    The account itself is the product.  It is opened with a defeated liveness
    check and then sells its receiving capacity to every other typology in the
    atlas, so the fraud IMMUNIS labels here is the cash-out leg: the moment
    received value leaves the account.
    """

    vector_id = "AV-DEEPFAKE-KYC"
    key = "deepfake_kyc"
    label = "Deepfake KYC onboarding → mule cash-out"
    uses = ("aggression", "velocity", "device_hygiene", "spread", "dwell")
    defaults = {
        "aggression": 0.75, "velocity": 0.85, "device_hygiene": 0.30,
        "spread": 0.60, "mimicry": 0.30, "dwell": 0.10, "stealth": 0.35,
        "narrative_intensity": 0.0,
    }
    weight = 0.85
    txns_per_campaign = 12.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-DKY-{i:05d}"
            strain_id = f"ST-{self.key}"
            open_day = rng.randint(0, max(1, cfg.n_days - 6))
            mule = make_synthetic_customer(
                world, rng, hygiene=p["device_hygiene"],
                persona=rng.weighted(["student", "gig_worker"], [0.5, 0.5]),
                account_age_days=rng.uniform(0.5, 5.0),
                balance=0.0,
            )
            dev = mule.devices[0]
            # A rushed onboarding farm reuses one device across many identities.
            if rng.chance(1.0 - p["spread"]):
                dev.device_id = f"AD-FARM{rng.randint(0, 40):02d}"

            # -- inbound: victims paying in (fan-in) -------------------------
            n_payers = max(2, int(round(2 + 12 * p["aggression"] * (0.3 + 0.7 * p["spread"]))))
            payers = pick_victims(world, rng, n_payers)
            received = 0.0
            cursor = attack_window_ts(cfg, rng, t0=t0, day=open_day + 1,
                                      hour=rng.uniform(9.0, 22.0))
            for payer in payers:
                rec = self.new_record(world, payer, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "upi_p2p"
                rec["amount"] = round(
                    stealth_amount(rng, payer.balance * rng.uniform(0.05, 0.35)
                                   * p["aggression"] + 500, p["stealth"]), 2)
                apply_beneficiary(rec, world.accounts[mule.self_account])
                rec["session_duration_s"] = round(rng.lognormal(5.0, 0.6), 1)
                rec["call_active"] = int(rng.chance(0.45))
                received += rec["amount"]
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                batch.edges.append({
                    "src": payer.self_account, "dst": mule.self_account,
                    "ts": cursor, "amount": rec["amount"], "layer": 0,
                    "campaign_id": campaign_id,
                })
                cursor += max(60.0, rng.lognormal(7.2 - 3.0 * p["velocity"], 0.8))

            # -- outbound: cash-out (fan-out) --------------------------------
            dwell_s = (60.0 + 20 * 3600.0 * p["dwell"]) * rng.lognormal(0, 0.4)
            cursor += dwell_s
            n_out = max(1, int(round(1 + 5 * p["spread"])))
            for _ in range(n_out):
                rec = self.new_record(world, mule, cursor, rng, campaign_id, strain_id)
                if rng.chance(0.55):
                    rec["rail"] = "upi_p2p"
                    nxt = make_mule_account(world, rng, layer=2,
                                            max_age_days=10.0 + 40.0 * p["spread"])
                    apply_beneficiary(rec, nxt)
                    batch.edges.append({
                        "src": mule.self_account, "dst": nxt.account_id,
                        "ts": cursor, "amount": 0.0, "layer": 1,
                        "campaign_id": campaign_id,
                    })
                else:
                    rec["rail"] = "card_cp"
                    m = _liquid_merchant(world, rng, 0.9)
                    _apply_merchant(rec, m)
                rec["amount"] = round(max(100.0, received / n_out * rng.uniform(0.75, 0.98)), 2)
                if rec["beneficiary_id"] and batch.edges:
                    batch.edges[-1]["amount"] = rec["amount"]
                apply_device(rec, dev)
                rec["instrument_age_days"] = mule.account_age_days
                rec["session_duration_s"] = round(rng.lognormal(2.5, 0.4), 1)
                rec["hesitation_ms"] = round(rng.lognormal(5.0, 0.4), 1)
                rec["form_corrections"] = 0
                batch.transactions.append(rec)
                cursor += max(20.0, rng.lognormal(5.4 - 2.4 * p["velocity"], 0.7))

            batch.campaigns += 1

        batch.notes = ("Account age plus dwell time plus fan-in/out asymmetry is "
                       "the observable; the deepfake itself is upstream of payments.")
        return batch


register(SyntheticIdentity())
register(DeepfakeKyc())
