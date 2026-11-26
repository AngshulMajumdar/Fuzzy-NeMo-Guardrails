"""Actual NeMo 0.25.x runtime integration tests (no LLM or GPU required).

Run in Python 3.11/3.12/3.13 with `pip install -e '.[test,nemo]'`.
Without NeMo installed this module is skipped; CI has a dedicated NeMo job.
"""
import pytest

nemo = pytest.importorskip("nemoguardrails")
from nemoguardrails import RailsConfig, Guardrails, LLMRails
from nemoguardrails.rails.llm.options import RailStatus, RailType
from fuzzy_nemo import FuzzyPolicy, LLMRailsAdapter, IORailsAdapter
from pathlib import Path

POLICY = FuzzyPolicy.from_yaml(str(Path(__file__).resolve().parents[1] / "examples" / "policy.yaml"))
SAFE = {"injection_risk": 0.02, "toxicity_risk": 0.02}
HIGH = {"injection_risk": 0.99, "toxicity_risk": 0.02}
REGEX_CONFIG = {
    "models": [],
    "rails": {
        "input": {"flows": ["regex check input"]},
        "config": {"regex_detection": {"input": {"patterns": [r"\bSECRET\b"]}}},
    },
}


def test_real_nemo_api_symbols():
    assert hasattr(Guardrails, "check_async")
    assert hasattr(Guardrails, "generate_async")
    assert hasattr(LLMRails, "register_action")
    assert RailStatus.BLOCKED.value == "blocked"
    assert RailType.INPUT.value == "input"


@pytest.mark.parametrize("engine", ["legacy", "io"])
@pytest.mark.asyncio
async def test_real_nemo_regex_check_with_fuzzy_adapter(engine):
    config = RailsConfig.from_content(config=REGEX_CONFIG)
    if engine == "io":
        rails = Guardrails(config, require_iorails=True)
        assert rails.use_iorails_engine
        adapter = IORailsAdapter(rails, POLICY)
    else:
        rails = Guardrails(config, use_iorails=False)
        assert not rails.use_iorails_engine
        adapter = LLMRailsAdapter(rails, POLICY)
    try:
        allowed = await adapter.check_async(
            [{"role": "user", "content": "hello world"}], scores=SAFE,
            rail_types=[RailType.INPUT],
        )
        assert allowed.released
        assert allowed.native.status == RailStatus.PASSED
        assert allowed.checked_content == "hello world"

        blocked_native = await adapter.check_async(
            [{"role": "user", "content": "SECRET"}], scores=SAFE,
            rail_types=[RailType.INPUT],
        )
        assert blocked_native.decision == "block" and not blocked_native.released
        assert blocked_native.native is None

        blocked_fuzzy = await adapter.check_async(
            [{"role": "user", "content": "hello world"}], scores=HIGH,
            rail_types=[RailType.INPUT],
        )
        assert blocked_fuzzy.decision == "block" and not blocked_fuzzy.released
    finally:
        await rails.shutdown()


@pytest.mark.asyncio
async def test_real_llmrails_python_action_registration():
    rails = Guardrails(RailsConfig.from_content(yaml_content="models: []"), use_iorails=False)
    try:
        adapter = LLMRailsAdapter(rails, POLICY)
        adapter.register_action()
        action = rails.runtime.action_dispatcher.get_action("fuzzy_nemo_input")
        assert action is not None
        assert await action(context={"fuzzy_nemo_input_scores": SAFE})
        assert not await action(context={"fuzzy_nemo_input_scores": HIGH})
        assert not await action(context={})
    finally:
        await rails.shutdown()


def test_real_iorails_rejects_native_action():
    rails = Guardrails(RailsConfig.from_content(yaml_content="models: []"), require_iorails=True)
    adapter = IORailsAdapter(rails, POLICY)
    assert adapter is not None
    with pytest.raises(TypeError):
        LLMRailsAdapter(rails, POLICY)
    with pytest.raises(NotImplementedError):
        rails.register_action(lambda: True, name="unsupported")


@pytest.mark.asyncio
async def test_real_llmrails_colang_action_executes_with_context_scores():
    from nemoguardrails.actions.actions import ActionResult

    co = """\ndefine flow fuzzy nemo input
  $detected = execute trusted_fuzzy_detector
  $allowed = execute fuzzy_nemo_input
  if not $allowed
    bot refuse to respond
    stop
"""
    config = RailsConfig.from_content(
        config={"colang_version": "1.0", "models": [],
                "rails": {"input": {"flows": ["fuzzy nemo input"]}}},
        colang_content=co,
    )
    rails = Guardrails(config, use_iorails=False)
    adapter = LLMRailsAdapter(rails, POLICY)
    adapter.register_action()
    scores = dict(SAFE)

    async def trusted_fuzzy_detector(context=None):
        return ActionResult(return_value=True,
                            context_updates={"fuzzy_nemo_input_scores": dict(scores)})

    rails.register_action(trusted_fuzzy_detector, name="trusted_fuzzy_detector")
    try:
        for value, expected in ((.02, RailStatus.PASSED), (.99, RailStatus.BLOCKED)):
            scores["injection_risk"] = value
            result = await rails.check_async(
                [{"role": "user", "content": "hello"}], rail_types=[RailType.INPUT]
            )
            assert result.status == expected
    finally:
        await rails.shutdown()
