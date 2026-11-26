"""Fuzzy NeMo Guardrails: CPU-only fuzzy policy layer; no built-in text detectors."""
from .engine import FuzzyPolicy, Verdict, FiredRule
from .adapters import LLMRailsAdapter, IORailsAdapter, FuzzyNeMoAdapter, NativeOutcome

__version__ = "0.1.0"
__all__ = ["FuzzyPolicy", "Verdict", "FiredRule", "LLMRailsAdapter", "IORailsAdapter", "FuzzyNeMoAdapter", "NativeOutcome"]
