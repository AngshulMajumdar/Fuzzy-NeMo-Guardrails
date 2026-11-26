# Deployment

## Illustrated GitHub Pages site

The no-build site lives in `docs/index.html`, alongside eight accessible SVG
illustrations. After the files land in the repository, enable **Settings →
Pages → Deploy from a branch → main → /docs → Save**. See [PAGES.md](PAGES.md).
The Pages URL is available in GitHub settings once its first deployment finishes.

## GitHub and Python distribution

The GitHub package is a standard src-layout Python project with tests, Apache-2.0
license, examples, a CLI, CI workflow, wheel and source distribution. The project
name is `csfsm-guardrails`; imports use `csfsm_guardrails`. No published PyPI
package or existing remote repository is assumed.

```bash
pip install -e '.[api,dev]'
pytest
python -m build
gh auth login
python scripts/publish.py --github YOUR_ACCOUNT/CSFSM-Guardrails
```

`publish.py --github` creates a new **public** repository and pushes the current
source. Configure Git author identity first. It fails if creation is not allowed
or the repository already exists; it does not overwrite an unrelated repository.
To publish a wheel to PyPI later, use your normal verified release process.

## API container

```bash
docker build -t csfsm-guardrails .
docker run --rm -p 8000:8000 --env-file .env -v csfsm-data:/data csfsm-guardrails
```

Create `.env` from `.env.example` and generate independent credentials, for example
with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Never commit
the populated file. The container runs as a non-root user. Mount a local
persistent volume at `/data`; SQLite does not provide a distributed database.
The default server has no executable external tools. Supply your application
factory to register real tools; `examples/api_server.py` demonstrates the pattern.

## Hugging Face Gradio Space

The release contains `hf-space/`, ready for upload to a Gradio Space. It includes
the runtime, root `app.py`, requirements and a Space README with SDK metadata.
Alternatively regenerate it from the GitHub source:

```bash
python scripts/build_space.py --output build/hf-space
pip install huggingface_hub
hf auth login
python scripts/publish.py --space YOUR_ACCOUNT/CSFSM-Guardrails
```

Choose the free CPU hardware. No Hugging Face inference token, GPU or external
LLM service is used by the app. `hf auth login` is needed only by the publisher
with repository write permission. Space runtime dependencies pin Gradio 6.32.0;
the package test environment is recorded in `docs/VALIDATION.md`.

The Space is a public synthetic demonstration. Its verification controls are
deliberately available to the demo visitor, scoped to their Gradio session.
Do not expose those controls on an application that controls real resources.
Sessions live in process memory and reset on Space restart. If a session expires,
start a new conversation. Gradio's public demo API is separate from the keyed
FastAPI service intended for integration.

## Scope of this release

This is a reusable guardrail SDK and deployment package with an inspectable
stochastic model. It does not include a pretrained general language safety
classifier, a distributed persistence backend, production authentication for
your end users, or a validated domain-specific conditional risk envelope. Those
components can be integrated through the documented extension points.
