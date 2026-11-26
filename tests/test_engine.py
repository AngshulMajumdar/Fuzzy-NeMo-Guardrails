import math
from pathlib import Path
import pytest
from fuzzy_nemo import FuzzyPolicy
from fuzzy_nemo.membership import Membership

POLICY_FILE = Path(__file__).resolve().parents[1] / "examples" / "policy.yaml"

@pytest.fixture(scope="module")
def policy():
    return FuzzyPolicy.from_yaml(str(POLICY_FILE))


def test_fuzzy_membership_shoulders():
    tri = Membership.from_spec({"triangle": [0, 0, .25]})
    assert tri.at(0) == 1
    assert tri.at(.25) == 0
    assert tri.at(-.1) == 0
    trap = Membership.from_spec({"trapezoid": [0, 0, .2, .4]})
    assert trap.at(0) == 1
    assert trap.at(.3) == pytest.approx(.5)
    gauss = Membership.from_spec({"gaussian": [.5, .1]})
    assert gauss.at(.5) == 1
    assert gauss.at(.6) == pytest.approx(math.exp(-.5))


@pytest.mark.parametrize("spec", [
    {"triangle": [0, .5]}, {"trapezoid": [0, .2, .1, 1]},
    {"gaussian": [.5, 0]}, {"triangle": [0, float('nan'), 1]},
    {"triangle": [0, True, 1]}, {"unknown": [0, .5, 1]},
])
def test_bad_memberships(spec):
    with pytest.raises(ValueError):
        Membership.from_spec(spec)


def test_basic_verdicts(policy):
    safe = policy.evaluate("input", {"injection_risk": .05, "toxicity_risk": .05})
    assert safe.decision == "allow" and safe.risk < .35
    bad = policy.evaluate("input", {"injection_risk": .9, "toxicity_risk": .05})
    assert bad.decision == "block" and bad.risk >= .72
    midpoint = policy.evaluate("input", {"injection_risk": .5, "toxicity_risk": .05})
    assert midpoint.decision == "review"
    assert any(r.name == "ambiguous" for r in midpoint.fired_rules)


def test_missing_fail_closed(policy):
    result = policy.evaluate("input", {"injection_risk": .1})
    assert result.decision == "review" and "toxicity_risk" in result.missing_features
    assert result.risk is None


def test_hard_veto_even_with_low_aggregate():
    p = FuzzyPolicy({"version":1, "phases":{"input": {
        "features":{"risk":{"low":{"trapezoid":[0,0,1,1]}}},
        "rules":[{"if":{"risk":"low"},"then":0.0}],
        "hard_veto":{"risk":.9}}}})
    result = p.evaluate("input", {"risk":.95})
    assert result.decision == "block" and result.risk == 0 and result.hard_vetoes == ("risk",)


@pytest.mark.parametrize("value", [-1.0, 1.0001, float("inf"), float("nan"), True, "0.1"])
def test_invalid_scores_blocked_by_validation(policy, value):
    with pytest.raises(ValueError):
        policy.evaluate("input", {"injection_risk": value, "toxicity_risk": .1})


def test_unknown_score_or_phase(policy):
    with pytest.raises(ValueError):
        policy.evaluate("input", {"injection_risk": .1, "toxicity_risk": .1, "injected": 1})
    with pytest.raises(ValueError):
        policy.evaluate("not_valid", {})


@pytest.mark.parametrize("risk", [x / 100 for x in range(101)])
def test_101_input_levels(policy, risk):
    result = policy.evaluate("input", {"injection_risk": risk, "toxicity_risk": .1})
    assert result.decision in ("allow", "review", "block")
    assert result.risk is None or 0 <= result.risk <= 1
    assert result.to_dict()["phase"] == "input"


@pytest.mark.parametrize("risk", [x / 100 for x in range(101)])
def test_101_mamdani_levels(policy, risk):
    result = policy.evaluate("output", {"unsupported_claim_risk": risk})
    assert result.decision in ("allow", "review", "block")
    assert result.risk is None or 0 <= result.risk <= 1


def test_mamdani_extremes(policy):
    assert policy.evaluate("output", {"unsupported_claim_risk": 0}).decision == "allow"
    assert policy.evaluate("output", {"unsupported_claim_risk": 1}).decision == "block"


def test_invalid_rules():
    with pytest.raises(ValueError, match="unknown"):
        FuzzyPolicy({"version":1,"phases":{"input":{
            "features":{"risk":{"low":{"triangle":[0,.5,1]}}},
            "rules":[{"if":{"risk":"unknown"},"then":.5}]}}})


def test_no_active_rule_review():
    p = FuzzyPolicy({"version":1,"phases":{"input":{
       "features":{"risk":{"low":{"triangle":[0, .1, .2]}}},
       "rules":[{"if":{"risk":"low"},"then":.0}]}}})
    assert p.evaluate("input", {"risk":.9}).decision == "review"


def test_product_tnorm():
    p = FuzzyPolicy({"version":1,"phases":{"input":{
       "and_operator":"product",
       "features":{"a":{"mid":{"triangle":[0,.5,1]}},"b":{"mid":{"triangle":[0,.5,1]}}},
       "rules":[{"if":{"a":"mid","b":"mid"},"then":.3}]}}})
    result = p.evaluate("input", {"a":.25,"b":.25})
    assert result.fired_rules[0].strength == pytest.approx(.25)


def test_hard_veto_precedes_missing_feature(policy):
    r = policy.evaluate("input", {"injection_risk": .99})
    assert r.decision == "block"
    assert "toxicity_risk" in r.missing_features
    assert "injection_risk" in r.hard_vetoes
