# LLMRails / Colang 1.0 integration

This is a **real Colang-triggered fuzzy input rail**, using the legacy
`LLMRails` engine. It requires NVIDIA NeMo Guardrails v0.25.0 but does not
need an LLM API key or GPU.

From the project root:

```bash
python -m pip install -e '.[nemo]'
python examples/legacy_colang/run_local.py
```

`rails.co` invokes a trusted score provider action (`trusted_fuzzy_detector`)
that places `fuzzy_nemo_input_scores` into NeMo's conversational context.
It then calls the Python action registered by `LLMRailsAdapter.register_action`.
The fuzzy decision is translated into a strict boolean: **allow** passes;
**review/block** both block the flow.

Replace the **synthetic scores** in `run_local.py` with real detector outputs
before production use. Other native NeMo rails can remain enabled.

Do not use this Colang action with IORails; use its external Python wrapper.
