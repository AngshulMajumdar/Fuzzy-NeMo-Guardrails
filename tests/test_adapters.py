from pathlib import Path
from types import SimpleNamespace
import pytest
from fuzzy_nemo import FuzzyPolicy, LLMRailsAdapter, IORailsAdapter

policy = FuzzyPolicy.from_yaml(str(Path(__file__).resolve().parents[1] / "examples" / "policy.yaml"))
SAFE = {"injection_risk": .02, "toxicity_risk": .02}
BLOCK = {"injection_risk": .99, "toxicity_risk": .02}


class FakeRails:
    def __init__(self, blocked=False):
        self.calls = []
        self.blocked = blocked
        self.action = None

    async def check_async(self, **kwargs):
        self.calls.append(("check", kwargs))
        return SimpleNamespace(status=SimpleNamespace(value="BLOCKED" if self.blocked else "PASSED"), content="checked")

    async def generate_async(self, **kwargs):
        self.calls.append(("generate", kwargs))
        return {"role":"assistant", "content":"answer"}

    def register_action(self, fn, name):
        self.action = (fn, name)


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_adapter_checks_preserve_native(cls):
    fake = FakeRails()
    adapter = cls(fake, policy)
    r = await adapter.check_async([{"role":"user", "content":"hi"}], scores=SAFE)
    assert r.released and len(fake.calls) == 1
    assert fake.calls[0][0] == "check"
    r2 = await adapter.check_async([{"role":"user", "content":"hi"}], scores=BLOCK)
    assert r2.decision == "block" and len(fake.calls) == 1


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_missing_output_scorer_prevents_generation(cls):
    fake = FakeRails()
    response = await cls(fake, policy).generate_async([{"role":"user", "content":"hello"}], input_scores=SAFE)
    assert response.decision == "review" and not fake.calls
    assert response.fuzzy.phase == "output"


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_output_block_never_releases_native(cls):
    fake = FakeRails()
    response = await cls(fake, policy).generate_async(
        [{"role":"user", "content":"hello"}], input_scores=SAFE,
        output_scorer=lambda response: {"unsupported_claim_risk": .99})
    assert response.decision == "block" and response.native is None
    assert len(fake.calls) == 1


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_full_generation(cls):
    fake = FakeRails()
    response = await cls(fake, policy).generate_async(
        [{"role":"user", "content":"hello"}], input_scores=SAFE,
        output_scorer=lambda _: {"unsupported_claim_risk": .03})
    assert response.released and response.native["content"] == "answer"


@pytest.mark.asyncio
async def test_native_check_blocked():
    fake = FakeRails(blocked=True)
    result = await IORailsAdapter(fake, policy).check_async([{"role":"user","content":"hello"}], scores=SAFE)
    assert not result.released and result.native is None


@pytest.mark.asyncio
async def test_legacy_registration():
    fake = FakeRails()
    adapter = LLMRailsAdapter(fake, policy)
    adapter.register_action()
    fn, name = fake.action
    assert name == "fuzzy_nemo_input"
    assert await fn({"fuzzy_nemo_input_scores": SAFE})
    assert not await fn({"fuzzy_nemo_input_scores": BLOCK})
    assert not await fn({})


def test_incorrect_adapter():
    with pytest.raises(TypeError):
        IORailsAdapter(object(), policy)
    with pytest.raises(TypeError):
        LLMRailsAdapter(FakeNoActions(), policy).register_action()

class FakeNoActions:
    async def check_async(self): pass
    async def generate_async(self): pass

@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_fail_closed_on_unrecognized_native_result(cls):
    class UnknownStatus(FakeRails):
        async def check_async(self, **kwargs):
            self.calls.append(("check", kwargs))
            return SimpleNamespace(status="undecided", content="danger")
    result = await cls(UnknownStatus(), policy).check_async([{"role":"user","content":"ok"}], scores=SAFE)
    assert result.decision == "review" and not result.released
    assert result.native is None


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_never_return_original_when_native_modifies_content(cls):
    class ModifiedRails(FakeRails):
        async def check_async(self, **kwargs):
            return SimpleNamespace(status="modified", content="redacted")
    result = await cls(ModifiedRails(), policy).check_async([{"role":"user","content":"secret"}], scores=SAFE)
    assert result.released and result.checked_content == "redacted"


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_check_output_phase_uses_output_policy(cls):
    result = await cls(FakeRails(), policy).check_async(
        [{"role":"assistant", "content":"answer"}], phase="output",
        rail_types=["output"], scores={"unsupported_claim_risk":.99})
    assert result.decision == "block" and not result.released


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_phase_must_match_explicit_native_rail(cls):
    with pytest.raises(ValueError):
        await cls(FakeRails(), policy).check_async(
            [{"role":"assistant", "content":"answer"}], phase="input",
            rail_types=["output"], scores=SAFE)
    with pytest.raises(ValueError):
        await cls(FakeRails(), policy).check_async(
            [{"role":"user", "content":"x"}], phase="input",
            rail_types=[], scores=SAFE)


def test_wrong_engine_rejected_without_silent_fallback():
    # Mirror v0.25 Guardrails facade's documented use_iorails_engine attribute.
    class Facade(FakeRails):
        def __init__(self, use_iorails_engine):
            super().__init__()
            self.use_iorails_engine = use_iorails_engine
    with pytest.raises(TypeError):
        LLMRailsAdapter(Facade(True), policy)
    with pytest.raises(TypeError):
        IORailsAdapter(Facade(False), policy)


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_none_generation_is_not_released(cls):
    class Empty(FakeRails):
        async def generate_async(self, **kwargs): return None
    result = await cls(Empty(), policy).generate_async(
        [{"role":"user","content":"hi"}], input_scores=SAFE,
        output_scorer=lambda _: {"unsupported_claim_risk":.05})
    assert not result.released and result.decision == "review"


@pytest.mark.parametrize("cls", [LLMRailsAdapter, IORailsAdapter])
@pytest.mark.asyncio
async def test_ambiguous_native_auto_detect_is_rejected(cls):
    with pytest.raises(ValueError):
        await cls(FakeRails(), policy).check_async(
            [{"role": "user", "content": "question"},
             {"role": "assistant", "content": "answer"}], scores=SAFE)
    with pytest.raises(ValueError):
        await cls(FakeRails(), policy).check_async(
            [{"role": "assistant", "content": "answer"}], scores=SAFE)
