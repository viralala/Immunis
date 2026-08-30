"""Attack-vector discovery agent.

The atlas is a starting point, not a fixed list.  Real attackers do not invent
from nothing — they *compose*.  A synthetic-identity capability plus an agentic
mandate capability is a new attack that neither parent describes, and it is
exactly the kind of thing that appears in the wild six months before anybody
writes a typology note about it.

This module implements composition-based discovery:

  1. enumerate chainable pairs of atlas vectors (the output capability of one
     satisfies the input precondition of the other),
  2. compose their threat characteristics with a model that rewards composites
     which straddle *observability boundaries* — the cases where each half is
     seen by a different system and nobody sees the whole,
  3. score, rank and emit the survivors as first-class atlas entries.

An optional LLM pass (Claude, when ``ANTHROPIC_API_KEY`` is set) rewrites the
composed entries into analyst-grade prose and proposes additional signals.  The
deterministic path runs identically without it, so the repository is fully
reproducible offline — the LLM enriches, it is never load-bearing.
"""

from __future__ import annotations

import itertools
import os
from dataclasses import replace
from typing import Iterable

from .atlas import ATLAS
from .schema import AttackVector, Rail, Status, Surface

# Which surface a vector *produces* a capability on, and which it *consumes*.
# Discovery chains producer -> consumer.
_PRODUCES: dict[Surface, str] = {
    Surface.ONBOARDING: "a controlled, KYC-clean identity or account",
    Surface.AUTHENTICATION: "a valid authenticated session or credential",
    Surface.AUTHORISATION: "an approved movement of value",
    Surface.SETTLEMENT: "cleaned or repositioned funds",
    Surface.DISPUTE: "a reversal of a settled payment",
    Surface.MODEL: "knowledge of the defence's decision boundary",
}

# A producer surface is useful to a consumer surface only in these directions.
_CHAINS: dict[Surface, tuple[Surface, ...]] = {
    Surface.MODEL: (Surface.AUTHORISATION, Surface.AUTHENTICATION, Surface.SETTLEMENT),
    Surface.ONBOARDING: (Surface.SETTLEMENT, Surface.AUTHORISATION),
    Surface.AUTHENTICATION: (Surface.AUTHORISATION,),
    Surface.AUTHORISATION: (Surface.SETTLEMENT, Surface.DISPUTE),
    Surface.SETTLEMENT: (Surface.DISPUTE,),
    Surface.DISPUTE: (),
}


def _observability_bonus(a: AttackVector, b: AttackVector) -> float:
    """How much harder the composite is to see than its hardest half.

    The premise: a composite that spans two different institutions, rails or
    monitoring systems is disproportionately hard to detect, because each half
    looks unremarkable inside its own window.  That is the structural blind
    spot a payment *network* is uniquely placed to close.
    """
    bonus = 0.0
    if a.family != b.family:
        bonus += 0.35
    if not set(a.rails) & set(b.rails):
        bonus += 0.45          # no shared rail == no shared monitoring
    if a.surface is not b.surface:
        bonus += 0.25
    if Surface.MODEL in (a.surface, b.surface):
        bonus += 0.30          # boundary knowledge makes everything quieter
    return min(bonus, 1.0)


def _clip(x: float) -> int:
    return int(max(1, min(5, round(x))))


def _compose(a: AttackVector, b: AttackVector, index: int) -> AttackVector:
    obs = _observability_bonus(a, b)

    genai = _clip(max(a.genai_uplift, b.genai_uplift))
    # The composite inherits the worse blind spot and gains the seam between them.
    gap = _clip(max(a.detection_gap, b.detection_gap) + obs)
    # Value compounds, but only partly — the second stage taxes the first.
    impact = _clip(max(a.impact, b.impact) + 0.4 * min(a.impact, b.impact) / 5.0 * 2)
    # Composites are strictly harder to run than either half.
    feasibility = _clip(min(a.feasibility, b.feasibility) - 0.8)
    velocity = _clip(min(a.scale_velocity, b.scale_velocity) - 0.3)

    rails = tuple(dict.fromkeys([*a.rails, *b.rails]))
    name = f"{_short(a)} → {_short(b)}"

    summary = (
        f"Composite strain. Stage one uses {a.name.lower()} to obtain "
        f"{_PRODUCES[a.surface]}; stage two feeds that directly into "
        f"{b.name.lower()} to reach {_PRODUCES[b.surface]}. "
        f"Each stage is individually unremarkable to the system that observes it — "
        f"the fraud lives in the seam between them, which is precisely why no "
        f"single institution's monitoring closes it."
    )

    kill_chain = (
        f"[stage 1 · {a.id}] " + a.kill_chain[0],
        f"[stage 1 · {a.id}] " + a.kill_chain[-1],
        f"[handoff] {_PRODUCES[a.surface]} is carried across the observability boundary",
        f"[stage 2 · {b.id}] " + b.kill_chain[0],
        f"[stage 2 · {b.id}] " + b.kill_chain[-1],
    )

    signals = tuple(dict.fromkeys([
        *a.observable_signals[:3],
        *b.observable_signals[:3],
        "cross-stage linkage: the same entity/device/beneficiary appearing in both stages",
        "compressed handoff interval between the two stages",
    ]))

    mitigations = tuple(dict.fromkeys([
        "Link the two stages at the network layer — neither institution can do it alone",
        *a.mitigations[:1],
        *b.mitigations[:1],
    ]))

    return AttackVector(
        id=f"AV-HYB-{index:02d}",
        name=name,
        family="Composite (discovered)",
        rails=rails,
        surface=b.surface,
        summary=summary,
        genai_uplift=genai,
        detection_gap=gap,
        impact=impact,
        feasibility=feasibility,
        scale_velocity=velocity,
        uplift_note=(
            "Composition itself is the GenAI uplift: orchestrating two dissimilar "
            "attack stages across institutions used to require a coordinated crew. "
            "It is now a planning problem one operator delegates."
        ),
        kill_chain=kill_chain,
        observable_signals=signals,
        historical_analogue=f"{a.historical_analogue}; {b.historical_analogue}",
        victim_profile=f"{a.victim_profile} — then {b.victim_profile.lower()}",
        mitigations=mitigations,
        status=Status.DISCOVERED,
        parents=(a.id, b.id),
        notes=(
            f"Discovered by composition. Observability-seam bonus "
            f"{obs:.2f} applied to detection gap."
        ),
    )


