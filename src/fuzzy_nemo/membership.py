"""Pure Python membership functions; deterministic, dependency-light, bounded [0, 1]."""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, isfinite
from typing import Mapping


@dataclass(frozen=True)
class Membership:
    kind: str
    params: tuple[float, ...]

    @classmethod
    def from_spec(cls, spec: Mapping) -> "Membership":
        if not isinstance(spec, dict) or len(spec) != 1:
            raise ValueError("A membership must have one shape, e.g. {triangle: [0, .5, 1]}")
        shape, raw = next(iter(spec.items()))
        sizes = {"triangle": 3, "trapezoid": 4, "gaussian": 2}
        if shape not in sizes or not isinstance(raw, (list, tuple)) or len(raw) != sizes[shape]:
            raise ValueError(f"Invalid membership shape/arity: {shape}")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in raw):
            raise ValueError("Membership parameters must be finite numbers")
        params = tuple(float(v) for v in raw)
        if shape in ("triangle", "trapezoid") and list(params) != sorted(params):
            raise ValueError("Membership coordinates must be nondecreasing")
        if shape == "gaussian" and params[1] <= 0:
            raise ValueError("Gaussian sigma must be positive")
        return cls(shape, params)

    def at(self, x: float) -> float:
        p = self.params
        if self.kind == "gaussian":
            return exp(-0.5 * ((x - p[0]) / p[1]) ** 2)
        if self.kind == "triangle":
            a, b, c = p
            if x < a or x > c:
                return 0.0
            if x == b:
                return 1.0
            left = 1.0 if b == a else (x - a) / (b - a)
            right = 1.0 if c == b else (c - x) / (c - b)
            return max(0.0, min(1.0, left, right))
        a, b, c, d = p
        if x < a or x > d:
            return 0.0
        if b <= x <= c:
            return 1.0
        if x < b:
            return 1.0 if a == b else max(0.0, (x - a) / (b - a))
        return 1.0 if c == d else max(0.0, (d - x) / (d - c))
