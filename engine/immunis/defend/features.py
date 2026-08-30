"""Causal feature engineering.

Two rules govern this module, and both exist to stop the evaluation from
lying:

**1. Strictly causal.**  Every feature for a transaction at time *t* is computed
from events strictly before *t*.  The ledger is processed once, in timestamp
order, maintaining streaming state — the same shape a Flink/Kafka job would
have in production.  There is no group-by over the full dataset anywhere.

**2. No simulator internals.**  Fields that exist only because this is a
simulation — ``susceptibility`` (which drives victim selection), ``vector_id``,
``strain_id``, ``campaign_id``, ``benign_anomaly`` — are never featurised.  Nor
is the current transaction's own ``dispute_filed``, which is only knowable
after the fact; the customer's *prior* dispute history is used instead, because
that genuinely is available at authorisation time.

The feature families map onto the atlas: velocity and novelty catch takeover,
graph catches layering, session and variance catch cloning, mandate features
catch agentic abuse, and the narrative channel catches coercion.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

import numpy as np

from ..util.geo import HIGH_RISK_COUNTRIES, haversine_km

HOUR = 3600.0
DAY = 86_400.0
WEEK = 7 * DAY

RAILS = ["upi_p2m", "upi_p2p", "card_cnp", "card_cp", "wallet", "agentic", "remittance"]
AUTH_METHODS = ["pin", "otp", "3ds", "biometric", "passkey", "mandate", "none"]
CATEGORIES = ["essentials", "food", "transport", "health", "retail", "digital",
              "financial", "cash", "highrisk", "travel", "luxury", "liquid",
              "education", "services", "unknown"]
PERSONAS = ["salaried_urban", "student", "senior", "gig_worker", "sme_owner",
            "hnw", "homemaker"]
DEVICE_OS = ["android", "ios", "web", "android_tv", "unknown"]
LIQUID = {"liquid", "cash", "highrisk", "luxury", "financial"}

#: Fields that must never become features.
FORBIDDEN = {
    "is_fraud", "vector_id", "strain_id", "campaign_id", "benign_anomaly",
    "susceptibility", "dispute_filed", "txn_id", "customer_id", "merchant_id",
    "beneficiary_id", "device_id", "narrative_id", "agent_id", "city",
    "country", "merchant_country", "beneficiary_bank", "mcc",
    "merchant_category", "auth_method", "rail", "persona", "device_os",
    "mandate_intent_category", "lat", "lon", "ts",
}


NAN = float("nan")


def _opt(v: Any) -> float:
    """Optional telemetry: absent becomes NaN, which the GBM handles natively.

    Zero would be a lie — "no screen share" and "we could not observe screen
    share" are different facts, and conflating them is how a model learns to
    treat a whole channel as low risk.
    """
    return NAN if v is None else float(v)


def _idx(seq: list[str], v: Any, default: int = -1) -> int:
    try:
        return seq.index(v)
    except (ValueError, AttributeError):
        return default


class _RunningStat:
    """Welford accumulator: streaming mean/std with no stored history."""

    __slots__ = ("n", "mean", "m2")

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def push(self, x: float) -> None:
        if x is None or x != x:          # NaN-safe: absent telemetry is skipped
            return
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    @property
    def std(self) -> float:
        return math.sqrt(self.m2 / (self.n - 1)) if self.n > 1 else 0.0

    def z(self, x: float) -> float:
        if self.n < 3:
            return 0.0
        s = self.std
        return (x - self.mean) / s if s > 1e-9 else 0.0


class _Window:
    """Sliding time window of (ts, amount) with O(1) amortised eviction."""

    __slots__ = ("dq", "span", "total")

    def __init__(self, span: float) -> None:
        self.dq: deque[tuple[float, float]] = deque()
        self.span = span
        self.total = 0.0

    def evict(self, now: float) -> None:
        cut = now - self.span
        dq = self.dq
        while dq and dq[0][0] < cut:
            self.total -= dq.popleft()[1]

    def push(self, ts: float, amount: float) -> None:
        self.dq.append((ts, amount))
        self.total += amount

    def count(self, now: float) -> int:
        self.evict(now)
        return len(self.dq)

    def sum(self, now: float) -> float:
        self.evict(now)
        return self.total


class _CustState:
    __slots__ = ("w1h", "w24h", "w7d", "amt", "hour_sin", "hour_cos", "n",
                 "merchants", "beneficiaries", "devices", "cities", "categories",
                 "last_ts", "last_lat", "last_lon", "first_ts", "recent_amts",
                 "disputes", "session", "typing", "hesitation", "home_lat",
                 "home_lon", "mandates", "night_count")

    def __init__(self, lat: float, lon: float) -> None:
        self.w1h = _Window(HOUR)
        self.w24h = _Window(DAY)
        self.w7d = _Window(WEEK)
        self.amt = _RunningStat()
        self.session = _RunningStat()
        self.typing = _RunningStat()
        self.hesitation = _RunningStat()
        self.hour_sin = 0.0
        self.hour_cos = 0.0
        self.n = 0
        self.night_count = 0
        self.merchants: set[str] = set()
        self.beneficiaries: set[str] = set()
        self.devices: set[str] = set()
        self.cities: set[str] = set()
        self.categories: set[str] = set()
        self.last_ts = 0.0
        self.last_lat = lat
        self.last_lon = lon
        self.home_lat = lat
        self.home_lon = lon
        self.first_ts = 0.0
        self.recent_amts: deque[float] = deque(maxlen=60)
        self.disputes: deque[float] = deque()          # timestamps
        self.mandates: dict[str, float] = defaultdict(float)   # agent_id -> drawn


class _AcctState:
    __slots__ = ("in_1h", "in_24h", "in_payers_24h", "out_1h", "out_24h",
                 "last_in_ts", "last_in_amt", "first_seen", "n_in", "n_out")

    def __init__(self) -> None:
        self.in_1h = _Window(HOUR)
        self.in_24h = _Window(DAY)
        self.out_1h = _Window(HOUR)
        self.out_24h = _Window(DAY)
        self.in_payers_24h: deque[tuple[float, str]] = deque()
        self.last_in_ts = 0.0
        self.last_in_amt = 0.0
        self.first_seen = 0.0
        self.n_in = 0
        self.n_out = 0

    def payers(self, now: float) -> int:
        cut = now - DAY
        while self.in_payers_24h and self.in_payers_24h[0][0] < cut:
            self.in_payers_24h.popleft()
        return len({p for _, p in self.in_payers_24h})


class _DeviceState:
    __slots__ = ("customers", "w1h", "w24h", "first_seen", "n")

    def __init__(self) -> None:
        self.customers: set[str] = set()
        self.w1h = _Window(HOUR)
        self.w24h = _Window(DAY)
        self.first_seen = 0.0
        self.n = 0


class _MerchState:
    __slots__ = ("customers", "repeat", "w1h", "w24h", "amt", "first_seen", "n")

    def __init__(self) -> None:
        self.customers: set[str] = set()
        self.repeat = 0
        self.w1h = _Window(HOUR)
        self.w24h = _Window(DAY)
        self.amt = _RunningStat()
        self.first_seen = 0.0
        self.n = 0


FEATURE_NAMES: list[str] = [
    # -- amount ------------------------------------------------------------
    "amount", "log_amount", "amount_z_customer", "amount_to_p95",
    "amount_to_balance", "amount_to_merchant_mean", "amount_round_ness",
    "amount_below_threshold_gap",
    # -- velocity ----------------------------------------------------------
    "cust_txn_1h", "cust_txn_24h", "cust_txn_7d",
    "cust_amt_1h", "cust_amt_24h", "cust_amt_7d",
    "cust_burst_ratio", "secs_since_last_txn", "cust_txn_total",
    "cust_amt_24h_to_balance",
    # -- novelty -----------------------------------------------------------
    "is_new_merchant", "is_new_beneficiary", "is_new_device", "is_new_city",
    "is_new_category", "cust_tenure_days", "cust_known_merchants",
    "cust_known_beneficiaries", "cust_known_devices",
    # -- temporal ----------------------------------------------------------
    "hour", "hour_sin", "hour_cos", "is_night", "day_of_week", "is_weekend",
    "hour_deviation", "cust_night_rate",
    # -- geo ---------------------------------------------------------------
    "dist_from_home_km", "dist_from_last_km", "travel_speed_kmh",
    "is_foreign", "is_high_risk_country", "merchant_is_foreign",
    # -- device ------------------------------------------------------------
    "device_age_days", "device_is_emulator", "device_is_rooted",
    "device_sim_count", "device_attested", "device_customer_count",
    "device_txn_1h", "device_txn_24h", "device_tenure_days",
    # -- merchant ----------------------------------------------------------
    "merchant_age_days", "merchant_risk_tier", "merchant_is_liquid",
    "merchant_txn_1h", "merchant_txn_24h", "merchant_distinct_customers",
    "merchant_repeat_rate", "merchant_chargeback_rate", "merchant_tenure_days",
    # -- graph -------------------------------------------------------------
    "benef_age_days", "benef_in_count_1h", "benef_in_count_24h",
    "benef_distinct_payers_24h", "benef_in_amt_24h", "benef_out_count_1h",
    "benef_passthrough_ratio", "benef_dwell_secs", "benef_tenure_days",
    "sender_passthrough_ratio", "sender_dwell_secs", "sender_in_24h",
    # -- session / behavioural --------------------------------------------
    "session_duration_s", "session_ratio_customer", "hesitation_ms",
    "hesitation_ratio_customer", "app_switches", "form_corrections",
    "typing_variance", "typing_variance_ratio", "screen_share", "call_active",
    "screen_share_and_new_benef", "session_per_txn_value",
    # -- auth --------------------------------------------------------------
    "threeds_result", "otp_attempts", "step_up_shown", "instrument_age_days",
    "customer_account_age_days", "customer_balance",
    # -- disputes ----------------------------------------------------------
    "cust_prior_disputes_90d", "cust_prior_dispute_rate",
    # -- agentic -----------------------------------------------------------
    "is_agentic", "agent_attested", "mandate_ceiling", "mandate_age_h",
    "mandate_scope_breadth", "mandate_ceiling_to_typical",
    "mandate_drawdown_ratio", "mandate_intent_match", "human_confirmations",
    "amount_to_mandate_ceiling",
    # -- narrative (filled by the text channel) ----------------------------
    "has_episode", "coercion_score", "episode_turns", "episode_duration_s",
    # -- categoricals (ordinal-encoded; declared to the GBM) ---------------
    "cat_rail", "cat_auth_method", "cat_merchant_category", "cat_persona",
    "cat_device_os",
]

CATEGORICAL_FEATURES = ["cat_rail", "cat_auth_method", "cat_merchant_category",
                        "cat_persona", "cat_device_os"]
CATEGORICAL_IDX = [FEATURE_NAMES.index(c) for c in CATEGORICAL_FEATURES]

#: Human-readable explanations used for analyst-facing reason codes.
REASON_TEXT: dict[str, str] = {
    "amount_z_customer": "Amount far outside this customer's own spending distribution",
    "amount_to_p95": "Amount is a large multiple of the customer's 95th-percentile ticket",
    "amount_to_balance": "Transaction consumes an unusual share of available balance",
    "amount_below_threshold_gap": "Amount sits suspiciously just under a step-up threshold",
    "is_new_beneficiary": "First-ever payment to this beneficiary",
    "benef_age_days": "Beneficiary account opened very recently",
    "benef_distinct_payers_24h": "Many unrelated customers paid this beneficiary today",
    "benef_passthrough_ratio": "Beneficiary is passing funds straight through",
    "benef_dwell_secs": "Funds left the beneficiary within minutes of arriving",
    "sender_passthrough_ratio": "Sending account is relaying money it just received",
    "sender_dwell_secs": "Value held for only minutes before onward transfer",
    "screen_share": "Screen sharing was active during the payment",
    "call_active": "A call was in progress while the payment was authorised",
    "screen_share_and_new_benef": "Screen share active while paying a brand-new beneficiary",
    "coercion_score": "Pre-transaction conversation shows coercion and urgency patterns",
    "session_duration_s": "Session length inconsistent with this customer's habits",
    "session_ratio_customer": "Session far longer or shorter than this customer's norm",
    "typing_variance_ratio": "Interaction cadence unnaturally consistent — possible replay or cloning",
    "typing_variance": "Interaction cadence variance collapsed below human range",
    "form_corrections": "No natural correction events during entry",
    "device_customer_count": "Device has been seen across many unrelated customers",
    "device_is_emulator": "Transaction originated from an emulated device",
    "device_is_rooted": "Device integrity compromised (rooted/jailbroken)",
    "device_attested": "Device failed platform attestation",
    "is_new_device": "Device never previously seen on this account",
    "device_age_days": "Device registered very recently",
    "travel_speed_kmh": "Implied travel speed between transactions is impossible",
    "dist_from_home_km": "Transaction far from the customer's home geography",
    "is_high_risk_country": "Counterparty jurisdiction carries elevated risk",
    "cust_txn_1h": "Unusual transaction velocity in the last hour",
    "cust_burst_ratio": "Activity burst relative to the customer's weekly baseline",
    "merchant_age_days": "Merchant onboarded very recently",
    "merchant_repeat_rate": "Merchant has almost no repeat customers",
    "merchant_is_liquid": "High-liquidity merchant category (easily resold value)",
    "merchant_chargeback_rate": "Merchant carries an elevated chargeback rate",
    "instrument_age_days": "Payment instrument or token provisioned minutes ago",
    "mandate_ceiling_to_typical": "Agent mandate ceiling far exceeds this customer's spending",
    "mandate_drawdown_ratio": "Agent mandate being drawn down at an abnormal rate",
    "mandate_intent_match": "Purchase category diverges from the mandate's stated intent",
    "mandate_age_h": "Mandate created only hours before this drawdown",
    "human_confirmations": "No human confirmation anywhere in the mandate's life",
    "amount_to_mandate_ceiling": "Amount pinned to the mandate ceiling, not a price point",
    "cust_prior_disputes_90d": "Customer has an elevated recent dispute history",
    "cust_prior_dispute_rate": "Customer's dispute rate is far above portfolio norms",
    "is_new_merchant": "Merchant never previously used by this customer",
    "hour_deviation": "Payment made well outside the customer's usual hours",
    "otp_attempts": "Multiple one-time-code attempts before success",
    "step_up_shown": "Step-up authentication was presented",
    "benef_in_count_1h": "Beneficiary received an unusual number of credits this hour",
}

STEP_UP_THRESHOLDS = (5000.0, 25000.0, 50000.0, 100_000.0)


def build_features(transactions: list[dict], world, episodes: dict[str, dict] | None = None
                   ) -> dict[str, Any]:
    """Single causal pass over the ledger.

    Returns X (float32), y, the feature names, categorical indices and a meta
    dict of aligned arrays used for slicing and reporting.
    """
    episodes = episodes or {}
    n = len(transactions)
    d = len(FEATURE_NAMES)
    X = np.zeros((n, d), dtype=np.float32)
    y = np.zeros(n, dtype=np.int8)

    cust: dict[str, _CustState] = {}
    acct: dict[str, _AcctState] = defaultdict(_AcctState)
    dev: dict[str, _DeviceState] = defaultdict(_DeviceState)
    merch: dict[str, _MerchState] = defaultdict(_MerchState)

    cust_index = world.customer_index
    merch_index = world.merchant_index
    self_account = {c.customer_id: c.self_account for c in world.customers}

    meta_vector: list[str] = []
    meta_txn: list[str] = []
    meta_cust: list[str] = []
    meta_ts = np.zeros(n, dtype=np.float64)
    meta_amount = np.zeros(n, dtype=np.float32)
    meta_benign: list[str] = []
    meta_rail: list[str] = []
    meta_campaign: list[str] = []

    fi = {name: i for i, name in enumerate(FEATURE_NAMES)}

    for row_i, t in enumerate(transactions):
        cid = t["customer_id"]
        ts = t["ts"]
        amount = float(t["amount"])
        c_obj = cust_index.get(cid)
        home_lat = c_obj.lat if c_obj else t["lat"]
        home_lon = c_obj.lon if c_obj else t["lon"]

        st = cust.get(cid)
        if st is None:
            st = _CustState(home_lat, home_lon)
            st.first_ts = ts
            cust[cid] = st

        f = X[row_i]

        # ---------------- amount ------------------------------------------
        f[fi["amount"]] = amount
        f[fi["log_amount"]] = math.log1p(amount)
        f[fi["amount_z_customer"]] = st.amt.z(math.log1p(amount))
        if st.recent_amts:
            p95 = float(np.percentile(np.fromiter(st.recent_amts, float), 95))
            f[fi["amount_to_p95"]] = amount / max(50.0, p95)
        else:
            f[fi["amount_to_p95"]] = 1.0
        bal = max(1.0, float(t.get("customer_balance") or 1.0))
        f[fi["amount_to_balance"]] = amount / bal
        f[fi["amount_round_ness"]] = 1.0 if abs(amount - round(amount / 100) * 100) < 1e-6 else 0.0
        # Distance below the nearest step-up threshold, normalised. A spike near
        # zero across a population is the fingerprint of threshold-hugging.
        gaps = [(th - amount) / th for th in STEP_UP_THRESHOLDS if 0 <= th - amount]
        f[fi["amount_below_threshold_gap"]] = min(gaps) if gaps else 1.0

        # ---------------- velocity ----------------------------------------
        f[fi["cust_txn_1h"]] = st.w1h.count(ts)
        c24 = st.w24h.count(ts)
        c7 = st.w7d.count(ts)
        f[fi["cust_txn_24h"]] = c24
        f[fi["cust_txn_7d"]] = c7
        f[fi["cust_amt_1h"]] = st.w1h.sum(ts)
        a24 = st.w24h.sum(ts)
        f[fi["cust_amt_24h"]] = a24
        f[fi["cust_amt_7d"]] = st.w7d.sum(ts)
        f[fi["cust_burst_ratio"]] = c24 / max(1.0, c7 / 7.0)
        f[fi["secs_since_last_txn"]] = (ts - st.last_ts) if st.n else 999_999.0
        f[fi["cust_txn_total"]] = st.n
        f[fi["cust_amt_24h_to_balance"]] = a24 / bal

        # ---------------- novelty -----------------------------------------
        mid = t.get("merchant_id")
        bid = t.get("beneficiary_id")
        did = t.get("device_id")
        cat = t.get("merchant_category") or "unknown"
        f[fi["is_new_merchant"]] = float(bool(mid) and mid not in st.merchants)
        f[fi["is_new_beneficiary"]] = float(bool(bid) and bid not in st.beneficiaries)
        f[fi["is_new_device"]] = float(bool(did) and did not in st.devices)
        f[fi["is_new_city"]] = float(t.get("city") not in st.cities)
        f[fi["is_new_category"]] = float(cat not in st.categories)
        f[fi["cust_tenure_days"]] = (ts - st.first_ts) / DAY
        f[fi["cust_known_merchants"]] = len(st.merchants)
        f[fi["cust_known_beneficiaries"]] = len(st.beneficiaries)
        f[fi["cust_known_devices"]] = len(st.devices)

        # ---------------- temporal ----------------------------------------
        hour = (ts % DAY) / HOUR
        f[fi["hour"]] = hour
        hs, hc = math.sin(2 * math.pi * hour / 24.0), math.cos(2 * math.pi * hour / 24.0)
        f[fi["hour_sin"]] = hs
        f[fi["hour_cos"]] = hc
        is_night = 1.0 if (hour < 5.5 or hour >= 23.0) else 0.0
        f[fi["is_night"]] = is_night
        dow = int((ts // DAY) % 7)
        f[fi["day_of_week"]] = dow
        f[fi["is_weekend"]] = 1.0 if dow in (5, 6) else 0.0
        if st.n >= 3:
            mag = math.hypot(st.hour_sin / st.n, st.hour_cos / st.n)
            cosang = (hs * (st.hour_sin / st.n) + hc * (st.hour_cos / st.n)) / max(1e-6, mag)
            f[fi["hour_deviation"]] = 1.0 - max(-1.0, min(1.0, cosang))
        f[fi["cust_night_rate"]] = st.night_count / max(1, st.n)

        # ---------------- geo ---------------------------------------------
        lat, lon = float(t["lat"]), float(t["lon"])
        dist_home = haversine_km(st.home_lat, st.home_lon, lat, lon)
        f[fi["dist_from_home_km"]] = dist_home
        if st.n:
            dlast = haversine_km(st.last_lat, st.last_lon, lat, lon)
            dt_h = max(1e-3, (ts - st.last_ts) / HOUR)
            f[fi["dist_from_last_km"]] = dlast
            f[fi["travel_speed_kmh"]] = dlast / dt_h
        country = t.get("country")
        home_country = c_obj.country if c_obj else country
        f[fi["is_foreign"]] = float(country != home_country)
        f[fi["is_high_risk_country"]] = float(country in HIGH_RISK_COUNTRIES)
        f[fi["merchant_is_foreign"]] = float(
            bool(t.get("merchant_country")) and t.get("merchant_country") != home_country)

        # ---------------- device ------------------------------------------
        f[fi["device_age_days"]] = float(t.get("device_age_days") or 0.0)
        f[fi["device_is_emulator"]] = float(t.get("device_is_emulator") or 0)
        f[fi["device_is_rooted"]] = float(t.get("device_is_rooted") or 0)
        f[fi["device_sim_count"]] = float(t.get("device_sim_count") or 1)
        f[fi["device_attested"]] = float(t.get("device_attested") or 0)
        if did:
            ds = dev[did]
            f[fi["device_customer_count"]] = len(ds.customers)
            f[fi["device_txn_1h"]] = ds.w1h.count(ts)
            f[fi["device_txn_24h"]] = ds.w24h.count(ts)
            f[fi["device_tenure_days"]] = (ts - ds.first_seen) / DAY if ds.n else 0.0

        # ---------------- merchant ----------------------------------------
        m_obj = merch_index.get(mid) if mid else None
        f[fi["merchant_age_days"]] = float(t.get("merchant_age_days") or 0.0)
        f[fi["merchant_risk_tier"]] = float(t.get("merchant_risk_tier") or 1)
        f[fi["merchant_is_liquid"]] = 1.0 if cat in LIQUID else 0.0
        f[fi["merchant_chargeback_rate"]] = float(
            m_obj.chargeback_rate if m_obj else 0.004)
        if mid:
            ms = merch[mid]
            f[fi["merchant_txn_1h"]] = ms.w1h.count(ts)
            f[fi["merchant_txn_24h"]] = ms.w24h.count(ts)
            f[fi["merchant_distinct_customers"]] = len(ms.customers)
            f[fi["merchant_repeat_rate"]] = ms.repeat / max(1, ms.n)
            f[fi["merchant_tenure_days"]] = (ts - ms.first_seen) / DAY if ms.n else 0.0
            f[fi["amount_to_merchant_mean"]] = (
                amount / max(50.0, ms.amt.mean) if ms.amt.n > 2 else 1.0)
        else:
            f[fi["amount_to_merchant_mean"]] = 1.0

        # ---------------- graph -------------------------------------------
        if bid:
            bs = acct[bid]
            f[fi["benef_age_days"]] = float(t.get("beneficiary_age_days") or 0.0)
            f[fi["benef_in_count_1h"]] = bs.in_1h.count(ts)
            f[fi["benef_in_count_24h"]] = bs.in_24h.count(ts)
            f[fi["benef_distinct_payers_24h"]] = bs.payers(ts)
            f[fi["benef_in_amt_24h"]] = bs.in_24h.sum(ts)
            f[fi["benef_out_count_1h"]] = bs.out_1h.count(ts)
            in24 = bs.in_24h.sum(ts)
            f[fi["benef_passthrough_ratio"]] = (
                bs.out_24h.sum(ts) / in24 if in24 > 1.0 else 0.0)
            f[fi["benef_dwell_secs"]] = (ts - bs.last_in_ts) if bs.n_in else 999_999.0
            f[fi["benef_tenure_days"]] = (ts - bs.first_seen) / DAY if bs.n_in else 0.0
        else:
            f[fi["benef_dwell_secs"]] = 999_999.0

        # The *sender's* own account: is this customer relaying money that
        # landed minutes ago? This is what catches a mule mid-chain.
        sa = self_account.get(cid)
        if sa:
            ss = acct[sa]
            in24s = ss.in_24h.sum(ts)
            f[fi["sender_in_24h"]] = in24s
            f[fi["sender_passthrough_ratio"]] = (
                (ss.out_24h.sum(ts) + amount) / in24s if in24s > 1.0 else 0.0)
            f[fi["sender_dwell_secs"]] = (ts - ss.last_in_ts) if ss.n_in else 999_999.0
        else:
            f[fi["sender_dwell_secs"]] = 999_999.0

        # ---------------- session / behavioural ---------------------------
        # All of this is optional telemetry; a third of the ledger does not
        # carry it (see PopulationConfig.telemetry_coverage) and NaN is
        # propagated rather than imputed.
        sess = _opt(t.get("session_duration_s"))
        hes = _opt(t.get("hesitation_ms"))
        typ = _opt(t.get("typing_variance"))
        f[fi["session_duration_s"]] = sess
        f[fi["session_ratio_customer"]] = (
            sess / max(1.0, st.session.mean) if st.session.n > 2 else NAN)
        f[fi["hesitation_ms"]] = hes
        f[fi["hesitation_ratio_customer"]] = (
            hes / max(1.0, st.hesitation.mean) if st.hesitation.n > 2 else NAN)
        f[fi["app_switches"]] = _opt(t.get("app_switches"))
        f[fi["form_corrections"]] = _opt(t.get("form_corrections"))
        f[fi["typing_variance"]] = typ
        # Variance collapse: the irreducible tell of a cloned motor signature.
        f[fi["typing_variance_ratio"]] = (
            typ / max(1e-4, st.typing.mean) if st.typing.n > 2 else NAN)
        ss_flag = _opt(t.get("screen_share"))
        f[fi["screen_share"]] = ss_flag
        f[fi["call_active"]] = _opt(t.get("call_active"))
        f[fi["screen_share_and_new_benef"]] = ss_flag * f[fi["is_new_beneficiary"]]
        f[fi["session_per_txn_value"]] = sess / max(1.0, math.log1p(amount))

        # ---------------- auth --------------------------------------------
        f[fi["threeds_result"]] = float(t.get("threeds_result") or 0)
        f[fi["otp_attempts"]] = float(t.get("otp_attempts") or 0)
        f[fi["step_up_shown"]] = float(t.get("step_up_shown") or 0)
        f[fi["instrument_age_days"]] = float(t.get("instrument_age_days") or 0.0)
        f[fi["customer_account_age_days"]] = float(t.get("customer_account_age_days") or 0.0)
        f[fi["customer_balance"]] = bal

        # ---------------- disputes (prior only) ---------------------------
        cut = ts - 90 * DAY
        while st.disputes and st.disputes[0] < cut:
            st.disputes.popleft()
        f[fi["cust_prior_disputes_90d"]] = len(st.disputes)
        f[fi["cust_prior_dispute_rate"]] = len(st.disputes) / max(1, st.n)

        # ---------------- agentic -----------------------------------------
        is_ag = float(t.get("is_agentic") or 0)
        f[fi["is_agentic"]] = is_ag
        f[fi["agent_attested"]] = float(t.get("agent_attested") or 0)
        ceiling = float(t.get("mandate_ceiling") or 0.0)
        f[fi["mandate_ceiling"]] = ceiling
        f[fi["mandate_age_h"]] = float(t.get("mandate_age_h") or 0.0)
        f[fi["mandate_scope_breadth"]] = float(t.get("mandate_scope_breadth") or 0.0)
        f[fi["human_confirmations"]] = float(t.get("human_confirmations") or 0)
        if is_ag and ceiling > 0:
            typical = math.expm1(st.amt.mean) if st.amt.n > 2 else max(200.0, amount)
            f[fi["mandate_ceiling_to_typical"]] = ceiling / max(100.0, typical)
            agent_key = f"{t.get('agent_id')}"
            drawn = st.mandates[agent_key]
            f[fi["mandate_drawdown_ratio"]] = (drawn + amount) / ceiling
            f[fi["amount_to_mandate_ceiling"]] = amount / ceiling
            intent = t.get("mandate_intent_category")
            f[fi["mandate_intent_match"]] = 1.0 if (intent and intent == cat) else 0.0
        else:
            f[fi["mandate_intent_match"]] = 1.0

        # ---------------- narrative (populated later by the text channel) --
        nid = t.get("narrative_id")
        if nid and nid in episodes:
            ep = episodes[nid]
            f[fi["has_episode"]] = 1.0
            f[fi["episode_turns"]] = float(ep.get("turn_count", 0))
            f[fi["episode_duration_s"]] = float(ep.get("duration_s", 0.0))
        # coercion_score stays 0 here; defend/narrative.py fills it in from a
        # model fitted on the training split only.

        # ---------------- categoricals ------------------------------------
        f[fi["cat_rail"]] = _idx(RAILS, t.get("rail"))
        f[fi["cat_auth_method"]] = _idx(AUTH_METHODS, t.get("auth_method"))
        f[fi["cat_merchant_category"]] = _idx(CATEGORIES, cat, len(CATEGORIES) - 1)
        f[fi["cat_persona"]] = _idx(PERSONAS, t.get("persona"))
        f[fi["cat_device_os"]] = _idx(DEVICE_OS, t.get("device_os"), len(DEVICE_OS) - 1)

        # ================= update state (strictly after featurising) ======
        y[row_i] = t["is_fraud"]
        meta_vector.append(t.get("vector_id") or "")
        meta_txn.append(t["txn_id"])
        meta_cust.append(cid)
        meta_ts[row_i] = ts
        meta_amount[row_i] = amount
        meta_benign.append(t.get("benign_anomaly") or "")
        meta_rail.append(t.get("rail") or "")
        meta_campaign.append(t.get("campaign_id") or "")

        st.w1h.push(ts, amount)
        st.w24h.push(ts, amount)
        st.w7d.push(ts, amount)
        st.amt.push(math.log1p(amount))
        st.session.push(sess)
        st.hesitation.push(hes)
        st.typing.push(typ)
        st.hour_sin += hs
        st.hour_cos += hc
        st.n += 1
        if is_night:
            st.night_count += 1
        st.recent_amts.append(amount)
        st.last_ts = ts
        st.last_lat, st.last_lon = lat, lon
        if mid:
            st.merchants.add(mid)
        if bid:
            st.beneficiaries.add(bid)
        if did:
            st.devices.add(did)
        if t.get("city"):
            st.cities.add(t["city"])
        st.categories.add(cat)
        if t.get("dispute_filed"):
            st.disputes.append(ts)
        if is_ag and ceiling > 0:
            st.mandates[f"{t.get('agent_id')}"] += amount

        if did:
            ds = dev[did]
            if ds.n == 0:
                ds.first_seen = ts
            ds.customers.add(cid)
            ds.w1h.push(ts, amount)
            ds.w24h.push(ts, amount)
            ds.n += 1

        if mid:
            ms = merch[mid]
            if ms.n == 0:
                ms.first_seen = ts
            if cid in ms.customers:
                ms.repeat += 1
            ms.customers.add(cid)
            ms.w1h.push(ts, amount)
            ms.w24h.push(ts, amount)
            ms.amt.push(amount)
            ms.n += 1

        if bid:
            bs = acct[bid]
            if bs.n_in == 0:
                bs.first_seen = ts
            bs.in_1h.push(ts, amount)
            bs.in_24h.push(ts, amount)
            bs.in_payers_24h.append((ts, cid))
            bs.last_in_ts = ts
            bs.last_in_amt = amount
            bs.n_in += 1
        if sa:
            ss = acct[sa]
            ss.out_1h.push(ts, amount)
            ss.out_24h.push(ts, amount)
            ss.n_out += 1

    return {
        "X": X,
        "y": y,
        "feature_names": FEATURE_NAMES,
        "categorical_idx": CATEGORICAL_IDX,
        "meta": {
            "vector_id": np.array(meta_vector),
            "txn_id": np.array(meta_txn),
            "customer_id": np.array(meta_cust),
            "ts": meta_ts,
            "amount": meta_amount,
            "benign_anomaly": np.array(meta_benign),
            "rail": np.array(meta_rail),
            "campaign_id": np.array(meta_campaign),
        },
    }
