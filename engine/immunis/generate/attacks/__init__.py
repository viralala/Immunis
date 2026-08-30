"""Attack injector library.

Importing this package registers every injector into ``base.REGISTRY``.
"""

from __future__ import annotations

from .base import (
    PARAM_NAMES,
    PARAM_SPACE,
    REGISTRY,
    AttackBatch,
    Injector,
    clamp_params,
    reset_sequences,
)

# Import for side effect: each module registers its injectors.
from . import social      # noqa: F401  AV-DIGITAL-ARREST, AV-VOICE-CLONE
from . import auth        # noqa: F401  AV-AITM-OTP, AV-BIO-CLONE
from . import identity    # noqa: F401  AV-SYNTH-ID, AV-DEEPFAKE-KYC
from . import rail        # noqa: F401  AV-BIN-ENUM, AV-QR-SWAP, AV-TOKEN-PROV
from . import merchant    # noqa: F401  AV-FAKE-MERCH, AV-FRIENDLY-FRAUD
from . import launder     # noqa: F401  AV-MULE-LAYER
from . import agentic     # noqa: F401  AV-AGENT-INJECT, AV-AGENT-MANDATE


def get_injector(key: str) -> Injector:
    try:
        return REGISTRY[key]
    except KeyError:
        raise KeyError(f"unknown injector {key!r}; have {sorted(REGISTRY)}") from None


def injector_for_vector(vector_id: str) -> Injector:
    for inj in REGISTRY.values():
        if inj.vector_id == vector_id:
            return inj
    raise KeyError(f"no injector for vector {vector_id!r}")


__all__ = [
    "REGISTRY",
    "PARAM_SPACE",
    "PARAM_NAMES",
    "AttackBatch",
    "Injector",
    "clamp_params",
    "reset_sequences",
    "get_injector",
    "injector_for_vector",
]
