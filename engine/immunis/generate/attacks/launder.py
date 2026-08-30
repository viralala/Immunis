"""Money-movement / laundering-structure injector."""

from __future__ import annotations

from ...util.rng import Rng
from ..population import World
from .base import (
    AttackBatch,
    Injector,
    apply_beneficiary,
    apply_device,
    attack_window_ts,
    make_mule_account,
    make_synthetic_customer,
    pick_victims,
    register,
    stealth_amount,
)
from .auth import _apply_merchant, _liquid_merchant


class MuleLayering(Injector):
    """AV-MULE-LAYER — fan-in / fan-out layering across a mule tree.

    This is the only injector whose signal is almost entirely *structural*.
    Every individual hop is a small, ordinary account-to-account transfer.  What
    is anomalous is the shape: a young account with simultaneous high in-degree
    and out-degree, a pass-through ratio near 1.0, dwell time in minutes, and
    value that decays by a constant fee margin at every hop.

    It is the clearest argument in the whole build for graph features living in
    the real-time authorisation path, and the clearest argument for a *network*
    doing it, since no single bank sees more than one layer of the tree.
    """

    vector_id = "AV-MULE-LAYER"
    key = "mule_layer"
    label = "Fan-in / fan-out mule layering"
    uses = ("aggression", "velocity", "spread", "mimicry", "dwell", "stealth")
    defaults = {
        "aggression": 0.65, "velocity": 0.85, "device_hygiene": 0.35,
        "spread": 0.70, "mimicry": 0.35, "dwell": 0.12, "stealth": 0.55,
        "narrative_intensity": 0.0,
    }
    weight = 1.25
    txns_per_campaign = 58.0

    def run(self, world: World, rng: Rng, cfg, params, n_campaigns: int, t0: int
            ) -> AttackBatch:
        p = params
        batch = AttackBatch()

        for i in range(n_campaigns):
            campaign_id = f"CMP-ML-{i:05d}"
            strain_id = f"ST-{self.key}"

            # -- layer 0: the predicate inflow --------------------------------
            n_sources = max(2, int(round(2 + 8 * p["aggression"])))
            sources = pick_victims(world, rng, n_sources)
            entry = make_synthetic_customer(
                world, rng, hygiene=p["device_hygiene"], persona="gig_worker",
                account_age_days=rng.uniform(1.0, 6.0 + 70.0 * p["mimicry"]),
                balance=0.0,
            )
            entry_dev = entry.devices[0]

            day = rng.randint(0, max(1, cfg.n_days - 3))
            cursor = attack_window_ts(cfg, rng, t0=t0, day=day,
                                      hour=rng.uniform(6.0, 23.0))
            pot = 0.0
            for src in sources:
                rec = self.new_record(world, src, cursor, rng, campaign_id, strain_id)
                rec["rail"] = "upi_p2p"
                rec["amount"] = round(stealth_amount(
                    rng, src.balance * rng.uniform(0.08, 0.40) * p["aggression"] + 800,
                    p["stealth"]), 2)
                apply_beneficiary(rec, world.accounts[entry.self_account])
                rec["session_duration_s"] = round(rng.lognormal(4.8, 0.6), 1)
                rec["call_active"] = int(rng.chance(0.35))
                pot += rec["amount"]
                batch.transactions.append(rec)
                batch.value_extracted += rec["amount"]
                batch.edges.append({"src": src.self_account, "dst": entry.self_account,
                                    "ts": cursor, "amount": rec["amount"], "layer": 0,
                                    "campaign_id": campaign_id})
                cursor += max(20.0, rng.lognormal(6.4 - 3.0 * p["velocity"], 0.7))

            # -- layers 1..n: the widening tree -------------------------------
            depth = max(1, int(round(1 + 3 * p["spread"])))
            # Real layering trees are wide but bounded — an operator only has so
            # many warm accounts. The cap keeps campaign size realistic and keeps
            # the fraud budget from being swallowed by one exponential tree.
            node_budget = int(24 + 46 * p["spread"])
            emitted = 0
            frontier = [(entry, entry_dev, pot)]
            for layer in range(1, depth + 1):
                next_frontier = []
                for holder, dev, value in frontier:
                    if value < 400 or emitted >= node_budget:
                        continue
                    # Dwell: value held before onward movement. Low dwell is fast
                    # and unrecoverable but glaringly obvious; high dwell is
                    # quieter but exposes the mule to freeze orders.
                    hold = (30.0 + 26 * 3600.0 * p["dwell"]) * rng.lognormal(0, 0.5)
                    t = cursor + hold
                    n_split = max(1, int(round(2 + 4 * p["spread"])))
                    # Operators retain a fee at each hop — value decays smoothly.
                    keep = 0.02 + 0.06 * (1 - p["mimicry"])
                    per = value * (1 - keep) / n_split
                    for _ in range(n_split):
                        if emitted >= node_budget:
                            break
                        emitted += 1
                        nxt = make_synthetic_customer(
                            world, rng, hygiene=p["device_hygiene"],
                            persona="student",
                            account_age_days=rng.uniform(0.5, 5.0 + 60.0 * p["mimicry"]),
                            balance=0.0,
                        ) if layer < depth else None

                        rec = self.new_record(world, holder, t, rng, campaign_id, strain_id)
                        rec["amount"] = round(stealth_amount(
                            rng, per * rng.lognormal(0, 0.12), p["stealth"]), 2)
                        apply_device(rec, dev)
                        if nxt is not None:
                            rec["rail"] = "upi_p2p"
                            apply_beneficiary(rec, world.accounts[nxt.self_account])
                            batch.edges.append({
                                "src": holder.self_account, "dst": nxt.self_account,
                                "ts": t, "amount": rec["amount"], "layer": layer,
                                "campaign_id": campaign_id})
                            next_frontier.append((nxt, nxt.devices[0], rec["amount"]))
                        else:
                            # Terminal hop: cash-equivalent exit.
                            rec["rail"] = rng.weighted(["card_cp", "upi_p2m"], [0.6, 0.4])
                            _apply_merchant(rec, _liquid_merchant(world, rng, 0.92))
                        rec["session_duration_s"] = round(rng.lognormal(2.3, 0.4), 1)
                        rec["hesitation_ms"] = round(rng.lognormal(4.7, 0.4), 1)
                        rec["form_corrections"] = 0
                        rec["instrument_age_days"] = holder.account_age_days
                        batch.transactions.append(rec)
                        t += max(5.0, rng.lognormal(4.4 - 2.6 * p["velocity"], 0.6))
                frontier = next_frontier
                if not frontier:
                    break
            batch.campaigns += 1

        batch.notes = ("Pass-through ratio, dwell time and simultaneous in/out "
                       "degree on a young account carry this typology.")
        return batch


register(MuleLayering())
