"""Builds the simulated payment ecosystem: customers, merchants, devices, accounts."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import PopulationConfig
from ..util.geo import CITIES, jitter_geo
from ..util.rng import Rng
from .entities import (
    BANKS,
    DEVICE_OS,
    MCCS,
    PERSONAS,
    Account,
    Customer,
    Device,
    Merchant,
)

_MERCHANT_WORDS_A = [
    "Anand", "Blue", "Sunrise", "Metro", "Royal", "Green", "Urban", "Prime",
    "Kaveri", "Sahara", "Nova", "Everest", "Lotus", "Orbit", "Zenith",
    "Vista", "Crown", "Pearl", "Silver", "Bharat", "Aster", "Vega",
]
_MERCHANT_WORDS_B = [
    "Traders", "Retail", "Stores", "Enterprises", "Mart", "Hub", "Bazaar",
    "Solutions", "Services", "Supplies", "Collective", "Corner", "Depot",
    "Exchange", "Studio", "Works", "Point", "Junction",
]


@dataclass
class World:
    customers: list[Customer]
    merchants: list[Merchant]
    accounts: dict[str, Account]
    config: PopulationConfig

    def __post_init__(self) -> None:
        self.customer_index = {c.customer_id: c for c in self.customers}
        self.merchant_index = {m.merchant_id: m for m in self.merchants}
        self.merchants_by_category: dict[str, list[Merchant]] = {}
        for m in self.merchants:
            self.merchants_by_category.setdefault(m.category, []).append(m)

    def stats(self) -> dict:
        from collections import Counter

        return {
            "customers": len(self.customers),
            "merchants": len(self.merchants),
            "accounts": len(self.accounts),
            "by_persona": dict(Counter(c.persona for c in self.customers)),
            "by_city": dict(Counter(c.city for c in self.customers).most_common(10)),
            "merchant_categories": dict(Counter(m.category for m in self.merchants)),
            "devices": sum(len(c.devices) for c in self.customers),
        }


def _pick_city(rng: Rng, *, domestic_bias: float = 0.94) -> tuple[str, str, float, float]:
    pool = [c for c in CITIES if c[1] == "IN"] if rng.chance(domestic_bias) else CITIES
    city = rng.weighted(pool, [c[4] for c in pool])
    return city[0], city[1], city[2], city[3]


def _make_device(rng: Rng, idx: int, maturity: float) -> Device:
    os_choice = rng.weighted(DEVICE_OS, [0.70, 0.22, 0.07, 0.01])
    return Device(
        device_id=f"D{idx:07d}",
        os=os_choice,
        age_days=max(2.0, rng.lognormal(5.4, 0.85)),
        # Low digital maturity correlates with older, less hygienic devices.
        is_rooted=rng.chance(0.035 + 0.05 * (1 - maturity)),
        is_emulator=False,
        sim_count=1 if rng.chance(0.72) else 2,
        attested=rng.chance(0.97),
    )


def build_world(cfg: PopulationConfig, rng: Rng) -> World:
    r_cust = rng.fork("customers")
    r_merch = rng.fork("merchants")
    r_dev = rng.fork("devices")
    r_acct = rng.fork("accounts")

    # -- merchants ---------------------------------------------------------
    merchants: list[Merchant] = []
    for i in range(cfg.n_merchants):
        mcc, label, category, tier, mu, sigma, online = r_merch.weighted(
            MCCS,
            # Essentials and food dominate merchant counts in a real portfolio;
            # high-risk categories are rare but disproportionately important.
            [3.0 if m[3] == 1 else (1.4 if m[3] == 2 else 0.45) for m in MCCS],
        )
        city, country, lat, lon = _pick_city(r_merch, domestic_bias=0.90)
        lat, lon = jitter_geo(lat, lon, r_merch.uniform(0.5, 14.0), r_merch)
        name = (f"{r_merch.choice(_MERCHANT_WORDS_A)} "
                f"{r_merch.choice(_MERCHANT_WORDS_B)}")
        # A genuine new-merchant cohort: recently onboarded, legitimate.
        age = (r_merch.uniform(2.0, 60.0) if r_merch.chance(cfg.new_merchant_share)
               else max(20.0, r_merch.lognormal(6.6, 0.85)))
        merchants.append(Merchant(
            merchant_id=f"M{i:06d}",
            name=name,
            mcc=mcc,
            label=label,
            category=category,
            risk_tier=tier,
            city=city,
            country=country,
            lat=lat,
            lon=lon,
            online_share=min(1.0, max(0.0, online + r_merch.normal(0, 0.06))),
            amount_mu=mu + r_merch.normal(0, 0.16),
            amount_sigma=max(0.35, sigma + r_merch.normal(0, 0.07)),
            age_days=age,
            acquirer=f"ACQ{r_merch.randint(1, 9):02d}",
            chargeback_rate=max(0.0004, r_merch.lognormal(-5.7, 0.75)),
        ))

    # -- customers ---------------------------------------------------------
    customers: list[Customer] = []
    accounts: dict[str, Account] = {}
    dev_counter = 0

    for i in range(cfg.n_customers):
        persona = r_cust.weighted(PERSONAS, [p.share for p in PERSONAS])
        city, country, lat, lon = _pick_city(r_cust)
        lat, lon = jitter_geo(lat, lon, r_cust.uniform(0.4, 11.0), r_cust)

        n_dev = 1 if r_cust.chance(0.74) else 2
        devices = []
        for _ in range(n_dev):
            devices.append(_make_device(r_dev, dev_counter, persona.digital_maturity))
            dev_counter += 1

        cust_id = f"C{i:06d}"
        self_acct = f"A{i:07d}"
        # Genuinely new customers, with everything that implies: no habitual
        # payees yet, few known merchants, a young account. They are the
        # legitimate population that a naive mule rule would destroy.
        is_new = r_cust.chance(cfg.new_account_share)
        acct_age = (r_acct.uniform(1.0, 55.0) if is_new
                    else max(30.0, r_acct.lognormal(6.9, 0.7)))
        accounts[self_acct] = Account(
            account_id=self_acct,
            bank=r_acct.choice(BANKS),
            age_days=acct_age,
            owner_customer=cust_id,
        )

        customers.append(Customer(
            customer_id=cust_id,
            persona=persona.key,
            city=city,
            country=country,
            lat=lat,
            lon=lon,
            account_age_days=accounts[self_acct].age_days,
            devices=devices,
            primary_device=devices[0].device_id,
            is_new_customer=is_new,
            txn_per_day=max(0.15, persona.txn_per_day * r_cust.lognormal(0.0, 0.42)),
            amount_mu=persona.amount_mu + r_cust.normal(0.0, 0.32),
            amount_sigma=max(0.4, persona.amount_sigma + r_cust.normal(0.0, 0.10)),
            night_share=min(0.65, max(0.005,
                                      persona.night_share * r_cust.lognormal(0, 0.35))),
            balance=r_cust.lognormal(persona.balance_mu, 0.75),
            susceptibility=min(0.98, max(0.02,
                                         persona.susceptibility + r_cust.normal(0, 0.11))),
            digital_maturity=min(1.0, max(0.05,
                                          persona.digital_maturity + r_cust.normal(0, 0.10))),
            agent_adoption=persona.agent_adoption,
            rail_mix=dict(persona.rail_mix),
            category_affinity=dict(persona.category_affinity),
            bio_mean=r_cust.uniform(0.25, 0.78),
            bio_variance=r_cust.uniform(0.09, 0.22),
            self_account=self_acct,
        ))

    # -- shared / household devices ---------------------------------------
    # A small share of devices are shared across customers. This is what makes
    # naive "device seen on multiple accounts == fraud" rules produce false
    # positives, so the model has to learn the difference.
    n_shared = int(len(customers) * cfg.shared_device_rate)
    for _ in range(n_shared):
        a, b = r_dev.sample(customers, 2)
        if a.customer_id != b.customer_id:
            b.devices.append(a.devices[0])

    # -- known contacts and merchants -------------------------------------
    # A customer's habitual payees. Legit P2P concentrates here; a first-ever
    # beneficiary is the single strongest APP-fraud signal, and it only means
    # something because legitimate customers really do have stable contact sets.
    for c in customers:
        # New customers have not built a payee list yet.
        n_contacts = max(0 if c.is_new_customer else 2,
                         int(r_acct.lognormal(0.6 if c.is_new_customer else 1.5, 0.55)))
        peers = r_acct.sample(customers, min(n_contacts, len(customers) - 1))
        c.contacts = [p.self_account for p in peers if p.customer_id != c.customer_id]

        n_known = max(1 if c.is_new_customer else 4,
                      int(r_cust.lognormal(1.2 if c.is_new_customer else 2.5, 0.5)))
        weights = [
            c.category_affinity.get(m.category, 0.25) * (1.0 if m.country == c.country else 0.15)
            for m in merchants
        ]
        total = sum(weights)
        if total <= 0:
            c.known_merchants = [m.merchant_id for m in r_cust.sample(merchants, n_known)]
        else:
            idx = r_cust.np.choice(
                len(merchants),
                size=min(n_known, len(merchants)),
                replace=False,
                p=[w / total for w in weights],
            )
            c.known_merchants = [merchants[int(j)].merchant_id for j in idx]

    return World(customers=customers, merchants=merchants, accounts=accounts, config=cfg)
