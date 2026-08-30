"""Social-engineering episode generator.

The whole point of the coercion typologies is that the *transaction* is
innocent: right customer, right device, right credential, right location.  The
fraud lives in the twenty minutes of conversation that preceded it, and that
conversation is a data source no production fraud stack consumes today.

This module synthesises those conversations — both fraudulent and legitimate.

Generating benign episodes matters as much as generating scam ones.  If only
fraud had a transcript, "has an episode" would be a perfect label and the
narrative channel would be a leak rather than a signal.  So genuine support
chats, family money requests, landlord and vendor threads are generated too,
and some of them are urgent and emotional, because real ones are.

Downstream, ``defend/narrative.py`` fits a text model on the *training split
only* and emits a coercion score as a feature.  Nothing here writes a label
into the feature space.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from ..util.rng import Rng

# ---------------------------------------------------------------------------
# Fragment banks
# ---------------------------------------------------------------------------

_AUTHORITY_OPEN = [
    "This is Inspector {name} from the Cyber Crime Cell. Your Aadhaar has been linked to a parcel containing contraband.",
    "Sir, I am calling from the Narcotics Control Bureau. A courier in your name was intercepted at {city} airport.",
    "Madam, this is the Telecom Regulatory verification desk. Your number will be disconnected in two hours in connection with a criminal case.",
    "I am calling from the CBI financial crimes unit regarding a money laundering complaint registered against your bank account.",
]
_AUTHORITY_PRESSURE = [
    "Do not disconnect this call. Under the ongoing investigation you are prohibited from contacting anyone, including family.",
    "You are currently under digital surveillance. Stay on video until the verification is complete.",
    "If you disconnect, a non-bailable warrant will be issued in your name within the hour.",
    "Keep your screen shared with me so the officer can witness the verification.",
    "Do not discuss this with your bank branch. They are also under investigation.",
]
_AUTHORITY_ASK = [
    "For verification, transfer your available balance to the RBI-supervised escrow account I am sending now. It will be refunded within 24 hours.",
    "The department needs to verify the source of funds. Transfer {amount} to the verification account and it will be returned after clearance.",
    "You must move the funds to a government-monitored safe account so they cannot be seized as evidence.",
]
_AUTHORITY_OBJECTION = [
    "Sir, my bank is asking me to confirm this is not a scam.",
    "Can I call you back after speaking to my son?",
    "This is a very large amount. I am not comfortable.",
    "Why can the police not verify my account directly with the bank?",
]
_AUTHORITY_REBUT = [
    "Ma'am, obstruction of an active investigation is itself an offence. Select 'yes' and proceed.",
    "If you involve a third party you will be treated as a co-accused. Please continue.",
    "The bank cannot help you; they are the ones who flagged your account. Continue the transfer.",
    "I am recording this call as evidence of your cooperation. Complete the transfer now.",
]

_KIN_OPEN = [
    "Ma, it's me. I'm in trouble, please don't tell dad.",
    "Papa, I've had an accident and the hospital wants a deposit before they treat me.",
    "Bhaiya, my phone broke, this is a friend's number. I need help urgently.",
]
_KIN_PRESSURE = [
    "Please don't call back on this number, the police have taken my phone.",
    "I'm crying, please just do it fast, they won't admit me otherwise.",
    "Please don't tell anyone, I'll explain everything tonight.",
]
_KIN_ASK = [
    "Send {amount} to this UPI ID, it's my friend's father's account.",
    "Please transfer {amount} right now to the number I'm sending.",
]

_EXEC_OPEN = [
    "Hi, this is {name}. I'm in a confidential acquisition call and I need a payment released today.",
    "This is urgent and confidential — do not loop in the team. The regulator's counsel needs the retainer wired now.",
]
_EXEC_PRESSURE = [
    "The deal collapses if this is not settled before close of business. Do not raise a ticket.",
    "I'm authorising this verbally. Proceed and we will regularise the paperwork tomorrow.",
]
_EXEC_ASK = [
    "Release {amount} to the account in the message. Confirm once done.",
]

_INVEST_OPEN = [
    "Good morning! Your allocation on today's block trade is confirmed. Current portfolio value is up 34%.",
    "The withdrawal request is pending. To release it, the platform requires a settlement deposit.",
]
_INVEST_PRESSURE = [
    "This window closes in 40 minutes and the slot cannot be reissued.",
    "Your gains are locked until the compliance deposit is cleared. Everyone else in the group has already paid.",
]
_INVEST_ASK = [
    "Deposit {amount} to complete the settlement and your full balance will be released.",
]

_VICTIM_COMPLY = [
    "Okay. Okay, I'm doing it.",
    "I've entered the amount. It's asking for my PIN.",
    "Done. Please confirm you received it.",
    "I'm scared but I'm doing what you said.",
    "The transfer has gone through.",
]

# -- Benign episodes: real conversations that precede real payments ---------

_BENIGN_THREADS = [
    [("payee", "Hi, sharing the rent receipt for this month. Same account as last time."),
     ("customer", "Got it, transferring now."),
     ("payee", "Thanks, received.")],
    [("payee", "Beta, can you send the money for the electricity bill when you get time?"),
     ("customer", "Sending now ma."),
     ("payee", "Received, thank you.")],
    [("support", "Thanks for contacting support. I can see the failed transaction on your account."),
     ("customer", "It debited but the merchant says they didn't get it."),
     ("support", "I've raised a reversal, it will reflect in 3 working days. You can retry the payment safely.")],
    [("payee", "Invoice INV-2291 attached for the quarter. Payment terms 15 days."),
     ("customer", "Approved, releasing today."),
     ("payee", "Appreciated.")],
    # Deliberately urgent and emotional, but entirely genuine. This is what
    # stops the narrative channel from simply learning "urgency == fraud".
    [("payee", "Please send whatever you can, dad's admission deposit is due before surgery at 6."),
     ("customer", "How much do they need?"),
     ("payee", "Hospital says 45,000 now, rest after."),
     ("customer", "Transferring now, don't worry."),
     ("payee", "Thank you, they've confirmed receipt.")],
    [("payee", "Hi! New account details for the tuition fees this term, the old one was closed."),
     ("customer", "Can you confirm on a call first?"),
     ("payee", "Yes calling now."),
     ("customer", "Okay confirmed, sending.")],
    [("support", "Your card ending 4412 was blocked due to a suspected duplicate charge."),
     ("customer", "That charge was mine, I was travelling."),
     ("support", "Understood, I've removed the block. No action needed from your side.")],
    [("payee", "Bhai the deposit for the shop advance — owner wants it today itself."),
     ("customer", "Okay sending in 10 minutes."),
     ("payee", "Done, got it.")],
]

_NAMES = ["Sharma", "Verma", "Rao", "Iyer", "Khan", "Nair", "Desai", "Reddy",
          "Chatterjee", "Mehta", "Gill", "Bose"]


@dataclass
class Episode:
    episode_id: str
    kind: str                 # coercion_authority | kin_distress | exec_request |
                              # investment_grooming | benign
    is_fraud: int
    turns: list[dict[str, str]]
    duration_s: float
    channel: str              # voice | video | chat | mixed
    vector_id: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(f"{t['speaker']}: {t['text']}" for t in self.turns)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["text"] = self.text
        d["turn_count"] = len(self.turns)
        return d


_COUNTER = {"n": 0}


def _eid() -> str:
    _COUNTER["n"] += 1
    return f"EP{_COUNTER['n']:07d}"


def reset_counter() -> None:
    _COUNTER["n"] = 0


def _fmt(t: str, rng: Rng, amount: float, city: str) -> str:
    return (t.replace("{name}", rng.choice(_NAMES))
             .replace("{city}", city)
             .replace("{amount}", f"₹{amount:,.0f}"))


def make_scam_episode(rng: Rng, kind: str, amount: float, city: str,
                      vector_id: str, *, intensity: float = 0.7) -> Episode:
    """Generate a fraudulent social-engineering transcript.

    ``intensity`` is a red-team-controllable knob: a low-intensity script is
    softer, shorter and much harder for the narrative model to catch, which is
    exactly the axis a real operator would tune. It is one of the strain
    parameters the evolutionary red agent mutates.
    """
    banks = {
        "coercion_authority": (_AUTHORITY_OPEN, _AUTHORITY_PRESSURE, _AUTHORITY_ASK, "video"),
        "kin_distress": (_KIN_OPEN, _KIN_PRESSURE, _KIN_ASK, "voice"),
        "exec_request": (_EXEC_OPEN, _EXEC_PRESSURE, _EXEC_ASK, "chat"),
        "investment_grooming": (_INVEST_OPEN, _INVEST_PRESSURE, _INVEST_ASK, "chat"),
    }
    opens, pressures, asks, channel = banks.get(kind, banks["coercion_authority"])

    turns: list[dict[str, str]] = []
    turns.append({"speaker": "caller", "text": _fmt(rng.choice(opens), rng, amount, city)})

    n_pressure = max(1, int(round(1 + 3 * intensity)))
    for _ in range(n_pressure):
        turns.append({"speaker": "caller",
                      "text": _fmt(rng.choice(pressures), rng, amount, city)})
        if rng.chance(0.55):
            turns.append({"speaker": "victim",
                          "text": _fmt(rng.choice(_AUTHORITY_OBJECTION), rng, amount, city)})
            turns.append({"speaker": "caller",
                          "text": _fmt(rng.choice(_AUTHORITY_REBUT), rng, amount, city)})

    turns.append({"speaker": "caller", "text": _fmt(rng.choice(asks), rng, amount, city)})
    turns.append({"speaker": "victim", "text": rng.choice(_VICTIM_COMPLY)})

    # Longer, more intense scripts take longer — and session duration is itself
    # one of the strongest transaction-side features for these typologies.
    duration = 180 + 900 * intensity * rng.lognormal(0.0, 0.35)
    return Episode(
        episode_id=_eid(),
        kind=kind,
        is_fraud=1,
        turns=turns,
        duration_s=round(min(duration, 14400.0), 1),
        channel=channel,
        vector_id=vector_id,
    )


def make_benign_episode(rng: Rng) -> Episode:
    thread = rng.choice(_BENIGN_THREADS)
    turns = [{"speaker": s, "text": t} for s, t in thread]
    return Episode(
        episode_id=_eid(),
        kind="benign",
        is_fraud=0,
        turns=turns,
        duration_s=round(rng.lognormal(4.4, 0.8), 1),
        channel=rng.weighted(["chat", "voice", "video"], [0.72, 0.24, 0.04]),
        vector_id=None,
    )


def attach_benign_episodes(records: list[dict], rng: Rng, *, rate: float = 0.055
                           ) -> list[Episode]:
    """Give a realistic share of *legitimate* payments a conversation too.

    Without this the narrative channel degenerates into a label detector.
    """
    r = rng.fork("benign_narrative")
    eligible = [x for x in records
                if x["is_fraud"] == 0 and x["rail"] in ("upi_p2p", "card_cnp")]
    chosen = r.sample(eligible, int(len(eligible) * rate)) if eligible else []
    episodes: list[Episode] = []
    for rec in chosen:
        ep = make_benign_episode(r)
        rec["narrative_id"] = ep.episode_id
        episodes.append(ep)
    return episodes
