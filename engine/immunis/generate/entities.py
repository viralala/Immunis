"""Entity types and reference data for the simulated payment ecosystem.

Fidelity note: fraud is only anomalous *relative to a baseline*.  Everything in
this module exists to make the baseline rich enough that "unusual" and
"fraudulent" are genuinely different things.  Personas differ in ticket size,
circadian rhythm, instrument mix, merchant affinity and — importantly —
susceptibility, so the attack overlay lands on plausible victims rather than
uniformly at random.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Merchant category codes
# (code, label, category, base risk tier 1-3, log-normal mu/sigma of ticket,
#  online share)
# ---------------------------------------------------------------------------

MCCS: list[tuple[str, str, str, int, float, float, float]] = [
    ("5411", "Grocery & supermarket",    "essentials",   1, 6.55, 0.62, 0.22),
    ("5814", "Quick service restaurant", "food",         1, 5.75, 0.55, 0.55),
    ("5812", "Restaurant & dining",      "food",         1, 6.85, 0.60, 0.18),
    ("5541", "Fuel",                     "transport",    1, 6.90, 0.45, 0.06),
    ("4121", "Ride hailing",             "transport",    1, 5.55, 0.62, 0.98),
    ("4111", "Public transport",         "transport",    1, 4.20, 0.50, 0.70),
    ("5912", "Pharmacy",                 "health",       1, 6.10, 0.70, 0.35),
    ("8062", "Hospital & clinic",        "health",       2, 8.40, 0.95, 0.10),
    ("5311", "Department store",         "retail",       1, 7.35, 0.80, 0.45),
    ("5651", "Apparel",                  "retail",       1, 7.15, 0.75, 0.60),
    ("5732", "Consumer electronics",     "retail",       2, 8.65, 0.85, 0.62),
    ("5999", "Misc retail",              "retail",       2, 6.80, 0.95, 0.55),
    ("4899", "Streaming & subscriptions","digital",      1, 5.45, 0.50, 1.00),
    ("5816", "Gaming & in-app",          "digital",      2, 5.90, 0.90, 1.00),
    ("4814", "Telecom recharge",         "digital",      1, 5.60, 0.55, 0.95),
    ("6300", "Insurance premium",        "financial",    1, 8.90, 0.70, 0.65),
    ("6012", "Financial institution",    "financial",    2, 8.20, 1.05, 0.75),
    ("6051", "Quasi-cash / crypto ramp", "financial",    3, 8.55, 1.15, 0.98),
    ("6011", "ATM withdrawal",           "cash",         2, 7.60, 0.60, 0.00),
    ("7995", "Betting & gaming",         "highrisk",     3, 7.30, 1.10, 0.95),
    ("5967", "Adult & direct marketing", "highrisk",     3, 6.70, 0.95, 1.00),
    ("4722", "Travel agency",            "travel",       2, 9.30, 0.85, 0.85),
    ("3000", "Airline",                  "travel",       2, 9.55, 0.75, 0.90),
    ("7011", "Hotel & lodging",          "travel",       2, 8.75, 0.80, 0.72),
    ("5944", "Jewellery",                "luxury",       3, 9.70, 0.95, 0.30),
    ("5691", "Gift cards & vouchers",    "liquid",       3, 7.55, 0.80, 0.88),
    ("8220", "Education & fees",         "education",    1, 9.10, 0.90, 0.60),
    ("1731", "Home services & repair",   "services",     1, 7.40, 0.85, 0.25),
    ("7399", "Business services",        "services",     2, 8.10, 1.00, 0.70),
    ("5045", "Computers & peripherals",  "retail",       2, 8.80, 0.80, 0.75),
]

# Categories that are attractive to a fraudster because value is fungible and
# resale is trivial.  Used both by the attack generators and as a model feature.
LIQUID_CATEGORIES = {"liquid", "cash", "highrisk", "luxury", "financial"}

BANKS = [
    "HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "PNB", "BOB", "YES",
    "IDFC", "INDUSIND", "FEDERAL", "CANARA", "AU", "RBL",
]

DEVICE_OS = ["android", "ios", "web", "android_tv"]

AGENT_PLATFORMS = [
    "orion-shop", "cartpilot", "atlas-assist", "nova-buy", "helix-agent",
]


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    share: float                      # portfolio share
    txn_per_day: float                # Poisson rate
    amount_mu: float                  # log-normal location of ticket size
    amount_sigma: float
    night_share: float                # share of activity 23:00-05:00
    travel_rate: float                # probability of a travel episode per month
    rail_mix: dict[str, float]
    category_affinity: dict[str, float]
    # Susceptibility to social engineering. Drives *who* the attack generators
    # target, so victim selection is realistic rather than uniform.
    susceptibility: float
    digital_maturity: float           # affects device hygiene, session pacing
    balance_mu: float                 # log-normal available-balance proxy
    agent_adoption: float             # probability of using an AI shopping agent


PERSONAS: list[Persona] = [
    Persona(
        key="salaried_urban", label="Salaried urban professional", share=0.30,
        txn_per_day=2.4, amount_mu=6.6, amount_sigma=1.05, night_share=0.10,
        travel_rate=0.35,
        rail_mix={"upi_p2m": 0.44, "card_cnp": 0.24, "card_cp": 0.16,
                  "upi_p2p": 0.11, "wallet": 0.04, "agentic": 0.01},
        category_affinity={"essentials": 1.5, "food": 1.6, "transport": 1.4,
                           "digital": 1.3, "retail": 1.2, "travel": 1.0,
                           "health": 0.8, "financial": 0.7, "services": 0.7},
        susceptibility=0.30, digital_maturity=0.85, balance_mu=11.3,
        agent_adoption=0.16,
    ),
    Persona(
        key="student", label="Student", share=0.16,
        txn_per_day=2.1, amount_mu=5.5, amount_sigma=0.95, night_share=0.26,
        travel_rate=0.18,
        rail_mix={"upi_p2m": 0.52, "upi_p2p": 0.22, "card_cnp": 0.14,
                  "wallet": 0.08, "card_cp": 0.03, "agentic": 0.01},
        category_affinity={"food": 2.2, "digital": 2.0, "transport": 1.5,
                           "education": 1.4, "retail": 0.9, "essentials": 0.8,
                           "health": 0.4, "travel": 0.5},
        susceptibility=0.46, digital_maturity=0.80, balance_mu=9.4,
        agent_adoption=0.22,
    ),
    Persona(
        key="senior", label="Senior citizen", share=0.12,
        txn_per_day=0.85, amount_mu=6.9, amount_sigma=0.85, night_share=0.03,
        travel_rate=0.12,
        rail_mix={"upi_p2m": 0.30, "card_cp": 0.28, "upi_p2p": 0.22,
                  "card_cnp": 0.17, "wallet": 0.03},
        category_affinity={"health": 2.6, "essentials": 1.8, "financial": 1.2,
                           "food": 0.7, "digital": 0.4, "retail": 0.8,
                           "travel": 0.6, "transport": 0.5},
        # The single highest-susceptibility segment, which is exactly what the
        # coercion and voice-clone typologies exploit in the real world.
        susceptibility=0.82, digital_maturity=0.32, balance_mu=12.0,
        agent_adoption=0.03,
    ),
    Persona(
        key="gig_worker", label="Gig / delivery worker", share=0.14,
        txn_per_day=3.1, amount_mu=5.2, amount_sigma=0.90, night_share=0.30,
        travel_rate=0.08,
        rail_mix={"upi_p2m": 0.48, "upi_p2p": 0.30, "wallet": 0.12,
                  "card_cnp": 0.06, "card_cp": 0.04},
        category_affinity={"transport": 2.4, "food": 1.8, "digital": 1.2,
                           "essentials": 1.3, "cash": 1.4, "retail": 0.6},
        susceptibility=0.55, digital_maturity=0.62, balance_mu=9.0,
        agent_adoption=0.05,
    ),
    Persona(
        key="sme_owner", label="Small business owner", share=0.13,
        txn_per_day=3.6, amount_mu=7.6, amount_sigma=1.25, night_share=0.09,
        travel_rate=0.42,
        rail_mix={"upi_p2m": 0.34, "upi_p2p": 0.26, "card_cnp": 0.20,
                  "card_cp": 0.14, "wallet": 0.04, "agentic": 0.02},
        category_affinity={"services": 2.2, "retail": 1.5, "transport": 1.3,
                           "financial": 1.4, "essentials": 1.1, "travel": 1.2,
                           "food": 1.0},
        susceptibility=0.44, digital_maturity=0.70, balance_mu=12.4,
        agent_adoption=0.14,
    ),
    Persona(
        key="hnw", label="High-net-worth", share=0.07,
        txn_per_day=2.0, amount_mu=8.5, amount_sigma=1.35, night_share=0.14,
        travel_rate=0.72,
        rail_mix={"card_cnp": 0.36, "card_cp": 0.26, "upi_p2m": 0.18,
                  "upi_p2p": 0.10, "wallet": 0.05, "agentic": 0.05},
        category_affinity={"travel": 2.4, "luxury": 2.6, "retail": 1.6,
                           "food": 1.4, "financial": 1.5, "health": 1.0,
                           "digital": 0.9, "essentials": 0.5},
        susceptibility=0.26, digital_maturity=0.88, balance_mu=13.6,
        agent_adoption=0.30,
    ),
    Persona(
        key="homemaker", label="Homemaker", share=0.08,
        txn_per_day=1.5, amount_mu=6.2, amount_sigma=0.90, night_share=0.06,
        travel_rate=0.14,
        rail_mix={"upi_p2m": 0.46, "upi_p2p": 0.22, "card_cnp": 0.18,
                  "card_cp": 0.11, "wallet": 0.03},
        category_affinity={"essentials": 2.4, "retail": 1.5, "health": 1.3,
                           "education": 1.2, "food": 1.1, "digital": 0.7,
                           "travel": 0.4},
        susceptibility=0.68, digital_maturity=0.45, balance_mu=10.5,
        agent_adoption=0.06,
    ),
]

PERSONA_BY_KEY = {p.key: p for p in PERSONAS}


# ---------------------------------------------------------------------------
# Runtime entities
# ---------------------------------------------------------------------------

@dataclass
class Device:
    device_id: str
    os: str
    age_days: float
    is_emulator: bool = False
    is_rooted: bool = False
    sim_count: int = 1
    attested: bool = True


@dataclass
class Merchant:
    merchant_id: str
    name: str
    mcc: str
    label: str
    category: str
    risk_tier: int
    city: str
    country: str
    lat: float
    lon: float
    online_share: float
    amount_mu: float
    amount_sigma: float
    age_days: float
    acquirer: str
    is_synthetic: bool = False          # planted by the fake-merchant injector
    chargeback_rate: float = 0.004


@dataclass
class Account:
    """A receiving account / VPA on the account-to-account rail."""
    account_id: str
    bank: str
    age_days: float
    owner_customer: str | None = None
    is_mule: bool = False
    mule_layer: int = 0


@dataclass
class Customer:
    customer_id: str
    persona: str
    city: str
    country: str
    lat: float
    lon: float
    account_age_days: float
    devices: list[Device]
    primary_device: str
    contacts: list[str] = field(default_factory=list)   # known beneficiary accounts
    known_merchants: list[str] = field(default_factory=list)
    txn_per_day: float = 1.5
    amount_mu: float = 6.5
    amount_sigma: float = 1.0
    night_share: float = 0.1
    balance: float = 50_000.0
    susceptibility: float = 0.3
    digital_maturity: float = 0.7
    agent_adoption: float = 0.1
    rail_mix: dict[str, float] = field(default_factory=dict)
    category_affinity: dict[str, float] = field(default_factory=dict)
    # Behavioural-biometric signature: mean and natural variance of the
    # customer's interaction cadence.  Cloning attacks reproduce the mean but
    # collapse the variance, which is the detection hook.
    bio_mean: float = 0.5
    bio_variance: float = 0.14
    self_account: str = ""
    is_new_customer: bool = False
