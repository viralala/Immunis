"""Typed schema for the Attack Atlas.

The atlas is deliberately *machine-readable* rather than prose: every vector is
a record that the generator can key off, the detector can be evaluated against,
and the discovery agent can recombine.  Threat scoring is therefore computed,
not asserted.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Rail(str, Enum):
    CARD_CP = "card_cp"            # card present / contactless
    CARD_CNP = "card_cnp"          # e-commerce, MOTO
    UPI_P2P = "upi_p2p"            # account-to-account push
    UPI_P2M = "upi_p2m"            # merchant collect / QR
    WALLET = "wallet"              # tokenised wallet / prepaid
    AGENTIC = "agentic"            # AI-agent-initiated commerce
    REMITTANCE = "remittance"      # cross-border


class Surface(str, Enum):
    ONBOARDING = "onboarding"
    AUTHENTICATION = "authentication"
    AUTHORISATION = "authorisation"
    SETTLEMENT = "settlement"
    DISPUTE = "dispute"
    MODEL = "model"                # attacks on the defence itself


class Status(str, Enum):
    DOCUMENTED = "documented"      # catalogued, signals mapped
    SIMULATED = "simulated"        # has a high-fidelity generator in this repo
    DISCOVERED = "discovered"      # proposed by the discovery agent


@dataclass(frozen=True)
class AttackVector:
    id: str
    name: str
    family: str
    rails: tuple[Rail, ...]
    surface: Surface
    summary: str
    # 1-5 scales.
    genai_uplift: int          # how much generative AI multiplies this attack
    detection_gap: int         # how poorly a conventional stack catches it today
    impact: int                # loss severity per successful attack
    feasibility: int           # how cheap/easy it is for the attacker
    scale_velocity: int        # how fast it can be industrialised
    uplift_note: str
    kill_chain: tuple[str, ...]          # defender-facing behavioural stages
    observable_signals: tuple[str, ...]  # the telemetry a defender can actually see
    historical_analogue: str
    victim_profile: str
    mitigations: tuple[str, ...]
    status: Status = Status.DOCUMENTED
    injector: str | None = None          # generator key, when simulated
    parents: tuple[str, ...] = ()        # for discovered hybrids
    notes: str = ""

    # -- derived ----------------------------------------------------------
    @property
    def threat_score(self) -> float:
        """Composite 0-100 priority score.

        Weighted so that *what we cannot currently see* dominates: a cheap,
        scalable attack that the incumbent stack misses is worth more red-team
        attention than an expensive one it already catches.
        """
        w = {
            "detection_gap": 0.30,
            "genai_uplift": 0.24,
            "impact": 0.20,
            "scale_velocity": 0.15,
            "feasibility": 0.11,
        }
        raw = (
            w["detection_gap"] * self.detection_gap
            + w["genai_uplift"] * self.genai_uplift
            + w["impact"] * self.impact
            + w["scale_velocity"] * self.scale_velocity
            + w["feasibility"] * self.feasibility
        )
        return round(raw / 5.0 * 100.0, 1)

    @property
    def priority(self) -> str:
        s = self.threat_score
        if s >= 82:
            return "critical"
        if s >= 70:
            return "high"
        if s >= 56:
            return "medium"
        return "watch"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rails"] = [r.value for r in self.rails]
        d["surface"] = self.surface.value
        d["status"] = self.status.value
        d["kill_chain"] = list(self.kill_chain)
        d["observable_signals"] = list(self.observable_signals)
        d["mitigations"] = list(self.mitigations)
        d["parents"] = list(self.parents)
        d["threat_score"] = self.threat_score
        d["priority"] = self.priority
        return d
