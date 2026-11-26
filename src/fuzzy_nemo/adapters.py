"""Conservative integration adapters for NeMo Guardrails 0.25.0.

LLMRails: external wrapper and optional registered Colang action.
IORails: external wrapper only (IORails does not run custom Python actions).
Neither adapter performs LLM inference or computes its own detector scores.

The caller must *only* release NativeOutcome.native on an ALLOW verdict, and
for a native MODIFIED check must consume the resulting native.content rather
than reusing the original input. REVIEW is not permission to release.
"""
from __future__ import annotations
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Callable, Mapping
from .engine import FuzzyPolicy, Verdict


@dataclass(frozen=True)
class NativeOutcome:
    decision: str
    phase: str
    fuzzy: Verdict
    native: Any = None
    reason: str = ""

    @property
    def released(self) -> bool:
        return self.decision == "allow" and self.native is not None

    @property
    def checked_content(self) -> str | None:
        """Release-safe checked/modified text, never the original unchecked input."""
        return getattr(self.native, "content", None) if self.released else None


def _status(native: Any) -> str | None:
    """NeMo RailsResult.status is a RailStatus enum (string-valued)."""
    val = getattr(native, "status", None)
    val = getattr(val, "value", val)
    return val.lower() if isinstance(val, str) else None


class FuzzyNeMoAdapter:
    def __init__(self, rails: Any, policy: FuzzyPolicy):
        if not callable(getattr(rails, "check_async", None)) or not callable(getattr(rails, "generate_async", None)):
            raise TypeError("rails must support check_async and generate_async")
        self.rails = rails
        self.policy = policy

    async def check_async(self, messages: list[dict], *, scores: Mapping[str, float],
                          phase: str = "input", rail_types: list | None = None,
                          **kwargs: Any) -> NativeOutcome:
        """Evaluate fuzzy phase, then call NeMo's native rail checker.

        For multi-phase native checks, call this separately with the relevant
        detector scores for each phase rather than reusing one fuzzy score set.
        """
        if rail_types is None:
            # NeMo autodetects both input and output rails when both roles occur.
            # A single-phase fuzzy score set must not silently claim coverage
            # for a different or additional phase.
            roles = {m.get("role") for m in messages if isinstance(m, dict)}
            if "assistant" in roles and "user" in roles:
                raise ValueError("Mixed user/assistant messages require explicit single-phase rail_types")
            inferred = "output" if "assistant" in roles else "input"
            if inferred != phase:
                raise ValueError(f"Messages imply {inferred} rail; requested fuzzy phase is {phase}")
        if rail_types is not None:
            requested = [getattr(rt, "value", rt) for rt in rail_types]
            if len(requested) != 1 or requested[0] != phase:
                raise ValueError("check_async requires one matching rail type; check each phase separately")
        fuzzy = self.policy.evaluate(phase, scores)
        if fuzzy.decision != "allow":
            return NativeOutcome(fuzzy.decision, phase, fuzzy, reason=fuzzy.reason)
        native = await self.rails.check_async(messages=messages, rail_types=rail_types, **kwargs)
        status = _status(native)
        if status == "blocked":
            return NativeOutcome("block", phase, fuzzy, reason="blocked by native NeMo rail")
        if status not in ("passed", "modified"):
            return NativeOutcome("review", phase, fuzzy, reason="unexpected native check status; fail closed")
        return NativeOutcome("allow", phase, fuzzy, native=native,
                             reason="consume native.content (may be modified)" if status == "modified" else "")

    async def generate_async(self, messages: list[dict], *,
                             input_scores: Mapping[str, float],
                             output_scorer: Callable[[Any], Any] | None = None,
                             **kwargs: Any) -> NativeOutcome:
        """Protect model generation with pre-check and post-check; never stream unchecked tokens."""
        fuzzy_in = self.policy.evaluate("input", input_scores)
        if fuzzy_in.decision != "allow":
            return NativeOutcome(fuzzy_in.decision, "input", fuzzy_in, reason=fuzzy_in.reason)
        if "output" in self.policy.phases and output_scorer is None:
            missing_output = self.policy.evaluate("output", {})
            return NativeOutcome(missing_output.decision, "output", missing_output,
                                 reason="output detector is required but missing")
        native = await self.rails.generate_async(messages=messages, **kwargs)
        if native is None:
            return NativeOutcome("review", "output", fuzzy_in, reason="empty native generation; fail closed")
        if "output" not in self.policy.phases:
            return NativeOutcome("allow", "input", fuzzy_in, native=native)
        scores = output_scorer(native)
        if isawaitable(scores):
            scores = await scores
        fuzzy_out = self.policy.evaluate("output", scores)
        if fuzzy_out.decision != "allow":
            return NativeOutcome(fuzzy_out.decision, "output", fuzzy_out, reason=fuzzy_out.reason)
        return NativeOutcome("allow", "output", fuzzy_out, native=native)


class LLMRailsAdapter(FuzzyNeMoAdapter):
    """LLMRails adapter (external wrapper, optional native Colang action)."""

    def __init__(self, rails: Any, policy: FuzzyPolicy):
        super().__init__(rails, policy)
        if getattr(rails, "use_iorails_engine", False) or type(rails).__name__ == "IORails":
            raise TypeError("LLMRailsAdapter requires an LLMRails engine; IORails is not supported")

    def register_action(self, name: str = "fuzzy_nemo_input") -> None:
        """Legacy Colang action. A trusted application must populate context scores.

        Action returns False for REVIEW and BLOCK. Native NeMo rails still apply.
        """
        if not callable(getattr(self.rails, "register_action", None)):
            raise TypeError("Expected LLMRails with register_action; not an IORails engine")
        policy = self.policy

        async def fuzzy_action(context: dict | None = None) -> bool:
            context = context or {}
            signals = context.get("fuzzy_nemo_input_scores", {})
            return policy.evaluate("input", signals).decision == "allow"

        self.rails.register_action(fuzzy_action, name=name)


class IORailsAdapter(FuzzyNeMoAdapter):
    """IORails adapter; external checking only, never registers Colang actions."""

    def __init__(self, rails: Any, policy: FuzzyPolicy):
        super().__init__(rails, policy)
        if (getattr(rails, "use_iorails_engine", True) is False or
                type(rails).__name__ == "LLMRails"):
            raise TypeError("IORailsAdapter requires IORails, not a legacy fallback")
