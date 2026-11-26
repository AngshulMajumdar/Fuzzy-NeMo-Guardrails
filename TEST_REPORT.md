# Fuzzy NeMo Guardrails — verification report

**Date:** 2026-11-26  
**NeMo upstream source:** user-supplied `Guardrails-0.25.0.zip`  
**Published runtime:** `nemoguardrails==0.25.0`, Python 3.12 (CPU only)

## Local package suite

Command:

```bash
NEMO_V025_SOURCE_ZIP=/path/to/Guardrails-0.25.0.zip python -m pytest -q
```

Result: **258 passed, 1 skipped** (the optional live-package module was skipped
locally because `nemoguardrails` is not installed in that runtime). The tests
cover the fuzzy membership functions, rule inference, hard veto, missing scores,
fail-closed handling, output withholding, API endpoints, phase selection, both
adapters through test doubles, and six AST API/source-contract checks against
the exact NVIDIA ZIP.

## Real NeMo 0.25.0 runtime checks

Real NeMo `Guardrails` facade with both `require_iorails=True` and
`use_iorails=False` was started on Hugging Face CPU jobs with version `0.25.0`.

- Native input regex check: benign message PASSED under both engines.
- Native input regex check: prohibited message BLOCKED under both engines.
- **Exact project adapter module** (SHA-256
  `6bd125bb93b3027e6319b4839aefa6d7d0a5748781d96490b4cc2d55d95a0b69`)
  executed against both real NeMo engines in a CPU job:
  - safe fuzzy input + safe native input: allow
  - safe fuzzy input + blocked native input: block
  - blocking fuzzy input + otherwise safe native input: block
- LLMRails custom Python action: registered through NeMo's own action registry;
  called with safe and blocked detector contexts; returned True/False as intended.
- IORails action registration is intentionally not implemented; it uses the
  external adapter.

The remote adapter test used a *deterministic stub policy* with the same
`evaluate()` verdict interface to isolate native integration. The actual fuzzy
inference engine and YAML configurations were tested in the local package suite.

CPU job record (actual adapter bytecode execution):
https://huggingface.co/jobs/Angshul/6b07d71cb6a90bbe997f71f3

NeMo v0.25.0 live deterministic Colang tests:
https://huggingface.co/jobs/Angshul/6b07d769d91f621b930a0abe
https://huggingface.co/jobs/Angshul/6b07d788b6a90bbe997f731c

The repository also contains `tests/test_live_nemo_optional.py`, which runs
real package integration end-to-end on CI after installing NeMo 0.25.0.

## Limits

- No real remote LLM call, RAG retrieval, or production injection/grounding
  detector was run. Detector scores were synthetic/trusted inputs.
- A CPU NeMo runtime also executed a complete deterministic Colang 1.0
  input-rail flow with a registered Python action: the FALSE verdict blocked
  and the TRUE verdict passed. A second live Colang check verified a trusted
  detector action can pass scores through `ActionResult.context_updates` to
  the fuzzy action. This was a no-LLM input flow; LLM-driven Colang generation
  was not tested.
- We did not test `IORails.generate_async` with an actual main model. Output
  score gating was covered using test doubles, not real LLM output.
- No claim of production readiness or of equivalence with NVIDIA's guardrails.
- The fuzzy thresholds and linguistic memberships are illustrative, not
  calibrated security policies.
- No streaming. This is deliberate: post-hoc output scoring must not leak
  unsafe text through a stream.

## Reproduce after publication

```bash
python -m pip install -e '.[test]' 'nemoguardrails==0.25.0'
python -m pytest -q
python -m pytest -q tests/test_live_nemo_optional.py
```

The GitHub Actions workflow includes a dedicated `nemo-025-integration` job.
