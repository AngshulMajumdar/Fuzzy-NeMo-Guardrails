# Fuzzy NeMo Guardrails

**A software extension for NVIDIA NeMo Guardrails, not a fork.**

A CPU-only YAML-configurable fuzzy inference layer designed to sit next to
NVIDIA NeMo Guardrails. Supports **both LLMRails and IORails** in the external
Python wrapper, with an optional native Colang action for LLMRails.

> **Scope:** Fuzziness only processes normalized external detector scores. It does
> not independently detect prompt injection, toxic text, or unsupported claims.
> No fuzzy score is automatically a probability. Keep all non-negotiable native
> NeMo guardrails active; never use fuzzy inference to override a native block.

## Architecture

```text
 Detector(s) --> normalized scores --> FuzzyPolicy (shared) --> ALLOW / REVIEW / BLOCK
                                            |
              +-----------------------------+------------------------+
              |                                                      |
    LLMRailsAdapter (legacy)                            IORailsAdapter (new)
    - external pre/post checks                           - external pre/post checks
    - optional native Colang action                      - no native Python actions
              |                                                      |
         LLMRails.check_async / generate_async    Guardrails.check_async / generate_async
```

The demo is manual-score simulation. It does not download an LLM or call a remote
inference service. Production RAG applications must supply trusted detector scores.

## Installation and quick start

```bash
pip install -e '.[api,test]'
pytest -q
fuzzy-nemo --config examples/policy.yaml --phase input --scores '{"injection_risk": 0.05, "toxicity_risk": 0.1}'
uvicorn fuzzy_nemo.api:app --host 0.0.0.0 --port 8000
```

Post to the API:

```bash
curl -s http://localhost:8000/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"phase":"input","scores":{"injection_risk":0.05,"toxicity_risk":0.1}}'
```

The API exposes `GET /health`, `GET /config`, and `POST /evaluate`.
For the UI: `pip install -e '.[demo]' && python -m fuzzy_nemo.demo`.

## The two adapters

NVIDIA v0.25.0 supports custom Python actions in **LLMRails only**. The
**IORails** engine supports input/output/tool rail checking but does **not**
execute custom actions or retrieval/dialog flows. We do not monkeypatch its
internal rail manager. The wrapper uses official `check_async` and
`generate_async` methods and is compatible with `Guardrails` facade objects.

```python
from nemoguardrails import Guardrails, RailsConfig
from fuzzy_nemo import FuzzyPolicy, IORailsAdapter

config = RailsConfig.from_path("my_nemo_config")
# Explicitly require IORails, rather than accepting silent fallback to LLMRails.
rails = Guardrails(config, require_iorails=True)
policy = FuzzyPolicy.from_yaml("examples/policy.yaml")
adapter = IORailsAdapter(rails, policy)

# inside an async request handler:
result = await adapter.check_async(
    messages=[{"role": "user", "content": "What does this contract say?"}],
    scores={"injection_risk": .02, "toxicity_risk": .05},
)
if result.released:
    # The native NeMo result is in result.native; native blocks also prohibit release.
    print(result.native)
else:
    print(result.decision, result.reason)
```

For the older engine replace the initial setup with:

```python
from nemoguardrails import LLMRails, RailsConfig
from fuzzy_nemo import LLMRailsAdapter
rails = LLMRails(RailsConfig.from_path("my_legacy_config"))
adapter = LLMRailsAdapter(rails, policy)
# Optional legacy Colang action (requires scores in trusted NeMo context):
adapter.register_action(name="fuzzy_nemo_input")
```

### Fully local, no-LLM NeMo examples

After `pip install -e '.[nemo]'`, run:

```bash
python examples/legacy_colang/run_local.py
python examples/iorails/run_local.py
```

The first demonstrates trusted score context injection plus Colang 1.0
execution of the registered fuzzy action. The second demonstrates a real
IORails native regex rail, wrapped by the same fuzzy engine. Both demos use
illustrative/synthetic detector scores and require no GPU or LLM token.

