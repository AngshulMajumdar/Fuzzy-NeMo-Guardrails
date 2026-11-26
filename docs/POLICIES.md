# Policies and extensions

The default policy is `src/csfsm_guardrails/policies/default.yaml`. Copy it, edit
it, and run `csfsm validate my-policy.yaml`. Generate an editor schema with
`csfsm schema --output policy.schema.json`. Load it with
`Guardrail(Policy.from_file('my-policy.yaml'))` or set `CSFSM_POLICY` on the API.
YAML is loaded with `safe_load`; policy files never execute code or import tools.
Policies are trusted host configuration, not user-supplied chat attachments.

| Field | Meaning |
|---|---|
| states, prior | Latent modes and normalized starting probabilities |
| observations, emissions | Finite evidence alphabet and likelihood matrix |
| transitions | Row-stochastic action-conditioned matrices; default required |
| joint_kernels | Optional general event/observation kernels replacing factorized updates |
| actions | Stage eligibility, per-state utilities, risks and fallback messages |
| protocol_rules | Trusted event transitions, with optional source/action wildcards |
| patterns | Hard candidate validators expressed as trusted regular expressions |
| tools | Registered tool policy: verification and argument-bound grant requirements |
| selection | `max` (default) or `sample` from the projected distribution |
| uncertainty_radius | Radius in total variation, in [0,1] |
| risk_semantics | `model_score` or explicitly assumed `conditional_bound` |
| session_alpha | Optional conditional conversation budget |
| max_decisions | Bound including input, output and tool decisions |
| max_clarifications | Bound on repeated clarification decisions |

Required action names are `allow_input`, `release`, `execute_tool`, and `stop`.
Only the corresponding permit action sets `Decision.allowed=True`; every other
action returns a configured fixed fallback. Keep fallback messages non-sensitive.
Missing transition actions use the default matrix. Equal-specificity conflicting
protocol wildcard rules are rejected. Closed state is absorbing, even under a
later verification event. A policy digest binds sessions to the entire model;
start new sessions after changing configuration.

## Custom content validator

```python
from csfsm_guardrails import Finding, Guardrail


class PrivateMarker:
    def validate(self, candidate, state):
        if candidate.stage == "output" and "INTERNAL_ONLY" in candidate.text:
            return [Finding(code="internal_marker")]
        return []


guard = Guardrail(validators=[PrivateMarker()])
```

## Custom evidence encoder

```python
from csfsm_guardrails import Evidence


class MyEncoder:
    def encode(self, text, state):
        label = your_detector(text)  # map to a configured observation symbol
        return Evidence(observation=label, source="my-detector")
```

The encoder returns an observation symbol, not a trusted protocol event. Ensure
the emission matrix represents the observation mechanism used at deployment.
Classifier posterior probabilities are not emission likelihoods. If building a
custom filter, `posterior_to_likelihood(posterior, training_prior)` computes the
relative likelihood implied by Bayes' rule under positive training priors and
the relevant calibration/prior-shift assumptions; it does not calibrate a model.

For response-specific semantic risk, implement
`RiskProvider.risks(candidate, state)` returning a finite `n_states × n_actions`
matrix in the policy's ordering. The stop column must be zero. A detector's score
does not become a conditional safety bound merely by using this interface.

An extension must be thread-safe if the host serves concurrent requests. Keep
network detector timeouts bounded; an exception produces a stop. The standard
regex validator normalizes Unicode NFKC and removes format characters, but it
does not provide general adversarial robustness or multilingual coverage.
