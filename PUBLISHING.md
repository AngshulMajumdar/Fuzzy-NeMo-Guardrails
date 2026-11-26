# Publishing the two repositories

Two separate deployable source trees are provided:

1. `Fuzzy-NeMo-Guardrails.zip`: Python package, tests, REST API, examples, Docker.
2. `Fuzzy-NeMo-HF-Space.zip`: CPU Gradio Docker Space.

Both are local release archives. Neither is an already-created online repository.

## GitHub

Unzip `Fuzzy-NeMo-Guardrails.zip`, create a new GitHub repository named
`Fuzzy-NeMo-Guardrails`, and upload or push **the extracted files at the root**.
For a terminal with authenticated GitHub CLI, from the extracted directory:

```bash
git init
git add .
git commit -m "Initial fuzzy NeMo guardrails implementation"
gh repo create Fuzzy-NeMo-Guardrails --public --source=. --remote=origin --push
```

## Hugging Face Space

Create a new Hugging Face Space `Fuzzy-NeMo-Guardrails` with **Docker SDK**
and CPU hardware. Unzip `Fuzzy-NeMo-HF-Space.zip` and upload **its extracted
files at the Space repository root**. The Dockerfile starts a Gradio server
at port 7860. Neither repository needs an API key for the fuzzy demo.

## Post-publish verification

- GitHub: check the CI job for Python 3.11 and 3.12 passes.
- HF Space: ensure the Container build succeeds and the UI shows all three sliders.
- Production NeMo: inspect the `nemo-025-integration` CI job, which installs
  `nemoguardrails==0.25.0` and runs actual regex-rail adapter checks.
- Integrate trusted detector outputs before enabling the package to make actual
  allow/block decisions. The supplied rule thresholds are example defaults.
