"""A fuzzy inference + hard-veto layer; scores are supplied by external detectors."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping
import yaml
from .membership import Membership


@dataclass(frozen=True)
class FiredRule:
    name: str
    strength: float
    consequent: float | str


@dataclass(frozen=True)
class Verdict:
    phase: str
    decision: str  # allow | review | block
    risk: float | None
    reason: str
    fired_rules: tuple[FiredRule, ...]
    hard_vetoes: tuple[str, ...] = ()
    missing_features: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FuzzyPolicy:
    """Validated policy compiled from YAML. No model inference is performed."""

    def __init__(self, data: Mapping[str, Any]):
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Policy must be a mapping with version: 1")
        phases = data.get("phases")
        if not isinstance(phases, dict) or not phases:
            raise ValueError("A nonempty phases mapping is required")
        self.phases: dict[str, dict[str, Any]] = {}
        for name, spec in phases.items():
            self.phases[name] = self._compile(name, spec)

    @classmethod
    def from_yaml(cls, path: str) -> "FuzzyPolicy":
        with open(path, "r", encoding="utf-8") as f:
            return cls(yaml.safe_load(f))

    @staticmethod
    def _number(value: Any, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
            raise ValueError(f"{label} must be a finite number")
        return float(value)

    @classmethod
    def _unit(cls, value: Any, label: str) -> float:
        v = cls._number(value, label)
        if not 0 <= v <= 1:
            raise ValueError(f"{label} must lie in [0, 1]")
        return v

    @classmethod
    def _compile(cls, phase: str, spec: Any) -> dict[str, Any]:
        if not isinstance(spec, dict):
            raise ValueError(f"{phase}: invalid policy")
        features = spec.get("features")
        if not isinstance(features, dict) or not features:
            raise ValueError(f"{phase}: nonempty feature membership dictionary required")
        compiled_features = {}
        for feature, labels in features.items():
            if not isinstance(labels, dict) or not labels:
                raise ValueError(f"{phase}: empty labels for {feature}")
            compiled_features[feature] = {label: Membership.from_spec(shape) for label, shape in labels.items()}
        required = spec.get("required", list(features))
        if not isinstance(required, list) or any(f not in features for f in required):
            raise ValueError(f"{phase}: required must list defined features")
        method = spec.get("inference", "sugeno")
        if method not in ("sugeno", "mamdani"):
            raise ValueError(f"{phase}: inference must be sugeno or mamdani")
        op = spec.get("and_operator", "min")
        if op not in ("min", "product"):
            raise ValueError(f"{phase}: and_operator must be min or product")
        threshold = spec.get("thresholds", {})
        if not isinstance(threshold, dict):
            raise ValueError(f"{phase}: thresholds must be mapping")
        allow = cls._unit(threshold.get("allow_below", .35), "allow_below")
        block = cls._unit(threshold.get("block_at", .7), "block_at")
        if not allow < block:
            raise ValueError(f"{phase}: require allow_below < block_at")
        hard = spec.get("hard_veto", {})
        if not isinstance(hard, dict) or any(f not in features for f in hard):
            raise ValueError(f"{phase}: hard_veto references undefined feature")
        hard = {f: cls._unit(v, "hard_veto threshold") for f, v in hard.items()}
        output_sets = {}
        if method == "mamdani":
            raw = spec.get("output_sets")
            if not isinstance(raw, dict) or not raw:
                raise ValueError(f"{phase}: Mamdani requires output_sets")
            output_sets = {name: Membership.from_spec(shape) for name, shape in raw.items()}
        rules = spec.get("rules")
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"{phase}: a nonempty list of rules is required")
        parsed = []
        seen = set()
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict) or not isinstance(rule.get("if"), dict) or not rule["if"]:
                raise ValueError(f"{phase}: rule {idx} must have a nonempty 'if'")
            rid = rule.get("id", f"rule_{idx}")
            if not isinstance(rid, str) or rid in seen:
                raise ValueError(f"{phase}: rule ids must be unique strings")
            seen.add(rid)
            for f, label in rule["if"].items():
                if f not in compiled_features or label not in compiled_features[f]:
                    raise ValueError(f"{phase}: {rid} references unknown {f}.{label}")
            consequent = rule.get("then")
            if method == "sugeno":
                consequent = cls._unit(consequent, f"{rid} consequent")
            elif consequent not in output_sets:
                raise ValueError(f"{phase}: {rid} refers to undefined output set")
            parsed.append((rid, dict(rule["if"]), consequent))
        return {"features": compiled_features, "required": tuple(required), "method": method,
                "op": op, "allow": allow, "block": block, "hard": hard,
                "output_sets": output_sets, "rules": tuple(parsed)}

    def evaluate(self, phase: str, scores: Mapping[str, float]) -> Verdict:
        if phase not in self.phases:
            raise ValueError(f"Unknown phase {phase!r}; configured: {list(self.phases)}")
        if not isinstance(scores, Mapping):
            raise ValueError("scores must be a mapping")
        spec = self.phases[phase]
        unknown = set(scores) - set(spec["features"])
        if unknown:
            raise ValueError(f"Unknown features: {sorted(unknown)}")
        numeric = {f: self._unit(v, f"feature {f}") for f, v in scores.items()}
        vetoes = tuple(f for f, threshold in spec["hard"].items()
                       if f in numeric and numeric[f] >= threshold)
        missing = tuple(f for f in spec["required"] if f not in numeric)
        if missing:
            return Verdict(phase, "block" if vetoes else "review", None,
                           "hard veto" if vetoes else "missing required detector scores; do not release",
                           (), vetoes, missing)
        rules: list[FiredRule] = []
        for rid, antecedents, consequent in spec["rules"]:
            values = [spec["features"][f][label].at(numeric[f]) if f in numeric else 0.0
                      for f, label in antecedents.items()]
            strength = min(values) if spec["op"] == "min" else self._product(values)
            if strength > 0:
                rules.append(FiredRule(rid, strength, consequent))
        if not rules:
            return Verdict(phase, "block" if vetoes else "review", None,
                           "hard veto" if vetoes else "no active fuzzy rule; do not release", (), vetoes)
        if spec["method"] == "sugeno":
            risk = sum(r.strength * r.consequent for r in rules) / sum(r.strength for r in rules)
        else:
            # Centroid of max-aggregated, min-clipped consequent membership functions.
            steps = 401
            xs = [i / (steps - 1) for i in range(steps)]
            clipped = [max(min(r.strength, spec["output_sets"][r.consequent].at(x))
                           for r in rules) for x in xs]
            total = sum(clipped)
            if total == 0:
                return Verdict(phase, "block" if vetoes else "review", None,
                               "empty aggregated output", tuple(rules), vetoes)
            risk = sum(x * y for x, y in zip(xs, clipped)) / total
        risk = max(0.0, min(1.0, risk))
        decision = "block" if vetoes or risk >= spec["block"] else (
            "allow" if risk < spec["allow"] else "review")
        return Verdict(phase, decision, risk,
                       "hard veto" if vetoes else f"fuzzy {spec['method']} risk",
                       tuple(rules), vetoes)

    @staticmethod
    def _product(values: list[float]) -> float:
        result = 1.0
        for v in values:
            result *= v
        return result
