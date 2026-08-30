"""Social-engineering / authorised-push-payment injectors.

These are the hardest class in the whole atlas and the reason IMMUNIS is
cross-modal.  The victim authenticates correctly, on their own device, from
their own home, with their own PIN.  Every conventional authorisation feature
reports "legitimate", because it *is* legitimate — the customer really did
authorise it.

What is anomalous lives in three places:
  1. the counterparty (a beneficiary that did not exist an hour ago),
  2. the session (a payment made during a two-hour call with screen share on),
  3. the conversation itself.

The red agent gets levers on all three, which is what makes this an interesting
optimisation rather than a fixed rule.
"""

from __future__ import annotations

from ...util.rng import Rng
from ..narrative import make_scam_episode
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    apply_beneficiary,
    attack_window_ts,
    hours_between,
    make_mule_account,
    pick_victims,
    register,
    stealth_amount,
)


class DigitalArrest(Injector):
    """AV-DIGITAL-ARREST — coercion-authorised payment."""

    vector_id = "AV-DIGITAL-ARREST"
    key = "digital_arrest"
    label = "Coercion-authorised payment (digital arrest)"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth",
            "narrative_intensity", "dwell")
    defaults = {
        "aggression": 0.72, "velocity": 0.68, "spread": 0.35,
        "mimicry": 0.30, "stealth": 0.25, "narrative_intensity": 0.80,
        "dwell": 0.10, "device_hygiene": 1.0,
    }
    weight = 1.35
    txns_per_campaign = 2.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        # Coercion campaigns select the most susceptible customers — this is a
        # targeted-list crime, not an opportunistic one.
        victims = pick_victims(
            world, rng, n_campaigns,
            predicate=lambda c: c.persona in ("senior", "homemaker", "student",
                                              "gig_worker", "salaried_urban"),
        )

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-DA-{i:05d}"
            strain_id = f"ST-{self.key}"
            day = rng.randint(1, max(2, cfg.n_days - 1))
            # These calls run in office hours: the impersonated authority has to
            # be plausible, so the timing is *normal*, not 3am.
            hour = rng.clip_normal(13.0, 3.2, 8.0, 21.0)
            ts = attack_window_ts(cfg, rng, t0=t0, day=day, hour=hour)

            # How much can actually be taken: balance-limited, aggression-scaled.
            extractable = victim.balance * (0.25 + 0.70 * p["aggression"])
            n_legs = 1 + int(round(3 * p["aggression"] * (0.4 + 0.6 * p["spread"])))
            n_legs = max(1, min(5, n_legs))

            episode = make_scam_episode(
                rng, "coercion_authority", extractable, victim.city,
                self.vector_id, intensity=p["narrative_intensity"],
            )
            batch.episodes.append(episode)

            mules = [make_mule_account(world, rng, layer=1,
                                       max_age_days=6.0 + 80.0 * p["mimicry"])
                     for _ in range(max(1, int(round(1 + 2 * p["spread"]))))]

            cursor = ts
            for leg in range(n_legs):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "upi_p2p"
                # Escalating ladder: the script extracts more on each leg.
                share = (0.35 + 0.65 * (leg + 1) / n_legs) / n_legs
                amt = stealth_amount(rng, extractable * share * rng.lognormal(0, 0.18),
                                     p["stealth"])
                rec["amount"] = round(min(amt, victim.balance * 0.98), 2)

                apply_beneficiary(rec, mules[leg % len(mules)])
                rec["auth_method"] = "pin"
                rec["otp_attempts"] = 1 if rng.chance(0.6 + 0.3 * p["mimicry"]) else 2
                rec["step_up_shown"] = int(rec["amount"] > 25000)

                # -- the session is where the fraud is visible ---------------
                # A high-mimicry operator instructs the victim to stop sharing
                # their screen and step away from the call before paying. That
                # buys evasion at the cost of losing control of the victim, so
                # the red agent has to trade it off.
                rec["screen_share"] = int(rng.chance(max(0.02, 0.80 - 0.78 * p["mimicry"])))
                rec["call_active"] = int(rng.chance(max(0.05, 0.95 - 0.70 * p["mimicry"])))
                rec["session_duration_s"] = round(
                    episode.duration_s * (1.0 - 0.75 * p["mimicry"]) * rng.lognormal(0, 0.2)
                    + 60.0, 1)
                # Coerced entry: slow, hesitant, many corrections.
                rec["hesitation_ms"] = round(
                    rng.lognormal(7.6 - 0.9 * p["mimicry"], 0.4), 1)
                rec["form_corrections"] = rng.poisson(3.4 * (1 - 0.6 * p["mimicry"]) + 0.5)
                rec["app_switches"] = rng.poisson(4.0 * (1 - 0.5 * p["mimicry"]) + 0.5)
                rec["typing_variance"] = round(
                    max(0.01, victim.bio_variance * rng.lognormal(0.35, 0.35)), 4)
                rec["narrative_id"] = episode.episode_id

                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                batch.edges.append({
                    "src": victim.self_account, "dst": rec["beneficiary_id"],
                    "ts": cursor, "amount": rec["amount"], "layer": 0,
                    "campaign_id": campaign_id,
                })
                cursor += max(45.0, hours_between(rng, 0.55 + 0.45 * p["velocity"]) * 900)

            batch.campaigns += 1
        batch.notes = "Victim-authorised; transaction telemetry is clean by construction."
        return batch


