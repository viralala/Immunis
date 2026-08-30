"""Legitimate transaction generation — the baseline the attacks are measured against.

Design principle: **make the legitimate class hard.**

A synthetic fraud dataset whose legitimate traffic is homogeneous makes
"unusual == fraud" trivially true, and every model trained on it reports a
meaningless AUC.  So this generator deliberately produces messy legitimate
behaviour:

  * heterogeneous personas with different tickets, rhythms and instrument mixes,
  * salary-day, weekend and festival demand structure,
  * shared household devices,
  * and ~3% *benign anomalies* — real travel, genuine first big-ticket
    purchases, device upgrades, first payments to a new landlord — which look
    exactly like the surface signals of fraud and are labelled legitimate.

Those benign anomalies are the false-positive pressure.  Everything the
detector claims about precision only means something because they are there.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ..util.geo import haversine_km, jitter_geo
from ..util.rng import Rng
from .entities import PERSONA_BY_KEY, Customer, Merchant
from .population import World

SECONDS_PER_DAY = 86_400

# Benign-anomaly taxonomy. These are legitimate, and each one mimics a
# different fraud tell.
BENIGN_ANOMALIES = [
    "travel",             # looks like geo-velocity fraud
    "big_ticket",         # looks like a bust-out or ATO cash-out
    "new_device",         # looks like device takeover
    "new_beneficiary",    # looks like APP fraud
    "night_activity",     # looks like an out-of-hours attack
    "category_excursion", # looks like a liquidation spree
    "burst",              # looks like card testing
]
BENIGN_WEIGHTS = [0.22, 0.20, 0.14, 0.16, 0.10, 0.11, 0.07]


def epoch_of(date_str: str) -> int:
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _day_multiplier(day: int, start_dow: int) -> float:
    """Demand structure across the calendar."""
    dow = (start_dow + day) % 7
    m = 1.0
    if dow in (5, 6):                       # weekend uplift
        m *= 1.18
    if dow == 0:                            # Monday dip
        m *= 0.93
    dom = (day % 30) + 1
    if dom <= 5:                            # salary week
        m *= 1.22
    elif 25 <= dom <= 29:                   # pre-payday squeeze
        m *= 0.88
    if 18 <= day <= 21:                     # festival window
        m *= 1.45
    return m


def _pick_hour(rng: Rng, night_share: float) -> float:
    """Circadian mixture: morning, midday, evening peaks plus a night tail."""
    if rng.chance(night_share):
        h = rng.uniform(23.0, 29.0) % 24.0
    else:
        comp = rng.weighted([0, 1, 2], [0.26, 0.32, 0.42])
        mu, sd = [(9.6, 1.5), (13.6, 1.5), (19.6, 2.0)][comp]
        h = rng.clip_normal(mu, sd, 5.0, 23.5)
    return h


def _amount_for(rng: Rng, cust: Customer, merch: Merchant) -> float:
    mu = 0.55 * cust.amount_mu + 0.45 * merch.amount_mu
    sigma = 0.6 * cust.amount_sigma + 0.4 * merch.amount_sigma
    amt = rng.lognormal(mu, sigma)
    # Real payment amounts cluster on round numbers far more than a lognormal.
    if rng.chance(0.34):
        step = 50.0 if amt < 2000 else (100.0 if amt < 20000 else 500.0)
        amt = max(step, round(amt / step) * step)
    return round(min(amt, 900_000.0), 2)


def _pick_merchant(rng: Rng, cust: Customer, world: World, *, novel: bool = False) -> Merchant:
    if not novel and cust.known_merchants and rng.chance(0.78):
        return world.merchant_index[rng.choice(cust.known_merchants)]
    # Novel merchant, but still weighted by the customer's category taste and
    # by distance — customers do not shop uniformly at random.
    pool = rng.sample(world.merchants, min(60, len(world.merchants)))
    weights = []
    for m in pool:
        w = cust.category_affinity.get(m.category, 0.3)
        if m.country != cust.country:
            w *= 0.10
        else:
            d = haversine_km(cust.lat, cust.lon, m.lat, m.lon)
            w *= 1.0 / (1.0 + (d / 25.0) ** 1.35) if m.online_share < 0.5 else 0.75
        weights.append(max(w, 1e-4))
    return rng.weighted(pool, weights)


def _pick_rail(rng: Rng, cust: Customer) -> str:
    keys = list(cust.rail_mix.keys())
    return rng.weighted(keys, [cust.rail_mix[k] for k in keys])


def base_record(txn_id: str, ts: float, cust: Customer) -> dict:
    """Every transaction — legitimate or fraudulent — starts from this shape."""
    return {
        "txn_id": txn_id,
        "ts": float(ts),
        "customer_id": cust.customer_id,
        "persona": cust.persona,
        "rail": "upi_p2m",
        "amount": 0.0,
        "merchant_id": None,
        "mcc": None,
        "merchant_category": None,
        "merchant_risk_tier": 1,
        "merchant_age_days": 0.0,
        "merchant_country": cust.country,
        "beneficiary_id": None,
        "beneficiary_bank": None,
        "beneficiary_age_days": 0.0,
        "device_id": cust.primary_device,
        "device_os": cust.devices[0].os,
        "device_age_days": cust.devices[0].age_days,
        "device_is_emulator": 0,
        "device_is_rooted": int(cust.devices[0].is_rooted),
        "device_sim_count": cust.devices[0].sim_count,
        "device_attested": int(cust.devices[0].attested),
        "city": cust.city,
        "country": cust.country,
        "lat": cust.lat,
        "lon": cust.lon,
        "auth_method": "pin",
        "otp_attempts": 1,
        "threeds_result": 1,
        "step_up_shown": 0,
        "session_duration_s": 60.0,
        "screen_share": 0,
        "call_active": 0,
        "hesitation_ms": 900.0,
        "app_switches": 0,
        "typing_variance": cust.bio_variance,
        "form_corrections": 1,
        "is_agentic": 0,
        "agent_id": None,
        "agent_attested": 1,
        "mandate_ceiling": 0.0,
        "mandate_age_h": 0.0,
        "mandate_scope_breadth": 0.0,
        "mandate_intent_category": None,
        "human_confirmations": 0,
        "instrument_age_days": cust.account_age_days,
        "dispute_filed": 0,
        "customer_balance": cust.balance,
        "customer_account_age_days": cust.account_age_days,
        "susceptibility": cust.susceptibility,
        "narrative_id": None,
        "coercion_score": 0.0,
        "is_fraud": 0,
        "vector_id": None,
        "strain_id": None,
        "campaign_id": None,
        "benign_anomaly": None,
    }


def _fill_session(rng: Rng, rec: dict, cust: Customer, rail: str) -> None:
    """Session and behavioural telemetry for a legitimate interaction."""
    if rail in ("upi_p2p",):
        base = rng.lognormal(3.9, 0.55)      # payee entry takes longer
    elif rail in ("card_cnp", "agentic"):
        base = rng.lognormal(4.6, 0.75)      # browsing before checkout
    else:
        base = rng.lognormal(3.1, 0.50)
    rec["session_duration_s"] = round(min(base, 3600.0), 1)
    # Habitual users are fast; low-maturity users hesitate more.
    rec["hesitation_ms"] = round(
        max(120.0, rng.lognormal(6.4 + 0.9 * (1 - cust.digital_maturity), 0.45)), 1)
    rec["app_switches"] = rng.poisson(0.7 if rail != "card_cnp" else 1.4)
    # Genuine humans vary. The behavioural-clone attack is detectable precisely
    # because it fails to reproduce this variance.
    rec["typing_variance"] = round(
        max(0.01, cust.bio_variance * rng.lognormal(0.0, 0.30)), 4)
    rec["form_corrections"] = rng.poisson(1.1 + 1.4 * (1 - cust.digital_maturity))
    # Legitimate screen-share and in-call payments DO happen (genuine support
    # calls, someone helping a parent). Non-zero base rates are what stop these
    # from being trivially perfect fraud rules.
    rec["screen_share"] = int(rng.chance(0.0022))
    rec["call_active"] = int(rng.chance(0.016))


def _apply_auth(rng: Rng, rec: dict, cust: Customer, rail: str, amount: float) -> None:
    if rail == "card_cnp":
        rec["auth_method"] = "3ds"
        challenged = amount > 5000 or rng.chance(0.22)
        rec["step_up_shown"] = int(challenged)
        rec["threeds_result"] = 2 if challenged else 1
        rec["otp_attempts"] = 1 if rng.chance(0.93) else 2
    elif rail in ("upi_p2m", "upi_p2p"):
        rec["auth_method"] = "pin"
        rec["otp_attempts"] = 1
        rec["step_up_shown"] = int(amount > 25000)
    elif rail == "card_cp":
        rec["auth_method"] = "biometric" if rng.chance(0.4) else "pin"
        rec["threeds_result"] = 0
        rec["step_up_shown"] = int(amount > 5000)
    elif rail == "wallet":
        rec["auth_method"] = "biometric"
        rec["threeds_result"] = 0
    elif rail == "agentic":
        rec["auth_method"] = "mandate"
        rec["threeds_result"] = 1


def generate_legit(world: World, rng: Rng, cfg) -> list[dict]:
    """Generate the legitimate transaction ledger."""
    r = rng.fork("legit")
    t0 = epoch_of(cfg.start_date)
    start_dow = datetime.fromisoformat(cfg.start_date).weekday()
    n_days = cfg.n_days

    records: list[dict] = []
    counter = 0

    # Multi-day travel episodes are assigned up front so they are contiguous,
    # not a scattering of single anomalous transactions.
    travel_windows: dict[str, tuple[int, int, tuple[str, str, float, float]]] = {}
    from ..util.geo import CITIES

    for c in world.customers:
        persona_travel = PERSONA_BY_KEY[c.persona].travel_rate
        if r.chance(min(0.85, persona_travel)) and n_days > 6:
            start = r.randint(1, max(2, n_days - 4))
            length = r.randint(2, 6)
            dest = r.weighted(CITIES, [x[4] for x in CITIES])
            if dest[0] != c.city:
                travel_windows[c.customer_id] = (start, start + length,
                                                 (dest[0], dest[1], dest[2], dest[3]))

    for c in world.customers:
        tw = travel_windows.get(c.customer_id)
        # Per-customer device-upgrade event: a new device that then becomes
        # primary. Mimics device-takeover signals but is entirely legitimate.
        upgrade_day = r.randint(3, n_days) if r.chance(0.06) else None
        upgraded_device = None

        for day in range(n_days):
            lam = c.txn_per_day * _day_multiplier(day, start_dow)
            n = r.poisson(lam)
            if n == 0:
                continue

            travelling = bool(tw and tw[0] <= day < tw[1])
            if upgrade_day is not None and day == upgrade_day and upgraded_device is None:
                upgraded_device = f"{c.devices[0].device_id}-N"

            for _ in range(n):
                counter += 1
                hour = _pick_hour(r, c.night_share)
                ts = t0 + day * SECONDS_PER_DAY + hour * 3600 + r.uniform(0, 3600)
                rec = base_record(f"T{counter:08d}-{c.customer_id[-4:]}", ts, c)
                # Entity ages advance with the simulation clock, so a young
                # account genuinely matures over the window.
                rec["customer_account_age_days"] = c.account_age_days + day
                rec["instrument_age_days"] = c.account_age_days + day

                rail = _pick_rail(r, c)
                rec["rail"] = rail

                # -- device --------------------------------------------------
                dev = c.devices[0] if r.chance(0.88) else r.choice(c.devices)
                rec["device_id"] = dev.device_id
                rec["device_os"] = dev.os
                rec["device_age_days"] = dev.age_days + day
                rec["device_is_rooted"] = int(dev.is_rooted)
                rec["device_sim_count"] = dev.sim_count
                rec["device_attested"] = int(dev.attested)
                if upgraded_device and day >= (upgrade_day or 0):
                    if r.chance(0.8):
                        rec["device_id"] = upgraded_device
                        rec["device_age_days"] = float(day - (upgrade_day or 0)) + 0.5
                        rec["benign_anomaly"] = "new_device"

                # -- geography ----------------------------------------------
                if travelling and tw:
                    dcity, dcountry, dlat, dlon = tw[2]
                    jl, jo = jitter_geo(dlat, dlon, r.uniform(0.5, 12.0), r)
                    rec["city"], rec["country"] = dcity, dcountry
                    rec["lat"], rec["lon"] = jl, jo
                    rec["benign_anomaly"] = "travel"
                else:
                    jl, jo = jitter_geo(c.lat, c.lon, r.uniform(0.1, 9.0), r)
                    rec["lat"], rec["lon"] = jl, jo

                # -- counterparty -------------------------------------------
                if rail == "upi_p2p":
                    if c.contacts and r.chance(0.88):
                        acct = r.choice(c.contacts)
                    else:
                        acct = r.choice(list(world.accounts.keys()))
                        if r.chance(0.5):
                            rec["benign_anomaly"] = "new_beneficiary"
                    a = world.accounts[acct]
                    rec["beneficiary_id"] = acct
                    rec["beneficiary_bank"] = a.bank
                    rec["beneficiary_age_days"] = a.age_days + day
                    amount = round(min(r.lognormal(c.amount_mu + 0.35,
                                                   c.amount_sigma), 400_000.0), 2)
                else:
                    m = _pick_merchant(r, c, world)
                    rec["merchant_id"] = m.merchant_id
                    rec["mcc"] = m.mcc
                    rec["merchant_category"] = m.category
                    rec["merchant_risk_tier"] = m.risk_tier
                    rec["merchant_age_days"] = m.age_days + day
                    rec["merchant_country"] = m.country
                    if travelling and m.online_share < 0.5:
                        rec["city"] = m.city
                        rec["country"] = m.country
                    amount = _amount_for(r, c, m)

                # -- agentic adoption ----------------------------------------
                if rail == "agentic" or (rail == "card_cnp" and r.chance(c.agent_adoption * 0.25)):
                    rec["rail"] = "agentic" if rail == "agentic" else rec["rail"]
                    rec["is_agentic"] = 1
                    rec["agent_id"] = f"AG-{r.randint(1, 6):02d}"
                    rec["agent_attested"] = 1
                    # A sane consumer mandate: a small multiple of their own
                    # typical ticket, used well below the ceiling.
                    rec["mandate_ceiling"] = round(math.exp(c.amount_mu) * r.uniform(2.5, 6.0), 2)
                    rec["mandate_age_h"] = r.uniform(24.0, 2400.0)
                    rec["mandate_scope_breadth"] = r.uniform(0.05, 0.35)
                    # A genuine agent buys what it was asked to buy; intent and
                    # merchant category agree almost all of the time.
                    rec["mandate_intent_category"] = (
                        rec["merchant_category"] if r.chance(0.93)
                        else r.choice(["retail", "digital", "travel", "essentials"]))
                    rec["human_confirmations"] = 1 if r.chance(0.55) else 0
                    amount = min(amount, rec["mandate_ceiling"] * r.uniform(0.05, 0.55))

                rec["amount"] = round(amount, 2)
                _fill_session(r, rec, c, rec["rail"])
                _apply_auth(r, rec, c, rec["rail"], rec["amount"])
                records.append(rec)

    # -- point benign anomalies -------------------------------------------
    _inject_benign_anomalies(records, world, r, cfg)

    # Genuine disputes happen on legitimate transactions too (goods not
    # received, duplicate charges). Without them, "customer has disputed before"
    # would be a perfect first-party-misuse detector.
    for rec in records:
        if r.chance(0.0035):
            rec["dispute_filed"] = 1

    records.sort(key=lambda x: x["ts"])
    return records


def _inject_benign_anomalies(records: list[dict], world: World, rng: Rng, cfg) -> None:
    """Overlay the remaining benign-anomaly types onto legitimate records.

    Travel, new-device and new-beneficiary anomalies are produced structurally
    above; this adds the point-in-time ones.  Together they land at roughly
    ``benign_anomaly_rate`` of the ledger.
    """
    need = int(len(records) * cfg.benign_anomaly_rate)
    if need == 0:
        return

    candidates = [r_ for r_ in records if not r_["benign_anomaly"]]
    chosen = rng.sample(candidates, min(need, len(candidates)))
    point_types = ["big_ticket", "night_activity", "category_excursion", "burst"]
    point_weights = [0.38, 0.20, 0.26, 0.16]

    for rec in chosen:
        kind = rng.weighted(point_types, point_weights)
        rec["benign_anomaly"] = kind
        cust = world.customer_index[rec["customer_id"]]

        if kind == "big_ticket":
            # A genuine large purchase: a laptop, a flight, a hospital bill.
            rec["amount"] = round(rec["amount"] * rng.uniform(7.0, 24.0), 2)
            rec["amount"] = min(rec["amount"], cust.balance * 0.9 + 5000)
            rec["step_up_shown"] = 1
            rec["session_duration_s"] = round(rec["session_duration_s"] * rng.uniform(1.5, 4.0), 1)
        elif kind == "night_activity":
            day_ts = rec["ts"] - (rec["ts"] % SECONDS_PER_DAY)
            rec["ts"] = day_ts + rng.uniform(1.0, 4.5) * 3600
        elif kind == "category_excursion":
            pool = [m for m in world.merchants
                    if cust.category_affinity.get(m.category, 0.0) < 0.6]
            if pool:
                m = rng.choice(pool)
                rec["merchant_id"] = m.merchant_id
                rec["mcc"] = m.mcc
                rec["merchant_category"] = m.category
                rec["merchant_risk_tier"] = m.risk_tier
                rec["merchant_age_days"] = m.age_days
                rec["merchant_country"] = m.country
                rec["rail"] = "card_cnp" if m.online_share > 0.5 else rec["rail"]
        elif kind == "burst":
            # A genuine rapid sequence: retries after a failure, or splitting a
            # payment across instruments. Looks exactly like card testing.
            rec["amount"] = round(max(20.0, rec["amount"] * rng.uniform(0.05, 0.2)), 2)
            rec["session_duration_s"] = round(rec["session_duration_s"] * 0.4, 1)


def generate_cover_traffic(world: World, rng: Rng, cfg, customer_ids: list[str],
                           t0: int) -> list[dict]:
    """Ordinary, legitimate activity from attacker-controlled identities.

    A mule account that has only ever moved fraud proceeds is a simulation
    artefact. Real mules and real synthetic identities buy groceries, top up
    their phone and pay for a ride — that cover traffic is exactly why
    "this account only ever did something suspicious" is not a feature you get
    in production. Generating it removes a shortcut the detector would
    otherwise learn instead of learning the typology.
    """
    r = rng.fork("cover")
    lo, hi = cfg.cover_traffic_per_synthetic
    out: list[dict] = []
    counter = 0
    everyday = [m for m in world.merchants
                if m.category in ("essentials", "food", "transport", "digital")]
    everyday = everyday or world.merchants

    for cid in customer_ids:
        c = world.customer_index.get(cid)
        if c is None:
            continue
        for _ in range(r.randint(lo, hi + 1)):
            counter += 1
            day = r.randint(0, max(1, cfg.n_days))
            hour = _pick_hour(r, 0.12)
            ts = t0 + day * SECONDS_PER_DAY + hour * 3600 + r.uniform(0, 3600)
            rec = base_record(f"TC{counter:07d}-{cid[-4:]}", ts, c)
            m = r.choice(everyday)
            rec["rail"] = r.weighted(["upi_p2m", "card_cnp", "wallet"], [0.7, 0.2, 0.1])
            rec["merchant_id"] = m.merchant_id
            rec["mcc"] = m.mcc
            rec["merchant_category"] = m.category
            rec["merchant_risk_tier"] = m.risk_tier
            rec["merchant_age_days"] = m.age_days + day
            rec["merchant_country"] = m.country
            rec["amount"] = round(r.lognormal(m.amount_mu - 0.3, m.amount_sigma), 2)
            rec["customer_account_age_days"] = c.account_age_days + day
            rec["instrument_age_days"] = c.account_age_days + day
            lat, lon = jitter_geo(c.lat, c.lon, r.uniform(0.2, 8.0), r)
            rec["lat"], rec["lon"] = lat, lon
            _fill_session(r, rec, c, rec["rail"])
            _apply_auth(r, rec, c, rec["rail"], rec["amount"])
            out.append(rec)
    return out
