# IORails integration

`IORails` does not execute arbitrary registered Python custom actions.
The fuzzy controller therefore wraps the official `Guardrails` facade with
`require_iorails=True`, ensuring there is **no silent legacy fallback**.

CPU-only demo with a real NeMo regex rail:

```bash
python -m pip install -e '.[nemo]'
python examples/iorails/run_local.py
```

The external fuzzy scores in this example are synthetic. Real applications
must provide scores from trusted detectors. A native NeMo block always wins.