class VoiceClone(Injector):
    """AV-VOICE-CLONE — cloned-voice relative-in-distress / executive request."""

    vector_id = "AV-VOICE-CLONE"
    key = "voice_clone"
    label = "Cloned-voice distress / executive request"
    uses = ("aggression", "velocity", "spread", "mimicry", "stealth",
            "narrative_intensity")
    defaults = {
        "aggression": 0.45, "velocity": 0.75, "spread": 0.20,
        "mimicry": 0.45, "stealth": 0.55, "narrative_intensity": 0.65,
        "device_hygiene": 1.0, "dwell": 0.08,
    }
    weight = 1.0
    txns_per_campaign = 1.4

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()
        victims = pick_victims(world, rng, n_campaigns)

        for i, victim in enumerate(victims):
            campaign_id = f"CMP-VC-{i:05d}"
            strain_id = f"ST-{self.key}"
            kind = "exec_request" if victim.persona == "sme_owner" else "kin_distress"
            hour = rng.clip_normal(15.0, 4.0, 7.0, 22.5)
            ts = attack_window_ts(cfg, rng, t0=t0,
                                  day=rng.randint(1, max(2, cfg.n_days - 1)), hour=hour)

            # Distress asks stay mid-sized: too large and the victim calls back.
            target = victim.balance * (0.10 + 0.45 * p["aggression"])
            episode = make_scam_episode(rng, kind, target, victim.city,
                                        self.vector_id,
                                        intensity=p["narrative_intensity"])
            batch.episodes.append(episode)

            mule = make_mule_account(world, rng, layer=1,
                                     max_age_days=3.0 + 60.0 * p["mimicry"])
            n_legs = 1 if rng.chance(0.65) else 2
            cursor = ts
            for _ in range(n_legs):
                rec = self.new_record(world, victim, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "upi_p2p"
                rec["amount"] = round(
                    min(stealth_amount(rng, target / n_legs * rng.lognormal(0, 0.2),
                                       p["stealth"]),
                        victim.balance * 0.9), 2)
                apply_beneficiary(rec, mule)
                rec["auth_method"] = "pin"
                rec["step_up_shown"] = int(rec["amount"] > 25000)
                rec["call_active"] = int(rng.chance(max(0.10, 0.92 - 0.6 * p["mimicry"])))
                rec["screen_share"] = int(rng.chance(0.05))
                rec["session_duration_s"] = round(
                    rng.lognormal(5.6 - 0.7 * p["mimicry"], 0.5), 1)
                rec["hesitation_ms"] = round(rng.lognormal(7.1 - 0.7 * p["mimicry"], 0.45), 1)
                rec["form_corrections"] = rng.poisson(2.2)
                rec["app_switches"] = rng.poisson(2.6)
                rec["narrative_id"] = episode.episode_id

                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                batch.edges.append({
                    "src": victim.self_account, "dst": mule.account_id,
                    "ts": cursor, "amount": rec["amount"], "layer": 0,
                    "campaign_id": campaign_id,
                })
                cursor += rng.uniform(120, 900)
            batch.campaigns += 1
        return batch


register(DigitalArrest())
register(VoiceClone())
