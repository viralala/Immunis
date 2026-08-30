"""Deterministic randomness.

Every stochastic component in IMMUNIS draws from a named substream so that a
run is bit-for-bit reproducible from `(seed, profile)` and adding a new
component never shifts the numbers produced by an existing one.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Sequence, TypeVar

import numpy as np

T = TypeVar("T")


def _substream_seed(seed: int, name: str) -> int:
    digest = hashlib.blake2b(name.encode("utf-8"), digest_size=8).digest()
    return (seed ^ int.from_bytes(digest, "big")) % (2**63 - 1)


class Rng:
    """A named, forkable random source."""

    __slots__ = ("_np", "name", "seed")

    def __init__(self, seed: int, name: str = "root") -> None:
        self.seed = seed
        self.name = name
        self._np = np.random.default_rng(_substream_seed(seed, name))

    def fork(self, name: str) -> "Rng":
        return Rng(self.seed, f"{self.name}/{name}")

    # -- primitives --------------------------------------------------------
    @property
    def np(self) -> np.random.Generator:
        return self._np

    def uniform(self, lo: float = 0.0, hi: float = 1.0) -> float:
        return float(self._np.uniform(lo, hi))

    def normal(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        return float(self._np.normal(mu, sigma))

    def lognormal(self, mu: float, sigma: float) -> float:
        return float(self._np.lognormal(mu, sigma))

    def poisson(self, lam: float) -> int:
        return int(self._np.poisson(lam))

    def exponential(self, scale: float) -> float:
        return float(self._np.exponential(scale))

    def beta(self, a: float, b: float) -> float:
        return float(self._np.beta(a, b))

    def randint(self, lo: int, hi: int) -> int:
        """Inclusive-exclusive, like ``range``."""
        return int(self._np.integers(lo, hi))

    def chance(self, p: float) -> bool:
        return bool(self._np.random() < p)

    def choice(self, seq: Sequence[T]) -> T:
        return seq[int(self._np.integers(0, len(seq)))]

    def sample(self, seq: Sequence[T], k: int) -> list[T]:
        k = min(k, len(seq))
        idx = self._np.choice(len(seq), size=k, replace=False)
        return [seq[int(i)] for i in idx]

    def weighted(self, seq: Sequence[T], weights: Sequence[float]) -> T:
        w = np.asarray(weights, dtype=float)
        total = w.sum()
        if total <= 0:
            return self.choice(seq)
        return seq[int(self._np.choice(len(seq), p=w / total))]

    def shuffled(self, seq: Iterable[T]) -> list[T]:
        items = list(seq)
        self._np.shuffle(items)  # type: ignore[arg-type]
        return items

    def clip_normal(self, mu: float, sigma: float, lo: float, hi: float) -> float:
        return float(np.clip(self._np.normal(mu, sigma), lo, hi))


def weighted_choice(rng: Rng, mapping: dict[T, float]) -> T:
    keys = list(mapping.keys())
    return rng.weighted(keys, [mapping[k] for k in keys])