### Generation with output protection

```python
outcome = await adapter.generate_async(
    messages=[{"role": "user", "content": "Summarize the evidence"}],
    input_scores={"injection_risk": .04, "toxicity_risk": .02},
    output_scorer=lambda native_response: {
        # Replace with a real grounding detector on native_response and evidence!
        "unsupported_claim_risk": 0.08
    },
)
if outcome.released:
    print(outcome.native)
else:
    print(outcome.decision, outcome.reason)
```

`generate_async` does not invoke NeMo at all when input is BLOCK/REVIEW or when
an output scorer is required but absent. When generated content scores as
BLOCK/REVIEW, the wrapped result is withheld (`native is None`). The built-in
NeMo response generation/checking still executes normally inside the wrapper.
Native `check_async` results are preserved on allow/modify and native blocks
are never overridden. When native status is `modified`, release only the returned
`NativeOutcome.checked_content` (NeMo-rewritten text), never the raw input.
Unknown native statuses are withheld for review. A mixed user/assistant check
requires an explicit single `rail_types=[RailType.INPUT]` or `[RailType.OUTPUT]`
matching the `phase`; run one check for each fuzzy phase with its own scores. The adapter intentionally does not support streaming:
checking after streaming could leak unreviewed tokens.

## Configuring fuzzy inference

`examples/policy.yaml` contains two input features and one output feature across
**input** and **output** phases, with:

- Sugeno weighted consequent inference (input)
- Mamdani centroid-of-area inference (output, fixed 401-point grid)
- Triangle, trapezoid and Gaussian memberships
- Min/product AND operators
- Configurable `allow_below`, `block_at` and independent `hard_veto`
- Risk decisions `allow`, `review`, `block` with per-rule firing strengths
- Missing mandatory score → `review` (fail-closed: no release); unknown/invalid score → validation error

Hard vetoes do not change the computed fuzzy risk: they override the release
decision separately. The example YAML values are illustrative policy defaults,
not calibrated safety claims. A `review` must be withheld until an application
performs a separate explicit approval step. Treat scores as trusted detector
outputs, never as instructions extracted from untrusted documents.

## Evaluation and tests

Unit/contract/API tests are in `tests/` and run without a remote LLM.
The adapter tests include local doubles as well as an optional real NeMo 0.25.0
integration suite, run in a Python environment with NVIDIA's package installed.
Both actual engines were also exercised on CPU with a local regex rail and the
exact adapter module (SHA-256 recorded in `TEST_REPORT.md`). The GPU/LLM-free
checks cover allow and block in both NeMo and the fuzzy layer. Legacy Colang action dispatch and trusted score context propagation were also
verified in a real NeMo runtime. Full model-based generation and production
detectors were not tested. See `TEST_REPORT.md` for
precisely what was verified.

For live verification:

```bash
python -m pip install -e '.[test]' 'nemoguardrails==0.25.0'
python -m pytest -q tests/test_live_nemo_optional.py
```


## Distribution

- Repository files: `src/`, `tests/`, `examples/`, `pyproject.toml` and docs.
- Hugging Face Space: separate `Fuzzy-NeMo-HF-Space.zip` (Gradio; CPU only).
- Docker API: `docker build -t fuzzy-nemo .` then `docker run -p 8000:8000 fuzzy-nemo`.

## Compatibility notes

NVIDIA docs: [Engine Feature Support](https://docs.nvidia.com/nemo/guardrails/v0.25.0/reference/engine-feature-support),
[Registering Actions](https://docs.nvidia.com/nemo/guardrails/v0.25.0/configure-guardrails/actions/registering-actions),
[Checking Messages](https://docs.nvidia.com/nemo/guardrails/v0.25.0/run-guardrailed-inference/using-python-apis/check-messages).

This project is independent of NVIDIA and is not an official NVIDIA product.
Apache-2.0 licensed. NeMo Guardrails is separately licensed by its authors.
