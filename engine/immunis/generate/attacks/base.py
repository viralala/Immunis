"""Attack injector framework.

Every attack in IMMUNIS is an *injector*: it takes the simulated world and a
vector of continuous **strain parameters** and emits transactions (plus, where
relevant, conversations and mule-graph edges) into the same ledger as
legitimate traffic.

The strain parameters are the contract with the red agent.  They are exactly
the levers a real operator controls — how much to take, how fast, how clean the
devices are, how many mules to spread across, how hard to push the script, how
close to the threshold to hug — normalised to [0, 1] so an evolutionary search
can optimise over them under realism constraints.

That is what makes the loop closed: the red agent does not invent new *code*,
it discovers new *parameterisations* of known typologies that the current model
fails on, which is precisely how attack evolution works in the field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ...util.rng import Rng
from ..entities import Account, Device
from ..narrative import Episode
from ..population import World

SECONDS_PER_DAY = 86_400

# ---------------------------------------------------------------------------
# Strain parameter space
# ---------------------------------------------------------------------------

#: name -> (low, high, human description)
PARAM_SPACE: dict[str, tuple[float, float, str]] = {
    "aggression":          (0.0, 1.0, "share of available value extracted per event"),
    "velocity":            (0.0, 1.0, "how tightly events are packed in time"),
    "device_hygiene":      (0.0, 1.0, "0 = emulator/rooted/sloppy, 1 = clean attested device"),
    "spread":              (0.0, 1.0, "how many distinct mules / merchants / cards are used"),
    "mimicry":             (0.0, 1.0, "how closely the victim's normal behaviour is imitated"),
    "dwell":               (0.0, 1.0, "how long value is held before onward movement"),
    "stealth":             (0.0, 1.0, "how hard amounts hug just under known thresholds"),
    "narrative_intensity": (0.0, 1.0, "how aggressive the social-engineering script is"),
}

PARAM_NAMES = tuple(PARAM_SPACE.keys())


def clamp_params(params: dict[str, float]) -> dict[str, float]:
    out = {}
    for k, (lo, hi, _) in PARAM_SPACE.items():
        v = float(params.get(k, 0.5))
        out[k] = min(hi, max(lo, v))
    return out


@dataclass
class AttackBatch:
    """Everything one injector run produced."""
    transactions: list[dict] = field(default_factory=list)
    episodes: list[Episode] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)      # mule-graph edges
    campaigns: int = 0
    value_extracted: float = 0.0
    notes: str = ""

    def extend(self, other: "AttackBatch") -> "AttackBatch":
        self.transactions.extend(other.transactions)
        self.episodes.extend(other.episodes)
        self.edges.extend(other.edges)
        self.campaigns += other.campaigns
        self.value_extracted += other.value_extracted
        return self


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MULE_SEQ = {"n": 0}
_TXN_SEQ = {"n": 0}


def reset_sequences() -> None:
    _MULE_SEQ["n"] = 0
    _TXN_SEQ["n"] = 0


def next_txn_id(prefix: str = "F") -> str:
    _TXN_SEQ["n"] += 1
    return f"{prefix}{_TXN_SEQ['n']:08d}"


def make_mule_account(world: World, rng: Rng, *, layer: int = 1,
                      max_age_days: float = 45.0) -> Account:
    """Create (and register) a fresh receiving account controlled by the attacker.

    Account age is the single most reliable mule tell, so it is modelled
    explicitly and is one of the things ``spread``/``mimicry`` can push on:
    an operator with a deeper mule inventory can afford older accounts.
    """
    _MULE_SEQ["n"] += 1
    from ..entities import BANKS

    acct = Account(
        account_id=f"MU{_MULE_SEQ['n']:07d}",
        bank=rng.choice(BANKS),
        age_days=max(0.5, rng.uniform(0.5, max_age_days)),
        owner_customer=None,
        is_mule=True,
        mule_layer=layer,
    )
    world.accounts[acct.account_id] = acct
    return acct


def attacker_device(rng: Rng, hygiene: float, *, os_hint: str | None = None) -> Device:
    """A device under attacker control.

    ``hygiene`` is the red agent's investment in looking clean: a high-hygiene
    operator buys real handsets and warms them up; a low-hygiene one runs
    emulator farms, which is cheaper but leaves obvious telemetry.
    """
    return Device(
        device_id=f"AD{rng.randint(0, 10**7):07d}",
        os=os_hint or rng.weighted(["android", "ios", "web"], [0.82, 0.06, 0.12]),
        age_days=max(0.2, 0.5 + 120.0 * hygiene * rng.lognormal(0, 0.5)),
        is_emulator=rng.chance(max(0.0, 0.85 - 0.85 * hygiene)),
        is_rooted=rng.chance(max(0.0, 0.7 - 0.7 * hygiene)),
        sim_count=1 if hygiene > 0.6 else rng.weighted([1, 2, 3], [0.3, 0.4, 0.3]),
        attested=rng.chance(min(1.0, 0.15 + 0.85 * hygiene)),
    )


def apply_device(rec: dict, dev: Device) -> None:
    rec["device_id"] = dev.device_id
    rec["device_os"] = dev.os
    rec["device_age_days"] = dev.age_days
    rec["device_is_emulator"] = int(dev.is_emulator)
    rec["device_is_rooted"] = int(dev.is_rooted)
    rec["device_sim_count"] = dev.sim_count
    rec["device_attested"] = int(dev.attested)


def apply_beneficiary(rec: dict, acct: Account) -> None:
    rec["beneficiary_id"] = acct.account_id
    rec["beneficiary_bank"] = acct.bank
    rec["beneficiary_age_days"] = acct.age_days


def pick_victims(world: World, rng: Rng, n: int, *,
                 by_susceptibility: bool = True,
                 predicate: Callable[[Any], bool] | None = None) -> list:
    """Select victims the way an attacker would: not uniformly at random.

    Attackers target lists. Susceptibility-weighted selection is what makes the
    victim distribution realistic (seniors and homemakers over-represented in
    coercion typologies, HNW customers over-represented in takeover typologies).
    """
    pool = [c for c in world.customers if (predicate is None or predicate(c))]
    if not pool:
        pool = world.customers
    n = min(n, len(pool))
    if not by_susceptibility:
        return rng.sample(pool, n)
    weights = [max(1e-3, c.susceptibility ** 1.6) for c in pool]
    total = sum(weights)
    idx = rng.np.choice(len(pool), size=n, replace=False,
                        p=[w / total for w in weights])
    return [pool[int(i)] for i in idx]


def stealth_amount(rng: Rng, target: float, stealth: float,
                   thresholds: Iterable[float] = (5000.0, 25000.0, 50000.0, 100_000.0)
                   ) -> float:
    """Shape an amount to hug just under the nearest control threshold.

    This is ``AV-3DS-EXEMPT`` and ``AV-ADV-PERTURB`` expressed as a knob: at
    high stealth the amount distribution develops the characteristic spike just
    below a step-up boundary, which is itself a detectable artefact — the model
    gets to learn that trade-off rather than being told about it.
    """
    if stealth < 0.15:
        return round(target, 2)
    below = [t for t in thresholds if t <= target * 1.6]
    if not below:
        return round(target, 2)
    edge = max(below)
    pull = stealth * rng.uniform(0.75, 1.0)
    shaped = target * (1 - pull) + (edge * rng.uniform(0.93, 0.995)) * pull
    return round(max(50.0, shaped), 2)


def hours_between(rng: Rng, velocity: float) -> float:
    """Inter-event spacing driven by the velocity knob (fast == suspicious)."""
    fast = rng.lognormal(-1.6, 0.7)          # minutes-scale
    slow = rng.lognormal(2.4, 0.9)           # hours-to-days scale
    return float(fast * velocity + slow * (1 - velocity))


def attack_window_ts(cfg, rng: Rng, *, t0: int, day: int | None = None,
                     hour: float | None = None) -> float:
    d = day if day is not None else rng.randint(1, max(2, cfg.n_days - 1))
    h = hour if hour is not None else rng.uniform(0.0, 24.0)
    return t0 + d * SECONDS_PER_DAY + h * 3600.0


# ---------------------------------------------------------------------------
# Injector base
# ---------------------------------------------------------------------------

class Injector:
    """Base class for every attack generator."""

    vector_id: str = ""
    key: str = ""
    label: str = ""
    uses: tuple[str, ...] = PARAM_NAMES
    defaults: dict[str, float] = {}
    #: relative share of the total fraud budget this injector receives
    weight: float = 1.0
    #: transactions produced per campaign (approximate, for budgeting)
    txns_per_campaign: float = 1.0

    def params(self, override: dict[str, float] | None = None) -> dict[str, float]:
        base = {k: 0.5 for k in PARAM_NAMES}
        base.update(self.defaults)
        if override:
            base.update(override)
        return clamp_params(base)

    def run(self, world: World, rng: Rng, cfg, params: dict[str, float],
            n_campaigns: int, t0: int) -> AttackBatch:      # pragma: no cover
        raise NotImplementedError

    # -- convenience -------------------------------------------------------
    def new_record(self, world: World, cust, ts: float, rng: Rng,
                   campaign_id: str, strain_id: str) -> dict:
        from ..behaviour import base_record

        rec = base_record(next_txn_id(), ts, cust)
        rec["is_fraud"] = 1
        rec["vector_id"] = self.vector_id
        rec["strain_id"] = strain_id
        rec["campaign_id"] = campaign_id
        return rec


REGISTRY: dict[str, Injector] = {}


def register(inj: Injector) -> Injector:
    REGISTRY[inj.key] = inj
    return inj


_SYNTH_SEQ = {"n": 0}


def make_synthetic_customer(world: World, rng: Rng, *, hygiene: float = 0.5,
                            persona: str = "salaried_urban",
                            account_age_days: float | None = None,
                            balance: float | None = None):
    """Create an attacker-controlled 'customer' and register it in the world.

    Used by the synthetic-identity, deepfake-KYC and mule-layering injectors.
    These identities carry the structural tells of a manufactured person: a
    thin footprint, no habitual payees, no merchant history, one fresh device.
    """
    from ..entities import BANKS, PERSONA_BY_KEY, Customer

    _SYNTH_SEQ["n"] += 1
    pk = PERSONA_BY_KEY[persona]
    cid = f"SC{_SYNTH_SEQ['n']:06d}"
    acct_id = f"SA{_SYNTH_SEQ['n']:07d}"
    age = account_age_days if account_age_days is not None else rng.uniform(1.0, 40.0)

    world.accounts[acct_id] = Account(
        account_id=acct_id,
        bank=rng.choice(BANKS),
        age_days=age,
        owner_customer=cid,
        is_mule=True,
        mule_layer=1,
    )
    dev = attacker_device(rng, hygiene)
    city = rng.choice(world.customers).city if world.customers else "Mumbai"
    ref = rng.choice(world.customers)

    cust = Customer(
        customer_id=cid,
        persona=persona,
        city=city,
        country=ref.country,
        lat=ref.lat,
        lon=ref.lon,
        account_age_days=age,
        devices=[dev],
        primary_device=dev.device_id,
        contacts=[],
        known_merchants=[],
        txn_per_day=pk.txn_per_day,
        amount_mu=pk.amount_mu,
        amount_sigma=pk.amount_sigma,
        night_share=pk.night_share,
        balance=balance if balance is not None else rng.lognormal(pk.balance_mu, 0.6),
        susceptibility=0.05,
        digital_maturity=0.9,
        agent_adoption=0.0,
        rail_mix=dict(pk.rail_mix),
        category_affinity=dict(pk.category_affinity),
        bio_mean=rng.uniform(0.3, 0.7),
        bio_variance=rng.uniform(0.09, 0.20),
        self_account=acct_id,
    )
    world.customers.append(cust)
    world.customer_index[cid] = cust
    return cust
