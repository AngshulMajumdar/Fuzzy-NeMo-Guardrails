"""CPU-only real NeMo v0.25.0 Colang integration demonstration.

Install: pip install -e '.[nemo]'
Run from repository root: python examples/legacy_colang/run_local.py

The demo scores below are synthetic. For production, trusted_fuzzy_detector
must compute scores from real detectors, never accept untrusted document scores.
"""
import asyncio
from pathlib import Path

from nemoguardrails import Guardrails, RailsConfig
from nemoguardrails.actions.actions import ActionResult
from nemoguardrails.rails.llm.options import RailType
from fuzzy_nemo import FuzzyPolicy, LLMRailsAdapter

ROOT = Path(__file__).resolve().parents[2]
POLICY = FuzzyPolicy.from_yaml(str(ROOT / "examples" / "policy.yaml"))
SCORES = {"injection_risk": 0.02, "toxicity_risk": 0.02}


async def main():
    config = RailsConfig.from_path(str(Path(__file__).resolve().parent))
    rails = Guardrails(config, use_iorails=False)
    adapter = LLMRailsAdapter(rails, POLICY)
    adapter.register_action()

    async def trusted_fuzzy_detector(context=None):
        return ActionResult(return_value=True, context_updates={"fuzzy_nemo_input_scores": dict(SCORES)})

    rails.register_action(trusted_fuzzy_detector, name="trusted_fuzzy_detector")
    try:
        for label, injection_risk in (("safe", 0.02), ("blocked", 0.99)):
            SCORES["injection_risk"] = injection_risk
            result = await rails.check_async(
                [{"role": "user", "content": "Hello, please help"}], rail_types=[RailType.INPUT]
            )
            print(f"{label}: {result.status.value} (NeMo + fuzzy Colang action)")
            assert result.status.value == ("passed" if label == "safe" else "blocked")
    finally:
        await rails.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
