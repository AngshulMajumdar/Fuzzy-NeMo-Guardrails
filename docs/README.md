# Drop-in GitHub Pages docs

This folder is ready for a GitHub repository with Pages configured to deploy from the `main` branch, `/docs` directory. `index.html` is the rendered, responsive illustrated article; no Jekyll plugins or remote dependencies are required. Keep the entire folder together, including `assets/`.

## Use with Medium

- Open `medium-article.md`: it contains the full text, both project links, and image URLs pointing to the repository's `main/docs/assets/` files.
- Medium's editor does not reliably import Markdown image syntax from a pasted document. Copy the prose into Medium and upload the six PNG files from `assets/` at the corresponding positions.
- The PNGs are 1600 px wide (cover 1536 px) and require no SVG support or custom HTML. Use the image captions from the article.
- `index.md` is an additional Markdown copy with relative local image paths, suitable for README-style reuse.

## Infographics (in article order)

1. `01-cover.png` — visual overview (concept illustration)
2. `02-architecture.png` — pipeline and role of detector scores
3. `03-fuzzy-mechanics.png` — memberships and rule inference
4. `04-dual-adapter.png` — LLMRails and IORails compatibility
5. `05-fail-closed.png` — hard veto and native NeMo enforcement
6. `06-live-demo.png` — illustrative scores and three verified demo outcomes

Five diagrams also ship with matching SVG vector masters for future editing.

## Project

GitHub: https://github.com/AngshulMajumdar/Fuzzy-NeMo-Guardrails
Hugging Face: https://huggingface.co/spaces/Angshul/Fuzzy-NeMo-Guardrails

The project is an independent extension and is not affiliated with NVIDIA.
