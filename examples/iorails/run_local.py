"""CPU-only real NeMo 0.25.0 IORails adapter demonstration.

Install: pip install -e '.[nemo]'
Run: python examples/iorails/run_local.py
"""
import asyncio
from pathlib import Path
from nemoguardrails import Guardrails, RailsConfig
from nemoguardrails.rails.llm.options import RailType
from fuzzy_nemo import FuzzyPolicy, IORailsAdapter

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {
    "models": [],
    "rails": {
        "input": {"flows": ["regex check input"]},
        "config": {"regex_detection": {"input": {"patterns": ["SECRET"]}}},
    },
}


async def main():
    rails = Guardrails(RailsConfig.from_content(config=CONFIG), require_iorails=True)
    adapter = IORailsAdapter(rails, FuzzyPolicy.from_yaml(str(ROOT / "examples" / "policy.yaml")))
    try:
        for label, text, scores in (
            ("safe", "Hello", {"injection_risk": .02, "toxicity_risk": .02}),
            ("nemo-block", "SECRET", {"injection_risk": .02, "toxicity_risk": .02}),
            ("fuzzy-block", "Hello", {"injection_risk": .99, "toxicity_risk": .02}),
        ):
            result = await adapter.check_async(
                [{"role": "user", "content": text}], scores=scores, rail_types=[RailType.INPUT]
            )
            print(f"{label}: {result.decision}")
            assert result.decision == ("allow" if label == "safe" else "block")
    finally:
        await rails.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