def _short(v: AttackVector) -> str:
    name = v.name.split("(")[0].strip()
    return name if len(name) <= 44 else name[:41].rstrip() + "…"


def discover(top_k: int = 10, *, exclude_families: Iterable[str] = ()) -> list[AttackVector]:
    """Compose chainable atlas pairs and return the highest-threat hybrids."""
    excl = set(exclude_families)
    pool = [v for v in ATLAS if v.family not in excl and v.family != "Composite (discovered)"]

    candidates: list[tuple[float, AttackVector, AttackVector]] = []
    for a, b in itertools.permutations(pool, 2):
        if b.surface not in _CHAINS.get(a.surface, ()):
            continue
        if a.family == b.family and not (set(a.rails) - set(b.rails)):
            continue  # same family, same rails — not a meaningful composite
        # A cheap pre-score to keep the permutation space manageable.
        pre = (
            0.5 * (a.threat_score + b.threat_score) / 100.0
            + 0.6 * _observability_bonus(a, b)
        )
        candidates.append((pre, a, b))

    candidates.sort(key=lambda t: -t[0])

    # Diversity guard: at most two hybrids may share a given parent, so the
    # output is a spread of blind spots rather than ten variations on one.
    used: dict[str, int] = {}
    out: list[AttackVector] = []
    for _, a, b in candidates:
        if used.get(a.id, 0) >= 2 or used.get(b.id, 0) >= 2:
            continue
        used[a.id] = used.get(a.id, 0) + 1
        used[b.id] = used.get(b.id, 0) + 1
        out.append(_compose(a, b, len(out) + 1))
        if len(out) >= top_k:
            break

    out.sort(key=lambda v: -v.threat_score)
    return [replace(v, id=f"AV-HYB-{i + 1:02d}") for i, v in enumerate(out)]


# ---------------------------------------------------------------------------
# Optional LLM enrichment
# ---------------------------------------------------------------------------

_ENRICH_PROMPT = """You are a payment-fraud typology analyst at a card network.

Below is a machine-composed hybrid attack vector. Rewrite its `summary` and add
up to three additional `observable_signals` that a fraud detection system could
realistically compute from authorisation, session and graph telemetry.

Constraints:
- Describe observable behaviour and telemetry only. Do not produce operational
  instructions, tooling, prompts or infrastructure guidance.
- Signals must be computable features, not aspirations.
- Return strict JSON: {{"summary": str, "extra_signals": [str, ...]}}

Vector:
{vector}
"""


def enrich_with_llm(vectors: list[AttackVector], *, model: str = "claude-opus-5") -> list[AttackVector]:
    """Optionally rewrite discovered vectors with Claude.

    No-ops (returning the input unchanged) when the SDK or API key is absent, so
    that the pipeline is deterministic and offline-reproducible by default.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return vectors
    try:
        import json

        from anthropic import Anthropic  # type: ignore
    except Exception:
        return vectors

    client = Anthropic()
    out: list[AttackVector] = []
    for v in vectors:
        try:
            payload = json.dumps(v.to_dict(), indent=2)[:6000]
            msg = client.messages.create(
                model=model,
                max_tokens=900,
                messages=[{"role": "user",
                           "content": _ENRICH_PROMPT.format(vector=payload)}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            start, end = text.find("{"), text.rfind("}")
            data = json.loads(text[start:end + 1])
            extra = tuple(str(s) for s in data.get("extra_signals", [])[:3])
            out.append(replace(
                v,
                summary=str(data.get("summary") or v.summary),
                observable_signals=tuple(dict.fromkeys([*v.observable_signals, *extra])),
                notes=v.notes + " LLM-enriched.",
            ))
        except Exception:
            out.append(v)
    return out


def build_extended_atlas(top_k: int = 10, use_llm: bool = False) -> list[AttackVector]:
    """The full atlas: curated vectors plus discovered composites."""
    hybrids = discover(top_k=top_k)
    if use_llm:
        hybrids = enrich_with_llm(hybrids)
    return [*ATLAS, *hybrids]
